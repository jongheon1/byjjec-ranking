import pandas as pd
from src.crawl import get_companies_ratings
from src.download import download_data

if __name__ == "__main__":
    file_name = "병역지정업체.xls"
    download_data(file_name)  # 필요한 경우 데이터 다운로드 함수 호출

    # 엑셀 파일 읽기
    df = pd.read_excel(file_name)
    company_names = df['업체명'].tolist()  # '업체명' 열의 데이터를 리스트로 변환

    # 평점 및 리뷰 수 가져오기
    ratings_reviews = get_companies_ratings(company_names)

    # 결과 DataFrame 생성
    results_df = pd.DataFrame(ratings_reviews, columns=['업체명', '평점', '리뷰 수', '채용 수'])
    
    # 원본 DataFrame과 병합
    df_merged = pd.merge(df, results_df, on='업체명')

    # 병역지정업체랭킹에서 주소 가져와서 세부주소만 빼서 새 열에 저장
    address = df_merged['주소'].tolist()
    address = [a.split(' ') for a in address]

    df_merged['구'] = [a[1] for a in address]

    # 불 필요한 헤더 제거 (순번, 지방청, 전화번호, 팩스번호, 보충역 배정인원, 현역 배정인원, 현역 편입인원, 현역 복무인원)

    new_order = ['업체명', '평점', '리뷰 수', '채용 수', '구', '선정년도', '주소', '기업규모', '보충역 편입인원', '보충역 복무인원']
    df_final = df_merged[new_order]

    # 새로운 Excel 파일로 저장
    new_file_name = "병역지정업체_랭킹.xlsx"
    df_final.to_excel(new_file_name, index=False)
    print("병역지정업체_랭킹.xlsx 파일이 생성되었습니다.")


    # # # 원하는 순서로 열 재배치
    # # new_order = ['순번', '업체명', '평점', '리뷰 수', '채용 수', '선정년도', '지방청', '주소', '전화번호', '팩스번호', '업종', '기업규모', '주생산품목', '연구분야', '보충역 배정인원', '보충역 편입인원', '보충역 복무인원', '현역 배정인원', '현역 편입인원', '현역 복무인원']
    # # df_final = df_merged[new_order]

    # # # 새로운 Excel 파일로 저장
    # # new_file_name = "병역지정업체_랭킹.xlsx"
    # # df_final.to_excel(new_file_name, index=False)

    # # 병역지정업체랭킹에서 주소 가져와서 세부주소만 빼서 새 열에 저장
    # # 불 필요한 헤더 제거 (순번, 지방청, 전화번호, 팩스번호, 보충역 배정인원, 현역 배정인원, 현역 편입인원, 현역 복무인원)
    # file_name = "병역지정업체_랭킹.xlsx"
    # df = pd.read_excel(file_name)
    # address = df['주소'].tolist()
    # address = [a.split(' ') for a in address]

    # df['구'] = [a[1] for a in address]

    # # 헤더 정리
    # new_order = ['업체명', '평점', '리뷰 수', '채용 수', '구', '선정년도', '주소', '업종', '기업규모', '보충역 편입인원', '보충역 복무인원']
    # df = df[new_order]

    # new_file_name = "병역지정업체_랭킹_주소추가.xlsx"
    # df.to_excel(new_file_name, index=False)
    # print("병역지정업체_랭킹_주소추가.xlsx 파일이 생성되었습니다.")
    # print(df.head())
    




