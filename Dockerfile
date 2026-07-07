FROM python:3.11-slim AS builder
WORKDIR /app
COPY pyproject.toml .
COPY cloudfared_tunnel/ cloudfared_tunnel/
RUN pip install --no-cache-dir flask flask-cors requests python-dotenv psutil rich cryptography

FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && \
    curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared && \
    chmod +x /usr/local/bin/cloudflared && \
    rm -rf /var/lib/apt/lists/*
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY cloudfared_tunnel/ cloudfared_tunnel/
EXPOSE 5000
CMD ["python", "-m", "cloudfared_tunnel.main", "--serve"]
