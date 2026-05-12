#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/infra/docker/docker-compose.wsl.yml"
ENV_FILE="$PROJECT_ROOT/.env"
EXPERIMENTS_DIR="$PROJECT_ROOT/docs/research/experiments"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "=== AI Control Center — Research Sandbox ==="
echo ""

# ── Create sandbox dirs ──────────────────────────────────────────────────────
echo "--- Setting up sandbox directories ---"
mkdir -p "$EXPERIMENTS_DIR"
mkdir -p "$PROJECT_ROOT/docs/research/decisions"
mkdir -p "$PROJECT_ROOT/docs/research/benchmarks"
mkdir -p "$PROJECT_ROOT/docs/research/reports"
echo "  OK: research dirs ready"
echo ""

# ── Create experiment template ────────────────────────────────────────────────
EXPERIMENT_FILE="$EXPERIMENTS_DIR/experiment_${TIMESTAMP}.md"
echo "--- Creating experiment template ---"
cat > "$EXPERIMENT_FILE" << 'TMPL'
# Experiment: [Tool or Technology Name]

**Date**: REPLACE_DATE
**Researcher**: REPLACE_RESEARCHER
**Experiment ID**: EXP-REPLACE_ID
**Sandbox**: docker compose --profile research

---

## Research Question
[What are you trying to find out?]

## Options Compared
1. [Option A]
2. [Option B]

## Evaluation Criteria

| Criteria          | Score (1-5) | Notes |
|-------------------|-------------|-------|
| usefulness        |             |       |
| docker_compat     |             |       |
| wsl_compat        |             |       |
| alma8_compat      |             |       |
| security_risk     |             |       |
| maintenance_risk  |             |       |
| resource_usage    |             |       |
| token_cost        |             |       |
| rollback_plan     |             |       |
| **Total**         | **/45**     |       |

## Experiment Steps
```bash
# Commands run in this sandbox
```

## Results
[What happened?]

## Pros
- [Pro]

## Cons
- [Con]

## Risk
- [Risk]

## Recommendation
[Your recommendation]

## Adoption Status
> **[reject | keep watching | PoC only | staging | production-ready]**

## Next Steps
- [ ] [Next step]
TMPL

sed -i "s/REPLACE_DATE/$(date +%Y-%m-%d)/g" "$EXPERIMENT_FILE" 2>/dev/null || true
echo "  Created: $EXPERIMENT_FILE"
echo ""

# ── Start research sandbox ────────────────────────────────────────────────────
echo "--- Starting research sandbox (profile: research) ---"
if [ -f "$ENV_FILE" ]; then
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" --profile research up -d 2>/dev/null || \
        echo "  INFO: research-sandbox container started (or already running)"
else
    echo "  WARN: .env not found — run make bootstrap first"
fi
echo ""

echo "=== Research Sandbox Ready ==="
echo ""
echo "Experiment template: $EXPERIMENT_FILE"
echo "Sandbox container  : aicc-research-sandbox"
echo ""
echo "Rules:"
echo "  - Adopt status must be: reject | keep watching | PoC only | staging | production-ready"
echo "  - Never use production volumes in sandbox"
echo "  - Never merge PoC code to main without TDR approval"
