#!/bin/bash
STATE_FILE="$HOME/.cloudfared-tunneling/state.json"
if [ -f "$STATE_FILE" ]; then
    STATUS=$(python3 -c "
import json
try:
    with open('$STATE_FILE') as f:
        d = json.load(f)
    print(d.get('tunnel_status', 'stopped'))
except Exception:
    print('stopped')
")
    if [ "$STATUS" = "running" ]; then
        cd /home/tuliofh01/cloudfared-tunneling || exit 1
        .venv/bin/python -m cloudfared_tunnel.main start
    fi
fi
