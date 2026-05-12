#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "=== AI Control Center Bootstrap (WSL) ==="
echo "Project: $PROJECT_ROOT"

# ── 1. Check Docker ──────────────────────────────────────────────────────────
echo ""
echo "--- Checking Docker ---"
if ! command -v docker &>/dev/null; then
    echo "  ERROR: docker not found. Install Docker Desktop or Docker Engine."
    exit 1
fi
docker --version && echo "  OK: Docker found"

# ── 2. Check Docker Compose v2 ───────────────────────────────────────────────
echo ""
echo "--- Checking Docker Compose v2 ---"
if ! docker compose version &>/dev/null; then
    echo "  ERROR: docker compose v2 not found."
    exit 1
fi
docker compose version && echo "  OK: Docker Compose v2 found"

# ── 3. Copy .env.example → .env ──────────────────────────────────────────────
echo ""
echo "--- Environment file ---"
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "  OK: .env already exists (skipped)"
else
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    echo "  CREATED: .env from .env.example"
    echo "  ACTION REQUIRED: Edit .env and change all passwords!"
fi

# ── 4. Create data directories ───────────────────────────────────────────────
echo ""
echo "--- Creating data directories ---"
mkdir -p "$PROJECT_ROOT/data/documents"
mkdir -p "$PROJECT_ROOT/data/uploads"
mkdir -p "$PROJECT_ROOT/data/exports"
mkdir -p "$PROJECT_ROOT/data/backups"
echo "  OK: data/ directories ready"

# ── 5. Summary ───────────────────────────────────────────────────────────────
echo ""
echo "=== Bootstrap complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit .env and change all passwords"
echo "  2. make up                   — start core services"
echo "  3. make verify               — health check"
echo "  4. make ingest               — ingest documents"
echo ""
echo "Quick start:"
echo "  docker compose --env-file .env -f infra/docker/docker-compose.wsl.yml --profile core up -d"
