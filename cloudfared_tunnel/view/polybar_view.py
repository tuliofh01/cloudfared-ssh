"""Polybar view — generates status snippets for Polybar ``custom/script``.

Output format follows the Polybar ``custom/script`` contract:

  - ``%{F#<color>}…%{F-}`` for coloured output
  - ``%{A1:<action>:}…%{A}`` for click handlers
"""

from __future__ import annotations

from typing import Any, Dict


# Polybar colour palette
_COLORS = {
    "running": "#00FF88",
    "starting": "Yellow",
    "stopped": "#FF5555",
    "crashed": "#FF0000",
    "connecting": "Yellow",
}


def polybar_status_line(status: Dict[str, Any]) -> str:
    """Return a single-line status string for Polybar ``custom/script``.

    Click actions:
      - Left click  → start tunnel
      - Right click → stop tunnel
      - Middle click → open URL in browser
    """
    state = status.get("status", "stopped")
    url = status.get("url", "Not Connected")

    color = _COLORS.get(state, "White")
    icon = _polybar_icon(state)

    label = state.upper()
    if state == "running":
        label = url or "TUNNEL"

    line = f"%{{F{color}}}{icon} {label}%{{F-}}"

    # Click handlers  (A1 = left, A3 = right, A2 = middle)
    start_action = "cloudfared-tunneling start"
    stop_action = "cloudfared-tunneling stop"
    open_action = f"xdg-open {url}" if url and url.startswith("http") else ""

    line = f"%{{A1:{start_action}:}}{line}%{{A}}"
    line = f"%{{A3:{stop_action}:}}{line}%{{A}}"
    if open_action:
        line = f"%{{A2:{open_action}:}}{line}%{{A}}"

    return line


def polybar_status_short(status: Dict[str, Any]) -> str:
    """Ultra-compact output — icon + one char."""
    state = status.get("status", "stopped")
    color = _COLORS.get(state, "White")
    icon = _polybar_icon(state)
    return f"%{{F{color}}}{icon}%{{F-}}"


# -- internal helpers ------------------------------------------------------

def _polybar_icon(state: str) -> str:
    """Return a single-character icon for the given tunnel state."""
    icons = {
        "running": "力",   # nf-fa-cloud (or use a simple ASCII fallback)
        "starting": "",
        "stopped": "ﱙ",
        "crashed": "",
        "connecting": "",
    }
    return icons.get(state, "")  # circle with exclamation
