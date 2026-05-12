#!/usr/bin/env bash
set -euo pipefail

echo "=== Docker Clean (Safe — No Volume Removal) ==="
echo ""
echo "This script removes:"
echo "  - Build cache"
echo "  - Dangling (untagged) images"
echo ""
echo "This script DOES NOT remove:"
echo "  - Named volumes (postgres_data, redis_data, qdrant_data)"
echo "  - Running containers"
echo "  - Networks"
echo ""

read -r -p "Proceed? [y/N] " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "--- Pruning build cache ---"
docker builder prune -f
echo "  OK"

echo ""
echo "--- Pruning dangling images ---"
docker image prune -f
echo "  OK"

echo ""
echo "--- Current disk usage ---"
docker system df

echo ""
echo "=== Clean complete (volumes preserved) ==="
