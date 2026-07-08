"""View — curses TUI dashboard for the hosted VM tunnel."""

from __future__ import annotations

import curses
import os
import subprocess
import time

from ..core.config import VERSION, DOMAIN
from ..core.state import format_uptime
from ..core.system import read_logs
from ..controller.tunnel import tunnel_start, tunnel_stop, tunnel_status

SSH_USER = "duke"


# ── First-run password prompt ────────────────────────────────────────

def _duke_has_password() -> bool:
    """Check if the duke user has a password set."""
    try:
        result = subprocess.run(
            ["passwd", "--status", SSH_USER],
            capture_output=True, text=True, timeout=5,
        )
        # Format: "duke P 2026-01-01 ..." (P=password set, NP=no password, L=locked)
        fields = result.stdout.strip().split()
        return len(fields) >= 2 and fields[1] == "P"
    except (subprocess.TimeoutExpired, FileNotFoundError, IndexError):
        return True  # Assume OK if we can't check


def _set_duke_password(password: str) -> tuple[bool, str]:
    """Set duke's password. Returns (success, message)."""
    user = os.environ.get("USER", "")
    try:
        if user == "root":
            proc = subprocess.run(
                ["passwd", SSH_USER],
                input=f"{password}\n{password}\n",
                capture_output=True, text=True, timeout=10,
            )
        else:
            proc = subprocess.run(
                ["sudo", "passwd", SSH_USER],
                input=f"{password}\n{password}\n",
                capture_output=True, text=True, timeout=10,
            )
        return (proc.returncode == 0, proc.stderr.strip() or proc.stdout.strip())
    except subprocess.TimeoutExpired:
        return (False, "Timed out setting password")


def _password_prompt(stdscr) -> None:
    """Curses form to set duke's password on first run."""
    curses.curs_set(1)
    stdscr.erase()
    rows, cols = stdscr.getmaxyx()

    prompt_lines = [
        "╔══════════════════════════════════════════════════════════╗",
        "║          First Run — Set duke SSH Password              ║",
        "╠══════════════════════════════════════════════════════════╣",
        "║  The 'duke' user has no password set.                   ║",
        "║  This password is used for SSH access to this VM.       ║",
        "║                                                         ║",
        "║  You will need sudo privileges to set it.               ║",
        "╚══════════════════════════════════════════════════════════╝",
        "",
        "  Password: ",
        "  Confirm:  ",
        "",
        "  [Enter] Set password   [Q] Quit",
    ]

    y_offset = max(0, (rows - len(prompt_lines)) // 2)
    for i, line in enumerate(prompt_lines):
        try:
            x = max(0, (cols - len(line)) // 2) if "║" in line else 4
            attr = curses.A_BOLD if "║" in line and "duke" in line else curses.A_NORMAL
            stdscr.addstr(y_offset + i, x, line, attr)
        except curses.error:
            pass

    pw_input_y = y_offset + 9
    cf_input_y = y_offset + 10
    pw_x = 16

    curses.echo(False)
    password = ""
    confirm = ""

    while True:
        # Clear input fields
        try:
            stdscr.addstr(pw_input_y, pw_x, " " * (cols - pw_x - 4))
            stdscr.addstr(cf_input_y, pw_x, " " * (cols - pw_x - 4))
        except curses.error:
            pass

        # Draw masked password
        try:
            stdscr.addstr(pw_input_y, pw_x, "*" * len(password), curses.A_BOLD)
            stdscr.addstr(cf_input_y, pw_x, "*" * len(confirm), curses.A_BOLD)
        except curses.error:
            pass

        # Prompt for password
        try:
            stdscr.move(pw_input_y, pw_x + len(password))
        except curses.error:
            pass
        stdscr.refresh()

        # Read password field
        password = ""
        while True:
            ch = stdscr.getch()
            if ch in (ord("\n"), ord("\r"), curses.KEY_ENTER):
                break
            elif ch in (ord("q"), ord("Q"), 27):
                return
            elif ch in (curses.KEY_BACKSPACE, 127, 8):
                password = password[:-1]
            elif 32 <= ch <= 126:
                password += chr(ch)
            try:
                stdscr.addstr(pw_input_y, pw_x, "*" * len(password), curses.A_BOLD)
                stdscr.move(pw_input_y, pw_x + len(password))
            except curses.error:
                pass
            stdscr.refresh()

        # Read confirm field
        confirm = ""
        while True:
            ch = stdscr.getch()
            if ch in (ord("\n"), ord("\r"), curses.KEY_ENTER):
                break
            elif ch in (ord("q"), ord("Q"), 27):
                return
            elif ch in (curses.KEY_BACKSPACE, 127, 8):
                confirm = confirm[:-1]
            elif 32 <= ch <= 126:
                confirm += chr(ch)
            try:
                stdscr.addstr(cf_input_y, pw_x, "*" * len(confirm), curses.A_BOLD)
                stdscr.move(cf_input_y, pw_x + len(confirm))
            except curses.error:
                pass
            stdscr.refresh()

        if not password:
            continue

        if password != confirm:
            try:
                msg = "  Passwords do not match — try again"
                stdscr.addstr(cf_input_y + 2, 4, msg, curses.color_pair(1))
                stdscr.refresh()
            except curses.error:
                pass
            time.sleep(1.5)
            continue

        if len(password) < 4:
            try:
                msg = "  Password too short — minimum 4 characters"
                stdscr.addstr(cf_input_y + 2, 4, msg, curses.color_pair(1))
                stdscr.refresh()
            except curses.error:
                pass
            time.sleep(1.5)
            continue

        # Set the password
        ok, msg = _set_duke_password(password)
        try:
            if ok:
                stdscr.addstr(cf_input_y + 2, 4, "  Password set successfully!", curses.color_pair(2) | curses.A_BOLD)
            else:
                stdscr.addstr(cf_input_y + 2, 4, f"  Failed: {msg[:cols-20]}", curses.color_pair(1) | curses.A_BOLD)
            stdscr.refresh()
        except curses.error:
            pass
        time.sleep(1.5)
        break

    curses.curs_set(0)


# ── TUI Dashboard ────────────────────────────────────────────────────

def _init_colors() -> None:
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_RED, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_CYAN, -1)
    curses.init_pair(4, curses.COLOR_YELLOW, -1)
    curses.init_pair(5, curses.COLOR_MAGENTA, -1)


def _draw_outer_top(stdscr, cols: int) -> None:
    try:
        stdscr.addstr(0, 0, "╔" + "═" * (cols - 2) + "╗", curses.A_BOLD)
    except curses.error:
        pass


def _draw_outer_bottom(stdscr, rows: int, cols: int) -> None:
    try:
        stdscr.addstr(rows - 1, 0, "╚" + "═" * (cols - 2) + "╝", curses.A_DIM)
    except curses.error:
        pass


def _draw_title_bar(stdscr, cols: int, active: bool) -> None:
    title = f" cloudfared-tunnel v{VERSION} "
    domain = f" {DOMAIN} "
    hints = " [S]tart/[S]top [R]estart [L]ogs [Q]uit "
    color = (curses.color_pair(2) | curses.A_BOLD) if active else (curses.color_pair(1) | curses.A_BOLD)
    filler = max(cols - len(title) - len(domain) - len(hints) - 4, 1)
    try:
        stdscr.addstr(1, 0, f"║{title}║{' ' * filler}║{domain}║{hints}║", color)
    except curses.error:
        pass


def _draw_separator(stdscr, y: int, cols: int, char: str = "─") -> None:
    try:
        stdscr.addstr(y, 0, "╟" + char * (cols - 2) + "╢", curses.A_DIM)
    except curses.error:
        pass


def _panel_write(stdscr, y: int, x: int, text: str, attr: int = curses.A_NORMAL) -> None:
    try:
        stdscr.addstr(y, x, text, attr)
    except curses.error:
        pass


def main_tui(stdscr) -> None:
    curses.curs_set(0)
    _init_colors()
    stdscr.timeout(2000)
    show_logs = False
    log_buffer: list[str] = []

    # ── First-run: check duke password ──────────────────────────────
    if not _duke_has_password():
        _password_prompt(stdscr)

    # ── Main loop ───────────────────────────────────────────────────
    while True:
        stdscr.erase()
        rows, cols = stdscr.getmaxyx()
        if rows < 16 or cols < 58:
            stdscr.addstr(0, 0, "Terminal too small — resize to at least 58×16")
            stdscr.refresh()
            time.sleep(1.5)
            continue

        s = tunnel_status()
        active = s["active"]
        y = 0

        _draw_outer_top(stdscr, cols)
        _draw_title_bar(stdscr, cols, active)
        _draw_separator(stdscr, 2, cols)
        y = 3

        sc = curses.color_pair(2) if active else curses.color_pair(1)
        ver = s["version"].replace("cloudflared version ", "") if s["version"] != "not found" else "not found"
        _panel_write(stdscr, y, 2, f"  ●  HOSTED VM {'ACTIVE' if active else 'STOPPED'}    cloudflared {ver}", sc | curses.A_BOLD)
        y += 2

        if not show_logs:
            _panel_write(stdscr, y, 2, "Connection", curses.color_pair(3) | curses.A_BOLD)
            for line in (f"  SSH:      {s['ssh_user']}@{s['domain']}",
                         f"  Token:    {'✓ configured' if s['token_ok'] else '✗ missing'}",
                         f"  Service:  {s['service_status']}"):
                y += 1
                _panel_write(stdscr, y, 4, line)
            y += 2

            _panel_write(stdscr, y, 2, "Metrics", curses.color_pair(3) | curses.A_BOLD)
            up = format_uptime(s["uptime_seconds"]) if s["uptime_seconds"] > 0 else "—"
            for line in (f"  HA connections    {s['ha_connections']}",
                         f"  Active sessions   {s['active_sessions']}",
                         f"  Total requests    {s['requests']}",
                         f"  Uptime            {up}"):
                y += 1
                _panel_write(stdscr, y, 4, line)
            y += 2

            _panel_write(stdscr, y, 2, "Quick Connect", curses.color_pair(3) | curses.A_BOLD)
            y += 1
            _panel_write(stdscr, y, 4, f"  $ ssh {s['ssh_user']}@{s['domain']}")
            y += 1
            _panel_write(stdscr, y, 4, "  Config:  ProxyCommand cloudflared access ssh --hostname %h", curses.A_DIM)
            y += 2
        else:
            if not log_buffer:
                log_buffer = read_logs(max(rows - y - 2, 10))
            _panel_write(stdscr, y, 2, "Service Logs  ([L] back, [Q] quit)", curses.color_pair(3) | curses.A_BOLD)
            y += 1
            for i, ln in enumerate(log_buffer[-(rows - y - 1):]):
                _panel_write(stdscr, y + i, 2, f"  {ln[:cols-4] if len(ln) > cols-4 else ln}", curses.A_DIM)

        _draw_outer_bottom(stdscr, rows, cols)
        stdscr.refresh()

        key = stdscr.getch()
        if key in (ord('q'), ord('Q'), 27):
            break
        elif key in (ord('s'), ord('S')):
            tunnel_stop() if s["active"] else tunnel_start()
            log_buffer = []
        elif key in (ord('r'), ord('R')):
            tunnel_stop()
            time.sleep(0.5)
            tunnel_start()
            log_buffer = []
        elif key in (ord('l'), ord('L')):
            show_logs = not show_logs
            log_buffer = read_logs(50) if show_logs else []
