#!/usr/bin/env bash
set -euo pipefail

echo "=== AI Control Center — WSL Verify ==="
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

# ── Docker ───────────────────────────────────────────────────────────────────
echo "--- Docker ---"
check "docker version"         "docker --version"
check "docker compose v2"      "docker compose version"
echo ""

# ── Containers running ───────────────────────────────────────────────────────
echo "--- Containers ---"
docker ps --format "  container: {{.Names}}  status: {{.Status}}"
echo ""

# ── Health checks ────────────────────────────────────────────────────────────
echo "--- Health Checks ---"
check "mobile-gateway  :8088" "curl -sf http://127.0.0.1:8088/health"
check "rag-api         :8090" "curl -sf http://127.0.0.1:8090/health"
check "tto-api         :8091" "curl -sf http://127.0.0.1:8091/health"
check "rtk-bridge      :8092" "curl -sf http://127.0.0.1:8092/health"
check "webhook-gateway :8093" "curl -sf http://127.0.0.1:8093/health"
check "observer        :8094" "curl -sf http://127.0.0.1:8094/health"
check "worker          :8095" "curl -sf http://127.0.0.1:8095/health"
check "qdrant          :6333" "curl -sf http://127.0.0.1:6333/healthz"
echo ""

# ── Disk usage ───────────────────────────────────────────────────────────────
echo "--- Docker Disk Usage ---"
docker system df 2>/dev/null || echo "  (docker system df unavailable)"
echo ""

# ── Summary ──────────────────────────────────────────────────────────────────
echo "=== Result: $PASS passed, $FAIL failed ==="
if [ "$FAIL" -gt 0 ]; then
    echo "  Some services may still be starting. Wait 30s and retry."
    echo "  Debug: docker compose -f infra/docker/docker-compose.wsl.yml logs --tail=30"
    exit 1
fi
echo "  All checks passed!"
