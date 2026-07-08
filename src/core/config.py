"""Config — constants, paths, and .env loading."""

from __future__ import annotations

import os
from pathlib import Path

STATE_DIR   = Path.home() / ".cloudfared-tunneling"
STATE_FILE  = STATE_DIR / "state.json"
TOKEN_FILE  = Path.home() / ".cloudflared" / "tunnel-token"

VERSION     = "2.0.0"
DOMAIN      = "ssh.your-domain.com"
SSH_USER    = "duke"
SERVICE_NM  = "cloudflared-tunnel.service"
METRICS_URL = "http://127.0.0.1:20241/metrics"

_ENV_LOADED = False


def load_env() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
    except FileNotFoundError:
        pass


load_env()

DOMAIN      = os.environ.get("DOMAIN", DOMAIN)
SSH_USER    = os.environ.get("SSH_USER", SSH_USER)
SERVICE_NM  = os.environ.get("SERVICE_NAME", SERVICE_NM)
METRICS_URL = os.environ.get("METRICS_URL", METRICS_URL)

os.makedirs(STATE_DIR, exist_ok=True)
os.makedirs(Path.home() / ".cloudflared", exist_ok=True)
