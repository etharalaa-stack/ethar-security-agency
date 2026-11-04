#!/usr/bin/env bash
# After Cloudflare A records → 128.140.121.115 and Coolify domain on web:80
set -euo pipefail
PRIMARY="${1:-ai.etharlabs.com}"
ALT="${ALT_DOMAIN:-www.api.etharlabs.com}"
IP_EXPECT="${IP_EXPECT:-128.140.121.115}"

probe() {
  local host="$1"
  local res
  res="$(dig +short "$host" A | head -1 || true)"
  echo "== DNS: $host =="
  if [[ -z "$res" ]]; then
    echo "  No A record."
    return 1
  fi
  echo "  Resolved: $res"
  local code body
  code="$(curl -sS -m 20 -k -o /tmp/ethar-health -w '%{http_code}' "https://${host}/health" 2>/dev/null || echo 000)"
  body="$(head -c 80 /tmp/ethar-health 2>/dev/null || true)"
  echo "  HTTPS /health: HTTP ${code}  ${body}"
  [[ "$code" == "200" ]]
}

echo "Production check (ETHAR LABS Coolify / web:80)"
echo ""

OK_PRIMARY=0
OK_ALT=0
probe "$PRIMARY" && OK_PRIMARY=1 || true
echo ""
probe "$ALT" && OK_ALT=1 || true
echo ""

if [[ "$OK_ALT" == 1 ]]; then
  echo "LIVE: https://${ALT}/index.html"
  ./scripts/smoke-production.sh "https://${ALT}" 2>/dev/null || true
fi

if [[ "$OK_PRIMARY" == 1 ]]; then
  echo "LIVE: https://${PRIMARY}/index.html"
  exit 0
fi

if [[ "$OK_ALT" == 1 && "$OK_PRIMARY" != 1 ]]; then
  echo ""
  echo "DIAGNOSIS: ${ALT} works; ${PRIMARY} is NOT in Coolify Domains (503 = no router)."
  echo "Fix: Coolify → web → Domains → copy settings from ${ALT} for ${PRIMARY} (service web, port 80, HTTPS)."
  echo "Or set FRONTEND_URL / PUBLIC_API_BASE_URL to https://${ALT} in Environment until ai is added."
  exit 0
fi

echo "FAIL: neither hostname returns /health 200. Fix Coolify web domains (port 80, not api:8000)."
exit 1
