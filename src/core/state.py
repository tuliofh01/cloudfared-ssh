"""State — JSON persistence and formatting."""

from __future__ import annotations

import json
import time

from .config import STATE_FILE


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {"status": "stopped", "timestamp": 0, "ha_connections": 0}


def save_state(d: dict) -> None:
    d["timestamp"] = int(time.time())
    STATE_FILE.write_text(json.dumps(d, indent=2))


def format_uptime(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h > 24:
        d, h = divmod(h, 24)
        return f"{d}d {h}h {m}m"
    return f"{h}h {m}m"
