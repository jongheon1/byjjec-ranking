"""유틸리티 함수 모듈"""
import csv
import os
import re
import pandas as pd


# ============================================================
# 회사명 정규화 함수
# ============================================================

def normalize_company_name(name: str) -> dict:
    """
    회사명을 정규화하여 검색에 적합한 형태로 변환

    Returns:
        {
            'original': 원본 이름,
            'korean': 한글 핵심 이름,
            'english': 영문명 (있는 경우),
            'search_variants': 검색에 사용할 변형들
        }
    """
    if not name:
        return {'original': '', 'korean': '', 'english': None, 'search_variants': []}

    original = name.strip()

    # 1. 영문명 추출 (괄호 안의 영문)
    english = None
    eng_match = re.search(r'\(([A-Za-z][A-Za-z0-9\s.,&]+(?:Co\.?,?\s*Ltd\.?|Inc\.?|LLC|Corp\.?)?)\s*\)', name)
    if eng_match:
        english = eng_match.group(1).strip()
        # 영문명에서 법인 형태 제거
        english = re.sub(r'\s*(Co\.?,?\s*Ltd\.?|Inc\.?|LLC|Corp\.?)\s*$', '', english, flags=re.IGNORECASE).strip()

    # 2. 한글 이름 정규화
    korean = name

    # 접두어/접미어 제거
    korean = re.sub(r'^[\(（]?주[\)）]?\s*', '', korean)  # (주), ㈜
    korean = re.sub(r'^㈜\s*', '', korean)
    korean = re.sub(r'\s*주식회사\s*', '', korean)
    korean = re.sub(r'\s*유한회사\s*', '', korean)
    korean = re.sub(r'\s*유한책임회사\s*', '', korean)

    # 영문 괄호 부분 제거
    korean = re.sub(r'\s*\([A-Za-z][^)]*\)\s*', '', korean)

    # 끝에 붙은 (주) 제거
    korean = re.sub(r'\s*[\(（]주[\)）]$', '', korean)

    # 공백 정규화
    korean = re.sub(r'\s+', ' ', korean).strip()

    # 3. 검색 변형 생성
    search_variants = []

    # 기본 한글 이름
    if korean:
        search_variants.append(korean)

    # 영문명
    if english:
        search_variants.append(english)

    # 띄어쓰기 없는 버전
    no_space = korean.replace(' ', '')
    if no_space != korean and no_space:
        search_variants.append(no_space)

    # 특수문자 제거 버전
    clean = re.sub(r'[&\-.,]', '', korean)
    if clean != korean and clean:
        search_variants.append(clean)

    # 중복 제거
    search_variants = list(dict.fromkeys(search_variants))

    return {
        'original': original,
        'korean': korean,
        'english': english,
        'search_variants': search_variants
    }


def similarity_score(name1: str, name2: str) -> float:
    """두 회사명의 유사도 점수 계산 (0.0 ~ 1.0)"""
    if not name1 or not name2:
        return 0.0

    # 정규화
    n1 = normalize_company_name(name1)['korean'].lower()
    n2 = normalize_company_name(name2)['korean'].lower()

    if not n1 or not n2:
        return 0.0

    # 완전 일치
    if n1 == n2:
        return 1.0

    # 포함 관계
    if n1 in n2:
        return len(n1) / len(n2)
    if n2 in n1:
        return len(n2) / len(n1)

    # 공통 문자 비율 (간단한 유사도)
    set1 = set(n1.replace(' ', ''))
    set2 = set(n2.replace(' ', ''))
    if not set1 or not set2:
        return 0.0

    intersection = len(set1 & set2)
    union = len(set1 | set2)

    return intersection / union if union > 0 else 0.0


def is_good_match(search_name: str, result_name: str, threshold: float = 0.6) -> bool:
    """검색 결과가 좋은 매칭인지 판단"""
    score = similarity_score(search_name, result_name)

    # 점수 기반 판단
    if score >= threshold:
        return True

    # 정규화된 이름 비교
    s_norm = normalize_company_name(search_name)
    r_norm = normalize_company_name(result_name)

    # 한글 이름 포함 관계
    s_korean = s_norm['korean']
    r_korean = r_norm['korean']

    if s_korean and r_korean:
        if s_korean in r_korean or r_korean in s_korean:
            return True

    # 영문명 일치
    if s_norm['english'] and r_norm['english']:
        if s_norm['english'].lower() == r_norm['english'].lower():
            return True

    return False


# ============================================================
# 기존 CSV 유틸리티 함수
# ============================================================

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