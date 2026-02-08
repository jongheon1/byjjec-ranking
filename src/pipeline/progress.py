"""진행상황 관리 모듈 - 중단/재시작 지원"""
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from src.config import PROGRESS_DIR


class ProgressTracker:
    """크롤링 진행상황 추적기"""

    def __init__(self, name: str):
        self.name = name
        self.file_path = PROGRESS_DIR / f"{name}_progress.json"
        self.data = self._load()

    def _load(self) -> dict:
        """진행상황 파일 로드"""
        if self.file_path.exists():
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "completed": {},  # company_id -> result
            "failed": {},  # company_id -> error message
            "lastUpdated": None,
        }

    def save(self):
        """진행상황 저장"""
        self.data["lastUpdated"] = datetime.now().isoformat()
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def is_completed(self, company_id: str) -> bool:
        """회사가 이미 처리되었는지 확인"""
        return company_id in self.data["completed"]

    def is_failed(self, company_id: str) -> bool:
        """회사 처리가 실패했는지 확인"""
        return company_id in self.data["failed"]

    def get_result(self, company_id: str) -> Optional[dict]:
        """처리 결과 조회"""
        return self.data["completed"].get(company_id)

    def mark_completed(self, company_id: str, result: dict):
        """처리 완료로 표시"""
        self.data["completed"][company_id] = result
        # 실패 목록에서 제거
        if company_id in self.data["failed"]:
            del self.data["failed"][company_id]
        self.save()

    def mark_failed(self, company_id: str, error: str):
        """처리 실패로 표시"""
        self.data["failed"][company_id] = error
        self.save()

    def get_pending(self, all_ids: list[str]) -> list[str]:
        """아직 처리하지 않은 ID 목록 반환"""
        completed = set(self.data["completed"].keys())
        return [id for id in all_ids if id not in completed]

    def get_stats(self) -> dict:
        """통계 반환"""
        return {
            "completed": len(self.data["completed"]),
            "failed": len(self.data["failed"]),
            "lastUpdated": self.data["lastUpdated"],
        }

    def reset(self):
        """진행상황 초기화"""
        self.data = {
            "completed": {},
            "failed": {},
            "lastUpdated": None,
        }
        self.save()

    def reset_failed(self):
        """실패한 항목만 재시도 가능하게 초기화"""
        self.data["failed"] = {}
        self.save()
