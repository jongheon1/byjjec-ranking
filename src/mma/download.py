"""병무청 엑셀 다운로드 모듈"""
import requests
import os
from pathlib import Path

from src.config import MMA_DOWNLOAD_URL, MMA_EXCEL_PATH


def download_all_companies(file_path: Path = MMA_EXCEL_PATH) -> Path:
    """전국 병역지정업체 목록을 한 번에 다운로드합니다."""
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if file_path.exists():
        print(f"[스킵] 이미 존재: {file_path}")
        return file_path

    # sido_addr를 비우면 전국 데이터
    params = {
        "eopjong_gbcd": "1",
        "al_eopjong_gbcd": "11111",
        "eopjong_gbcd_list": "11111",
        "eopjong_cd": "11111",
        "sido_addr": "",
    }

    print("전국 병역지정업체 다운로드 중...")
    response = requests.post(MMA_DOWNLOAD_URL, data=params, timeout=120)
    response.raise_for_status()

    with open(file_path, "wb") as f:
        f.write(response.content)

    print(f"[완료] {file_path}")
    return file_path
