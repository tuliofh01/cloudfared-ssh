"""Flask view — REST API micro-service for tunnel control.

This is a **thin HTTP adapter** over the controllers.  All business
logic lives in the controllers; this module only maps HTTP verbs →
controller methods and serialises responses as JSON.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict

from flask import Flask, jsonify, request
from flask_cors import CORS

logger = logging.getLogger("cloudfared")


def create_app(
    *,
    start_fn: Callable[..., Dict[str, Any]],
    stop_fn: Callable[..., Dict[str, Any]],
    status_fn: Callable[..., Dict[str, Any]],
    logs_fn: Callable[..., Dict[str, Any]],
    health_fn: Callable[..., Dict[str, Any]],
    sysinfo_fn: Callable[..., Dict[str, Any]],
    cloudflared_fn: Callable[..., bool],
) -> Flask:
    """Build a configured Flask application.

    Each endpoint delegates to the injected callable so the view never
    imports controllers directly — that keeps the HTTP layer swappable.
    """
    app = Flask(__name__)
    CORS(app)

    # -- health ------------------------------------------------------------

    @app.route("/api/health")
    def health():
        return jsonify(health_fn())

    # -- tunnel ------------------------------------------------------------

    @app.route("/api/tunnel/start", methods=["POST"])
    def start():
        data = request.get_json(silent=True) or {}
        svc = data.get("service")
        return jsonify(start_fn(svc) if svc else start_fn())

    @app.route("/api/tunnel/stop", methods=["POST"])
    def stop():
        return jsonify(stop_fn())

    @app.route("/api/tunnel/status")
    def status():
        return jsonify(status_fn())

    # -- logs --------------------------------------------------------------

    @app.route("/api/logs")
    def logs():
        lines = request.args.get("lines", 100, type=int)
        return jsonify(logs_fn(lines))

    # -- system ------------------------------------------------------------

    @app.route("/api/system/info")
    def sysinfo():
        return jsonify(sysinfo_fn())

    # -- cloudflared check -------------------------------------------------

    @app.route("/api/cloudflared/check")
    def cloudflared_check():
        return jsonify({"installed": cloudflared_fn()})

    return app
