"""cloudfared-tunnel — hosted VM management via Cloudflare Tunnel.

Usage:
    python3 -m src                   # TUI dashboard
    python3 -m src --status          # One-liner for scripts
"""

from .controller.tunnel import tunnel_start, tunnel_stop, tunnel_status, status_line
from .controller.cli import main

__all__ = ["tunnel_start", "tunnel_stop", "tunnel_status", "status_line", "main"]
