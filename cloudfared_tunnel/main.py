#!/usr/bin/env python3
"""cloudfared-tunneling — CLI entry point.

Procedural main(): parses arguments, wires up Model → Controller → View,
then dispatches to the appropriate handler.  OOP classes do the heavy
lifting behind the scenes.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

import psutil

from cloudfared_tunnel.model.config import AppConfig
from cloudfared_tunnel.model.state import StateStore
from cloudfared_tunnel.controller.tunnel_controller import TunnelController
from cloudfared_tunnel.controller.syncer_controller import SyncerController
from cloudfared_tunnel.view.cli_view import CLIView
from cloudfared_tunnel.view.flask_view import create_app


# ---------------------------------------------------------------------------
# Logging setup (called once from main)
# ---------------------------------------------------------------------------

def _setup_logging(cfg: AppConfig) -> logging.Logger:
    log = logging.getLogger("cloudfared")
    log.setLevel(logging.DEBUG if os.getenv("DEBUG") else logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Rotating file handler (10 MB × 5 = 50 MB cap)
    rf = RotatingFileHandler(
        cfg.log_dir / "tunnel.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    rf.setFormatter(fmt)
    log.addHandler(rf)

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    log.addHandler(ch)

    return log


# ---------------------------------------------------------------------------
# Health / system helpers (used by both CLI and Flask)
# ---------------------------------------------------------------------------

def _health() -> dict:
    from datetime import datetime
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


def _sysinfo() -> dict:
    try:
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.5),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
            "uptime": int(__import__("time").time() - psutil.boot_time()),
        }
    except Exception as exc:
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    cfg = AppConfig()
    logger = _setup_logging(cfg)
    store = StateStore()
    tunnel = TunnelController(cfg, store)

    # Fetch-methods shared between CLI and Flask
    def _status() -> dict:
        return tunnel.status()

    def _logs(lines: int = 100) -> dict:
        return tunnel.fetch_logs(lines)

    syncer = SyncerController(cfg, store, _status, _logs)

    parser = argparse.ArgumentParser(
        prog="cloudfared-tunneling",
        description="Cloudflare Tunnel Manager — CLI & API",
    )
    parser.add_argument(
        "--serve", action="store_true",
        help="Start Flask API server (micro-service 1)"
    )
    parser.add_argument("--host", default=cfg.flask_host)
    parser.add_argument("--port", type=int, default=cfg.flask_port)

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show tunnel status")
    sub.add_parser("start", help="Start tunnel")
    sub.add_parser("stop", help="Stop tunnel")
    sub.add_parser("logs", help="Show recent logs")
    sub.add_parser("health", help="Health check")
    sub.add_parser("sysinfo", help="System resource usage")
    sub.add_parser("check", help="Verify cloudflared is installed")

    args = parser.parse_args()

    # -- CLI mode ----------------------------------------------------------
    if args.command:
        view = CLIView()

        if args.command == "status":
            view.show_status(_status())

        elif args.command == "start":
            syncer.start()
            result = tunnel.start()
            view.show_result("start", result)
            view.show_status(_status())

        elif args.command == "stop":
            result = tunnel.stop()
            syncer.stop()
            view.show_result("stop", result)
            view.show_status(_status())

        elif args.command == "logs":
            view.show_logs(_logs())

        elif args.command == "health":
            view.show_health(_health())

        elif args.command == "sysinfo":
            view.show_system(_sysinfo())

        elif args.command == "check":
            view.show_cloudflared_check(tunnel.check_cloudflared())

        sys.exit(0)

    # -- Server mode -------------------------------------------------------
    if args.serve:
        syncer.start()

        app = create_app(
            start_fn=lambda svc=None: tunnel.start(svc),
            stop_fn=tunnel.stop,
            status_fn=_status,
            logs_fn=_logs,
            health_fn=_health,
            sysinfo_fn=_sysinfo,
            cloudflared_fn=tunnel.check_cloudflared,
        )

        logger.info(
            "Starting API server on %s:%s", args.host, args.port
        )
        app.run(host=args.host, port=args.port)
        return

    # -- No args -----------------------------------------------------------
    parser.print_help()


if __name__ == "__main__":
    main()
