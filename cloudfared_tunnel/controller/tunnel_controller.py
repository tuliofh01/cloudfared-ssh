"""Tunnel controller — owns TunnelProcess and mediates state transitions.

Fat controller: all tunnel business logic lives here, not in a service layer.
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional

from cloudfared_tunnel.model.config import AppConfig
from cloudfared_tunnel.model.state import StateStore
from cloudfared_tunnel.model.tunnel import TunnelProcess, TunnelState

logger = logging.getLogger("cloudfared")


class TunnelController:
    """Coordinates cloudflared lifecycle, state persistence, and log
    retrieval.  Single source of truth for "is the tunnel up?"."""

    def __init__(self, config: AppConfig, store: StateStore) -> None:
        self._cfg = config
        self._store = store
        self._proc = TunnelProcess()

    # -- lifecycle ---------------------------------------------------------

    def start(self, service_url: Optional[str] = None) -> Dict[str, Any]:
        """Start the tunnel and persist state.

        *service_url* overrides the config default when provided
        (e.g. on-the-fly HTTP → SSH switch).
        """
        url = service_url or self._cfg.service_url

        state = self._proc.start(
            tunnel_uuid=self._cfg.tunnel_uuid,
            config_path=self._cfg.config_path,
            service_url=url,
        )

        self._store.update(
            tunnel_status=state.status,
            tunnel_pid=state.pid,
            tunnel_started_at=state.started_at,
        )

        logger.info(
            "Tunnel start → %s  (pid=%s, url=%s)",
            state.status,
            state.pid,
            url,
        )
        return state.to_dict()

    def stop(self) -> Dict[str, Any]:
        """Stop the tunnel and persist state."""
        state = self._proc.stop()
        self._store.update(
            tunnel_status=state.status,
            tunnel_pid=None,
            tunnel_started_at=None,
        )
        logger.info("Tunnel stopped")
        return state.to_dict()

    def status(self) -> Dict[str, Any]:
        """Return fresh status reconciled with the OS process."""
        state = self._proc.refresh()
        return state.to_dict()

    # -- logs --------------------------------------------------------------

    def fetch_logs(self, lines: int = 100) -> Dict[str, Any]:
        """Return recent cloudflared + sshd logs.

        Reads both the rotating file handler *and* journald for sshd so
        operators can confirm SSH is actually accepting connections.
        """
        logs: list[str] = []

        # 1. Local app logs ------------------------------------------------
        log_file = self._cfg.log_dir / "tunnel.log"
        if log_file.exists():
            try:
                with open(log_file) as f:
                    logs.extend(f.readlines()[-lines:])
            except Exception:
                pass

        # 2. System journal for sshd ---------------------------------------
        try:
            result = subprocess.run(
                ["journalctl", "-u", "sshd", "-n", str(lines), "--no-pager"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout:
                logs.extend(result.stdout.splitlines())
        except Exception:
            pass

        # Deduplicate and trim
        seen: set = set()
        deduped: list[str] = []
        for line in reversed(logs):
            key = line.strip()
            if key not in seen:
                seen.add(key)
                deduped.append(line)
        deduped.reverse()

        return {"logs": deduped[-lines:], "count": min(len(deduped), lines)}

    # -- config helpers ----------------------------------------------------

    def ensure_config(self) -> str:
        """Auto-create a named tunnel + ``config.yml`` if none exists.

        Returns a status message describing what was done.
        """
        creds_dir = Path.home() / ".cloudflared"
        creds_dir.mkdir(parents=True, exist_ok=True)
        config_path = creds_dir / "config.yml"
        creds_file = creds_dir / "credentials.json"

        # Step 1 — see if cloudflared already knows a tunnel
        tunnel_name = "cloudfared-tunnel"
        try:
            result = subprocess.run(
                ["cloudflared", "tunnel", "list"],
                capture_output=True, text=True, timeout=10,
            )
            if tunnel_name in result.stdout:
                # Extract UUID from list output
                for line in result.stdout.splitlines():
                    if tunnel_name in line:
                        parts = line.split()
                        for p in parts:
                            if len(p) == 36 and p.count("-") == 4:
                                self._cfg.tunnel_uuid = p
                                break
                logger.info("Tunnel '%s' exists (UUID=%s)", tunnel_name, self._cfg.tunnel_uuid)
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            return f"cloudflared not available: {e}"

        # Step 2 — create tunnel if missing
        if not self._cfg.tunnel_uuid:
            try:
                result = subprocess.run(
                    ["cloudflared", "tunnel", "create", tunnel_name],
                    capture_output=True, text=True, timeout=15,
                )
                if result.returncode != 0:
                    return f"Failed to create tunnel: {result.stderr.strip()}"
                for line in result.stdout.splitlines():
                    if len(line) == 36 and line.count("-") == 4:
                        self._cfg.tunnel_uuid = line
                        break
                logger.info("Created tunnel '%s' (UUID=%s)", tunnel_name, self._cfg.tunnel_uuid)
            except subprocess.TimeoutExpired:
                return "Timed out creating tunnel"

        # Step 3 — write config.yml
        if config_path.exists():
            return f"Config already exists at {config_path}"

        hostname = os.getenv("TUNNEL_HOSTNAME", "ssh.example.com")
        config_yml = f"""tunnel: {self._cfg.tunnel_uuid}
credentials-file: {creds_file}

ingress:
  - hostname: {hostname}
    service: ssh://localhost:22
  - service: http_status:404
"""
        config_path.write_text(config_yml)
        logger.info("Wrote config.yml → %s", config_path)
        return f"Tunnel '{tunnel_name}' ready. Config at {config_path}"

    @staticmethod
    def check_cloudflared() -> bool:
        """Return True if ``cloudflared`` is on $PATH."""
        try:
            subprocess.run(
                ["cloudflared", "--version"],
                capture_output=True,
                timeout=5,
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
