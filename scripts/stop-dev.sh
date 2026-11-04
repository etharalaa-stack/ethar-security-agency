#!/usr/bin/env bash
# Stop local dev stack (start-dev.sh) and stuck frontend sync/rsync.
set -euo pipefail
API_PORT="${API_PORT:-9815}"
FRONT_PORT="${FRONT_PORT:-8788}"

fuser -k "${API_PORT}/tcp" "${FRONT_PORT}/tcp" 2>/dev/null || true
pkill -f 'backend-engine/.venv.*uvicorn app.main' 2>/dev/null || true
pkill -f 'backend-engine.*python -m app.worker' 2>/dev/null || true
pkill -f 'backend-engine.*run-worker' 2>/dev/null || true
pkill -f 'http.server '"${FRONT_PORT}" 2>/dev/null || true
pkill -f 'backend-engine/start-dev.sh' 2>/dev/null || true
pkill -f 'rsync.*frontend-cloudflare.*backend-engine/frontend-cloudflare' 2>/dev/null || true
pkill -f 'backend-engine/scripts/sync-frontend.sh' 2>/dev/null || true

echo "Stopped local dev (ports ${API_PORT}, ${FRONT_PORT}) and sync/rsync helpers."
