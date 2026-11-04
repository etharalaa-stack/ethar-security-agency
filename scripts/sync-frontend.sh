#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$(cd "$ROOT/../frontend-cloudflare" && pwd)"
DST="$ROOT/frontend-cloudflare"
if command -v rsync >/dev/null 2>&1; then
  timeout 120 rsync -a --delete --exclude config.local.js "$SRC/" "$DST/" 2>/dev/null || {
    echo "rsync slow/failed — using cp fallback"
    mkdir -p "$DST"
    cp -a "$SRC"/. "$DST/"
    rm -f "$DST/assets/config.local.js" 2>/dev/null || true
  }
else
  mkdir -p "$DST"
  cp -a "$SRC"/. "$DST/"
  rm -f "$DST/assets/config.local.js" 2>/dev/null || true
fi
echo "Synced frontend → $DST"
