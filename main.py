import pandas as pd
import os
from src.crawl import get_companies_ratings
from src.download import download_data

if __name__ == "__main__":
    if not os.path.exists('data'):
        os.makedirs('data')

    # 파일 경로 설정
    input_file = "data/병역지정업체.xls"
    output_file = "data/병역지정업체_랭킹.xlsx"
    
    # 데이터 다운로드
    download_data(input_file)

    # 엑셀 파일 읽기
    df = pd.read_excel(input_file)
    company_names = df['업체명'].tolist()

    # 평점, 리뷰 수, 채용 수, 연봉, 백엔드 포지션 정보 가져오기
    ratings_reviews = get_companies_ratings(company_names)

    # 결과 DataFrame 생성
    results_df = pd.DataFrame(ratings_reviews, 
                            columns=['업체명', '평점', '리뷰 수', '채용 수', '연봉', '백엔드 채용'])
    
    # 원본 DataFrame과 병합
    df_merged = pd.merge(df, results_df, on='업체명')

    # 주소에서 '구' 정보 추출
    address = df_merged['주소'].tolist()
    address = [a.split(' ') for a in address]
    df_merged['구'] = [a[1] if len(a) > 1 else '' for a in address]

    # 필요한 컬럼만 선택
    new_order = ['업체명', '평점', '리뷰 수', '채용 수', '연봉', '백엔드 채용', 
                 '구', '선정년도', '보충역 복무인원']
    df_final = df_merged[new_order]

    # 새로운 Excel 파일로 저장
    df_final.to_excel(output_file, index=False)
    print(f"{output_file} 파일이 생성되었습니다.")