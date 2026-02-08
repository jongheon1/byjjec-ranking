"""데이터 통합 모듈"""
import json
from pathlib import Path
from typing import Optional

from src.config import OUTPUT_FILE, DATA_DIR
from src.models import Company, JobplanetData, WantedData, create_output_data
from src.pipeline.progress import ProgressTracker


def load_companies(file_path: Path = OUTPUT_FILE) -> list[Company]:
    """JSON 파일에서 회사 목록 로드"""
    if not file_path.exists():
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return [Company.from_dict(c) for c in data.get("companies", [])]


def save_companies(companies: list[Company], file_path: Path = OUTPUT_FILE):
    """회사 목록을 JSON 파일로 저장"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    data = create_output_data(companies)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"저장 완료: {file_path} ({len(companies)}개 회사)")


def merge_jobplanet_data(companies: list[Company]) -> list[Company]:
    """잡플래닛 진행상황에서 데이터 병합"""
    progress = ProgressTracker("jobplanet")

    for company in companies:
        result = progress.get_result(company.id)
        # URL이나 rating이나 avgSalary 중 하나라도 있으면 병합
        if result and (result.get("url") or result.get("rating") or result.get("avgSalary")):
            company.jobplanet = JobplanetData(
                rating=result.get("rating"),
                reviewCount=result.get("reviewCount", 0),
                avgSalary=result.get("avgSalary"),
                address=result.get("address"),
                url=result.get("url"),
            )

    return companies


def merge_wanted_data(companies: list[Company]) -> list[Company]:
    """원티드 진행상황에서 데이터 병합"""
    progress = ProgressTracker("wanted")

    for company in companies:
        result = progress.get_result(company.id)
        if result:
            company.wanted = WantedData(
                isHiring=result.get("isHiring", False),
                jobCount=result.get("jobCount", 0),
                jobs=result.get("jobs", []),
                address=result.get("address"),
                foundedYear=result.get("foundedYear"),
                employees=result.get("employees"),
                url=result.get("url"),
            )

            # 원티드 주소가 있으면 업데이트 (더 정확할 수 있음)
            if result.get("address") and not company.address:
                company.address = result["address"]

    return companies


def merge_geocode_data(companies: list[Company]) -> list[Company]:
    """Geocoding 진행상황에서 좌표 병합"""
    progress = ProgressTracker("geocode")

    for company in companies:
        result = progress.get_result(company.id)
        if result and result.get("lat"):
            company.lat = result["lat"]
            company.lng = result["lng"]

    return companies


def update_address_priority(companies: list[Company]) -> list[Company]:
    """주소 우선순위 적용: 원티드 > 잡플래닛 > 병무청"""
    for company in companies:
        # 현재 주소 유지 (병무청 기본)
        address = company.address

        # 잡플래닛 주소가 있으면 업데이트
        if company.jobplanet and company.jobplanet.address:
            address = company.jobplanet.address

        # 원티드 주소가 있으면 최우선 (가장 정확함)
        if company.wanted and company.wanted.address:
            address = company.wanted.address

        company.address = address

    return companies


def enrich_all(companies: list[Company]) -> list[Company]:
    """모든 데이터 소스 통합"""
    print("데이터 통합 시작...")

    companies = merge_jobplanet_data(companies)
    companies = merge_wanted_data(companies)
    companies = update_address_priority(companies)  # 주소 먼저 업데이트
    companies = merge_geocode_data(companies)

    # 통계 출력
    total = len(companies)
    with_jobplanet = sum(1 for c in companies if c.jobplanet and c.jobplanet.rating)
    with_wanted = sum(1 for c in companies if c.wanted)
    with_coords = sum(1 for c in companies if c.lat and c.lng)
    hiring = sum(1 for c in companies if c.wanted and c.wanted.isHiring)

    print(f"\n통합 결과:")
    print(f"  총 회사: {total}개")
    print(f"  잡플래닛 정보: {with_jobplanet}개 ({with_jobplanet/total*100:.1f}%)")
    print(f"  원티드 정보: {with_wanted}개 ({with_wanted/total*100:.1f}%)")
    print(f"  좌표 정보: {with_coords}개 ({with_coords/total*100:.1f}%)")
    print(f"  채용 중: {hiring}개")

    return companies
