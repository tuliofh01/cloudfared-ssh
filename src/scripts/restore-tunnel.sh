#!/bin/bash
# Restore tunnel state on boot.
# Reads ~/.cloudfared-tunneling/state.json and restarts if was running.
STATE_FILE="$HOME/.cloudfared-tunneling/state.json"
if [ -f "$STATE_FILE" ]; then
    STATUS=$(python3 -c "
import json
try:
    d = json.load(open('$STATE_FILE'))
    print(d.get('status', 'stopped'))
except Exception:
    print('stopped')
")
    if [ "$STATUS" = "running" ]; then
        systemctl --user start cloudflared-tunnel.service
    fi
fi
