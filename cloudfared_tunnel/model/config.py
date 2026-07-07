"""Config model — environment + file-based configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


# Load project .env (safe if absent)
load_dotenv()


_CONFIG_DIR = Path.home() / ".cloudfared-tunneling"


@dataclass
class AppConfig:
    """Immutable configuration derived from environment.

    All defaults work out-of-the-box; override via ``.env`` or env vars.
    """

    # -- Cloudflare Worker ------------------------------------------------
    worker_url: str = field(
        default_factory=lambda: os.getenv(
            "WORKER_URL", "https://nxs1.tuliofh01.workers.dev"
        )
    )
    tunnel_secret: str = field(
        default_factory=lambda: os.getenv("TUNNEL_SECRET", "")
    )

    # -- Local services ----------------------------------------------------
    flask_host: str = field(
        default_factory=lambda: os.getenv("FLASK_HOST", "0.0.0.0")
    )
    flask_port: int = field(
        default_factory=lambda: int(os.getenv("FLASK_PORT", "5000"))
    )

    # -- Cloudflare Tunnel -------------------------------------------------
    tunnel_uuid: Optional[str] = field(
        default_factory=lambda: os.getenv("TUNNEL_UUID") or None
    )
    config_path: Path = field(
        default_factory=lambda: Path(
            os.getenv("TUNNEL_CONFIG", str(_CONFIG_DIR / "config.yml"))
        )
    )
    service_url: str = field(
        default_factory=lambda: os.getenv("SERVICE_URL", "http://localhost:80")
    )

    # -- Sync --------------------------------------------------------------
    sync_interval: int = field(
        default_factory=lambda: int(os.getenv("SYNC_INTERVAL", "30"))
    )

    # -- Paths -------------------------------------------------------------
    state_dir: Path = _CONFIG_DIR
    log_dir: Path = _CONFIG_DIR / "logs"

    def __post_init__(self) -> None:
        """Ensure storage directories exist."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    @property
    def has_tunnel_secret(self) -> bool:
        return bool(self.tunnel_secret)
