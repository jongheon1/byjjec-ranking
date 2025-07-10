import os
import pandas as pd
import json
import numpy as np
from src.download import download_data
from src.jobplanet.crawler import JobPlanetCrawler
from src.wanted.crawler import WantedCrawler
from src.utils import get_company_list, create_csv_if_not_exists, update_company_data, get_processed_companies
from src.geocoding import GeocodingService

def main():
    # data 디렉토리가 없으면 생성
    if not os.path.exists('data'):
        os.makedirs('data')
    
    by_data_file = "data/by_data.xls"
    crawled_result_file = "data/company_info.csv"
    final_result_file = "data/final_company_data.csv"
    final_with_coords_file = "data/final_company_data_with_coords.csv"

    print("병역지정업체 목록 다운로드를 시작합니다.")
    download_data(by_data_file)
    print("다운로드 완료.")

    company_names = get_company_list(by_data_file)
    create_csv_if_not_exists(crawled_result_file)
    
    # 이미 처리된 회사들 확인
    processed_companies = get_processed_companies(crawled_result_file)
    remaining_companies = [name for name in company_names if name not in processed_companies]
    
    print(f"총 {len(company_names)}개 회사")
    print(f"처리 완료: {len(processed_companies)}개")
    print(f"처리 대상: {len(remaining_companies)}개")
    
    if not remaining_companies:
        print("모든 회사 처리 완료! 최종 데이터 병합을 시작합니다.")
    else:
        # 두 크롤러를 동시에 시작
        print("\n=== 크롤러 초기화 중 ===")
        jp_crawler = JobPlanetCrawler(headless=False)
        wanted_crawler = WantedCrawler(headless=False)
        
        # 잡플래닛 로그인
        jp_login_success = jp_crawler.login()
        if jp_login_success:
            print("잡플래닛 로그인 성공!")
        else:
            print("잡플래닛 로그인 실패")
        
        print("원티드 크롤러 준비 완료!")
        
        # 각 회사별로 순차 처리
        for i, company_name in enumerate(remaining_companies, 1):
            print(f"\n[{i}/{len(remaining_companies)}] === {company_name} 처리 중 ===")
            
            # 잡플래닛에서 정보 수집
            jp_data = {}
            if jp_login_success:
                print(f"잡플래닛 - {company_name} 검색 중...")
                company_url = jp_crawler.search_company(company_name)
                if company_url:
                    jp_details = jp_crawler.get_company_details(company_url)
                    jp_data = {
                        'rating': jp_details.get('rating', '-1'),
                        'review_count': jp_details.get('review_count', '0'),
                        'salary_jobplanet': jp_details.get('salary', '0'),  # 잡플래닛 연봉
                        'hiring_count_jobplanet': jp_details.get('hiring_count', '0'),  # 잡플래닛 채용수
                        'backend_position_jobplanet': jp_details.get('backend_position', False),  # 잡플래닛 백엔드 포지션
                        'address': jp_details.get('address', '')
                    }
                    print(f"잡플래닛 결과: {jp_data}")
                else:
                    print("잡플래닛 검색 실패")
            
            # 원티드에서 정보 수집
            wanted_data = {}
            print(f"원티드 - {company_name} 검색 중...")
            company_url = wanted_crawler.search_company(company_name)
            if company_url:
                wanted_details = wanted_crawler.get_company_details(company_url)
                wanted_data = {
                    'hiring_count_wanted': wanted_details.get('hiring_count', '0'),  # 원티드 채용수
                    'backend_position_wanted': wanted_details.get('backend_position', False),  # 원티드 백엔드 포지션
                    'founded_year': wanted_details.get('founded_year', ''),
                    'revenue': wanted_details.get('revenue', ''),
                    'salary_wanted': wanted_details.get('salary', ''),  # 원티드 연봉
                    'total_employees': wanted_details.get('total_employees', ''),
                    'resignees': wanted_details.get('resignees', ''),
                    'new_hires': wanted_details.get('new_hires', '')
                }
                print(f"원티드 결과: {wanted_data}")
            else:
                print("원티드 검색 실패")
            
            # 데이터 통합 및 저장
            combined_data = {**jp_data, **wanted_data}
            # 백엔드 포지션은 둘 중 하나라도 True면 True
            combined_data['backend_position'] = combined_data.get('backend_position_jobplanet', False) or combined_data.get('backend_position_wanted', False)
            
            update_company_data(crawled_result_file, company_name, combined_data)
            print(f"통합 데이터 저장 완료: {combined_data}")
        
        # 크롤러 종료
        jp_crawler.close()
        wanted_crawler.close()
    
    # === 최종 데이터 병합 ===
    print("\n=== 최종 데이터 병합 시작 ===")
    try:
        df_crawled = pd.read_csv(crawled_result_file)
        df_excel = pd.read_excel(by_data_file, header=0)
        
        # 필요한 엑셀 컬럼만 선택
        df_excel_selected = df_excel[['업체명', '선정년도', '보충역 복무인원']]
        
        # 컬럼명 통일
        df_excel_selected = df_excel_selected.rename(columns={'업체명': 'company_name'})
        
        # 데이터 병합 (crawled 데이터를 기준으로)
        df_final = pd.merge(df_crawled, df_excel_selected, on='company_name', how='left')
        
        # 최종 파일로 저장 (utf-8-sig로 엑셀에서 한글 깨짐 방지)
        df_final.to_csv(final_result_file, index=False, encoding='utf-8-sig')
        
        print(f"성공적으로 최종 데이터를 {final_result_file} 에 저장했습니다.")
    except Exception as e:
        print(f"최종 데이터 병합 실패: {e}")
        return

    # === 지오코딩 처리 ===
    print("\n=== 주소 좌표 변환 시작 ===")
    geocoding_service = GeocodingService()
    
    # 최종 데이터 읽기
    df_final = pd.read_csv(final_result_file)
    
    # 주소를 좌표로 변환
    df_with_coords = geocoding_service.process_dataframe(df_final)
    
    # 좌표가 포함된 최종 파일 저장
    df_with_coords.to_csv(final_with_coords_file, index=False, encoding='utf-8-sig')
    
    # 통계 출력
    total_companies = len(df_with_coords)
    companies_with_coords = df_with_coords[df_with_coords['x'].notna()].shape[0]
    companies_without_coords = total_companies - companies_with_coords
    
    print(f"\n=== 지오코딩 처리 결과 ===")
    print(f"전체 회사 수: {total_companies}")
    print(f"좌표 변환 성공: {companies_with_coords}")
    print(f"좌표 변환 실패: {companies_without_coords}")

    # === JSON 변환 ===
    print("\n=== JSON 변환 시작 ===")
    json_output_file = "data/final_company_data.json"
    
    try:
        # NaN 값을 None으로 변환
        df_with_coords = df_with_coords.replace({np.nan: None})
        
        # 데이터를 딕셔너리 리스트로 변환
        companies_list = []
        
        for _, row in df_with_coords.iterrows():
            company_data = {
                "company_name": row['company_name'],
                "rating": row['rating'] if row['rating'] != -1.0 else None,
                "review_count": int(row['review_count']) if pd.notna(row['review_count']) else 0,
                "salary_jobplanet": row['salary_jobplanet'] if pd.notna(row['salary_jobplanet']) else None,
                "salary_wanted": row['salary_wanted'] if pd.notna(row['salary_wanted']) else None,
                "hiring_count_jobplanet": int(row['hiring_count_jobplanet']) if pd.notna(row['hiring_count_jobplanet']) else 0,
                "hiring_count_wanted": int(row['hiring_count_wanted']) if pd.notna(row['hiring_count_wanted']) else 0,
                "backend_position": bool(row['backend_position']) if pd.notna(row['backend_position']) else False,
                "backend_position_jobplanet": bool(row['backend_position_jobplanet']) if pd.notna(row['backend_position_jobplanet']) else False,
                "backend_position_wanted": bool(row['backend_position_wanted']) if pd.notna(row['backend_position_wanted']) else False,
                "founded_year": row['founded_year'] if pd.notna(row['founded_year']) else None,
                "revenue": row['revenue'] if pd.notna(row['revenue']) else None,
                "total_employees": float(row['total_employees']) if pd.notna(row['total_employees']) else None,
                "resignees": float(row['resignees']) if pd.notna(row['resignees']) else None,
                "new_hires": float(row['new_hires']) if pd.notna(row['new_hires']) else None,
                "address": row['address'] if pd.notna(row['address']) else None,
                "selection_year": int(row['선정년도']) if pd.notna(row['선정년도']) else None,
                "supplementary_service_personnel": int(row['보충역 복무인원']) if pd.notna(row['보충역 복무인원']) else 0,
                "coordinates": {
                    "x": float(row['x']) if pd.notna(row['x']) else None,
                    "y": float(row['y']) if pd.notna(row['y']) else None
                } if pd.notna(row['x']) and pd.notna(row['y']) else None
            }
            
            companies_list.append(company_data)
        
        # JSON 파일로 저장
        with open(json_output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "total_count": len(companies_list),
                "companies": companies_list
            }, f, ensure_ascii=False, indent=2)
        
        print(f"성공적으로 JSON 파일을 생성했습니다: {json_output_file}")
        
    except Exception as e:
        print(f"JSON 변환 중 오류 발생: {e}")

    print(f"\n=== 모든 작업이 완료되었습니다! ===")
    print(f"최종 CSV 파일: {final_with_coords_file}")
    print(f"최종 JSON 파일: {json_output_file}")

if __name__ == "__main__":
    main()