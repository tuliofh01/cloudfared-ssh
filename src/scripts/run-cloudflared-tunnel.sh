#!/bin/bash
# Wrapper that reads the tunnel token and launches cloudflared.
# The token file lives outside the git repo (in ~/.cloudflared/).
set -euo pipefail

TOKEN_FILE="$HOME/.cloudflared/tunnel-token"

if [ ! -f "$TOKEN_FILE" ]; then
    echo "FATAL: token file not found at $TOKEN_FILE" >&2
    exit 1
fi

TOKEN=$(cat "$TOKEN_FILE" | tr -d '[:space:]')

if [ -z "$TOKEN" ]; then
    echo "FATAL: token file is empty" >&2
    exit 1
fi

exec cloudflared tunnel run --token "$TOKEN"
