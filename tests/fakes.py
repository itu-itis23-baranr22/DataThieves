# tests/fakes.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class FakeCursor:
    """
    Very small fake cursor that can:
    - capture executed SQL + params
    - return pre-planned results via a queue
    """
    executed: List[Tuple[str, Tuple[Any, ...]]] = field(default_factory=list)
    _fetchone_queue: List[Optional[Dict[str, Any]]] = field(default_factory=list)
    _fetchall_queue: List[List[Dict[str, Any]]] = field(default_factory=list)
    closed: bool = False

    def plan_fetchone(self, *rows: Optional[Dict[str, Any]]) -> None:
        self._fetchone_queue.extend(rows)

    def plan_fetchall(self, *rows_list: List[Dict[str, Any]]) -> None:
        self._fetchall_queue.extend(rows_list)

    def execute(self, sql: str, params: Tuple[Any, ...] = ()) -> None:
        self.executed.append((sql, tuple(params)))

    def fetchone(self) -> Optional[Dict[str, Any]]:
        if self._fetchone_queue:
            return self._fetchone_queue.pop(0)
        return None

    def fetchall(self) -> List[Dict[str, Any]]:
        if self._fetchall_queue:
            return self._fetchall_queue.pop(0)
        return []

    def close(self) -> None:
        self.closed = True


@dataclass
class FakeConnection:
    cursor_obj: FakeCursor

    def cursor(self) -> FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        return

    def rollback(self) -> None:
        return


@dataclass
class FakeMySQL:
    cursor_obj: FakeCursor = field(default_factory=FakeCursor)

    def init_app(self, app):
        return

    @property
    def connection(self) -> FakeConnection:
        return FakeConnection(self.cursor_obj)
