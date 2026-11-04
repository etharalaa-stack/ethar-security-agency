#!/usr/bin/env bash
# After Cloudflare A records → 128.140.121.115 and Coolify domain on web:80
set -euo pipefail
DOMAIN="${1:-ai.etharlabs.com}"
IP_EXPECT="${IP_EXPECT:-128.140.121.115}"
echo "== DNS: $DOMAIN =="
RES="$(dig +short "$DOMAIN" A | head -1 || true)"
if [[ -z "$RES" ]]; then
  echo "FAIL: no A record. Cloudflare Name must be 'ai' (not ai.etharlabs.com), Content $IP_EXPECT, DNS only."
  exit 1
fi
if [[ "$RES" != "$IP_EXPECT" && "$RES" != 104.* && "$RES" != 172.* ]]; then
  echo "WARN: A record is $RES (expected $IP_EXPECT). Fix typo 123 vs 128."
fi
echo "Resolved: $RES"
echo ""
echo "== HTTPS /health =="
if curl -fsS -m 20 "https://${DOMAIN}/health" 2>/dev/null; then
  echo ""
  echo "OK — site live."
  exit 0
fi
echo ""
echo "FAIL: HTTPS not routing to the web container yet."
echo "Coolify → service WEB (not api) → Domains:"
echo "  https://${DOMAIN}  internal port 80  HTTPS/Let's Encrypt ON"
echo "  Remove domains pointing web to port 8000."
echo "Then Redeploy and run this script again."
