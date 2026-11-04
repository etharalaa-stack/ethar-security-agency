#!/usr/bin/env bash
# ETHAR LABS — one script after you add SSH key or PAT. Run: ./scripts/complete-all.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
KEY="$HOME/.ssh/id_ed25519_ethar"
SSH_CFG='Host github.com-ethar
  HostName github.com
  User git
  IdentityFile '"$KEY"'
  IdentitiesOnly yes'

echo "== 1) Sync frontend =="
chmod +x scripts/*.sh start-dev.sh 2>/dev/null || true
./scripts/sync-frontend.sh

echo ""
echo "== 2) Git push via SSH =="
if [[ ! -f "$KEY" ]]; then
  ssh-keygen -t ed25519 -C "etharalaa-stack@github" -f "$KEY" -N ""
fi
grep -q 'Host github.com-ethar' ~/.ssh/config 2>/dev/null || {
  mkdir -p ~/.ssh
  chmod 700 ~/.ssh
  echo "$SSH_CFG" >> ~/.ssh/config
  chmod 600 ~/.ssh/config
}
git remote set-url origin git@github.com-ethar:etharalaa-stack/ethar-security-agency.git
export GIT_SSH_COMMAND="ssh -F $HOME/.ssh/config -o BatchMode=yes"
if ! git push -u origin main; then
  echo ""
  echo "Push failed. Add this public key to GitHub → Settings → SSH keys:"
  echo "https://github.com/settings/ssh/new"
  echo ""
  cat "${KEY}.pub"
  echo ""
  echo "Then run again: ./scripts/complete-all.sh"
  exit 1
fi

echo ""
echo "== 3) Coolify environment file =="
if [[ -n "${PUBLIC_DOMAIN:-}" ]]; then
  ./scripts/generate-coolify-world-env.sh "$PUBLIC_DOMAIN"
  echo "Paste file: $ROOT/coolify-paste.env"
else
  echo "Run: PUBLIC_DOMAIN=your.coolify.domain ./scripts/generate-coolify-world-env.sh"
  echo "Then paste coolify-paste.env into Coolify → Environment → Save → Redeploy"
fi

echo ""
echo "== 4) Coolify UI =="
echo "  http://128.140.121.115:8000 → ethar-security-agency"
echo "  Compose: docker-compose.coolify.yml · Domain on service: web · Deploy"
echo ""
echo "== 5) Smoke test (after deploy) =="
echo "  ./scripts/smoke-production.sh https://\${PUBLIC_DOMAIN:-YOUR_PUBLIC_URL}"
echo ""
echo "Done (git pushed). Finish Coolify paste + domain in browser."
