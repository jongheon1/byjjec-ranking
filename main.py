import os
import pandas as pd
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
                        'salary': jp_details.get('salary', '0'),
                        'hiring_count': jp_details.get('hiring_count', '0'),
                        'backend_position': jp_details.get('backend_position', False),
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
                    'hiring_count': wanted_details.get('hiring_count', '0'),  # 잡플래닛 것 덮어쓰기
                    'backend_position': wanted_details.get('backend_position', False),  # 잡플래닛 것 덮어쓰기
                    'founded_year': wanted_details.get('founded_year', ''),
                    'revenue': wanted_details.get('revenue', ''),
                    'salary': wanted_details.get('salary', ''),
                    'total_employees': wanted_details.get('total_employees', ''),
                    'resignees': wanted_details.get('resignees', ''),
                    'new_hires': wanted_details.get('new_hires', '')
                }
                print(f"원티드 결과: {wanted_data}")
            else:
                print("원티드 검색 실패")
            
            # 데이터 통합 및 저장
            combined_data = {**jp_data, **wanted_data}  # 원티드 데이터가 잡플래닛 데이터를 덮어쓰기
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

    print(f"\n=== 모든 작업이 완료되었습니다! ===")
    print(f"최종 결과 파일: {final_with_coords_file}")

if __name__ == "__main__":
    main()