#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$(cd "$ROOT/../frontend-cloudflare" && pwd)"
DST="$ROOT/frontend-cloudflare"
rsync -a --delete --exclude config.local.js "$SRC/" "$DST/"
echo "Synced frontend → $DST"
