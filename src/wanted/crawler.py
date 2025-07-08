from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import re

class WantedCrawler:
    def __init__(self, headless=True):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(3)
        self.wait = WebDriverWait(self.driver, 5)
        self.short_wait = WebDriverWait(self.driver, 0.1)

    def close(self):
        self.driver.quit()

    def search_company(self, company_name):
        try:
            # '(주)'나 '주식회사' 같은 단어는 검색의 정확도를 떨어뜨릴 수 있어 제거합니다.
            search_name = company_name.replace("(주)", "").replace("주식회사", "").strip()
            search_url = f"https://www.wanted.co.kr/search?query={search_name}"
            self.driver.get(search_url)
            
            # 검색 결과에서 회사 링크 찾기
            company_link_element = self.short_wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".SearchCompanyContainer_companyListContainer__Oll5Q a"))
            )

            # href 속성에서 상대 URL 추출하고 절대 URL로 변환
            relative_url = company_link_element.get_attribute('href')
            if relative_url.startswith('/'):
                company_url = f"https://www.wanted.co.kr{relative_url}"
            else:
                company_url = relative_url
            
            return company_url
            
        except Exception as e:
            print(f"'{company_name}' 원티드 검색 실패")
            return None

    def get_company_details(self, company_url):
        # 원티드에서 회사 상세 정보를 수집합니다.
        details = {
            "hiring_count": "0",
            "backend_position": False,
            "founded_year": "",
            "revenue": "",
            "salary": "",
            "total_employees": "",
            "resignees": "",
            "new_hires": ""
        }
        
        if not company_url:
            return details

        try:
            self.driver.get(company_url)
            
            # 1. 채용 공고 수와 백엔드 포지션 확인
            try:
                job_links = self.driver.find_elements(By.CSS_SELECTOR, "section ul li a[href*='/wd/']")
                details["hiring_count"] = str(len(job_links))
                print(f"채용 공고 수: {details['hiring_count']}")
                
                # 백엔드 관련 포지션 찾기
                backend_keywords = ['백엔드', 'backend', 'server', '서버', 'api', 'java', 'python', 'spring', 'node', 'developer', '개발자', 'engineer', '엔지니어']
                
                for job_link in job_links[:5]:  # 최대 5개만 확인
                    try:
                        job_title = job_link.text.lower()
                        if any(keyword in job_title for keyword in backend_keywords):
                            details["backend_position"] = True
                            print(f"백엔드 관련 포지션 발견: {job_link.text}")
                            break
                    except:
                        continue
                        
            except Exception as e:
                print(f"채용 공고 정보 수집 실패")

            # 2. 설립 년도
            try:
                founded_element = self.short_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "time")))
                details["founded_year"] = founded_element.text.strip()
                print(f"설립 년도: {details['founded_year']}")
            except:
                print("설립 년도 수집 실패")

            # 3. 매출액 (줄바꿈 제거)
            try:
                # 매출 텍스트가 포함된 섹션의 차트 데이터 찾기
                revenue_element = self.short_wait.until(EC.presence_of_element_located((By.XPATH, "//span[contains(text(), '매출')]/ancestor::section//div[contains(@class, 'ChartSummary_wrapper')]//div[contains(@class, 'wds-u1e2rb')]")))
                raw_text = revenue_element.text
                # 공백, 줄바꿈 제거
                clean_text = re.sub(r'\s+', ' ', raw_text).strip()
                details["revenue"] = clean_text
                print(f"매출액: {details['revenue']}")
            except:
                print("매출액 수집 실패")

            # 4. 평균 연봉 ('만원' 제거)
            try:
                salary_element = self.short_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div dl:nth-child(6) dd")))
                raw_text = salary_element.text.strip()
                # '만원' 제거
                clean_text = raw_text.replace('만원', '').strip()
                details["salary"] = clean_text
                print(f"평균 연봉: {details['salary']}")
            except:
                print("평균 연봉 수집 실패")

            # 5. 총 인원 (공백 및 줄바꿈 제거, 숫자만 추출)
            try:
                employees_element = self.short_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div dl:nth-child(10) dd")))
                raw_text = employees_element.text
                # 공백, 줄바꿈 제거하고 숫자만 추출
                clean_text = re.sub(r'\s+', '', raw_text)
                numbers = re.findall(r'\d+', clean_text)
                if numbers:
                    details["total_employees"] = numbers[0]
                    print(f"총 인원: {details['total_employees']}")
            except:
                print("총 인원 수집 실패")

            # 6. 퇴사자 (공백 및 줄바꿈 제거, 숫자만 추출)
            try:
                resignees_element = self.short_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div dl:nth-child(13) dd div:nth-child(1)")))
                raw_text = resignees_element.text
                # 공백, 줄바꿈 제거하고 숫자만 추출
                clean_text = re.sub(r'\s+', '', raw_text)
                numbers = re.findall(r'\d+', clean_text)
                if numbers:
                    details["resignees"] = numbers[0]
                    print(f"퇴사자: {details['resignees']}")
            except:
                print("퇴사자 수집 실패")

            # 7. 입사자 (공백 및 줄바꿈 제거, 숫자만 추출)
            try:
                new_hires_element = self.short_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div dl:nth-child(13) dd div:nth-child(3)")))
                raw_text = new_hires_element.text
                # 공백, 줄바꿈 제거하고 숫자만 추출
                clean_text = re.sub(r'\s+', '', raw_text)
                numbers = re.findall(r'\d+', clean_text)
                if numbers:
                    details["new_hires"] = numbers[0]
                    print(f"입사자: {details['new_hires']}")
            except:
                print("입사자 수집 실패")

        except Exception as e:
            print(f"원티드 회사 정보 수집 실패: {e}")
        
        return details 