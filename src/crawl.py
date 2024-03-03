from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

def get_companies_ratings(company_names):
    chrome_options = Options()
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(3)
    ratings = []

    for company_name in company_names:
        driver.get(f"https://www.jobplanet.co.kr/search?query={company_name}")
        time.sleep(0.1)  # 페이지 로드 대기
        try:
            rating_element = driver.find_element(By.CSS_SELECTOR, '#mainContents > div:nth-child(1) > div > div.result_company_card > div.is_company_card > div > span.rate_ty02')
            rating = rating_element.text if rating_element else "-1"


            #만약 에러가 없다면(평점이 있다면)
            # #mainContents > div:nth-child(1) > div > div.result_company_card > div.is_company_card > div:nth-child(1) > a > b
            # 위 css 셀렉터를 클릭해서 페이지 이동
            # 그 후
            # #viewCompaniesMenu > ul > li.viewReviews > a > span
            # 위 css 셀렉터에서 리뷰 수를 가져온다.

        except Exception as e:
            rating = "-1"
            print(f"{company_name}: {e}")
        ratings.append((company_name, float(rating)))
        print(f"{company_name}: {rating}")

    
    driver.quit()
    return ratings

# # 예제 사용
# company_names = ["(주)그렙", "(주) 드라마앤컴퍼니", "(주)가온아이"]
# print(get_companies_ratings(company_names))
