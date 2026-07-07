"""State model — durable JSON persistence for tunnel + sync state."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, Optional


STATE_FILE = Path.home() / ".cloudfared-tunneling" / "state.json"


@dataclass
class DurableState:
    """Persisted state that survives process restarts.

    Written atomically to ``~/.cloudfared-tunneling/state.json``
    every time the tunnel status changes.
    """

    tunnel_url: str = "Not Connected"
    tunnel_pid: Optional[int] = None
    tunnel_status: str = "stopped"
    tunnel_started_at: Optional[float] = None
    last_seen_url: str = "Not Connected"
    sync_count: int = 0
    last_sync_ok: Optional[float] = None
    last_sync_error: Optional[str] = None
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DurableState:
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


class StateStore:
    """Thread-safe, atomic JSON persistence for DurableState."""

    def __init__(self, path: Path = STATE_FILE) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._state = self._load()

    # -- public access ----------------------------------------------------

    @property
    def state(self) -> DurableState:
        return self._state

    def update(self, **kwargs: Any) -> DurableState:
        for k, v in kwargs.items():
            if hasattr(self._state, k):
                setattr(self._state, k, v)
        self._persist()
        return self._state

    def mark_sync_ok(self) -> None:
        self._state.sync_count += 1
        self._state.last_sync_ok = time.time()
        self._persist()

    def mark_sync_error(self, error: str) -> None:
        self._state.last_sync_error = error
        self._persist()

    # -- internals --------------------------------------------------------

    def _load(self) -> DurableState:
        if not self._path.exists():
            return DurableState()
        try:
            raw = self._path.read_text().strip()
            if not raw:
                return DurableState()
            return DurableState.from_dict(json.loads(raw))
        except (json.JSONDecodeError, Exception):
            return DurableState()

    def _persist(self) -> None:
        tmp = self._path.with_suffix(".json.tmp")
        try:
            tmp.write_text(
                json.dumps(self._state.to_dict(), indent=2, default=str)
            )
            tmp.rename(self._path)
        except Exception:
            if tmp.exists():
                tmp.unlink()
