from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from dotenv import load_dotenv
import os
import time

load_dotenv()

class JobPlanetCrawler:
    def __init__(self, headless=True):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(3)  # 기본 대기 시간을 3초로 단축
        self.wait = WebDriverWait(self.driver, 5)  # 명시적 대기 시간을 5초로 단축
        self.short_wait = WebDriverWait(self.driver, 0.1)  # 짧은 대기용

    def close(self):
        self.driver.quit()

    def login(self):
        try:
            self.driver.get("https://www.jobplanet.co.kr/users/sign_in?_nav=gb")
            
            email_input = self.wait.until(EC.presence_of_element_located((By.ID, "user_email")))
            password_input = self.wait.until(EC.presence_of_element_located((By.ID, "user_password")))
            
            email_input.send_keys(os.getenv('JOBPLANET_EMAIL'))
            password_input.send_keys(os.getenv('JOBPLANET_PASSWORD'))
            
            login_button = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn_sign_up")))
            login_button.click()
            
            
            # 로그인 실패 시 나타나는 에러 메시지 확인
            try:
                error_element = self.driver.find_element(By.CSS_SELECTOR, "div.flash_ty1.flash-on")
                print(f"로그인 실패: {error_element.text}")
                return False
            except:
                # 에러 메시지가 없으면 성공으로 간주
                pass
            
            # 현재 URL 확인
            current_url = self.driver.current_url
            print(f"로그인 후 현재 URL: {current_url}")
            
            # 로그인 성공 시 URL이 변경되거나 특정 요소가 나타나는지 확인
            if "sign_in" not in current_url:
                print("로그인 성공!")
                return True
            else:
                print("로그인 실패: 로그인 페이지에서 벗어나지 못했습니다.")
                return False
                
        except Exception as e:
            print(f"로그인 실패: {e}")
            return False

    def search_company(self, company_name):
        try:
            # '(주)'나 '주식회사' 같은 단어는 검색의 정확도를 떨어뜨릴 수 있어 제거합니다.
            search_name = company_name.replace("(주)", "").replace("주식회사", "").strip()
            self.driver.get(f"https://www.jobplanet.co.kr/search?query={search_name}")
            
            # 검색 결과 영역에서 회사 상세 페이지로 가는 첫 번째 링크 요소를 찾습니다.
            company_link_element = self.short_wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#contentsWrap ul a[href*='/companies/']"))
            )

            # 클릭하는 대신, href 속성 값을 직접 추출하여 URL을 반환합니다.
            # 이 방식이 더 빠르고 안정적입니다.
            company_url = company_link_element.get_attribute('href')
            return company_url
            
        except Exception as e:
            print(f"'{company_name}' 회사 검색 실패 또는 페이지 이동 실패")
            return None

    def get_company_details(self, company_url):
        # 연봉 페이지와 채용 페이지만 방문하여 필요한 정보를 수집합니다.
        details = {
            "rating": "-1", 
            "review_count": "0", 
            "salary": "0", 
            "hiring_count": "0",
            "backend_position": False,
            "address": ""
        }
        
        if not company_url:
            return details

        base_url = company_url.rstrip('/')

        # 1. 연봉 페이지에서 평점, 리뷰 수, 연봉 정보 가져오기
        try:
            salaries_url = f"{base_url}/salaries"
            self.driver.get(salaries_url)
            
            # 평점 정보 (companies-info__score 클래스 사용)
            try:
                rating_element = self.short_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".companies-info__score")))
                details["rating"] = rating_element.text.strip()
                print(f"평점 정보 수집 성공: {details['rating']}")
            except:
                # 대안 selector들
                for selector in [".score", "[class*='score']", ".rating"]:
                    try:
                        rating_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        details["rating"] = rating_element.text.strip()
                        print(f"평점 정보 수집 성공 (대안): {details['rating']}")
                        break
                    except:
                        continue

            # 리뷰 수 정보 (메뉴에서 리뷰 탭의 숫자)
            try:
                review_element = self.short_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".viewReviews a span")))
                review_text = review_element.text.strip()
                import re
                numbers = re.findall(r'\d+', review_text)
                if numbers:
                    details["review_count"] = numbers[0]
                    print(f"리뷰 수 정보 수집 성공: {details['review_count']}")
            except:
                # 대안 selector들
                for selector in ["a[href*='reviews'] span", ".review span", "[class*='review'] span"]:
                    try:
                        review_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        review_text = review_element.text.strip()
                        import re
                        numbers = re.findall(r'\d+', review_text)
                        if numbers:
                            details["review_count"] = numbers[0]
                            print(f"리뷰 수 정보 수집 성공 (대안): {details['review_count']}")
                            break
                    except:
                        continue

            # 연봉 정보 (메인 연봉 수치)
            try:
                # 먼저 연봉 작성 개수 확인
                salaries_num_element = self.short_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#salariesNum")))
                salaries_num_text = salaries_num_element.text.strip()
                import re
                numbers = re.findall(r'\d+', salaries_num_text)
                
                if numbers and int(numbers[0]) > 0:
                    # 연봉 작성 개수가 0보다 크면 실제 연봉 정보 수집
                    try:
                        salary_element = self.short_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".chart_header .num em")))
                        details["salary"] = salary_element.text.strip()
                        print(f"연봉 정보 수집 성공: {details['salary']}")
                    except:
                        # 대안 selector들
                        for selector in ["em", ".num em", ".salary em", "[class*='num'] em", ".amount"]:
                            try:
                                salary_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                                salary_text = salary_element.text.strip()
                                if salary_text and "만원" in salary_text:
                                    details["salary"] = salary_text
                                    print(f"연봉 정보 수집 성공 (대안): {details['salary']}")
                                    break
                            except:
                                continue
                else:
                    print("연봉 작성 개수가 0개이므로 연봉 정보를 수집하지 않습니다.")
                    
            except:
                print("연봉 작성 개수를 확인할 수 없습니다.")

        except Exception as e:
            print(f"연봉 페이지 정보 수집 실패: {e}")

        # 2. 채용 공고 페이지에서 채용 수와 백엔드 포지션 확인
        try:
            job_postings_url = f"{base_url}/job_postings"
            self.driver.get(job_postings_url)
            
            # 채용 공고 수 정보
            try:
                hiring_element = self.short_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".companyJob a span")))
                hiring_text = hiring_element.text.strip()
                import re
                numbers = re.findall(r'\d+', hiring_text)
                if numbers:
                    details["hiring_count"] = numbers[0]
                    print(f"채용 공고 수 정보 수집 성공: {details['hiring_count']}")
            except:
                # 대안 selector들
                for selector in ["a[href*='job'] span", ".job span", "[class*='job'] span"]:
                    try:
                        hiring_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        hiring_text = hiring_element.text.strip()
                        import re
                        numbers = re.findall(r'\d+', hiring_text)
                        if numbers:
                            details["hiring_count"] = numbers[0]
                            print(f"채용 공고 수 정보 수집 성공 (대안): {details['hiring_count']}")
                            break
                    except:
                        continue

            # 백엔드 관련 포지션 찾기 (채용 공고가 있을 때만)
            if details["hiring_count"] != "0":
                try:
                    # 채용 공고 목록에서 직종명들 확인 (짧은 타임아웃)
                    job_titles = self.driver.find_elements(By.CSS_SELECTOR, "#contents h2, .job-title, [class*='title'] h2")
                    
                    backend_keywords = ['백엔드', 'backend', 'server', '서버', 'api', 'java', 'python', 'spring', 'node', 'developer', '개발자', 'engineer', '엔지니어']
                    
                    for title_element in job_titles[:5]:  # 최대 5개만 확인하여 속도 향상
                        try:
                            title_text = title_element.text.lower()
                            if any(keyword in title_text for keyword in backend_keywords):
                                details["backend_position"] = True
                                print(f"백엔드 관련 포지션 발견: {title_element.text}")
                                break
                        except:
                            continue
                            
                except Exception as e:
                    print(f"백엔드 포지션 확인 실패: {e}")

        except Exception as e:
            print(f"채용 공고 페이지 정보 수집 실패: {e}")
            
        # 3. 주소 정보 수집
        try:
            landing_url = f"{base_url}/landing"
            self.driver.get(landing_url)
            
            address_selector = "#profile > div > ul > li:nth-child(3) > div > span"
            address_element = self.short_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, address_selector)))
            
            raw_address = address_element.text.strip()
            if ',' in raw_address:
                address = raw_address.split(',')[0].strip()
            else:
                address = raw_address
            details['address'] = address
            print(f"주소 정보 수집 성공: {details['address']}")
        except Exception as e:
            print(f"주소 정보 수집 실패: {e}")
        
        return details 