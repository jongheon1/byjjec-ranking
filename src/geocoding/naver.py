"""네이버 Geocoding API 모듈"""
import time
import requests
from typing import Optional

from src.config import (
    NAVER_CLIENT_ID,
    NAVER_CLIENT_SECRET,
    NAVER_GEOCODE_URL,
    NAVER_RATE_LIMIT,
    MAX_RETRIES,
    RETRY_BACKOFF,
)
from src.pipeline.progress import ProgressTracker


class NaverGeocoder:
    """네이버 Geocoding API 클라이언트"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
                "X-NCP-APIGW-API-KEY": NAVER_CLIENT_SECRET,
            }
        )
        self.progress = ProgressTracker("geocode")

    def geocode(self, address: str) -> Optional[tuple[float, float]]:
        """주소를 좌표로 변환 (lat, lng)"""
        if not address:
            return None

        if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
            print("[에러] 네이버 API 키가 설정되지 않았습니다.")
            print("  .env 파일에 NAVER_CLIENT_ID, NAVER_CLIENT_SECRET를 설정하세요.")
            return None

        for attempt in range(MAX_RETRIES):
            try:
                time.sleep(NAVER_RATE_LIMIT)

                response = self.session.get(
                    NAVER_GEOCODE_URL,
                    params={"query": address},
                    timeout=10,
                )

                if response.status_code == 200:
                    data = response.json()
                    addresses = data.get("addresses", [])

                    if addresses:
                        addr = addresses[0]
                        lat = float(addr.get("y"))
                        lng = float(addr.get("x"))
                        return (lat, lng)
                    else:
                        return None

                elif response.status_code == 429:
                    # Rate limit
                    print(f"  Rate limit, 대기 중...")
                    time.sleep(RETRY_BACKOFF ** (attempt + 1))

                else:
                    print(f"  API 에러: {response.status_code}")
                    return None

            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    print(f"  [재시도 {attempt + 1}/{MAX_RETRIES}] {e}")
                    time.sleep(RETRY_BACKOFF ** (attempt + 1))
                else:
                    print(f"  [에러] {e}")
                    return None

        return None

    def geocode_companies(
        self, companies: list, limit: Optional[int] = None
    ) -> dict[str, tuple[float, float]]:
        """여러 회사 주소를 좌표로 변환"""
        results = {}

        # 주소가 있는 회사만 필터링
        companies_with_address = [c for c in companies if c.address]
        company_ids = [c.id for c in companies_with_address]
        pending = self.progress.get_pending(company_ids)

        if limit:
            pending = pending[:limit]

        total = len(pending)
        print(f"Geocoding 시작: {total}개 회사")

        for idx, company_id in enumerate(pending, 1):
            company = next((c for c in companies_with_address if c.id == company_id), None)
            if not company:
                continue

            print(f"[{idx}/{total}] {company.name}: {company.address[:30]}...")

            try:
                coords = self.geocode(company.address)

                if coords:
                    results[company_id] = coords
                    self.progress.mark_completed(
                        company_id, {"lat": coords[0], "lng": coords[1]}
                    )
                    print(f"  좌표: {coords[0]:.6f}, {coords[1]:.6f}")
                else:
                    self.progress.mark_completed(company_id, {})
                    print("  좌표 변환 실패")

            except Exception as e:
                self.progress.mark_failed(company_id, str(e))
                print(f"  [에러] {e}")

        stats = self.progress.get_stats()
        print(f"\nGeocoding 완료: 성공 {stats['completed']}, 실패 {stats['failed']}")

        return results
