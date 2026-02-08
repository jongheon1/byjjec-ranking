"""카카오 로컬 API 모듈 - 회사명으로 주소 검색"""
import time
import requests
from typing import Optional

from src.config import MAX_RETRIES, RETRY_BACKOFF


class KakaoLocalSearch:
    """카카오 로컬 API로 회사 주소 검색"""

    SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"

    def __init__(self, api_key: str):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"KakaoAK {api_key}"
        })

    def search_company(self, company_name: str, region: str = None) -> Optional[dict]:
        """
        회사명으로 검색하여 주소와 좌표 반환

        Args:
            company_name: 회사명
            region: 지역 제한 (예: "서울", "경기")

        Returns:
            {
                'address': 도로명 주소,
                'address_old': 지번 주소,
                'lat': 위도,
                'lng': 경도
            }
        """
        # 검색어 구성
        query = company_name
        if region:
            query = f"{region} {company_name}"

        for attempt in range(MAX_RETRIES):
            try:
                time.sleep(0.1)  # Rate limit

                response = self.session.get(
                    self.SEARCH_URL,
                    params={
                        "query": query,
                        "category_group_code": "",  # 모든 카테고리
                        "size": 5
                    },
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    documents = data.get("documents", [])

                    if documents:
                        # 첫 번째 결과 사용 (가장 관련성 높음)
                        doc = documents[0]
                        return {
                            'address': doc.get('road_address_name') or doc.get('address_name'),
                            'address_old': doc.get('address_name'),
                            'lat': float(doc.get('y', 0)),
                            'lng': float(doc.get('x', 0)),
                            'place_name': doc.get('place_name'),
                            'category': doc.get('category_name'),
                        }

                elif response.status_code == 401:
                    print("[에러] 카카오 API 키가 유효하지 않습니다.")
                    return None

                elif response.status_code == 429:
                    time.sleep(RETRY_BACKOFF ** (attempt + 1))
                    continue

            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_BACKOFF ** (attempt + 1))
                else:
                    print(f"[에러] 카카오 API 검색 실패: {e}")

        return None

    def search_companies_batch(
        self, companies: list, region_field: str = 'sido'
    ) -> dict[str, dict]:
        """
        여러 회사의 주소를 일괄 검색

        Args:
            companies: Company 객체 리스트
            region_field: 지역 정보가 있는 필드명

        Returns:
            {company_id: {address, lat, lng, ...}}
        """
        results = {}

        for company in companies:
            region = getattr(company, region_field, None)
            result = self.search_company(company.name, region)

            if result:
                results[company.id] = result
                print(f"[카카오] {company.name}: {result['address']}")
            else:
                print(f"[카카오] {company.name}: 검색 결과 없음")

        return results
