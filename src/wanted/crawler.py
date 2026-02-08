"""원티드 크롤러 모듈"""
import time
import re
import requests
from typing import Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.config import WANTED_RATE_LIMIT, MAX_RETRIES, RETRY_BACKOFF
from src.models import WantedData, WantedJob
from src.pipeline.progress import ProgressTracker
from src.utils import normalize_company_name, is_good_match


class WantedCrawler:
    """원티드 크롤러"""

    BASE_URL = "https://www.wanted.co.kr"
    SEARCH_API = "https://www.wanted.co.kr/api/v4/search"
    COMPANY_API = "https://www.wanted.co.kr/api/v4/companies"

    def __init__(self, headless: bool = True):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            }
        )
        self.driver = None
        self.headless = headless
        self.progress = ProgressTracker("wanted")

    def _init_driver(self):
        """Selenium 드라이버 초기화 (API 실패시 백업)"""
        if self.driver:
            return

        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.implicitly_wait(5)

    def search_company_api(self, company_name: str) -> Optional[dict]:
        """API로 회사 검색 (다양한 검색어 시도)"""
        normalized = normalize_company_name(company_name)
        search_variants = normalized['search_variants']

        for search_query in search_variants:
            try:
                params = {"query": search_query, "country": "kr"}
                response = self.session.get(
                    self.SEARCH_API, params=params, timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    companies = data.get("data", {}).get("companies", [])
                    if companies:
                        # 회사명과 가장 유사한 결과 선택
                        for company in companies:
                            result_name = company.get("name", "")
                            if is_good_match(company_name, result_name):
                                return company
                        # 검색어와 정확히 일치하는 경우
                        for company in companies:
                            result_name = company.get("name", "")
                            if search_query.lower() in result_name.lower():
                                return company
                        # 매칭 실패해도 검색 결과가 3개 이하면 첫 번째 사용
                        if len(companies) <= 3:
                            print(f"    (검색 결과 {len(companies)}개, 첫 번째 사용)")
                            return companies[0]
            except Exception as e:
                print(f"  API 검색 실패 ({search_query}): {e}")

        return None

    def get_company_by_url(self, url: str) -> Optional[WantedData]:
        """이미 알고 있는 URL로 회사 정보 조회"""
        try:
            # URL에서 company_id 추출
            match = re.search(r'/company/(\d+)', url)
            if match:
                company_id = int(match.group(1))
                return self.get_company_detail_api(company_id)
        except Exception as e:
            print(f"  URL 직접 조회 실패: {e}")
        return None

    def get_company_detail_api(self, company_id: int, search_data: dict = None) -> Optional[WantedData]:
        """API로 회사 상세 정보 조회"""
        try:
            # 회사 정보 조회
            response = self.session.get(
                f"{self.COMPANY_API}/{company_id}", timeout=10
            )

            if response.status_code == 200:
                data = response.json().get("company", {})

                # 채용공고 목록 조회
                jobs = []
                try:
                    jobs_response = self.session.get(
                        f"{self.COMPANY_API}/{company_id}/jobs", timeout=10
                    )
                    if jobs_response.status_code == 200:
                        jobs_data = jobs_response.json().get("data", [])
                        if jobs_data:
                            jobs = [
                                {
                                    "title": j.get("position", ""),
                                    "url": f"{self.BASE_URL}/wd/{j.get('id')}"
                                }
                                for j in jobs_data[:5]  # 최대 5개
                            ]
                except:
                    pass

                return self._parse_api_response(data, search_data, jobs)
        except Exception as e:
            print(f"  API 상세 조회 실패: {e}")

        return None

    def _parse_api_response(self, data: dict, search_data: dict = None, jobs: list = None) -> WantedData:
        """API 응답 파싱"""
        company_id = data.get("id")

        # 채용공고 수는 실제 jobs 목록에서 가져오거나, confirmed_position_count 사용
        job_count = len(jobs) if jobs else data.get("confirmed_position_count", 0)

        # 주소 추출
        address = None
        company_address = data.get("company_address", {})
        if company_address:
            address = company_address.get("full_location")

        # 직원수 추출 (태그에서)
        employees = None
        tags = data.get("company_tags", [])
        for tag in tags:
            title = tag.get("title", "")
            if "명" in title:
                employees = title
                break

        # 검색 결과에서 설립년도 가져오기 (상세 API에도 있음)
        founded_year = data.get("founded_year")
        if not founded_year and search_data:
            founded_year = search_data.get("founded_year")

        return WantedData(
            isHiring=job_count > 0,
            jobCount=job_count,
            jobs=jobs or [],
            address=address,
            foundedYear=founded_year,
            employees=employees,
            url=f"{self.BASE_URL}/company/{company_id}" if company_id else None,
        )

    def search_company_selenium(self, company_name: str) -> Optional[WantedData]:
        """Selenium으로 회사 검색 (API 백업)"""
        self._init_driver()

        normalized = normalize_company_name(company_name)
        search_variants = normalized['search_variants']

        for search_query in search_variants:
            try:
                # URL 인코딩
                from urllib.parse import quote
                encoded_query = quote(search_query)
                search_url = f"{self.BASE_URL}/search?query={encoded_query}&tab=company"
                self.driver.get(search_url)
                time.sleep(3)

                # 회사 검색 결과 찾기
                try:
                    # 회사 카드 목록 찾기
                    company_cards = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_all_elements_located(
                            (By.CSS_SELECTOR, "a[href*='/company/']")
                        )
                    )

                    # 회사명 매칭
                    for card in company_cards:
                        card_text = card.text.strip()
                        href = card.get_attribute("href") or ""

                        if "/company/" in href and card_text:
                            if is_good_match(company_name, card_text):
                                card.click()
                                time.sleep(2)
                                return self._extract_selenium_data(href)

                    # 매칭 실패시 첫 번째 회사 카드 시도
                    for card in company_cards:
                        href = card.get_attribute("href") or ""
                        if "/company/" in href and card.text.strip():
                            card.click()
                            time.sleep(2)
                            return self._extract_selenium_data(href)

                except TimeoutException:
                    continue  # 다음 검색어 시도

            except Exception as e:
                print(f"  Selenium 검색 실패 ({search_query}): {e}")
                continue

        return None

    def _extract_selenium_data(self, company_url: str) -> WantedData:
        """Selenium으로 회사 정보 추출"""
        data = WantedData(url=company_url)

        try:
            page_text = self.driver.find_element(By.TAG_NAME, "body").text

            # 채용공고 수 (페이지 텍스트에서)
            job_match = re.search(r'채용.*?(\d+)', page_text)
            if job_match:
                data.jobCount = int(job_match.group(1))
                data.isHiring = data.jobCount > 0

            # 주소 추출 (페이지 텍스트에서)
            addr_patterns = [
                r'(서울[시특별시]*\s*[가-힣]+구[가-힣\s\d\-,]+)',
                r'(경기[도]*\s*[가-힣]+[시군구][가-힣\s\d\-,]+)',
                r'(부산[광역시]*\s*[가-힣]+구[가-힣\s\d\-,]+)',
                r'(인천[광역시]*\s*[가-힣]+구[가-힣\s\d\-,]+)',
                r'(대구[광역시]*\s*[가-힣]+구[가-힣\s\d\-,]+)',
                r'(대전[광역시]*\s*[가-힣]+구[가-힣\s\d\-,]+)',
                r'(광주[광역시]*\s*[가-힣]+구[가-힣\s\d\-,]+)',
                r'(울산[광역시]*\s*[가-힣]+구[가-힣\s\d\-,]+)',
                r'(세종[특별자치시]*\s*[가-힣\s\d\-,]+)',
            ]
            for pattern in addr_patterns:
                addr_match = re.search(pattern, page_text)
                if addr_match:
                    addr = addr_match.group(1).strip()
                    # 너무 짧거나 긴 주소 제외
                    if 10 < len(addr) < 100:
                        data.address = addr
                        break

            # 설립년도
            year_match = re.search(r'설립[^\d]*(\d{4})', page_text)
            if year_match:
                data.foundedYear = int(year_match.group(1))

            # 직원수
            emp_match = re.search(r'(\d+)\s*명', page_text)
            if emp_match:
                data.employees = emp_match.group(1) + "명"

            # 채용공고 목록
            try:
                job_links = self.driver.find_elements(
                    By.CSS_SELECTOR, "a[href*='/wd/']"
                )[:5]
                for link in job_links:
                    title = link.text.strip()
                    url = link.get_attribute("href")
                    if title and url and len(title) > 3:
                        data.jobs.append({"title": title, "url": url})
            except:
                pass

        except Exception as e:
            print(f"  데이터 추출 실패: {e}")

        return data

    def search_company(self, company_name: str) -> Optional[WantedData]:
        """회사 검색 (API 우선, 실패시 Selenium)"""
        # 1. API 시도
        company_data = self.search_company_api(company_name)
        if company_data:
            company_id = company_data.get("id")
            if company_id:
                detail = self.get_company_detail_api(company_id, company_data)
                if detail:
                    return detail

        # 2. Selenium 백업
        return self.search_company_selenium(company_name)

    def crawl_companies(
        self, companies: list, limit: Optional[int] = None
    ) -> dict[str, WantedData]:
        """여러 회사 크롤링"""
        results = {}
        company_ids = [c.id for c in companies]
        pending = self.progress.get_pending(company_ids)

        if limit:
            pending = pending[:limit]

        total = len(pending)
        print(f"원티드 크롤링 시작: {total}개 회사")

        for idx, company_id in enumerate(pending, 1):
            company = next((c for c in companies if c.id == company_id), None)
            if not company:
                continue

            print(f"[{idx}/{total}] {company.name}")

            for attempt in range(MAX_RETRIES):
                try:
                    time.sleep(WANTED_RATE_LIMIT)

                    data = None

                    # 1단계: 이미 URL이 있으면 바로 사용
                    existing_url = getattr(company, 'wanted', None)
                    if existing_url and hasattr(existing_url, 'url') and existing_url.url:
                        print(f"  기존 URL 사용: {existing_url.url}")
                        data = self.get_company_by_url(existing_url.url)

                    # 2단계: URL 없으면 검색
                    if not data:
                        data = self.search_company(company.name)

                    if data:
                        results[company_id] = data
                        self.progress.mark_completed(company_id, data.__dict__)
                        print(f"  채용: {data.jobCount}건, 채용중: {data.isHiring}")
                    else:
                        self.progress.mark_completed(company_id, {})
                        print("  검색 결과 없음")
                    break

                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        print(f"  [재시도 {attempt + 1}/{MAX_RETRIES}] {e}")
                        time.sleep(RETRY_BACKOFF ** (attempt + 1))
                    else:
                        self.progress.mark_failed(company_id, str(e))
                        print(f"  [에러] {e}")

        stats = self.progress.get_stats()
        print(f"\n원티드 크롤링 완료: 성공 {stats['completed']}, 실패 {stats['failed']}")

        return results

    def close(self):
        """드라이버 종료"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
