"""Polybar view — generates status snippets for Polybar ``custom/script``.

Output format follows the Polybar ``custom/script`` contract:

  - ``%{F#<color>}…%{F-}`` for coloured output
  - ``%{A1:<action>:}…%{A}`` for click handlers
"""

from __future__ import annotations

from typing import Any, Dict


_PALETTE = {
    "running":  "#00FF88",
    "starting": "#EBD369",
    "stopped":  "#FF5555",
    "crashed":  "#FF0000",
    "connecting": "#EBD369",
    "noapi":    "#EC7875",
}

_ICONS = {
    "running":    "\U0001f512",
    "starting":   "\u23f3",
    "stopped":    "\U0001f513",
    "crashed":    "\u26a0\ufe0f",
    "connecting": "\u23f3",
    "noapi":      "\u26a0\ufe0f",
}


def polybar_status_line(status: Dict[str, Any]) -> str:
    state = status.get("status", "stopped")
    url = status.get("url", "Not Connected")

    color = _PALETTE.get(state, "#FFFFFF")
    icon = _ICONS.get(state, "\u26a0")

    if state == "running" and url and url != "Not Connected":
        label = f"{icon} ON  %{{F#89b4fa}}{url}%{{F-}}"
    elif state == "noapi":
        label = f"{icon} NO API"
    else:
        label = f"{icon} {state.upper()}"

    line = f"%{{F{color}}}{label}%{{F-}}"

    start_action = "curl -s -X POST http://localhost:5000/api/tunnel/start >/dev/null"
    stop_action  = "curl -s -X POST http://localhost:5000/api/tunnel/stop >/dev/null"
    open_action  = f"xdg-open {url}" if url and url != "Not Connected" and url.startswith("http") else ""

    line = f"%{{A1:{start_action}:}}{line}%{{A}}"
    line = f"%{{A3:{stop_action}:}}{line}%{{A}}"
    if open_action:
        line = f"%{{A2:{open_action}:}}{line}%{{A}}"

    return line


def polybar_short(status: Dict[str, Any]) -> str:
    state = status.get("status", "stopped")
    color = _PALETTE.get(state, "#FFFFFF")
    icon = _ICONS.get(state, "\u26a0")
    return f"%{{F{color}}}{icon}%{{F-}}"
