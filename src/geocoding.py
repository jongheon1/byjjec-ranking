import requests
import time
import pandas as pd
import os
from typing import Dict, Optional, Tuple
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class GeocodingService:
    def __init__(self):
        # 환경 변수에서 API 키 읽기
        self.api_key_id = os.getenv('NAVER_MAP_API_KEY_ID')
        self.api_key = os.getenv('NAVER_MAP_API_KEY')
        
        # 환경 변수가 설정되지 않은 경우 에러 메시지
        if not self.api_key_id or not self.api_key:
            raise ValueError(
                "네이버 지도 API 키가 설정되지 않았습니다.\n"
                "다음 환경 변수를 설정해주세요:\n"
                "- NAVER_MAP_API_KEY_ID\n"
                "- NAVER_MAP_API_KEY"
            )
        
        self.base_url = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
        
    def get_coordinates(self, address: str) -> Optional[Tuple[float, float]]:
        """
        주소를 좌표로 변환합니다.
        
        Args:
            address: 변환할 주소
            
        Returns:
            (x, y) 좌표 튜플 또는 None
        """
        if not address or pd.isna(address) or address.strip() == '':
            return None
            
        headers = {
            'x-ncp-apigw-api-key-id': self.api_key_id,
            'x-ncp-apigw-api-key': self.api_key,
            'Accept': 'application/json'
        }
        
        params = {
            'query': address.strip()
        }
        
        try:
            response = requests.get(self.base_url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] == 'OK' and data['meta']['totalCount'] > 0:
                # 첫 번째 결과 사용
                first_address = data['addresses'][0]
                x = float(first_address['x'])
                y = float(first_address['y'])
                return (x, y)
            else:
                print(f"주소를 찾을 수 없음: {address}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"API 요청 오류 ({address}): {e}")
            return None
        except Exception as e:
            print(f"예상치 못한 오류 ({address}): {e}")
            return None
    
    def process_dataframe(self, df: pd.DataFrame, address_column: str = 'address') -> pd.DataFrame:
        """
        데이터프레임의 주소들을 좌표로 변환합니다.
        
        Args:
            df: 처리할 데이터프레임
            address_column: 주소가 들어있는 컬럼명
            
        Returns:
            x, y 컬럼이 추가된 데이터프레임
        """
        # 이미 x, y 컬럼이 있으면 건너뛰기
        if 'x' in df.columns and 'y' in df.columns:
            # 이미 처리된 행은 건너뛰고 비어있는 행만 처리
            need_processing = df[(df['x'].isna() | df['y'].isna()) & df[address_column].notna()]
        else:
            df['x'] = None
            df['y'] = None
            need_processing = df[df[address_column].notna()]
        
        total = len(need_processing)
        if total == 0:
            print("처리할 주소가 없습니다.")
            return df
            
        print(f"총 {total}개의 주소를 처리합니다...")
        
        for idx, (index, row) in enumerate(need_processing.iterrows(), 1):
            address = row[address_column]
            print(f"[{idx}/{total}] {row['company_name']}: {address}")
            
            coords = self.get_coordinates(address)
            if coords:
                df.at[index, 'x'] = coords[0]
                df.at[index, 'y'] = coords[1]
                print(f"  → 좌표: {coords[0]}, {coords[1]}")
            else:
                print(f"  → 좌표 변환 실패")
            
            # API 호출 제한을 위한 딜레이 (초당 10회 제한 고려)
            time.sleep(0.1)
        
        return df 