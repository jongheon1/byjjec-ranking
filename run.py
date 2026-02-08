#!/usr/bin/env python3
"""병특 지도 데이터 수집 스크립트"""
import argparse
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from src.config import OUTPUT_FILE, MMA_EXCEL_PATH
from src.mma.download import download_all_companies
from src.mma.parser import parse_excel, save_parsed_data
from src.jobplanet.crawler import JobplanetCrawler
from src.wanted.crawler import WantedCrawler
from src.geocoding.naver import NaverGeocoder
from src.pipeline.enricher import (
    load_companies,
    save_companies,
    enrich_all,
    merge_jobplanet_data,
    merge_wanted_data,
    merge_geocode_data,
)


def step_download():
    """병무청 엑셀 다운로드"""
    print("\n=== 병무청 데이터 다운로드 ===")
    download_all_companies()


def step_parse():
    """엑셀 파싱"""
    print("\n=== 엑셀 파싱 ===")

    if not MMA_EXCEL_PATH.exists():
        print(f"엑셀 파일이 없습니다: {MMA_EXCEL_PATH}")
        print("먼저 --step download를 실행하세요.")
        return []

    companies = parse_excel(MMA_EXCEL_PATH)
    save_companies(companies, OUTPUT_FILE)
    return companies


def step_jobplanet(limit: int = None):
    """잡플래닛 크롤링"""
    print("\n=== 잡플래닛 크롤링 ===")

    companies = load_companies()
    if not companies:
        print("회사 데이터가 없습니다. 먼저 --step parse를 실행하세요.")
        return

    with JobplanetCrawler(headless=True) as crawler:
        crawler.crawl_companies(companies, limit=limit)

    # 결과 병합
    companies = merge_jobplanet_data(companies)
    save_companies(companies, OUTPUT_FILE)


def step_wanted(limit: int = None):
    """원티드 크롤링"""
    print("\n=== 원티드 크롤링 ===")

    companies = load_companies()
    if not companies:
        print("회사 데이터가 없습니다. 먼저 --step parse를 실행하세요.")
        return

    with WantedCrawler(headless=True) as crawler:
        crawler.crawl_companies(companies, limit=limit)

    # 결과 병합
    companies = merge_wanted_data(companies)
    save_companies(companies, OUTPUT_FILE)


def step_geocode(limit: int = None):
    """Geocoding"""
    print("\n=== Geocoding ===")

    companies = load_companies()
    if not companies:
        print("회사 데이터가 없습니다. 먼저 --step parse를 실행하세요.")
        return

    geocoder = NaverGeocoder()
    geocoder.geocode_companies(companies, limit=limit)

    # 결과 병합
    companies = merge_geocode_data(companies)
    save_companies(companies, OUTPUT_FILE)


def step_merge():
    """모든 데이터 병합"""
    print("\n=== 데이터 병합 ===")

    companies = load_companies()
    if not companies:
        print("회사 데이터가 없습니다. 먼저 --step parse를 실행하세요.")
        return

    companies = enrich_all(companies)
    save_companies(companies, OUTPUT_FILE)


def step_all(limit: int = None):
    """전체 파이프라인 실행"""
    step_download()
    step_parse()
    step_jobplanet(limit)
    step_wanted(limit)
    step_geocode(limit)
    step_merge()


def main():
    parser = argparse.ArgumentParser(
        description="병역지정업체 데이터 수집",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "--step",
        choices=["all", "download", "parse", "jobplanet", "wanted", "geocode", "merge"],
        default="all",
        help="""실행할 단계:
  all       - 전체 파이프라인 (기본값)
  download  - 병무청 엑셀 다운로드
  parse     - 엑셀 → JSON 변환
  jobplanet - 잡플래닛 크롤링
  wanted    - 원티드 크롤링
  geocode   - 주소 → 좌표 변환
  merge     - 모든 데이터 통합""",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="처리할 회사 수 제한 (테스트용)",
    )

    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="브라우저를 표시 (디버깅용)",
    )

    args = parser.parse_args()

    print("=" * 50)
    print("병역지정업체 데이터 수집")
    print("=" * 50)

    if args.step == "all":
        step_all(args.limit)
    elif args.step == "download":
        step_download()
    elif args.step == "parse":
        step_parse()
    elif args.step == "jobplanet":
        step_jobplanet(args.limit)
    elif args.step == "wanted":
        step_wanted(args.limit)
    elif args.step == "geocode":
        step_geocode(args.limit)
    elif args.step == "merge":
        step_merge()

    print("\n" + "=" * 50)
    print("완료!")
    print(f"결과 파일: {OUTPUT_FILE}")
    print("=" * 50)


if __name__ == "__main__":
    main()
