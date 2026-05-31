#!/bin/bash
# TeleStore — MongoDB Backup Script
# Usage: ./scripts/backup.sh [--restore <backup_file>]
# Cron: 0 2 * * * /path/to/telestore/scripts/backup.sh

set -euo pipefail

# ─── Config ────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load .env if present
if [ -f "$PROJECT_DIR/.env" ]; then
    set -o allexport
    source "$PROJECT_DIR/.env"
    set +o allexport
fi

MONGODB_URI="${MONGODB_URI:-mongodb://localhost:27017}"
MONGODB_DB="${MONGODB_DB:-telestore}"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="telestore_${DATE}"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

# ─── Restore mode ──────────────────────────────────────────────────────
if [ "${1:-}" == "--restore" ] && [ -n "${2:-}" ]; then
    echo "🔄 Restoring from: $2"
    mongorestore \
        --uri="$MONGODB_URI" \
        --db="$MONGODB_DB" \
        --drop \
        "$2"
    echo "✅ Restore complete."
    exit 0
fi

# ─── Backup ────────────────────────────────────────────────────────────
mkdir -p "$BACKUP_DIR"

echo "📦 Starting backup: $BACKUP_NAME"
mongodump \
    --uri="$MONGODB_URI" \
    --db="$MONGODB_DB" \
    --out="$BACKUP_PATH" \
    --gzip

# Compress to single archive
tar -czf "$BACKUP_PATH.tar.gz" -C "$BACKUP_DIR" "$BACKUP_NAME"
rm -rf "$BACKUP_PATH"

BACKUP_SIZE=$(du -sh "$BACKUP_PATH.tar.gz" | cut -f1)
echo "✅ Backup saved: $BACKUP_PATH.tar.gz ($BACKUP_SIZE)"

# ─── Cleanup old backups ───────────────────────────────────────────────
echo "🧹 Removing backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "telestore_*.tar.gz" -mtime "+$RETENTION_DAYS" -delete

REMAINING=$(ls "$BACKUP_DIR"/telestore_*.tar.gz 2>/dev/null | wc -l)
echo "📁 Backups retained: $REMAINING"

echo "✅ Backup complete."
