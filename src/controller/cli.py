"""CLI — entry point, argument parsing, --help."""

from __future__ import annotations

import json
import sys

from ..core.config import VERSION
from ..core.system import read_logs
from .tunnel import tunnel_start, tunnel_stop, status_line

__doc__ = f"""cloudfared-tunnel v{VERSION} — hosted VM management via Cloudflare Tunnel

Usage:
  python3 -m src                  TUI dashboard
  python3 -m src --status          One-line status
  python3 -m src --on              Start tunnel
  python3 -m src --off             Stop tunnel
  python3 -m src --logs            Dump journal logs
  python3 -m src --help            This message
"""


def main() -> None:
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--status":
            print(status_line())
        elif arg == "--on":
            print(json.dumps(tunnel_start()))
        elif arg == "--off":
            print(json.dumps(tunnel_stop()))
        elif arg == "--logs":
            for line in read_logs(50):
                print(line)
        elif arg in ("--help", "-h"):
            print(__doc__)
        else:
            print(f"Unknown argument: {arg}", file=sys.stderr)
            print(__doc__)
            sys.exit(1)
    else:
        try:
            import curses
            from ..view.tui import main_tui
            curses.wrapper(main_tui)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
