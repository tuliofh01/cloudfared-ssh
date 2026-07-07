"""Syncer controller — background state sync to the Cloudflare Worker.

Fat controller: owns the sync loop, log buffering, and HTTP communication
with the remote Worker API.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, List, Optional

import requests

from cloudfared_tunnel.model.config import AppConfig
from cloudfared_tunnel.model.state import StateStore

logger = logging.getLogger("cloudfared")


class SyncerController:
    """Periodically pushes tunnel status + incremental logs to the remote
    Cloudflare Worker endpoint.

    Runs its own daemon thread so the Flask service stays responsive.
    """

    def __init__(
        self,
        config: AppConfig,
        store: StateStore,
        # The tunnel-controller is injected so we can read live status
        # without coupling the syncer to a particular transport.
        status_fn: Any,  # callable[[], dict]
        logs_fn: Any,  # callable[[int], dict]
    ) -> None:
        self._cfg = config
        self._store = store
        self._status_fn = status_fn
        self._logs_fn = logs_fn

        self._last_log_count = 0
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            logger.debug("Syncer already running")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="syncer",
        )
        self._thread.start()
        logger.info("Syncer started (interval=%ds)", self._cfg.sync_interval)

    def stop(self) -> None:
        self._stop_event.set()
        logger.info("Syncer stopped")

    # -- core loop ---------------------------------------------------------

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._sync()
                self._store.mark_sync_ok()
            except Exception as exc:
                self._store.mark_sync_error(str(exc))
                logger.debug("Sync failed: %s", exc)
            self._stop_event.wait(self._cfg.sync_interval)

    def _sync(self) -> None:
        """Assemble payload and POST to Worker."""
        status = self._status_fn()
        logs_data = self._logs_fn(100)
        all_logs: List[str] = logs_data.get("logs", [])
        current_count = len(all_logs)

        # Compute delta
        new_logs: List[str] = []
        if current_count > self._last_log_count:
            new_logs = all_logs[self._last_log_count:]
        elif current_count < self._last_log_count:
            new_logs = all_logs  # log rotation – send everything

        self._last_log_count = current_count

        payload: Dict[str, Any] = {
            "tunnelUrl": status.get("url", "Not Connected"),
            "tunnelStatus": status.get("status", "unknown"),
            "logs": new_logs,
            "timestamp": int(time.time() * 1000),
        }

        headers: Dict[str, str] = {}
        if self._cfg.has_tunnel_secret:
            headers["Authorization"] = f"Bearer {self._cfg.tunnel_secret}"

        resp = requests.post(
            f"{self._cfg.worker_url}/api/tunnel",
            json=payload,
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
