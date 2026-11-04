# Cloudflare edge (optional) — ETHAR LABS public site

Use when your Coolify domain is proxied through Cloudflare (orange cloud).

## Recommended settings

1. **SSL/TLS** → Full (strict)
2. **WAF** → Managed rules ON
3. **Bot Fight Mode** → ON (or Super Bot Fight on paid plan)
4. **Rate limiting rule**
   - URI contains `/api/v1/public/quick-scan`
   - 30 requests / minute / IP → Block 10 minutes
5. **Rate limiting rule**
   - URI contains `/api/v1/orders`
   - 15 requests / minute / IP → Block 15 minutes

## Cache

- **Do not cache** `/api/*` (Cache Level: Bypass for `/api/*`)
- Static HTML/assets may cache at edge (optional)

## Headers (Transform Rules)

Add response headers for `yourdomain.com`:

- `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
- `X-Content-Type-Options: nosniff`

API already sends security headers; this reinforces the `web` nginx layer.

## Origin

Point DNS A/AAAA or CNAME to Coolify server; restrict origin firewall to Cloudflare IPs if possible (Hetzner firewall).
