import csv
import os
import pandas as pd

def get_last_processed_company(csv_file_path):
    """CSV 파일에서 마지막으로 처리된 회사명을 반환합니다."""
    if not os.path.exists(csv_file_path):
        return None
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            rows = list(reader)
            if len(rows) > 1:  # 헤더 제외
                return rows[-1][0]  # 첫 번째 컬럼이 회사명
    except Exception as e:
        print(f"CSV 파일 읽기 오류: {e}")
    
    return None

def create_csv_if_not_exists(csv_file_path):
    """CSV 파일이 없으면 헤더와 함께 생성합니다."""
    if not os.path.exists(csv_file_path):
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            header = [
                'company_name', 'rating', 'review_count', 
                'salary_jobplanet', 'salary_wanted',  # 연봉 구분
                'hiring_count_jobplanet', 'hiring_count_wanted',  # 채용수 구분
                'backend_position', 'backend_position_jobplanet', 'backend_position_wanted',  # 백엔드 포지션 구분
                'founded_year', 'revenue',
                'total_employees', 'resignees', 'new_hires', 'address'
            ]
            writer.writerow(header)

def update_company_data(csv_file_path, company_name, data):
    """회사 데이터를 업데이트하거나 새로 추가합니다."""
    # 기존 데이터 읽기
    existing_data = {}
    if os.path.exists(csv_file_path):
        try:
            df = pd.read_csv(csv_file_path, encoding='utf-8')
            for _, row in df.iterrows():
                existing_data[row['company_name']] = row.to_dict()
        except Exception as e:
            print(f"기존 데이터 읽기 오류: {e}")
    
    # 해당 회사 데이터 가져오기 또는 새로 생성
    if company_name in existing_data:
        company_row = existing_data[company_name]
    else:
        company_row = {
            'company_name': company_name,
            'rating': '-1',
            'review_count': '0',
            'salary_jobplanet': '0',
            'salary_wanted': '',
            'hiring_count_jobplanet': '0',
            'hiring_count_wanted': '0',
            'backend_position': False,
            'backend_position_jobplanet': False,
            'backend_position_wanted': False,
            'founded_year': '',
            'revenue': '',
            'total_employees': '',
            'resignees': '',
            'new_hires': '',
            'address': ''
        }
    
    # 데이터 업데이트 (빈 값이 아닌 경우만 덮어쓰기)
    for key, value in data.items():
        if key in company_row:
            # 빈 값이 아니거나 기본값이 아닌 경우만 업데이트
            if value and value != '' and value != '0' and value != '-1':
                company_row[key] = value
            elif company_row[key] in ['', '0', '-1'] and value:
                company_row[key] = value
    
    # 데이터 업데이트
    existing_data[company_name] = company_row
    
    # CSV 파일 다시 쓰기
    df = pd.DataFrame(list(existing_data.values()))
    df.to_csv(csv_file_path, index=False, encoding='utf-8')

def get_company_list(file_name):
    """엑셀 파일에서 회사 목록을 가져옵니다."""
    df = pd.read_excel(file_name, header=0)
    return df['업체명'].dropna().tolist()

def get_processed_companies(csv_file_path):
    """이미 처리된 회사들을 확인합니다."""
    if not os.path.exists(csv_file_path):
        return set()
    
    try:
        df = pd.read_csv(csv_file_path, encoding='utf-8')
        processed = set()
        
        for _, row in df.iterrows():
            company_name = row['company_name']
            # 기본값이 아닌 데이터가 하나라도 있으면 처리된 것으로 간주
            if (row['rating'] != '-1' or row['review_count'] != '0' or 
                row.get('hiring_count_jobplanet', '0') != '0' or row.get('hiring_count_wanted', '0') != '0' or
                row['founded_year'] != '' or row.get('address', '') != ''):
                processed.add(company_name)
        
        return processed
    except Exception as e:
        print(f"처리된 회사 확인 오류: {e}")
        return set() 