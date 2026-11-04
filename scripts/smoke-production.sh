#!/usr/bin/env bash
# Quick health check after Coolify/VPS deploy. Usage: ./scripts/smoke-production.sh https://your-domain.com
set -euo pipefail
BASE="${1:?Usage: $0 https://public-base-url}"
BASE="${BASE%/}"
echo "== Smoke test: $BASE =="
curl -fsS "$BASE/health" | head -c 200
echo ""
curl -fsS "$BASE/api/v1/config/parts" | head -c 120
echo ""
curl -fsS -o /dev/null -w "index.html HTTP %{http_code}\n" "$BASE/index.html"
echo "OK"
