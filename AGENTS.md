# Cloudfared Tunnel — Agents Guide

## Architecture (v2)

```
cloudfared-tunnel/
├── cloudfared_tunnel/
│   ├── __init__.py
│   └── main.py              # Curses TUI + CLI — single file, ~280 LOC
├── scripts/
│   ├── cloudflared-tunnel.service   # systemd user unit
│   ├── run-cloudflared-tunnel.sh    # Token wrapper for cloudflared
│   ├── restore-tunnel.sh            # Boot-time state recovery
│   ├── setup.sh                     # Quick setup (any distro)
│   └── setup-vm.sh                  # Interactive VM setup wizard
├── pyproject.toml                   # Zero dependencies
├── README.md
└── LICENSE
```

## Key design decisions (v2)

| Decision | Why |
|----------|-----|
| **Zero deps** | Python stdlib only — `curses`, `subprocess`, `json`, `urllib.request` |
| **Curses TUI** | No Flask/Rich/Textual — one terminal window, no web server |
| **User-level systemd** | No sudo — `systemctl --user`, token in `~/.cloudflared/` |
| **Token auth** | Single string to copy-paste, headless setup |
| **JSON state** | `~/.cloudfared-tunneling/state.json` — debuggable, no DB |
| **Single file** | ~280 LOC replaces 7-file MVC (~700+ LOC) — 3× less code |

## Entry points

```
python3 -m cloudfared_tunnel.main           # TUI dashboard
python3 -m cloudfared_tunnel.main --status  # One-liner for scripts
python3 -m cloudfared_tunnel.main --on      # Start daemon
python3 -m cloudfared_tunnel.main --off     # Stop daemon
python3 -m cloudfared_tunnel.main --logs    # Journal logs dump
sudo bash scripts/setup.sh                  # Quick setup
sudo bash scripts/setup-vm.sh               # Interactive VM wizard
```

## Tunnel lifecycle

```
TUI [S]  →  systemctl --user start  →  run-cloudflared-tunnel.sh
                                            ↓
                                    cloudflared tunnel run --token
                                            ↓
                                    QUIC connection to Cloudflare Edge
```

## State persisted

Status written to `~/.cloudfared-tunneling/state.json` on start/stop.
Read by `restore-tunnel.sh` on boot to resume if it was running.
