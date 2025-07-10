import os
import pandas as pd
import json
import numpy as np
from src.download import download_data
from src.jobplanet.crawler import JobPlanetCrawler
from src.wanted.crawler import WantedCrawler
from src.utils import get_company_list, create_csv_if_not_exists, update_company_data, get_processed_companies
from src.geocoding import GeocodingService

def crawl_companies():
    """회사 정보 크롤링"""
    crawled_result_file = "data/company_info.csv"
    by_data_file = "data/by_data.xls"
    
    company_names = get_company_list(by_data_file)
    create_csv_if_not_exists(crawled_result_file)
    
    processed = get_processed_companies(crawled_result_file)
    remaining = [name for name in company_names if name not in processed]
    
    print(f"총 {len(company_names)}개 | 완료 {len(processed)}개 | 남음 {len(remaining)}개")
    
    if not remaining:
        return
    
    # 크롤러 초기화
    jp_crawler = JobPlanetCrawler(headless=False)
    wanted_crawler = WantedCrawler(headless=False)
    
    if not jp_crawler.login():
        print("잡플래닛 로그인 실패")
        jp_crawler.close()
        wanted_crawler.close()
        return
    
    # 크롤링 실행
    for i, company_name in enumerate(remaining, 1):
        print(f"\n[{i}/{len(remaining)}] {company_name}")
        
        # 잡플래닛 크롤링
        jp_data = {}
        if url := jp_crawler.search_company(company_name):
            if details := jp_crawler.get_company_details(url):
                jp_data = {
                    'rating': details.get('rating', '-1'),
                    'review_count': details.get('review_count', '0'),
                    'salary_jobplanet': details.get('salary', '0'),
                    'hiring_count_jobplanet': details.get('hiring_count', '0'),
                    'backend_position_jobplanet': details.get('backend_position', False),
                    'address': details.get('address', '')
                }
        
        # 원티드 크롤링
        wanted_data = {}
        if url := wanted_crawler.search_company(company_name):
            if details := wanted_crawler.get_company_details(url):
                wanted_data = {
                    'hiring_count_wanted': details.get('hiring_count', '0'),
                    'backend_position_wanted': details.get('backend_position', False),
                    'founded_year': details.get('founded_year', ''),
                    'revenue': details.get('revenue', ''),
                    'salary_wanted': details.get('salary', ''),
                    'total_employees': details.get('total_employees', ''),
                    'resignees': details.get('resignees', ''),
                    'new_hires': details.get('new_hires', '')
                }
        
        # 데이터 병합 및 저장
        combined = {**jp_data, **wanted_data}
        combined['backend_position'] = combined.get('backend_position_jobplanet', False) or combined.get('backend_position_wanted', False)
        update_company_data(crawled_result_file, company_name, combined)
    
    jp_crawler.close()
    wanted_crawler.close()

def merge_with_excel_data():
    """크롤링 데이터와 엑셀 데이터 병합"""
    crawled = pd.read_csv("data/company_info.csv")
    excel = pd.read_excel("data/by_data.xls", header=0)
    
    excel_selected = excel[['업체명', '선정년도', '보충역 복무인원']].rename(columns={'업체명': 'company_name'})
    merged = pd.merge(crawled, excel_selected, on='company_name', how='left')
    
    merged.to_csv("data/final_company_data.csv", index=False, encoding='utf-8-sig')
    return merged

def add_coordinates(df):
    """주소를 좌표로 변환"""
    geocoding = GeocodingService()
    df_with_coords = geocoding.process_dataframe(df)
    
    df_with_coords.to_csv("data/final_company_data_with_coords.csv", index=False, encoding='utf-8-sig')
    
    total = len(df_with_coords)
    success = df_with_coords[df_with_coords['x'].notna()].shape[0]
    print(f"\n좌표 변환: {success}/{total} 성공")
    
    return df_with_coords

def save_as_json(df):
    """JSON 파일로 저장"""
    df = df.replace({np.nan: None})
    
    companies = []
    for _, row in df.iterrows():
        company = {
            "company_name": row['company_name'],
            "rating": row['rating'] if row['rating'] != -1.0 else None,
            "review_count": int(row['review_count']) if pd.notna(row['review_count']) else 0,
            "salary_jobplanet": row['salary_jobplanet'] if pd.notna(row['salary_jobplanet']) else None,
            "salary_wanted": row['salary_wanted'] if pd.notna(row['salary_wanted']) else None,
            "hiring_count_jobplanet": int(row['hiring_count_jobplanet']) if pd.notna(row['hiring_count_jobplanet']) else 0,
            "hiring_count_wanted": int(row['hiring_count_wanted']) if pd.notna(row['hiring_count_wanted']) else 0,
            "backend_position": bool(row['backend_position']) if pd.notna(row['backend_position']) else False,
            "address": row['address'] if pd.notna(row['address']) else None,
            "selection_year": int(row['선정년도']) if pd.notna(row['선정년도']) else None,
            "coordinates": {
                "x": float(row['x']),
                "y": float(row['y'])
            } if pd.notna(row['x']) and pd.notna(row['y']) else None
        }
        companies.append(company)
    
    with open("data/final_company_data.json", 'w', encoding='utf-8') as f:
        json.dump({"total_count": len(companies), "companies": companies}, f, ensure_ascii=False, indent=2)

def main():
    # 디렉토리 생성
    os.makedirs('data', exist_ok=True)
    
    # 1. 데이터 다운로드
    print("1. 병역지정업체 목록 다운로드")
    download_data("data/by_data.xls")
    
    # 2. 크롤링
    print("\n2. 회사 정보 크롤링")
    crawl_companies()
    
    # 3. 데이터 병합
    print("\n3. 데이터 병합")
    merged_df = merge_with_excel_data()
    
    # 4. 좌표 변환
    print("\n4. 주소 → 좌표 변환")
    final_df = add_coordinates(merged_df)
    
    # 5. JSON 저장
    print("\n5. JSON 저장")
    save_as_json(final_df)
    
    print("\n✅ 완료!")

if __name__ == "__main__":
    main()