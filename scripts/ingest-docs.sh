#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RAG_URL="${RAG_URL:-http://127.0.0.1:8090}"
DOCS_DIR="$PROJECT_ROOT/data/documents"

echo "=== AI Control Center — Ingest Documents ==="
echo "RAG API : $RAG_URL"
echo "Docs dir: $DOCS_DIR"
echo ""

# ── Check RAG health ─────────────────────────────────────────────────────────
echo "--- Checking RAG API ---"
if ! curl -sf "$RAG_URL/health" &>/dev/null; then
    echo "  ERROR: RAG API not available at $RAG_URL"
    echo "  Make sure services are running: make up"
    exit 1
fi
echo "  OK: RAG API is healthy"
echo ""

# ── Check docs dir ────────────────────────────────────────────────────────────
echo "--- Checking documents ---"
if [ ! -d "$DOCS_DIR" ]; then
    echo "  ERROR: $DOCS_DIR not found. Run: make bootstrap"
    exit 1
fi

DOC_COUNT=$(find "$DOCS_DIR" -type f \( -name "*.md" -o -name "*.txt" \) | wc -l)
echo "  Found $DOC_COUNT .md/.txt files in $DOCS_DIR"

if [ "$DOC_COUNT" -eq 0 ]; then
    echo "  INFO: No documents to ingest. Add .md or .txt files to data/documents/"
    exit 0
fi
echo ""

# ── Ingest ────────────────────────────────────────────────────────────────────
echo "--- Ingesting ---"
RESPONSE=$(curl -sf -X POST "$RAG_URL/ingest" \
    -H "Content-Type: application/json" \
    -d "{\"path\": \"/app/data/documents\"}")

echo "  Response: $RESPONSE"
echo ""

INGESTED=$(echo "$RESPONSE" | grep -o '"ingested":[0-9]*' | cut -d: -f2 || echo "?")
CHUNKS=$(echo "$RESPONSE" | grep -o '"chunks":[0-9]*' | cut -d: -f2 || echo "?")
echo "=== Ingest complete: $INGESTED files, $CHUNKS chunks ==="
