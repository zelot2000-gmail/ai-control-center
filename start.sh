#!/usr/bin/env bash
# Quick-start script — รันได้จากทุกที่ใน WSL
# Usage: bash /mnt/e/Project/laragon/www/ai-control-center/start.sh
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/infra/docker/docker-compose.wsl.yml"
ENV_FILE="$PROJECT_ROOT/.env"

echo ""
echo "==================================================="
echo "  AI Control Center — Quick Start"
echo "  Project: $PROJECT_ROOT"
echo "==================================================="

# ── 1. Docker check ──────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    echo ""
    echo "  ERROR: docker not found"
    echo "  Install: https://docs.docker.com/engine/install/centos/ (AlmaLinux 8)"
    exit 1
fi
echo "  OK  docker $(docker --version | cut -d' ' -f3 | tr -d ',')"

if ! docker compose version &>/dev/null; then
    echo "  ERROR: docker compose v2 not found"
    exit 1
fi
echo "  OK  $(docker compose version)"

# ── 2. .env setup ────────────────────────────────────────────────────────────
echo ""
if [ ! -f "$ENV_FILE" ]; then
    cp "$PROJECT_ROOT/.env.example" "$ENV_FILE"
    echo "  CREATED .env from .env.example"
    echo "  WARN: กรุณาแก้ passwords ใน .env ก่อน production!"
else
    echo "  OK  .env exists"
fi

# ── 3. Data directories ──────────────────────────────────────────────────────
mkdir -p "$PROJECT_ROOT/data/documents"
mkdir -p "$PROJECT_ROOT/data/uploads"
mkdir -p "$PROJECT_ROOT/data/exports"
mkdir -p "$PROJECT_ROOT/data/backups"
echo "  OK  data/ directories ready"

# ── 4. Start services ────────────────────────────────────────────────────────
echo ""
echo "--- Starting core services ---"
docker compose --env-file "$ENV_FILE" \
               -f "$COMPOSE_FILE" \
               --profile core up -d --build

# ── 5. Wait for health ───────────────────────────────────────────────────────
echo ""
echo "--- Waiting for services to be healthy (max 60s) ---"
sleep 5

for i in $(seq 1 12); do
    UP=0
    for port in 8088 8090 8091 8092 8093 8094 8095; do
        if curl -sf "http://127.0.0.1:$port/health" &>/dev/null; then
            UP=$((UP+1))
        fi
    done
    echo "  [${i}0s] ${UP}/7 services UP"
    if [ "$UP" -eq 7 ]; then break; fi
    sleep 5
done

# ── 6. Dashboard check ───────────────────────────────────────────────────────
echo ""
if curl -sf "http://127.0.0.1:3000" &>/dev/null; then
    echo "  OK  Dashboard: http://127.0.0.1:3000"
else
    echo "  WARN: Dashboard not responding on :3000"
fi

# ── 7. Summary ───────────────────────────────────────────────────────────────
echo ""
echo "--- Service Status ---"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps

echo ""
echo "=== Ready ==="
echo "  Dashboard  : http://127.0.0.1:3000"
echo "  Gateway    : http://127.0.0.1:8088/health"
echo "  RAG API    : http://127.0.0.1:8090/health"
echo "  Observer   : http://127.0.0.1:8094/status"
echo ""
echo "  make logs  — follow logs"
echo "  make down  — stop all"
echo "  make verify — full health check"
