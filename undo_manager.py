"""
UndoManager — 记录每次注册表修改，支持回滚
"""
import json
import os
import time
from dataclasses import dataclass, asdict


@dataclass
class FixRecord:
    timestamp: str
    issue_id: str
    title: str
    key_path: str
    value_name: str
    old_value: int
    new_value: int


class UndoManager:
    def __init__(self, store_path: str):
        self.store_path = store_path
        self.records: list[FixRecord] = []
        self._load()

    def _load(self):
        if os.path.exists(self.store_path):
            try:
                with open(self.store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.records = [FixRecord(**r) for r in data]
            except (json.JSONDecodeError, TypeError):
                self.records = []

    def _save(self):
        with open(self.store_path, "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in self.records], f, indent=2, ensure_ascii=False)

    def record(self, issue_id: str, title: str, key_path: str,
               value_name: str, old_value: int, new_value: int):
        r = FixRecord(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            issue_id=issue_id,
            title=title,
            key_path=key_path,
            value_name=value_name,
            old_value=old_value,
            new_value=new_value,
        )
        self.records.append(r)
        self._save()

    def undo_last(self) -> FixRecord | None:
        if not self.records:
            return None
        r = self.records.pop()
        self._save()
        return r

    def undo_all(self) -> list[FixRecord]:
        reversed_records = list(reversed(self.records))
        self.records.clear()
        self._save()
        return reversed_records

    def count(self) -> int:
        return len(self.records)

    def get_records(self) -> list[FixRecord]:
        return list(self.records)
