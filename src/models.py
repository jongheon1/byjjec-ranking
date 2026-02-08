"""데이터 스키마 정의"""
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime


@dataclass
class MmaData:
    """병무청 데이터"""
    selectedYear: Optional[int] = None  # 선정년도
    address: Optional[str] = None  # 주소
    region: Optional[str] = None  # 지역 (시/도)
    phone: Optional[str] = None  # 전화번호
    industry: Optional[str] = None  # 업종
    companySize: Optional[str] = None  # 기업규모
    mainProduct: Optional[str] = None  # 주생산품
    reserveQuota: int = 0  # 현역 배정인원
    reserveServing: int = 0  # 현역 복무인원
    activeQuota: int = 0  # 보충역 배정인원
    activeServing: int = 0  # 보충역 복무인원


@dataclass
class JobplanetData:
    """잡플래닛 데이터"""
    rating: Optional[float] = None  # 평점 (1~5)
    reviewCount: int = 0  # 리뷰 수
    avgSalary: Optional[int] = None  # 평균 연봉 (만원)
    address: Optional[str] = None  # 회사 주소
    url: Optional[str] = None  # 잡플래닛 URL


@dataclass
class WantedJob:
    """원티드 채용공고"""
    title: str = ""
    url: str = ""


@dataclass
class WantedData:
    """원티드 데이터"""
    isHiring: bool = False  # 채용 중 여부
    jobCount: int = 0  # 채용공고 수
    jobs: list = field(default_factory=list)  # 채용공고 목록
    address: Optional[str] = None  # 주소
    foundedYear: Optional[int] = None  # 설립년도
    employees: Optional[str] = None  # 직원수
    url: Optional[str] = None  # 원티드 회사 URL


@dataclass
class Company:
    """회사 통합 데이터"""
    id: str  # 고유 ID
    name: str  # 회사명
    sido: Optional[str] = None  # 시/도
    sigungu: Optional[str] = None  # 시/군/구
    address: Optional[str] = None  # 최종 주소 (우선순위 적용)
    lat: Optional[float] = None  # 위도
    lng: Optional[float] = None  # 경도
    mma: Optional[MmaData] = None  # 병무청 데이터
    jobplanet: Optional[JobplanetData] = None  # 잡플래닛 데이터
    wanted: Optional[WantedData] = None  # 원티드 데이터

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        result = {
            "id": self.id,
            "name": self.name,
            "sido": self.sido,
            "sigungu": self.sigungu,
            "address": self.address,
            "lat": self.lat,
            "lng": self.lng,
        }

        if self.mma:
            result["mma"] = asdict(self.mma)
        if self.jobplanet:
            result["jobplanet"] = asdict(self.jobplanet)
        if self.wanted:
            result["wanted"] = asdict(self.wanted)

        return result

    @classmethod
    def from_dict(cls, data: dict) -> "Company":
        """딕셔너리에서 생성"""
        mma_data = data.get("mma")
        jobplanet_data = data.get("jobplanet")
        wanted_data = data.get("wanted")

        # MmaData 생성 (알 수 없는 필드 무시)
        mma = None
        if mma_data:
            mma_fields = {k: v for k, v in mma_data.items()
                         if k in MmaData.__dataclass_fields__}
            mma = MmaData(**mma_fields)

        # JobplanetData 생성 (알 수 없는 필드 무시)
        jobplanet = None
        if jobplanet_data:
            jp_fields = {k: v for k, v in jobplanet_data.items()
                        if k in JobplanetData.__dataclass_fields__}
            jobplanet = JobplanetData(**jp_fields)

        # WantedData 생성 (알 수 없는 필드 무시)
        wanted = None
        if wanted_data:
            w_fields = {k: v for k, v in wanted_data.items()
                       if k in WantedData.__dataclass_fields__}
            wanted = WantedData(**w_fields)

        return cls(
            id=data["id"],
            name=data["name"],
            sido=data.get("sido"),
            sigungu=data.get("sigungu"),
            address=data.get("address"),
            lat=data.get("lat"),
            lng=data.get("lng"),
            mma=mma,
            jobplanet=jobplanet,
            wanted=wanted,
        )


def create_output_data(companies: list[Company]) -> dict:
    """최종 출력 데이터 생성"""
    return {
        "lastUpdated": datetime.now().isoformat(),
        "companies": [c.to_dict() for c in companies],
    }
