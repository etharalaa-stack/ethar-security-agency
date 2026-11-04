# ETHAR LABS UK LTD — Static Frontend (Cloudflare Pages)

## Deploy

1. Cloudflare Pages → Connect repo → **Root directory:** `frontend-cloudflare` (or `backend-engine/frontend-cloudflare` in monorepo)
2. Build command: *(none)*  
3. Output: `/`

## API URL

Create **`assets/config.production.js`** (do not commit secrets):

```javascript
window.AGENCY_API_BASE = "https://api.yourdomain.com/api/v1";
```

Load order: `bootstrap-config.js` → `config.local.js` (dev) → `config.production.js`.

## Backend CORS

Set on API server:

```env
CORS_ORIGINS=https://your-pages.pages.dev,https://yourdomain.com
FRONTEND_URL=https://yourdomain.com
```

## Pitch links

`https://yourdomain.com/index.html?target=client.com&org=Client%20Name`
