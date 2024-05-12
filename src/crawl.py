from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import csv
import os

def get_last_processed_company(file_path):
    if not os.path.isfile(file_path):
        return None
    with open(file_path, 'r', encoding='utf-8') as file:
        last_line = None
        for last_line in csv.reader(file):
            pass
        if last_line:
            return last_line[0]  # Assuming the company name is in the first column
    return None

def read_results_from_file(file_path):
    results_list = []
    with open(file_path, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        for row in reader:
            results_list.append(row)
    return results_list


def get_companies_ratings(company_names):

    chrome_options = Options()
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(3)

    results_filename = 'company_ratings.csv'
    last_processed_company = get_last_processed_company(results_filename)
    start_processing = True if last_processed_company is None else False

    with open(results_filename, 'a', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)

        for company_name in company_names:
            if not start_processing:
                if company_name == last_processed_company:
                    start_processing = True
                continue

            search_name = company_name.replace("주식회사", "").strip()
            driver.get(f"https://www.jobplanet.co.kr/search?query={search_name}")
            time.sleep(0.1)
            try:
                rating_element = driver.find_element(By.CSS_SELECTOR, '#mainContents > div:nth-child(1) > div > div.result_company_card > div.is_company_card > div > span.rate_ty02')
                rating = rating_element.text if rating_element else "-1"
                company_link_element = driver.find_element(By.CSS_SELECTOR, '#mainContents > div:nth-child(1) > div > div.result_company_card > div.is_company_card > div:nth-child(1) > a')
                if company_link_element:
                    company_link_element.click()
                    time.sleep(0.1)
                    review_count_element = driver.find_element(By.CSS_SELECTOR, '#viewCompaniesMenu > ul > li.viewReviews > a > span')
                    review_count = review_count_element.text if review_count_element else "0"

                    hiring_count_element = driver.find_element(By.CSS_SELECTOR, '#viewCompaniesMenu > ul > li.companyJob > a > span')
                    hiring_count = hiring_count_element.text if hiring_count_element else "0"
                else:
                    review_count = "0"
                    hiring_count = "0"

            except Exception as e:
                rating = "-1"
                review_count = "0"
                hiring_count = "0"
                print(f"{company_name}: {e}")

            writer.writerow([company_name, rating, review_count, hiring_count])
            print(f"{company_name}: {rating}, Reviews: {review_count}, Hiring: {hiring_count}")

    driver.quit()

    
    return read_results_from_file(results_filename)

# # 예제 사용
# company_names = ["(주)그렙", "(주)드라마앤컴퍼니", "(주)가온아이"]
# print(get_companies_ratings(company_names))
