#!/usr/bin/env bash
set -euo pipefail

# ── PRODUCTION DEPLOY — requires CONFIRM DEPLOY ────────────────────────────
echo "=== AI Control Center — Production Deploy ==="
echo ""
echo "WARNING: This will deploy to PRODUCTION."
echo "Requirements:"
echo "  1. Backup must be completed first"
echo "  2. Prod readiness check must pass"
echo "  3. Approval phrase required"
echo ""

# ── Require approval phrase ───────────────────────────────────────────────────
read -r -p "Enter approval phrase: " phrase
if [ "$phrase" != "CONFIRM DEPLOY" ]; then
    echo "ERROR: Invalid phrase. Deploy cancelled."
    echo "Required: CONFIRM DEPLOY"
    exit 1
fi
echo ""

# ── Prod readiness check ──────────────────────────────────────────────────────
echo "--- Running prod readiness check ---"
bash "$(dirname "$0")/verify-prod-readiness.sh" || {
    echo "ERROR: Prod readiness check failed. Fix issues before deploying."
    exit 1
}
echo ""

# ── Backup ────────────────────────────────────────────────────────────────────
echo "--- Running backup ---"
bash "$(dirname "$0")/../infra/backup/backup.sh"
echo ""

# ── Deploy ────────────────────────────────────────────────────────────────────
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/infra/docker/docker-compose.prod.yml"
ENV_FILE="$PROJECT_ROOT/.env"

echo "--- Deploying production services ---"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" --profile core pull
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" --profile core up -d
echo ""

echo "--- Post-deploy health check ---"
sleep 10
bash "$(dirname "$0")/verify-wsl.sh" || {
    echo "ERROR: Health check failed after deploy. Check logs."
    echo "Rollback: docker compose -f $COMPOSE_FILE down && git checkout HEAD~1 && docker compose up -d"
    exit 1
}

echo ""
echo "=== Production deploy complete ==="
echo "Verify via: bash scripts/verify-prod-readiness.sh"
