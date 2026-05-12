#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_PROD="$PROJECT_ROOT/infra/docker/docker-compose.prod.yml"
ENV_FILE="$PROJECT_ROOT/.env"

echo "=== AI Control Center — Production Readiness Check ==="
echo ""

PASS=0
FAIL=0

check() {
    local name="$1"
    local cmd="$2"
    if eval "$cmd" &>/dev/null; then
        echo "  [OK]  $name"
        ((PASS++)) || true
    else
        echo "  [FAIL] $name"
        ((FAIL++)) || true
    fi
}

warn() {
    local name="$1"
    local cmd="$2"
    if eval "$cmd" &>/dev/null; then
        echo "  [WARN] $name"
    else
        echo "  [OK]  $name"
    fi
}

# ── Compose file ─────────────────────────────────────────────────────────────
echo "--- Compose Files ---"
check "docker-compose.prod.yml exists" "[ -f '$COMPOSE_PROD' ]"
check "docker-compose.wsl.yml exists"  "[ -f '$PROJECT_ROOT/infra/docker/docker-compose.wsl.yml' ]"
echo ""

# ── .env keys ────────────────────────────────────────────────────────────────
echo "--- Required .env Keys ---"
if [ -f "$ENV_FILE" ]; then
    check ".env: POSTGRES_PASSWORD set"      "grep -q 'POSTGRES_PASSWORD=' '$ENV_FILE' && ! grep -q 'POSTGRES_PASSWORD=change_me' '$ENV_FILE'"
    check ".env: REDIS_PASSWORD set"         "grep -q 'REDIS_PASSWORD=' '$ENV_FILE' && ! grep -q 'REDIS_PASSWORD=change_me' '$ENV_FILE'"
    check ".env: MOBILE_GATEWAY_SECRET set"  "grep -q 'MOBILE_GATEWAY_SECRET=' '$ENV_FILE' && ! grep -q 'MOBILE_GATEWAY_SECRET=change_me' '$ENV_FILE'"
    check ".env: WEBHOOK_SECRET set"         "grep -q 'WEBHOOK_SECRET=' '$ENV_FILE' && ! grep -q 'WEBHOOK_SECRET=change_me' '$ENV_FILE'"
    check ".env: RTK_ALLOW_RUN_COMMAND=false" "grep -q 'RTK_ALLOW_RUN_COMMAND=false' '$ENV_FILE'"
else
    echo "  [FAIL] .env not found — run: make bootstrap"
    ((FAIL++)) || true
fi
echo ""

# ── Prod compose: no DB public ports ─────────────────────────────────────────
echo "--- Production Port Security ---"
check "postgres: no public port in prod compose" \
    "! grep -A5 'container_name: aicc-postgres' '$COMPOSE_PROD' | grep -q '0.0.0.0:5432'"
check "redis: no public port in prod compose" \
    "! grep -A5 'container_name: aicc-redis' '$COMPOSE_PROD' | grep -q '0.0.0.0:6379'"
check "qdrant: no public port in prod compose" \
    "! grep -A5 'container_name: aicc-qdrant' '$COMPOSE_PROD' | grep -q '0.0.0.0:6333'"
check "public services bind 127.0.0.1 in prod compose" \
    "grep -q '127.0.0.1:8088' '$COMPOSE_PROD'"
echo ""

# ── Running containers (if any) ───────────────────────────────────────────────
if docker ps --format "{{.Names}}" 2>/dev/null | grep -q "aicc-"; then
    echo "--- Running Container Port Check ---"
    if docker ps --format "{{.Ports}}" 2>/dev/null | grep -qE "0\.0\.0\.0:5432|0\.0\.0\.0:6379|0\.0\.0\.0:6333"; then
        echo "  [FAIL] DB/Redis/Qdrant exposed on 0.0.0.0 — fix immediately!"
        ((FAIL++)) || true
    else
        echo "  [OK]  No DB/Redis/Qdrant on 0.0.0.0"
        ((PASS++)) || true
    fi
    echo ""
fi

# ── Security files ────────────────────────────────────────────────────────────
echo "--- Security Files ---"
check ".dockerignore exists"         "[ -f '$PROJECT_ROOT/.dockerignore' ]"
check ".env in .dockerignore"        "grep -q '\.env' '$PROJECT_ROOT/.dockerignore'"
check "backup script exists"         "[ -f '$PROJECT_ROOT/infra/backup/backup.sh' ]"
check "CWP notes exist"              "[ -f '$PROJECT_ROOT/infra/cwp/reverse-proxy-notes.md' ]"
check "CWP checklist exists"         "[ -f '$PROJECT_ROOT/infra/cwp/deployment-checklist.md' ]"
echo ""

# ── No .env in git ────────────────────────────────────────────────────────────
echo "--- Git Safety ---"
check ".env not tracked by git" "! git -C '$PROJECT_ROOT' ls-files | grep -q '^\.env$'"
echo ""

# ── Summary ──────────────────────────────────────────────────────────────────
echo "=== Result: $PASS passed, $FAIL failed ==="
if [ "$FAIL" -gt 0 ]; then
    echo "  Fix all FAIL items before deploying to production."
    exit 1
fi
echo "  Production readiness checks passed!"
