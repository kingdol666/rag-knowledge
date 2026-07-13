#!/usr/bin/env bash
# ============================================================
# RAG Knowledge Platform — Backup Script
#
# Backs up:
#   1. storage/tree-file-system/  (KB documents + metadata)
#   2. chroma_db/                 (vector embeddings)
#   3. Neo4j graph database       (full dump via neo4j-admin)
#
# Usage:
#   ./scripts/backup.sh [backup-dir]
#     backup-dir defaults to ./storage/backups/<YYYY-MM-DD_HH-MM-SS>/
#
# Output:
#   storage/backups/<timestamp>/
#     ├── tree-fs.tar.gz
#     ├── chroma_db.tar.gz
#     └── neo4j.dump          (empty if Neo4j unavailable)
# ============================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TIMESTAMP="$(date +%Y-%m-%d_%H-%M-%S)"
BACKUP_DIR="${1:-$ROOT/storage/backups/$TIMESTAMP}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo ""
echo "  =========================================="
echo "  RAG Knowledge Platform — Backup"
echo "  Target:  $BACKUP_DIR"
echo "  =========================================="
echo ""

mkdir -p "$BACKUP_DIR"

FAIL=0

# ── 1. KB Documents + Metadata ────────────────────────────
TREE_FS="$ROOT/storage/tree-file-system"
if [ -d "$TREE_FS" ]; then
    echo "  [1/3] Backing up KB documents & metadata…"
    tar -czf "$BACKUP_DIR/tree-fs.tar.gz" -C "$ROOT/storage" tree-file-system 2>/dev/null
    TREE_SIZE=$(du -sh "$BACKUP_DIR/tree-fs.tar.gz" 2>/dev/null | cut -f1)
    echo -e "  ${GREEN}[OK]${NC} tree-fs.tar.gz ($TREE_SIZE)"
else
    echo -e "  ${YELLOW}[SKIP]${NC} No storage/tree-file-system/ directory"
fi

# ── 2. Vector Index (ChromaDB) ────────────────────────────
CHROMA_DIR="$ROOT/chroma_db"
if [ -d "$CHROMA_DIR" ]; then
    echo "  [2/3] Backing up vector index (ChromaDB)…"
    tar -czf "$BACKUP_DIR/chroma_db.tar.gz" -C "$ROOT" chroma_db 2>/dev/null
    CHROMA_SIZE=$(du -sh "$BACKUP_DIR/chroma_db.tar.gz" 2>/dev/null | cut -f1)
    echo -e "  ${GREEN}[OK]${NC} chroma_db.tar.gz ($CHROMA_SIZE)"
else
    echo -e "  ${YELLOW}[SKIP]${NC} No chroma_db/ directory — run kb_reindex first"
fi

# ── 3. Neo4j Graph Database ───────────────────────────────
NEO4J_CONTAINER="rag-knowledge-neo4j"
if command -v docker &>/dev/null && docker ps --format '{{.Names}}' 2>/dev/null | grep -q "$NEO4J_CONTAINER"; then
    echo "  [3/3] Dumping Neo4j graph…"
    # Load env vars for password
    if [ -f "$ROOT/.env" ]; then
        set -a; source "$ROOT/.env"; set +a
    fi
    NEO4J_PW="${NEO4J_PASSWORD:-123456}"

    if docker exec "$NEO4J_CONTAINER" neo4j-admin database dump neo4j --to-path=/tmp 2>/dev/null; then
        # Find the dump file
        DUMP_FILE=$(docker exec "$NEO4J_CONTAINER" sh -c 'ls -t /tmp/neo4j-*.dump 2>/dev/null | head -1' 2>/dev/null)
        if [ -n "$DUMP_FILE" ]; then
            docker cp "$NEO4J_CONTAINER:$DUMP_FILE" "$BACKUP_DIR/neo4j.dump" 2>/dev/null
            DUMP_SIZE=$(du -sh "$BACKUP_DIR/neo4j.dump" 2>/dev/null | cut -f1)
            echo -e "  ${GREEN}[OK]${NC} neo4j.dump ($DUMP_SIZE)"
        else
            echo -e "  ${YELLOW}[WARN]${NC} Dump created but file not found"
        fi
    else
        echo -e "  ${RED}[FAIL]${NC} Neo4j dump failed (enterprise-only? try: schema export)"
        FAIL=1
    fi
else
    echo -e "  ${YELLOW}[SKIP]${NC} Neo4j container not running — graph not backed up"
fi

# ── Summary ─────────────────────────────────────────────
echo ""
if [ $FAIL -eq 0 ]; then
    echo -e "  ${GREEN}=========================================="
    echo "  Backup complete!"
    echo "  Location:  $BACKUP_DIR"
    echo -e "  ==========================================${NC}"
else
    echo -e "  ${RED}Backup completed with errors — check above.${NC}"
fi
echo ""