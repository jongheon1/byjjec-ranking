# 병역지정업체 랭킹

병역지정업체 정보를 크롤링하고 지도에 표시하는 프로젝트

## 설치

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 환경변수

`.env` 파일 생성:
```
NAVER_MAP_API_KEY_ID=your_key_id
NAVER_MAP_API_KEY=your_key
```

## 실행

```bash
# 데이터 수집 및 처리
python main.py

# 웹 서버 실행 (포트 8080)
python serve.py
```

브라우저에서 http://localhost:8080 접속

## 구조

- `main.py` - 메인 실행 파일
- `src/jobplanet/` - 잡플래닛 크롤러
- `src/wanted/` - 원티드 크롤러  
- `src/geocoding.py` - 주소→좌표 변환
- `map.html` - 지도 UI
- `data/` - 수집된 데이터
