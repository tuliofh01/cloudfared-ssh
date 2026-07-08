"""Tunnel — lifecycle: start, stop, status, one-liner."""

from __future__ import annotations

import time

from ..core.system import (
    is_active, service_action, service_status_text,
    cloudflared_version, tunnel_token, fetch_metric,
)
from ..core.state import load_state, save_state, format_uptime
from ..core.config import DOMAIN, SSH_USER


def tunnel_start() -> dict:
    token = tunnel_token()
    if not token:
        return {"status": "error", "message": "No token — run scripts/setup.sh"}
    service_action("start")
    time.sleep(1)
    active = is_active()
    state = load_state()
    state.update({"status": "running" if active else "error"})
    save_state(state)
    return {"status": "running" if active else "failed"}


def tunnel_stop() -> dict:
    service_action("stop")
    active = is_active()
    state = load_state()
    state.update({"status": "stopped" if not active else "error"})
    save_state(state)
    return {"status": "stopped" if not active else "failed"}


def tunnel_status() -> dict:
    active = is_active()
    ver = cloudflared_version()
    ha   = fetch_metric("cloudflared_tunnel_ha_connections")
    sess = fetch_metric("cloudflared_tcp_active_sessions")
    reqs = fetch_metric("cloudflared_tunnel_total_requests")
    up   = fetch_metric("cloudflared_tunnel_uptime_seconds")
    return {
        "active": active,
        "status": "running" if active else "stopped",
        "version": ver,
        "ha_connections": int(ha) if ha else 0,
        "active_sessions": int(sess) if sess else 0,
        "requests": int(reqs) if reqs else 0,
        "uptime_seconds": float(up) if up else 0.0,
        "service_status": service_status_text(),
        "token_ok": tunnel_token() is not None,
        "domain": DOMAIN,
        "ssh_user": SSH_USER,
    }


def status_line() -> str:
    s = tunnel_status()
    ha = s["ha_connections"]
    sess = s["active_sessions"]
    if not s["active"]:
        return "HOSTED VM OFF — tunnel stopped"
    if ha == 0:
        return "HOSTED VM — connecting..."
    if sess > 0:
        return f"HOSTED VM — {sess} active session{'s' if sess != 1 else ''}"
    return "HOSTED VM ON — tunnel active"
