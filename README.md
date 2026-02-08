# 병역지정업체 랭킹

병역지정업체(병특) 정보를 수집하고 지도에 표시하는 프로젝트

- 병무청 병역지정업체 목록 다운로드
- 잡플래닛 평점/연봉 크롤링
- 원티드 채용정보 크롤링
- 주소 → 좌표 변환 (네이버 Geocoding API)
- 지도 시각화

## 설치

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 환경변수

`.env.example`을 `.env`로 복사 후 수정:

```bash
cp .env.example .env
```

```env
# 잡플래닛 계정 (크롤링에 필요)
JOBPLANET_EMAIL=your@email.com
JOBPLANET_PASSWORD=yourpassword

# 네이버 Cloud Platform API 키
# https://console.ncloud.com/mc/solution/naverService/application
NAVER_GEOCODING_API_KEY_ID=your_client_id
NAVER_GEOCODING_API_KEY=your_client_secret

# 카카오 API 키 (선택, 회사명으로 주소 검색)
# https://developers.kakao.com/console/app
KAKAO_API_KEY=your_kakao_rest_api_key
```

## 실행

### 전체 파이프라인

```bash
python run.py --step all
```

### 단계별 실행

```bash
# 1. 병무청 엑셀 다운로드
python run.py --step download

# 2. 엑셀 파싱
python run.py --step parse

# 3. 잡플래닛 크롤링 (로그인 필요)
python run.py --step jobplanet

# 4. 원티드 크롤링
python run.py --step wanted

# 5. 주소 → 좌표 변환
python run.py --step geocode

# 6. 데이터 병합
python run.py --step merge
```

### 옵션

```bash
# 테스트용 (처음 10개만)
python run.py --step wanted --limit 10

# headless 모드 끄기 (브라우저 표시)
python run.py --step jobplanet --no-headless
```

## 지도 보기

```bash
# 간단한 웹서버 실행
python -m http.server 8080
```

브라우저에서 http://localhost:8080/map.html 접속

## 프로젝트 구조

```
byjjec-ranking/
├── run.py                    # 메인 실행 스크립트
├── src/
│   ├── config.py             # 설정 관리
│   ├── models.py             # 데이터 스키마
│   ├── utils.py              # 유틸리티 함수
│   ├── mma/                  # 병무청 데이터
│   │   ├── download.py       # 엑셀 다운로드
│   │   └── parser.py         # 엑셀 파싱
│   ├── jobplanet/            # 잡플래닛 크롤러
│   │   └── crawler.py
│   ├── wanted/               # 원티드 크롤러
│   │   └── crawler.py
│   ├── geocoding/            # 좌표 변환
│   │   ├── naver.py          # 네이버 Geocoding API
│   │   └── kakao.py          # 카카오 로컬 API
│   └── pipeline/             # 데이터 파이프라인
│       ├── enricher.py       # 데이터 병합
│       └── progress.py       # 진행상황 추적
├── data/
│   ├── companies.json        # 최종 통합 데이터
│   ├── all_companies.xls     # 병무청 원본
│   └── progress/             # 크롤링 진행상황
├── map.html                  # 지도 시각화
├── .env                      # 환경변수 (git 제외)
└── .env.example              # 환경변수 예시
```

## 데이터 구조

`data/companies.json`:

```json
{
  "lastUpdated": "2025-02-08T...",
  "companies": [
    {
      "id": "abc123",
      "name": "(주)회사명",
      "sido": "서울",
      "sigungu": "강남구",
      "address": "서울 강남구 테헤란로 123",
      "lat": 37.123,
      "lng": 127.456,
      "mma": {
        "selectedYear": 2024,
        "industry": "정보처리",
        "companySize": "중소기업",
        "reserveQuota": 10,
        "activeServing": 5
      },
      "jobplanet": {
        "rating": 3.5,
        "reviewCount": 100,
        "avgSalary": 4500,
        "url": "https://..."
      },
      "wanted": {
        "isHiring": true,
        "jobCount": 5,
        "address": "서울 강남구...",
        "url": "https://..."
      }
    }
  ]
}
```

## 진행상황 관리

크롤링은 `data/progress/` 폴더에 진행상황이 저장되어 중단/재시작이 가능합니다.

```bash
# 실패한 항목만 다시 시도
python -c "
from src.pipeline.progress import ProgressTracker
ProgressTracker('wanted').reset_failed()
"

# 전체 초기화 (처음부터 다시)
python -c "
from src.pipeline.progress import ProgressTracker
ProgressTracker('wanted').reset()
"
```

## 수동 데이터 추가

검색 실패한 회사들은 `data/failed_wanted.txt`, `data/failed_jobplanet.txt`에 저장됩니다.

수동으로 URL을 찾아서 추가하려면:

1. 파일을 다음 형식으로 수정:
   ```
   회사명[TAB]잡플래닛URL[TAB]원티드URL
   ```

2. 스크립트로 적용 (TODO)

## 현재 데이터 현황

- 전체 회사: 649개
- 잡플래닛: 487개 (75%)
- 원티드: 421개 (65%)
- 좌표: 391개 (60%)
