from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import csv
from dotenv import load_dotenv
import os

load_dotenv()

def login_jobplanet(driver):
    try:
        # 로그인 페이지로 이동
        driver.get("https://www.jobplanet.co.kr/users/sign_in?_nav=gb")
        wait = WebDriverWait(driver, 10)
        
        # 로그인 정보 입력
        email = wait.until(EC.presence_of_element_located((By.ID, "user_email")))
        password = wait.until(EC.presence_of_element_located((By.ID, "user_password")))
        
        email.send_keys(os.getenv('JOBPLANET_EMAIL'))
        password.send_keys(os.getenv('JOBPLANET_PASSWORD'))
        
        # 로그인 버튼 클릭
        login_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn_sign_up")))
        login_button.click()
                
        try:
            error_message = driver.find_element(By.CSS_SELECTOR, "div.flash_ty1.flash-on")
            print("로그인 실패: 에러 메시지 발견")
            return False
        except:
            # 에러 메시지가 없으면 로그인 성공
            print("로그인 성공!")
            return True
        
    except Exception as e:
        print(f"로그인 실패: {e}")
        return False


def get_last_processed_company(csv_path):
    if not os.path.isfile(csv_path):
        return None
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            rows = list(csv.reader(file))
            return rows[-1][0] if rows else None
    except Exception as e:
        print(f"파일 읽기 오류: {e}")
        return None

def read_results_from_file(csv_path):
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            return list(csv.reader(file))
    except Exception as e:
        print(f"파일 읽기 오류: {e}")
        return []


def get_companies_ratings(company_names):
    chrome_options = Options()
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(3)

    if not login_jobplanet(driver):
        driver.quit()
        return []
    
    result_path = 'data/company_ratings.csv'
    last_company = get_last_processed_company(result_path)
    start_index = (company_names.index(last_company) + 1) if last_company in company_names else 0
    company_names = company_names[start_index:]

    with open(result_path, 'a', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)

        for company_name in company_names:            
            try:
                search_name = company_name.replace("주식회사", "").strip()
                driver.get(f"https://www.jobplanet.co.kr/search?query={search_name}")
                time.sleep(1)

                try:
                    company_link_element = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, r'body > div.body_wrap > main > div > div > div > div:nth-child(1) > div:nth-child(2) > ul > a:nth-child(1)'))
                    )
                except:
                    print(f"{company_name}: 회사 링크 없음")
                    continue

                company_url = company_link_element.get_attribute('href')
                company_id = company_url.split('/')[-1]
                
                driver.execute_script(f"window.location.href='{company_url}'")
                time.sleep(1)

                # 평점 수집
                try:
                    rating_element = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, r'#premiumReviewStatistics > div > div.relative > div.relative > div.flex > div.w-\[287px\] > div.rate_star_top > span'))
                    )
                    rating = rating_element.text
                except:
                    rating = "-1"
                
                # 리뷰 수 수집
                try:
                    review_count_element = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, r'#viewReviewsTitle > span'))
                    )
                    review_count = review_count_element.text
                except:
                    review_count = "0"
                
                # 연봉 정보 수집
                salary_url = f"/companies/{company_id}/salaries"
                driver.execute_script(f"window.location.href='{salary_url}'")
                time.sleep(1)
                try:
                    salary_element = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '#mainContents > div.jpcont_wrap.salary_wrap.overflow > div:nth-child(2) > div.salary_chart_wrap > div.chart_header > div:nth-child(1) > div.num > em'))
                    )
                    salary = salary_element.text
                except:
                    salary = "0"
                
                # 채용 정보 수집
                job_url = f"/companies/{company_id}/job_postings"
                driver.execute_script(f"window.location.href='{job_url}'")
                time.sleep(1)

                try:
                    hiring_count_element = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, r'#viewCompaniesMenu > ul > li.companyJob > a > span'))
                    )
                    hiring_count = hiring_count_element.text
                except:
                    hiring_count = "0"
                
                # 백엔드 포지션 찾기
                backend_position = None
                backend_keywords = ['백엔드', 'Backend', 'backend', 'software', 'java', '웹', 'web']
                for i in range(1, int(hiring_count) + 1):
                        selector = f'#contents > div:nth-child(1) > div > div:nth-child({i}) > a > div > h2'
                        position = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        ).text
                        if any(keyword in position for keyword in backend_keywords):
                            backend_position = position
                            break
                        
            except Exception as e:
                rating = "-1"
                review_count = "0"
                hiring_count = "0"
                salary = "0"
                backend_position = None
                print(f"{company_name}: {e}")

            writer.writerow([company_name, rating, review_count, hiring_count, salary, backend_position])
            print(f"{company_name}: {rating}, Reviews: {review_count}, Hiring: {hiring_count}, Salary: {salary}, Backend Position: {backend_position}")

    driver.quit()
    return read_results_from_file(result_path)