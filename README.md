# ETHAR LABS UK LTD — Security Agency Backend (v2.1)

FastAPI API, async worker, modular audits, quick-scan, Telegram HITL.

Static frontend: `frontend-cloudflare/` (included in repo; sync via `./scripts/sync-frontend.sh` from sibling if needed). See `PRODUCTION.md` and `frontend-cloudflare/README.md`.

## Run locally (copy/paste)

```bash
./scripts/install-all.sh
API_PORT=9815 ./start-dev.sh
```

**Full command list:** see [`COPY-PASTE-RUNBOOK.md`](COPY-PASTE-RUNBOOK.md)

## Docker / Coolify / Railway

```bash
docker compose up --build
```

Use `coolify.compose.yaml` on Coolify. Set `PORT`, secrets, and persistent volumes for `data/` and `generated_reports/`.
# ethar-security-agency
