#!/usr/bin/env bash
# Max automation: sync, generate Coolify env, push git, print final steps.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
DOMAIN="${PUBLIC_DOMAIN:-${1:-}}"

chmod +x scripts/*.sh start-dev.sh 2>/dev/null || true
"$ROOT/scripts/sync-frontend.sh"

if [[ -n "$DOMAIN" ]]; then
  "$ROOT/scripts/generate-coolify-world-env.sh" "$DOMAIN"
else
  echo "Skip env file: set PUBLIC_DOMAIN=your.domain.com"
fi

echo ""
echo "=== Git push ==="
if GIT_SSH_COMMAND="ssh -F $HOME/.ssh/config -o BatchMode=yes" git push origin main; then
  echo "Push OK"
else
  echo "Push failed — run: git push origin main"
fi

echo ""
echo "=== Coolify (manual 2 min) ==="
echo "1. http://128.140.121.115:8000 → ethar-security-agency → Environment"
echo "2. Paste: $ROOT/coolify-paste.env (if generated)"
echo "3. web → Domains → https://${DOMAIN:-YOUR-DOMAIN}"
echo "4. Deploy / Redeploy"
echo ""
echo "=== Test ==="
echo "./scripts/smoke-production.sh https://${DOMAIN:-YOUR-DOMAIN}"
