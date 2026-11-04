#!/usr/bin/env bash
# One shot: sync, Coolify env for ai.etharlabs.com, English Telegram test, git push.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
chmod +x scripts/*.sh start-dev.sh 2>/dev/null || true

./scripts/sync-frontend.sh
PUBLIC_DOMAIN=ai.etharlabs.com EXTRA_DOMAINS=www.api.etharlabs.com ./scripts/generate-coolify-world-env.sh
./scripts/telegram-test.sh "ETHAR LABS UK LTD — Production env file refreshed. Paste coolify-paste.env into Coolify, set web domain port 80, then Redeploy."

echo ""
echo "=== Coolify ==="
echo "Panel: http://128.140.121.113:8000 (or .115)"
echo "Paste: $ROOT/coolify-paste.env → Environment → Save → Redeploy"
echo "Domains (service web): https://ai.etharlabs.com + https://www.api.etharlabs.com — internal port 80"
echo ""
echo "=== DNS (Cloudflare) ==="
echo "A  ai           → 128.140.121.115"
echo "A  www.api      → 128.140.121.115"
echo ""
echo "=== After DNS propagates ==="
echo "./scripts/smoke-production.sh https://ai.etharlabs.com"

export GIT_SSH_COMMAND="ssh -F $HOME/.ssh/config -o BatchMode=yes"
git push origin main 2>/dev/null || echo "(git push skipped — run manually if needed)"
