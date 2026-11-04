#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$(cd "$ROOT/../frontend-cloudflare" && pwd)"
DST="$ROOT/frontend-cloudflare"
mkdir -p "$DST"
cp -a "$SRC"/. "$DST/"
rm -f "$DST/assets/config.local.js" 2>/dev/null || true
echo "Synced frontend → $DST"
