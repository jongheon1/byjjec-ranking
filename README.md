## 프로젝트 개요

본 프로젝트는 병역 지정 업체의 리스트를 다운로드하고, 각 업체의 평점, 리뷰 수, 채용 공고 수를 잡플래닛에서 크롤링하여 엑셀 형식으로 요약하는 시스템입니다.

## 기능

- **데이터 다운로드**: 고용노동부 웹사이트에서 병역 지정 업체 리스트를 자동으로 다운로드합니다.
- **정보 크롤링**: 잡플래닛에서 각 업체의 평점, 리뷰 수, 채용 공고 수를 크롤링합니다.
- **데이터 처리 및 저장**: 크롤링된 데이터를 분석하고, 엑셀 파일로 요약하여 저장합니다.

## 사용 기술

- **Python**: 프로그래밍 언어
- **Pandas**: 데이터 처리
- **Selenium**: 웹 크롤링

## 설치 및 실행 방법

1. 이 프로젝트의 저장소를 클론합니다:
        
    `git clone https://github.com/yourusername/your-repository.git`
    
2. 필요한 라이브러리를 설치합니다:

    `pip install -r requirements.txt`
    
4. 스크립트를 실행하여 데이터를 다운로드하고 크롤링합니다:

    `python main.py`

## 결과 예시
| (주)비바리퍼블리카 | 3.6 | 305 | 0  | 강남구 | 2015 |

| (주)에이아이트릭스 | 3.6 | 25  | 16 | 강남구 | 2019 |

| (주)이지식스    | 3.6 | 11  | 5  | 강남구 | 2017 |

| (주)팀오투     | 3.6 | 17  | 0  | 강남구 | 2020 |

| (주)퍼블리     | 3.6 | 305 | 0  | 강남구 | 2022 |

| 데브시스터즈(주)  | 3.6 | 206 | 3  | 강남구 | 2011 |
