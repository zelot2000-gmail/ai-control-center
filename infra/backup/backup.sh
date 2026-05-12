#!/usr/bin/env bash
set -euo pipefail

# AI Control Center — Backup Script
# Backs up: Postgres, Qdrant note, data/documents, core/, docs/research
# Output: data/backups/backup_YYYYMMDD_HHMMSS/

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="$(cd "$(dirname "$0")/../.." && pwd)/data/backups/backup_${TIMESTAMP}"
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

echo "=== AI Control Center Backup ==="
echo "Timestamp : $TIMESTAMP"
echo "Backup dir: $BACKUP_DIR"

mkdir -p "$BACKUP_DIR"

# ── 1. Postgres dump ──────────────────────────────────────────────────────────
echo ""
echo "--- Postgres backup ---"
if docker ps --format "{{.Names}}" | grep -q "aicc-postgres"; then
    POSTGRES_USER="${POSTGRES_USER:-aicc_user}"
    POSTGRES_DB="${POSTGRES_DB:-aicc}"
    docker exec aicc-postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
        > "$BACKUP_DIR/postgres_${POSTGRES_DB}_${TIMESTAMP}.sql"
    echo "  OK: postgres dump saved"
else
    echo "  SKIP: aicc-postgres container not running"
fi

# ── 2. Qdrant note ────────────────────────────────────────────────────────────
echo ""
echo "--- Qdrant backup note ---"
cat > "$BACKUP_DIR/qdrant-backup-note.txt" << 'EOF'
Qdrant data is stored in Docker volume: qdrant_data
To backup the volume:
  docker run --rm -v qdrant_data:/data -v $(pwd)/data/backups:/backup \
    alpine tar czf /backup/qdrant_data_TIMESTAMP.tar.gz -C /data .

To restore:
  docker run --rm -v qdrant_data:/data -v $(pwd)/data/backups:/backup \
    alpine tar xzf /backup/qdrant_data_TIMESTAMP.tar.gz -C /data
EOF
echo "  OK: qdrant backup note saved"

# ── 3. data/documents ────────────────────────────────────────────────────────
echo ""
echo "--- Documents backup ---"
if [ -d "$PROJECT_ROOT/data/documents" ]; then
    cp -r "$PROJECT_ROOT/data/documents" "$BACKUP_DIR/documents"
    DOC_COUNT=$(find "$BACKUP_DIR/documents" -type f | wc -l)
    echo "  OK: $DOC_COUNT documents backed up"
else
    echo "  SKIP: data/documents not found"
fi

# ── 4. core/ ─────────────────────────────────────────────────────────────────
echo ""
echo "--- Core config backup ---"
cp -r "$PROJECT_ROOT/core" "$BACKUP_DIR/core"
echo "  OK: core/ backed up"

# ── 5. docs/research ─────────────────────────────────────────────────────────
echo ""
echo "--- Research docs backup ---"
if [ -d "$PROJECT_ROOT/docs/research" ]; then
    cp -r "$PROJECT_ROOT/docs/research" "$BACKUP_DIR/research"
    echo "  OK: docs/research backed up"
fi

# ── 6. .env.example (NOT .env) ───────────────────────────────────────────────
echo ""
echo "--- Config template backup ---"
cp "$PROJECT_ROOT/.env.example" "$BACKUP_DIR/.env.example"
echo "  OK: .env.example backed up (NOT .env)"

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "=== Backup complete ==="
echo "Location: $BACKUP_DIR"
ls -lh "$BACKUP_DIR"
echo ""
echo "Total size: $(du -sh "$BACKUP_DIR" | cut -f1)"
