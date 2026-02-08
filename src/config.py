"""설정 관리 모듈"""
import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 프로젝트 루트 경로
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROGRESS_DIR = DATA_DIR / "progress"

# 디렉토리 생성
for d in [DATA_DIR, RAW_DIR, PROGRESS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# 병무청 설정
MMA_DOWNLOAD_URL = "https://work.mma.go.kr/caisBYIS/search/downloadBYJJEopCheExcel.do"
MMA_EXCEL_PATH = DATA_DIR / "all_companies.xls"  # 기존 위치 유지

# 잡플래닛 설정
JOBPLANET_EMAIL = os.getenv("JOBPLANET_EMAIL", "")
JOBPLANET_PASSWORD = os.getenv("JOBPLANET_PASSWORD", "")
JOBPLANET_RATE_LIMIT = 3.0  # 초

# 원티드 설정
WANTED_RATE_LIMIT = 2.0  # 초

# 네이버 Geocoding API 설정
NAVER_CLIENT_ID = os.getenv("NAVER_GEOCODING_API_KEY_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_GEOCODING_API_KEY", "")
NAVER_GEOCODE_URL = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
NAVER_RATE_LIMIT = 0.1  # 초 (초당 10회)

# 카카오 로컬 API 설정 (회사명으로 주소 검색)
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY", "")

# 재시도 설정
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0  # exponential backoff 배수

# 출력 파일
OUTPUT_FILE = DATA_DIR / "companies.json"
