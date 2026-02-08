"""병무청 엑셀 파싱 모듈"""
import re
import hashlib
import pandas as pd
from pathlib import Path
from typing import Optional

from src.config import MMA_EXCEL_PATH
from src.models import Company, MmaData


def generate_company_id(name: str, address: str) -> str:
    """회사명 + 주소로 고유 ID 생성"""
    key = f"{name}|{address or ''}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


def extract_region(address: str) -> tuple[Optional[str], Optional[str]]:
    """주소에서 시/도, 시/군/구 추출"""
    if not address:
        return None, None

    # 정규화
    address = address.strip()

    # 시/도 패턴
    sido_patterns = [
        r"^(서울|부산|대구|인천|광주|대전|울산|세종)",
        r"^(경기|강원|충북|충남|전북|전남|경북|경남|제주)",
        r"^(충청북도|충청남도|전라북도|전라남도|경상북도|경상남도)",
        r"^(서울특별시|부산광역시|대구광역시|인천광역시|광주광역시|대전광역시|울산광역시|세종특별자치시)",
        r"^(경기도|강원도|제주특별자치도|제주도)",
    ]

    sido = None
    for pattern in sido_patterns:
        match = re.match(pattern, address)
        if match:
            sido = match.group(1)
            # 정규화
            sido_map = {
                "서울특별시": "서울",
                "부산광역시": "부산",
                "대구광역시": "대구",
                "인천광역시": "인천",
                "광주광역시": "광주",
                "대전광역시": "대전",
                "울산광역시": "울산",
                "세종특별자치시": "세종",
                "경기도": "경기",
                "강원도": "강원",
                "충청북도": "충북",
                "충청남도": "충남",
                "전라북도": "전북",
                "전라남도": "전남",
                "경상북도": "경북",
                "경상남도": "경남",
                "제주특별자치도": "제주",
                "제주도": "제주",
            }
            sido = sido_map.get(sido, sido)
            break

    # 시/군/구 추출
    sigungu = None
    sigungu_match = re.search(r"(?:시|도)\s*([가-힣]+(?:시|군|구))", address)
    if sigungu_match:
        sigungu = sigungu_match.group(1)
    else:
        # 광역시의 경우: "서울 강남구" 형태
        sigungu_match = re.search(r"(?:서울|부산|대구|인천|광주|대전|울산)\s*([가-힣]+구)", address)
        if sigungu_match:
            sigungu = sigungu_match.group(1)

    return sido, sigungu


def parse_excel(file_path: Path = MMA_EXCEL_PATH) -> list[Company]:
    """엑셀 파일을 파싱하여 Company 리스트로 변환"""
    print(f"엑셀 파일 파싱 중: {file_path}")

    # 엑셀 읽기 (HTML 형식인 경우도 처리)
    try:
        df = pd.read_excel(file_path, engine="xlrd")
    except Exception:
        # HTML 테이블로 저장된 경우
        df = pd.read_html(str(file_path))[0]

    print(f"총 {len(df)}개 행 로드됨")
    print(f"컬럼: {df.columns.tolist()}")

    companies = []

    # 컬럼 매핑 (병무청 엑셀 형식)
    col_map = {}
    for col in df.columns:
        col_str = str(col)
        if "업체명" in col_str or "회사명" in col_str or "기업명" in col_str:
            col_map["name"] = col
        elif "사업장" in col_str and "주소" in col_str:
            col_map["address"] = col  # 사업장주소 우선
        elif "주소" in col_str and "address" not in col_map:
            col_map["address"] = col
        elif "지역" in col_str:
            col_map["region"] = col
        elif "선정년도" in col_str or "지정년도" in col_str:
            col_map["year"] = col
        elif "전화" in col_str:
            col_map["phone"] = col
        elif "업종" in col_str:
            col_map["industry"] = col
        elif "기업규모" in col_str or col_str == "규모":
            col_map["companySize"] = col
        elif col_str == "지역":
            col_map["region"] = col
        elif "주생산품" in col_str or "생산품" in col_str:
            col_map["mainProduct"] = col
        elif "현역" in col_str and "배정" in col_str:
            col_map["activeQuota"] = col
        elif "현역" in col_str and "복무" in col_str:
            col_map["activeServing"] = col
        elif "보충역" in col_str and "배정" in col_str:
            col_map["reserveQuota"] = col
        elif "보충역" in col_str and "복무" in col_str:
            col_map["reserveServing"] = col

    print(f"컬럼 매핑: {col_map}")

    # 필수 컬럼 확인
    if "name" not in col_map:
        # 첫 번째 컬럼을 이름으로 가정
        col_map["name"] = df.columns[0]

    for idx, row in df.iterrows():
        try:
            name = str(row.get(col_map.get("name", ""), "")).strip()
            if not name or name == "nan":
                continue

            address = str(row.get(col_map.get("address", ""), "")).strip()
            if address == "nan":
                address = ""

            region = str(row.get(col_map.get("region", ""), "")).strip()
            if region == "nan":
                region = ""

            # 시/도, 시/군/구 추출
            sido, sigungu = extract_region(address or region)

            # 선정년도
            year_val = row.get(col_map.get("year", ""), None)
            year = None
            if pd.notna(year_val):
                try:
                    year = int(float(year_val))
                except (ValueError, TypeError):
                    pass

            # 전화번호
            phone = None
            if "phone" in col_map:
                phone_val = row.get(col_map["phone"], "")
                if pd.notna(phone_val) and str(phone_val).strip() != "nan":
                    phone = str(phone_val).strip()

            # 업종
            industry = None
            if "industry" in col_map:
                ind_val = row.get(col_map["industry"], "")
                if pd.notna(ind_val) and str(ind_val).strip() != "nan":
                    industry = str(ind_val).strip()

            # 기업규모
            company_size = None
            if "companySize" in col_map:
                size_val = row.get(col_map["companySize"], "")
                if pd.notna(size_val) and str(size_val).strip() != "nan":
                    company_size = str(size_val).strip()

            # 주생산품
            main_product = None
            if "mainProduct" in col_map:
                prod_val = row.get(col_map["mainProduct"], "")
                if pd.notna(prod_val) and str(prod_val).strip() != "nan":
                    main_product = str(prod_val).strip()

            # 인원 정보
            def safe_int(val):
                try:
                    return int(float(val or 0))
                except (ValueError, TypeError):
                    return 0

            active_quota = safe_int(row.get(col_map.get("activeQuota", ""), 0))
            active_serving = safe_int(row.get(col_map.get("activeServing", ""), 0))
            reserve_quota = safe_int(row.get(col_map.get("reserveQuota", ""), 0))
            reserve_serving = safe_int(row.get(col_map.get("reserveServing", ""), 0))

            company = Company(
                id=generate_company_id(name, address),
                name=name,
                sido=sido,
                sigungu=sigungu,
                address=address if address else None,
                mma=MmaData(
                    selectedYear=year,
                    address=address if address else None,
                    region=region if region else sido,
                    phone=phone,
                    industry=industry,
                    companySize=company_size,
                    mainProduct=main_product,
                    reserveQuota=reserve_quota,
                    reserveServing=reserve_serving,
                    activeQuota=active_quota,
                    activeServing=active_serving,
                ),
            )
            companies.append(company)

        except Exception as e:
            print(f"행 {idx} 파싱 오류: {e}")
            continue

    print(f"파싱 완료: {len(companies)}개 회사")
    return companies


def save_parsed_data(companies: list[Company], output_path: Path) -> None:
    """파싱된 데이터를 JSON으로 저장"""
    import json
    from src.models import create_output_data

    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = create_output_data(companies)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"저장 완료: {output_path}")
