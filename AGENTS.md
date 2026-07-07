# Cloudfared Tunnel Manager — Agents Guide

## Project Structure

```
cloudfared-tunneling/
├── cloudfared_tunnel/       # Python package (Poetry src-layout)
│   ├── __init__.py
│   ├── main.py              # Procedural CLI entry point
│   ├── model/               # OOP domain models
│   │   ├── tunnel.py        # TunnelProcess, TunnelState
│   │   ├── state.py         # StateStore (JSON persistence)
│   │   └── config.py        # AppConfig (env-based)
│   ├── controller/          # Fat controllers (business logic)
│   │   ├── tunnel_controller.py  # Tunnel lifecycle + logs
│   │   └── syncer_controller.py  # Background sync to Worker
│   └── view/                # Output adapters
│       ├── cli_view.py      # Rich-based CLI (not Textual)
│       ├── flask_view.py    # Flask REST API micro-service
│       └── polybar_view.py  # Polybar status-line generator
├── frontend/                # Angular frontend (unchanged)
├── src/                     # Cloudflare Worker (unchanged)
├── scripts/
│   └── tunnel.service       # systemd unit
├── pyproject.toml           # Poetry config
├── wrangler.json             # Cloudflare Worker config
└── .env                     # TUNNEL_SECRET
```

## Architecture

**MVC with fat controllers** — each controller owns its own business logic
(gateway pattern, no separate service layer).  Models are OOP dataclasses;
`main.py` is procedural and wires everything together.

### Micro-services
1. **API** (Flask, port 5000) — `--serve` flag
2. **Syncer** (background thread) — pushes status + logs to Worker every 30 s

### Commands
```bash
# CLI
python -m cloudfared_tunnel.main status
python -m cloudfared_tunnel.main start
python -m cloudfared_tunnel.main stop
python -m cloudfared_tunnel.main logs
python -m cloudfared_tunnel.main health

# API server
python -m cloudfared_tunnel.main --serve
```

### API Endpoints
- `GET /api/health` — Health check
- `GET /api/tunnel/status` — Tunnel status
- `POST /api/tunnel/start` — Start tunnel
- `POST /api/tunnel/stop` — Stop tunnel
- `GET /api/logs` — Recent logs
- `GET /api/system/info` — System resources
- `GET /api/cloudflared/check` — cloudflared installed?

### Key design decisions
- Rich for CLI output (no Textual dependency)
- State persisted to `~/.cloudfared-tunneling/state.json`
- Named tunnel + config.yml for SSH; quick tunnel fallback for HTTP
- Rotating log files: 10 MB × 5 = 50 MB cap
- Apache 2.0 License

### Environment Variables
```bash
TUNNEL_SECRET=your_secret_here
WORKER_URL=https://nxs1.tuliofh01.workers.dev
TUNNEL_UUID=              # Named tunnel UUID (optional)
SERVICE_URL=http://localhost:80  # Default local service
