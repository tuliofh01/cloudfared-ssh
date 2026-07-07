# cloudfared-tunneling

![Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)
![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-brightgreen)
![Cloudflare](https://img.shields.io/badge/Cloudflare-Tunnel-orange)
![Arch](https://img.shields.io/badge/Arch-supported-blue)
![Debian](https://img.shields.io/badge/Debian-supported-red)
![Ubuntu](https://img.shields.io/badge/Ubuntu-supported-orange)
![Fedora](https://img.shields.io/badge/Fedora-supported-blue)
![Docker](https://img.shields.io/badge/Docker-ELK-2496ED)
![Polybar](https://img.shields.io/badge/Polybar-toggle-success)

[ Leia em Português](https://translate.google.com/translate?sl=en&tl=pt&u=https://github.com/tuliofh01/cloudfared-ssh)

Control Cloudflare Tunnels from your desktop — CLI, REST API, Polybar toggle, and systemd service.

---

## Architecture

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────┐
│  User    │────▶│  CLI / API   │────▶│ Controller   │────▶│  Models  │
│          │     │  (Flask/Rich)│     │              │     │(Dataclass)│
└──────────┘     └──────────────┘     └──────┬───────┘     └──────────┘
                                             │
┌──────────┐     ┌──────────────┐            │
│ Polybar  │────▶│ Status Script│────────────┤
└──────────┘     └──────────────┘            │
                                             ▼
                                    ┌──────────────────┐
                                    │   cloudflared     │
                                    │   tunnel process  │
                                    └────────┬─────────┘
                                             │
                                             ▼
                                    ┌──────────────────┐
                                    │  Cloudflare      │
                                    │  Worker / Edge   │
                                    └────────┬─────────┘
                                             │
                                             ▼
                                    ┌──────────────────┐
                                    │    Internet      │
                                    │  (SSH / HTTP)    │
                                    └──────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                  ELK Log Pipeline                             │
│  cloudflared → Logstash → Elasticsearch → Kibana (:5601)     │
└──────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
bash wizard.sh
```

The wizard detects your distro (Arch, Debian, Ubuntu, Manjaro, Zorin, Fedora, openSUSE), installs cloudflared, sets up the Python environment, creates a systemd service, and optionally configures Polybar + shell aliases.

## 2 Micro-services

| Service | Role | Port |
|---------|------|------|
| **API** (Flask) | Tunnel lifecycle, status, logs | `5000` |
| **Syncer** (background) | Pushes state + logs to Cloudflare Worker every 30s | — |

### Start the API server

```bash
# Using run.sh
./run.sh serve

# Or directly
.venv/bin/python -m cloudfared_tunnel.main --serve
```

## CLI Usage

```bash
# Show tunnel status
python -m cloudfared_tunnel.main status

# Start / stop tunnel
python -m cloudfared_tunnel.main start
python -m cloudfared_tunnel.main stop

# Show logs
python -m cloudfared_tunnel.main logs

# Health check
python -m cloudfared_tunnel.main health

# System info
python -m cloudfared_tunnel.main sysinfo

# Check cloudflared
python -m cloudfared_tunnel.main check
```

## Polybar Toggle

Add a colored tunnel status indicator to your Polybar bar:

![Polybar example](https://via.placeholder.com/400x24/1e1e2e/00FF88?text= ON  https://something.trycloudflare.com)

**Colors:**
- Green `#00FF88` — tunnel active
- Yellow `#EBD369` — starting / connecting
- Red `#FF5555` — stopped / crashed

**Click actions:**
- Left click — start tunnel
- Right click — stop tunnel
- Middle click — open tunnel URL in browser

### Manual setup

1. Create the wrapper script:
```bash
mkdir -p ~/.config/polybar/scripts
cat > ~/.config/polybar/scripts/tunnel_status.sh << 'EOF'
#!/bin/bash
~/cloudfared-tunneling/.venv/bin/python -m cloudfared_tunnel.main --polybar
EOF
chmod +x ~/.config/polybar/scripts/tunnel_status.sh
```

2. Add to `~/.config/polybar/user_modules.ini`:
```ini
[module/cloudfared-tunnel]
type = custom/script
exec = ~/.config/polybar/scripts/tunnel_status.sh
interval = 5
click-left = curl -s -X POST http://localhost:5000/api/tunnel/start >/dev/null
click-right = curl -s -X POST http://localhost:5000/api/tunnel/stop >/dev/null
format = <label>
label = %output%
```

3. Add `cloudfared-tunnel` to your bar's `modules-right` in `bars.ini`.

## State Persistence

Tunnel state is persisted to `~/.cloudfared-tunneling/state.json` after every status change (start / stop / crash). The systemd service auto-restores the tunnel on boot:

```bash
# Enable auto-start on boot
sudo systemctl enable cloudfared-tunnel

# Start now
sudo systemctl start cloudfared-tunnel

# Check status
journalctl -u cloudfared-tunnel -f
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/tunnel/status` | Current tunnel status |
| `POST` | `/api/tunnel/start` | Start tunnel (body: `{"service":"..."}`) |
| `POST` | `/api/tunnel/stop` | Stop tunnel |
| `GET` | `/api/logs?lines=100` | Recent logs |
| `GET` | `/api/system/info` | CPU / RAM / Disk / Uptime |
| `GET` | `/api/cloudflared/check` | cloudflared installed? |

## Docker + ELK Stack

```bash
docker compose up -d
```

Starts 4 services:
- **app** — Flask API on `:5000`
- **elasticsearch** `:9200` — Log storage
- **logstash** `:5044` — Log ingestion
- **kibana** `:5601` — Log visualization

### Logstash pipeline

```
cloudflared tunnel logs → Logstash (:5044) → Elasticsearch → Kibana
```

Configure Kibana at `http://localhost:5601` with index pattern `cloudfared-*`.

## Project Structure

```
cloudfared-tunneling/
├── cloudfared_tunnel/       # Python package
│   ├── main.py              # CLI entry point
│   ├── model/               # Tunnel, State, Config dataclasses
│   ├── controller/          # TunnelController, SyncerController
│   └── view/                # Flask API, Rich CLI, Polybar output
├── frontend/                # Angular dashboard (unchanged)
├── src/                     # Cloudflare Worker (unchanged)
├── scripts/
│   └── tunnel.service       # systemd unit
├── wizard.sh                # Multi-distro setup wizard
├── run.sh                   # Quick launcher
├── build.sh                 # Build pipeline
├── Dockerfile               # Multi-stage Docker build
├── docker-compose.yml       # app + ELK stack
├── pyproject.toml            # Poetry config
└── LICENSE                  # Apache 2.0
```

## Dependencies

- Python 3.11+
- cloudflared (distro-specific install)
- Poetry (recommended) or pip

```bash
pip install flask flask-cors requests python-dotenv psutil rich cryptography
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TUNNEL_SECRET` | — | Auth token for Worker API |
| `WORKER_URL` | `https://nxs1.tuliofh01.workers.dev` | Remote Worker endpoint |
| `TUNNEL_UUID` | — | Named tunnel UUID for SSH |
| `SERVICE_URL` | `http://localhost:80` | Local service to expose |
| `FLASK_HOST` | `0.0.0.0` | API bind address |
| `FLASK_PORT` | `5000` | API port |

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/...`)
3. Commit changes (`git commit -m "feat: ..."`)
4. Push to the branch (`git push origin feat/...`)
5. Open a Pull Request

## License

Apache License 2.0 — see [LICENSE](LICENSE).

Copyright 2025 tuliofh01
