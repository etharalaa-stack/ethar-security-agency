# Production & Revenue Checklist — ETHAR LABS UK LTD

## 1. Environment

```bash
cp .env.production.example .env
# Fill wallets, BSCSCAN, Telegram, ADMIN_SECRET, public URLs
./scripts/validate-env.sh
```

## 2. Deploy options

| Target | Command |
|--------|---------|
| **Coolify (Hetzner)** | [`COOLIFY-HETZNER.md`](COOLIFY-HETZNER.md) + `docker-compose.coolify.yml` |
| **Coolify / VPS full stack** | `docker compose -f docker-compose.fullstack.yml up -d --build` |
| **API + worker only** | `docker compose up -d --build` |
| **Railway** | Connect repo, use `railway.toml`, set env vars in dashboard |
| **Cloudflare Pages** | Deploy `frontend-cloudflare/` + `config.production.js` |

Full stack serves UI on port **8080** and proxies `/api/*` to the API container.

## 3. Revenue flow

1. Generate pitches: `admin-pitch.html` + `ADMIN_SECRET`
2. Client opens pitch URL → quick scan → selects parts → pays USDT
3. Telegram: payment alert → worker runs desks → PDF → HITL approve link
4. Client downloads PDF from `track.html`

## 4. Git push (GitHub)

Use **Personal Access Token** or **SSH** — passwords are not supported.

```bash
git push -u origin main
```

## 5. Monorepo

Run `./scripts/sync-frontend.sh` after editing sibling `../frontend-cloudflare` before commit.
