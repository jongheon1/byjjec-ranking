"""잡플래닛 크롤러 모듈"""
import time
import re
from typing import Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.config import (
    JOBPLANET_EMAIL,
    JOBPLANET_PASSWORD,
    JOBPLANET_RATE_LIMIT,
    MAX_RETRIES,
    RETRY_BACKOFF,
)
from src.models import JobplanetData
from src.pipeline.progress import ProgressTracker
from src.utils import normalize_company_name, is_good_match


class JobplanetCrawler:
    """잡플래닛 크롤러"""

    BASE_URL = "https://www.jobplanet.co.kr"
    LOGIN_URL = "https://www.jobplanet.co.kr/users/sign_in"
    SEARCH_URL = "https://www.jobplanet.co.kr/search?query="  # 통합 검색 URL

    def __init__(self, headless: bool = True):
        self.driver = None
        self.headless = headless
        self.logged_in = False
        self.progress = ProgressTracker("jobplanet")

    def _init_driver(self):
        """웹드라이버 초기화"""
        if self.driver:
            return

        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.implicitly_wait(5)

    def login(self) -> bool:
        """잡플래닛 로그인"""
        if not JOBPLANET_EMAIL or not JOBPLANET_PASSWORD:
            print("[에러] 잡플래닛 계정 정보가 설정되지 않았습니다.")
            print("  .env 파일에 JOBPLANET_EMAIL, JOBPLANET_PASSWORD를 설정하세요.")
            return False

        self._init_driver()

        try:
            print("잡플래닛 로그인 중...")
            self.driver.get(self.LOGIN_URL)
            time.sleep(3)

            # 이메일 입력 필드 찾기 및 클릭하여 포커스
            email_input = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "user_email"))
            )
            email_input.click()
            time.sleep(0.5)
            email_input.clear()
            email_input.send_keys(JOBPLANET_EMAIL)
            time.sleep(0.5)

            # 비밀번호 입력
            password_input = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "user_password"))
            )
            password_input.click()
            time.sleep(0.5)
            password_input.clear()
            password_input.send_keys(JOBPLANET_PASSWORD)
            time.sleep(0.5)

            # 로그인 버튼 찾기 및 클릭 (btn_sign_up 클래스)
            login_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn_sign_up"))
            )
            # 스크롤하여 버튼이 보이도록
            self.driver.execute_script("arguments[0].scrollIntoView(true);", login_btn)
            time.sleep(0.5)
            login_btn.click()

            # 로그인 성공 확인
            time.sleep(4)

            # URL 변경 확인 (로그인 성공 시 리다이렉트)
            if "sign_in" not in self.driver.current_url:
                self.logged_in = True
                print("[완료] 잡플래닛 로그인 성공")
                return True

            # 로그인 실패 메시지 확인
            try:
                error = self.driver.find_element(By.CSS_SELECTOR, ".error_message, .alert")
                if error.is_displayed():
                    print(f"[에러] 로그인 실패: {error.text}")
                    return False
            except NoSuchElementException:
                pass

            # URL이 변경되지 않았으면 실패로 간주
            print("[에러] 로그인 실패: URL이 변경되지 않음")
            return False

        except Exception as e:
            print(f"[에러] 로그인 실패: {e}")
            return False

    def get_company_by_url(self, url: str) -> Optional[JobplanetData]:
        """이미 알고 있는 URL로 회사 정보 조회"""
        if not self.driver:
            self._init_driver()

        try:
            time.sleep(JOBPLANET_RATE_LIMIT)
            self.driver.get(url)
            time.sleep(2)
            return self._extract_company_data(url)
        except Exception as e:
            print(f"  URL 직접 조회 실패: {e}")
        return None

    def search_company(self, company_name: str) -> Optional[JobplanetData]:
        """회사명으로 검색하여 정보 수집 (다양한 검색어 시도)"""
        if not self.driver:
            self._init_driver()

        normalized = normalize_company_name(company_name)
        search_variants = normalized['search_variants']

        for search_query in search_variants:
            for attempt in range(MAX_RETRIES):
                try:
                    # Rate limit
                    time.sleep(JOBPLANET_RATE_LIMIT)

                    # 검색 (기업 검색 페이지로 바로 이동)
                    search_url = f"{self.SEARCH_URL}{search_query}"
                    self.driver.get(search_url)
                    time.sleep(2)

                    # 검색 결과에서 회사 링크 찾기 (/companies/숫자 URL 패턴)
                    company_url = None
                    try:
                        # 모든 링크에서 회사 페이지 URL 찾기
                        links = self.driver.find_elements(By.TAG_NAME, "a")
                        candidates = []
                        for link in links:
                            href = link.get_attribute("href") or ""
                            text = link.text.strip() if link.text else ""
                            # /companies/숫자 패턴 (cover 등 제외)
                            if re.search(r"/companies/\d+", href) and text:
                                candidates.append((text, href))

                        if not candidates:
                            continue  # 다음 검색어 시도

                        # 회사명과 가장 유사한 결과 선택
                        for text, href in candidates:
                            if is_good_match(company_name, text):
                                company_url = href
                                break

                        # 검색어가 결과에 포함된 경우
                        if not company_url:
                            for text, href in candidates:
                                clean_text = normalize_company_name(text)['korean']
                                if search_query.lower() in clean_text.lower():
                                    company_url = href
                                    break

                        # 매칭 실패해도 검색 결과가 3개 이하면 첫 번째 사용
                        if not company_url and len(candidates) <= 3:
                            company_url = candidates[0][1]
                            print(f"    (검색 결과 {len(candidates)}개, 첫 번째 사용)")

                        if not company_url:
                            continue  # 다음 검색어 시도

                        # 회사 페이지로 이동
                        self.driver.get(company_url)
                        time.sleep(2)

                    except Exception:
                        continue

                    # 회사 정보 페이지에서 데이터 추출
                    return self._extract_company_data(company_url)

                except Exception as e:
                    print(f"  [재시도 {attempt + 1}/{MAX_RETRIES}] {search_query}: {e}")
                    time.sleep(RETRY_BACKOFF ** (attempt + 1))

        return None

    def _extract_company_data(self, company_url: str) -> Optional[JobplanetData]:
        """회사 상세 페이지에서 데이터 추출"""
        try:
            data = JobplanetData(url=self.driver.current_url)

            # 평점 추출 (.rate_point 클래스)
            try:
                rating_elem = self.driver.find_element(By.CSS_SELECTOR, ".rate_point")
                rating_text = rating_elem.text.strip()
                rating_match = re.search(r"(\d+\.?\d*)", rating_text)
                if rating_match:
                    data.rating = float(rating_match.group(1))
            except NoSuchElementException:
                pass

            # 리뷰 수 추출 (타이틀에서: "회사명 | 기업리뷰 328건, 평점")
            try:
                title = self.driver.title
                review_match = re.search(r"(\d+)건", title)
                if review_match:
                    data.reviewCount = int(review_match.group(1))
            except:
                pass

            # 주소 추출 시도
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                # 주소 패턴: "서울", "경기", "부산" 등으로 시작하는 주소
                addr_patterns = [
                    r'(서울[^\n,]{10,50})',
                    r'(경기[^\n,]{10,50})',
                    r'(부산[^\n,]{10,50})',
                    r'(인천[^\n,]{10,50})',
                    r'(대구[^\n,]{10,50})',
                    r'(대전[^\n,]{10,50})',
                    r'(광주[^\n,]{10,50})',
                    r'(울산[^\n,]{10,50})',
                    r'(세종[^\n,]{10,50})',
                    r'(강원[^\n,]{10,50})',
                    r'(충북[^\n,]{10,50})',
                    r'(충남[^\n,]{10,50})',
                    r'(전북[^\n,]{10,50})',
                    r'(전남[^\n,]{10,50})',
                    r'(경북[^\n,]{10,50})',
                    r'(경남[^\n,]{10,50})',
                    r'(제주[^\n,]{10,50})',
                ]
                for pattern in addr_patterns:
                    addr_match = re.search(pattern, page_text)
                    if addr_match:
                        addr = addr_match.group(1).strip()
                        # 주소로 보이는지 추가 검증 (구, 동, 로, 길 포함)
                        if re.search(r'(구|동|로|길|읍|면)', addr):
                            data.address = addr
                            break
            except:
                pass

            # 평균 연봉 추출 (연봉 탭으로 이동)
            try:
                # 연봉 탭 URL 찾기
                salary_url = None
                links = self.driver.find_elements(By.TAG_NAME, "a")
                for link in links:
                    href = link.get_attribute("href") or ""
                    if "/salaries" in href:
                        salary_url = href
                        break

                if salary_url:
                    self.driver.get(salary_url)
                    time.sleep(1.5)

                    # 연봉 페이지에서 평균 연봉 추출
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text
                    # "평균 연봉 6,961만" 패턴
                    salary_match = re.search(r"평균[^\d]*(\d[\d,]*)\s*만", page_text)
                    if salary_match:
                        data.avgSalary = int(salary_match.group(1).replace(",", ""))
            except:
                pass

            return data

        except Exception as e:
            print(f"  [에러] 데이터 추출 실패: {e}")
            return None

    def crawl_companies(
        self, companies: list, limit: Optional[int] = None
    ) -> dict[str, JobplanetData]:
        """여러 회사 크롤링"""
        if not self.login():
            return {}

        results = {}
        company_ids = [c.id for c in companies]
        pending = self.progress.get_pending(company_ids)

        if limit:
            pending = pending[:limit]

        total = len(pending)
        print(f"잡플래닛 크롤링 시작: {total}개 회사")

        for idx, company_id in enumerate(pending, 1):
            company = next((c for c in companies if c.id == company_id), None)
            if not company:
                continue

            print(f"[{idx}/{total}] {company.name}")

            try:
                data = None

                # 1단계: 이미 URL이 있으면 바로 사용
                existing_jp = getattr(company, 'jobplanet', None)
                if existing_jp and hasattr(existing_jp, 'url') and existing_jp.url:
                    print(f"  기존 URL 사용")
                    data = self.get_company_by_url(existing_jp.url)

                # 2단계: URL 없으면 검색
                if not data:
                    data = self.search_company(company.name)

                if data:
                    results[company_id] = data
                    self.progress.mark_completed(company_id, data.__dict__)
                    salary_str = f", 연봉: {data.avgSalary}만" if data.avgSalary else ""
                    print(f"  평점: {data.rating}, 리뷰: {data.reviewCount}{salary_str}")
                else:
                    self.progress.mark_completed(company_id, {})
                    print("  검색 결과 없음")

            except Exception as e:
                self.progress.mark_failed(company_id, str(e))
                print(f"  [에러] {e}")

        stats = self.progress.get_stats()
        print(f"\n잡플래닛 크롤링 완료: 성공 {stats['completed']}, 실패 {stats['failed']}")

        return results

    def close(self):
        """드라이버 종료"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.logged_in = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
