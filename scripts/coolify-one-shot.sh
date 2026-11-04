#!/usr/bin/env bash
# Prepare repo + print Coolify checklist (run on laptop before/after git push).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
chmod +x scripts/*.sh start-dev.sh 2>/dev/null || true
"$ROOT/scripts/sync-frontend.sh"
echo ""
echo "=== Git (if not pushed) ==="
echo "  git push -u origin main"
echo ""
echo "=== Coolify UI (128.140.121.115:8000) ==="
echo "  Repo: etharalaa-stack/ethar-security-agency"
echo "  Compose: docker-compose.coolify.yml"
echo "  Domain on service: web"
echo "  Env: copy from .env.coolify.example"
echo ""
echo "=== After deploy ==="
echo "  ./scripts/smoke-production.sh https://YOUR_PUBLIC_URL"
