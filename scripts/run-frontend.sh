#!/usr/bin/env bash
set -euo pipefail
FRONT="$(cd "$(dirname "$0")/../.." && pwd)/frontend-cloudflare"
cd "$FRONT"
PORT="${PORT:-8788}"
echo "Static frontend: http://127.0.0.1:${PORT}/index.html"
echo "Set window.AGENCY_API_BASE in index.html/track.html if API is not localhost:8000"
exec python3 -m http.server "$PORT"
