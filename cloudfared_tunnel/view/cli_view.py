"""CLI view — rich-based terminal interface (NOT Textual).

Kept deliberately simple: one-shot status, logs, and control commands.
No event loop, no async framework — just rich ``print`` tables / panels.
"""

from __future__ import annotations

import sys
from datetime import datetime
from typing import Any, Dict

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.text import Text

console = Console()


class CLIView:
    """Rich CLI renderer.  All methods return ``sys.exit(0)`` on success,
    ``sys.exit(1)`` on error so the caller can simply call and return."""

    # -- status ------------------------------------------------------------

    @staticmethod
    def show_status(status: Dict[str, Any]) -> None:
        status_val = status.get("status", "unknown")
        url = status.get("url", "Not Connected")
        uptime = status.get("uptime_str", "0m00s")
        pid = status.get("pid")
        exit_code = status.get("exit_code")

        color = "green" if status_val == "running" else "red"
        status_text = Text(status_val.upper(), style=f"bold {color}")

        grid = Table.grid(padding=(0, 2))
        grid.add_column(style="bold cyan"); grid.add_column()

        grid.add_row("Status", status_text)
        if pid:
            grid.add_row("PID", str(pid))
        grid.add_row("URL", url or "—")
        grid.add_row("Uptime", uptime)
        if exit_code is not None:
            grid.add_row("Exit Code", str(exit_code))

        console.print(Panel(grid, title="🔐 Tunnel Status", border_style=color))

    # -- logs --------------------------------------------------------------

    @staticmethod
    def show_logs(log_data: Dict[str, Any]) -> None:
        logs = log_data.get("logs", [])
        count = log_data.get("count", 0)

        console.print(f"\n[bold]📋 Recent Logs[/bold]  ({count} lines)\n")
        if not logs:
            console.print("[dim]No logs yet.[/dim]")
            return

        for entry in logs[-50:]:  # show last 50
            console.print(entry.rstrip())

    # -- start / stop result ----------------------------------------------

    @staticmethod
    def show_result(action: str, result: Dict[str, Any]) -> None:
        status = result.get("status", "error")
        if status == "error":
            msg = result.get("message", "Unknown error")
            console.print(f"[red]✗ {action} failed:[/red] {msg}")
        else:
            url = result.get("url", result.get("service", ""))
            console.print(
                f"[green]✓ {action} successful[/green]"
                + (f"  ({url})" if url else "")
            )

    # -- health ------------------------------------------------------------

    @staticmethod
    def show_health(health: Dict[str, Any]) -> None:
        console.print(
            Panel(
                f"Status: [green]{health.get('status')}[/green]\n"
                f"Time:   {health.get('timestamp')}",
                title="🏥 Health Check",
            )
        )

    # -- system info -------------------------------------------------------

    @staticmethod
    def show_system(info: Dict[str, Any]) -> None:
        if "error" in info:
            console.print(f"[red]Error: {info['error']}[/red]")
            return
        grid = Table.grid(padding=(0, 2))
        grid.add_column(style="bold cyan"); grid.add_column()
        grid.add_row("CPU", f"{info.get('cpu_percent', '?')}%")
        grid.add_row("Memory", f"{info.get('memory_percent', '?')}%")
        grid.add_row("Disk", f"{info.get('disk_percent', '?')}%")
        uptime_s = info.get("uptime", 0)
        if isinstance(uptime_s, (int, float)):
            h, r = divmod(int(uptime_s), 3600)
            m, s = divmod(r, 60)
            uptime_s = f"{h}h{m:02d}m" if h else f"{m}m{s:02d}s"
        grid.add_row("Boot", str(uptime_s))
        console.print(Panel(grid, title="🖥️  System"))

    # -- cloudflared check -------------------------------------------------

    @staticmethod
    def show_cloudflared_check(found: bool) -> None:
        if found:
            console.print("[green]✓ cloudflared is installed[/green]")
        else:
            console.print(
                "[red]✗ cloudflared not found on $PATH[/red]\n"
                "  Install: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
            )
