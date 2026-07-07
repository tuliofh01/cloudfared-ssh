"""Basic unitary tests for cloudfared-tunneling."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from cloudfared_tunnel.model.config import AppConfig
from cloudfared_tunnel.model.state import DurableState, StateStore
from cloudfared_tunnel.model.tunnel import TunnelState, TunnelProcess


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_state_path():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d) / "state.json"


@pytest.fixture
def store(tmp_state_path):
    return StateStore(path=tmp_state_path)


@pytest.fixture
def cfg():
    return AppConfig()


# ---------------------------------------------------------------------------
# TunnelState
# ---------------------------------------------------------------------------

class TestTunnelState:
    def test_default_state(self):
        s = TunnelState()
        assert s.status == "stopped"
        assert s.url == "Not Connected"
        assert s.uptime == 0

    def test_uptime_calculation(self):
        import time
        s = TunnelState(started_at=time.time() - 3600)
        assert s.uptime >= 3599
        assert "h" in s.uptime_str

    def test_uptime_str_minutes(self):
        import time
        s = TunnelState(started_at=time.time() - 120)
        assert "m" in s.uptime_str

    def test_to_dict(self):
        s = TunnelState(pid=1234, url="https://test.trycloudflare.com", status="running")
        d = s.to_dict()
        assert d["pid"] == 1234
        assert d["status"] == "running"
        assert d["url"] == "https://test.trycloudflare.com"

    def test_is_running(self):
        assert TunnelState(status="running").is_running
        assert not TunnelState(status="stopped").is_running
        assert not TunnelState(status="crashed").is_running


# ---------------------------------------------------------------------------
# DurableState / StateStore
# ---------------------------------------------------------------------------

class TestDurableState:
    def test_default_state(self):
        s = DurableState()
        assert s.tunnel_status == "stopped"
        assert s.tunnel_url == "Not Connected"
        assert s.sync_count == 0

    def test_to_dict_roundtrip(self):
        s1 = DurableState(tunnel_status="running", tunnel_url="https://x.com", sync_count=5)
        d = s1.to_dict()
        s2 = DurableState.from_dict(d)
        assert s2.tunnel_status == "running"
        assert s2.tunnel_url == "https://x.com"
        assert s2.sync_count == 5

    def test_from_dict_ignores_extra_keys(self):
        d = {"tunnel_status": "running", "bogus": "yes", "tunnel_url": "url"}
        s = DurableState.from_dict(d)
        assert s.tunnel_status == "running"
        assert not hasattr(s, "bogus")


class TestStateStore:
    def test_new_store_is_default(self, store):
        assert store.state.tunnel_status == "stopped"

    def test_update_and_persist(self, store):
        store.update(tunnel_status="running", tunnel_url="https://t.test")
        assert store.state.tunnel_status == "running"
        assert store.state.tunnel_url == "https://t.test"

    def test_mark_sync_ok(self, store):
        store.mark_sync_ok()
        assert store.state.sync_count == 1
        assert store.state.last_sync_ok is not None

    def test_mark_sync_error(self, store):
        store.mark_sync_error("connection refused")
        assert store.state.last_sync_error == "connection refused"

    def test_file_persistence(self, tmp_state_path):
        s1 = StateStore(path=tmp_state_path)
        s1.update(tunnel_status="running", tunnel_pid=999)
        del s1

        s2 = StateStore(path=tmp_state_path)
        assert s2.state.tunnel_status == "running"
        assert s2.state.tunnel_pid == 999

    def test_corrupt_file_fallback(self, tmp_state_path):
        tmp_state_path.write_text("garbage")
        s = StateStore(path=tmp_state_path)
        assert s.state.tunnel_status == "stopped"


# ---------------------------------------------------------------------------
# TunnelProcess (mocked subprocess)
# ---------------------------------------------------------------------------

class TestTunnelProcess:
    def test_initial_state(self):
        tp = TunnelProcess()
        assert tp.state.status == "stopped"

    @mock.patch("cloudfared_tunnel.model.tunnel.subprocess.Popen")
    def test_start_quick_tunnel(self, mock_popen):
        mock_proc = mock.MagicMock()
        mock_proc.pid = 5678
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc

        tp = TunnelProcess()
        result = tp.start(service_url="http://localhost:80")
        assert result.status in ("starting", "running")
        assert result.pid == 5678

    @mock.patch("cloudfared_tunnel.model.tunnel.subprocess.Popen")
    def test_stop_tunnel(self, mock_popen):
        mock_proc = mock.MagicMock()
        mock_proc.pid = 1234
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc

        tp = TunnelProcess()
        tp.start()
        result = tp.stop()
        assert result.status == "stopped"

    def test_refresh_without_process(self):
        tp = TunnelProcess()
        tp.refresh()
        assert tp.state.status == "stopped"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class TestAppConfig:
    def test_default_values(self, cfg):
        assert cfg.flask_host == "0.0.0.0"
        assert cfg.flask_port == 5000
        assert cfg.sync_interval == 30

    def test_creates_dirs(self, cfg):
        assert cfg.state_dir.exists()
        assert cfg.log_dir.exists()

    def test_secret_detection(self):
        with mock.patch.dict(os.environ, {"TUNNEL_SECRET": "abc123"}, clear=True):
            c = AppConfig()
            assert c.has_tunnel_secret
            assert c.tunnel_secret == "abc123"

    def test_no_secret(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            c = AppConfig()
            assert not c.has_tunnel_secret


# ---------------------------------------------------------------------------
# Integration smoke-test (no cloudflared)
# ---------------------------------------------------------------------------

def test_status_controller_import():
    from cloudfared_tunnel.controller.tunnel_controller import TunnelController
    assert TunnelController is not None


def test_syncer_controller_import():
    from cloudfared_tunnel.controller.syncer_controller import SyncerController
    assert SyncerController is not None


def test_flask_view_import():
    from cloudfared_tunnel.view.flask_view import create_app
    assert create_app is not None


def test_cli_view_import():
    from cloudfared_tunnel.view.cli_view import CLIView
    assert CLIView is not None


def test_polybar_view_import():
    from cloudfared_tunnel.view.polybar_view import polybar_status_line
    line = polybar_status_line({"status": "stopped"})
    assert "STOPPED" in line or "OFF" in line


def test_main_help():
    import subprocess
    import sys
    result = subprocess.run(
        [sys.executable, "-m", "cloudfared_tunnel.main", "--help"],
        capture_output=True, text=True, cwd=Path(__file__).parent.parent,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "usage:" in result.stdout.lower()
