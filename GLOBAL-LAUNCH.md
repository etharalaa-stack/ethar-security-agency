# ETHAR LABS UK LTD — Global launch & cyber readiness

**Company No. 17032523** · England & Wales · London, United Kingdom

---

## 1) Brand & legal (already in product)

- Footer / PDF / pitch: **ETHAR LABS UK LTD**, Company No. **17032523**
- Pages: `privacy.html`, `terms.html`, `refund-sla.html`
- GDPR-aligned copy; defensive scope only

---

## 2) Production security (platform)

| Control | Implementation |
|---------|----------------|
| Order privacy | `access_token` in track URL; required when `REQUIRE_ORDER_ACCESS_TOKEN=true` |
| Admin | `X-Admin-Secret` header (not logged in query) |
| SSRF | Quick scan / http(s) targets blocked for private IPs |
| Rate limits | Quick scan, orders, admin, downloads |
| PDF path | Traversal-safe `safe_report_path` |
| API surface | `/docs` hidden when `DEBUG=false` |
| Headers | SecurityHeadersMiddleware + nginx hardening |
| CORS | Restrict to your domain(s); avoid `*` + credentials in production |
| Payments | USDT amount/wallet verify; `ALLOW_TEST_PAYMENTS=false` live |

---

## 3) Coolify / DNS checklist

```env
DEBUG=false
REQUIRE_ORDER_ACCESS_TOKEN=true
ALLOW_TEST_PAYMENTS=false
CORS_ORIGINS=https://yourdomain.com
TRUSTED_HOSTS=yourdomain.com,www.yourdomain.com
FRONTEND_URL=https://yourdomain.com
PUBLIC_API_BASE_URL=https://yourdomain.com
```

- **HTTPS** on `web` (Let’s Encrypt)
- **Cloudflare** (optional): WAF, DDoS, bot fight mode
- **Backups**: Coolify volumes `agency_data`, `agency_reports`

---

## 4) Operational

- Rotate `ADMIN_SECRET` quarterly
- Telegram HITL for payments + PDF approval
- Monitor Coolify logs; no secrets in git
- ICO UK: privacy policy matches actual data retention (`privacy.html`)

---

## 5) Deploy after security update

```bash
git push origin main
```

Coolify → **Redeploy** (rebuild `web`, `api`, `worker`).

---

## 6) Client communication

Give customers **full track URL** including `token=` (from order confirmation).  
Do not publish admin pitch URL without IP allowlist or VPN (optional nginx rule).
