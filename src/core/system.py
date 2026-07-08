"""System — subprocess, systemd, cloudflared, metrics."""

from __future__ import annotations

import subprocess
import urllib.request
from typing import Optional

from .config import SERVICE_NM, METRICS_URL, TOKEN_FILE


def _run(cmd: list[str], timeout: int = 10) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return subprocess.CompletedProcess(cmd, -1, "", "binary not found")
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, -1, "", "timed out")


def service_action(action: str) -> str:
    r = _run(["systemctl", "--user", action, SERVICE_NM])
    return r.stdout.strip() or r.stderr.strip()


def is_active() -> bool:
    return _run(["systemctl", "--user", "is-active", SERVICE_NM]).stdout.strip() == "active"


def service_status_text() -> str:
    r = _run(["systemctl", "--user", "is-active", SERVICE_NM])
    s = r.stdout.strip()
    if s == "active":
        r2 = _run(["systemctl", "--user", "show", SERVICE_NM,
                    "--property=ActiveEnterTimestamp"])
        ts = r2.stdout.strip().replace("ActiveEnterTimestamp=", "")
        return f"running  since {ts[:16]}" if ts else "running"
    return s if s else "not found"


def cloudflared_version() -> str:
    r = _run(["cloudflared", "--version"])
    return r.stdout.strip() or r.stderr.strip() or "not found"


def read_logs(n: int = 30) -> list[str]:
    r = _run(["journalctl", "--user", "-u", SERVICE_NM,
               "-n", str(n), "--no-pager", "-o", "short-iso"])
    return r.stdout.strip().splitlines() if r.stdout.strip() else ["(no logs yet)"]


def tunnel_token() -> Optional[str]:
    try:
        return TOKEN_FILE.read_text().strip()
    except FileNotFoundError:
        return None


def fetch_metric(pattern: str) -> Optional[str]:
    try:
        data = urllib.request.urlopen(METRICS_URL, timeout=3).read().decode()
        for line in data.splitlines():
            if line.startswith(pattern):
                return line.split()[-1]
    except Exception:
        return None
