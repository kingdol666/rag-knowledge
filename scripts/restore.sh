#!/usr/bin/env bash
# ============================================================
# RAG Knowledge Platform — Restore Script
#
# Restores from a backup directory created by backup.sh.
#
# Usage:
#   ./scripts/restore.sh <backup-dir>
#
# WARNING: This overwrites current data. Stop services first!
#   ./scripts/stop.sh
#   ./scripts/restore.sh storage/backups/2026-07-14_12-00-00
# ============================================================
set -euo pipefail

BACKUP_DIR="${1:-}"
if [ -z "$BACKUP_DIR" ] || [ ! -d "$BACKUP_DIR" ]; then
    echo "Usage: $0 <backup-directory>"
    echo "  e.g.  $0 storage/backups/2026-07-14_12-00-00"
    exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo ""
echo "  =========================================="
echo "  RAG Knowledge Platform — Restore"
echo "  Source:  $BACKUP_DIR"
echo "  =========================================="

# ── Pre-flight: warn about running services ───────────────
if [ -f "$ROOT/storage/pids/backend.pid" ] || [ -f "$ROOT/storage/pids/web.pid" ]; then
    echo ""
    echo -e "  ${YELLOW}[WARN]${NC} Services appear to be running!"
    echo "  Run ./scripts/stop.sh first, then retry."
    exit 1
fi

FAIL=0

# ── 1. KB Documents ───────────────────────────────────────
TREE_ARCHIVE="$BACKUP_DIR/tree-fs.tar.gz"
if [ -f "$TREE_ARCHIVE" ]; then
    echo "  [1/3] Restoring KB documents & metadata…"
    rm -rf "$ROOT/storage/tree-file-system"
    tar -xzf "$TREE_ARCHIVE" -C "$ROOT/storage/"
    echo -e "  ${GREEN}[OK]${NC} tree-file-system restored"
else
    echo -e "  ${YELLOW}[SKIP]${NC} No tree-fs.tar.gz in backup"
fi

# ── 2. Vector Index ───────────────────────────────────────
CHROMA_ARCHIVE="$BACKUP_DIR/chroma_db.tar.gz"
if [ -f "$CHROMA_ARCHIVE" ]; then
    echo "  [2/3] Restoring vector index…"
    rm -rf "$ROOT/chroma_db"
    tar -xzf "$CHROMA_ARCHIVE" -C "$ROOT/"
    echo -e "  ${GREEN}[OK]${NC} chroma_db restored"
else
    echo -e "  ${YELLOW}[SKIP]${NC} No chroma_db.tar.gz in backup"
fi

# ── 3. Neo4j Graph ────────────────────────────────────────
NEO4J_DUMP="$BACKUP_DIR/neo4j.dump"
NEO4J_CONTAINER="rag-knowledge-neo4j"
if [ -f "$NEO4J_DUMP" ]; then
    if command -v docker &>/dev/null && docker ps --format '{{.Names}}' 2>/dev/null | grep -q "$NEO4J_CONTAINER"; then
        echo "  [3/3] Restoring Neo4j graph…"
        echo -e "  ${YELLOW}[NOTE]${NC} Stopping Neo4j for restore…"
        docker stop "$NEO4J_CONTAINER" 2>/dev/null || true

        if [ -f "$ROOT/.env" ]; then
            set -a; source "$ROOT/.env"; set +a
        fi
        NEO4J_PW="${NEO4J_PASSWORD:-123456}"

        # Copy dump into container and restore
        docker cp "$NEO4J_DUMP" "$NEO4J_CONTAINER:/tmp/neo4j.dump"
        docker start "$NEO4J_CONTAINER" 2>/dev/null
        echo -e "  ${YELLOW}[NOTE]${NC} Neo4j restarting — run: docker exec $NEO4J_CONTAINER neo4j-admin database restore neo4j --from-path=/tmp/neo4j.dump --overwrite-destination=true"
        echo -e "  ${YELLOW}[NOTE]${NC} Then restart Neo4j: docker restart $NEO4J_CONTAINER"
    else
        echo -e "  ${YELLOW}[SKIP]${NC} Neo4j container not running — neo4j.dump not restored"
    fi
else
    echo -e "  ${YELLOW}[SKIP]${NC} No neo4j.dump in backup"
fi

# ── Post-restore: rebuild indexes ─────────────────────────
echo ""
echo "  =========================================="
echo -e "  ${GREEN}Restore complete!${NC}"
echo ""
echo "  Next steps:"
echo "    1. Start services:  ./scripts/start-prod.sh"
echo "    2. Rebuild graph:   use kb_graph_build_all or kb-mcp tool"
echo "    3. Verify:          check a few docs in the web UI"
echo "  =========================================="