# command-and-control
Monorepo that hosts the DietPi-friendly Flask API **and** a Nuxt 4 dashboard designed for Cloudflare Pages/Workers.

## Apps at a Glance
- [apps/api](apps/api) — Python 3.11 Flask service exposing OpenAPI-documented telemetry + Wake-on-LAN endpoints.
- [apps/frontend](apps/frontend) — Nuxt 4 UI that consumes the API through server-side proxies and ships as a Cloudflare artifact.

```
command-and-control/
├── apps/
│   ├── api/
│   │   ├── requirements.txt
│   │   ├── .env.example / nodes.example.json
│   │   └── src/
│   │       ├── app.py
│   │       ├── config.py
│   │       ├── proxmox_client.py
│   │       └── wol.py
│   └── frontend/
│       ├── package.json
│       ├── nuxt.config.ts
│       ├── pages/index.vue
│       ├── server/api/*.ts (Cloudflare-safe proxies)
│       └── assets/styles/theme.css
├── package.json (npm workspaces entry point)
└── README.md
```

## Flask API (apps/api)
- Source lives in [apps/api/src/app.py](apps/api/src/app.py); OpenAPI docs still served from `/openapi.json` + `/docs` via ReDoc.
- Configuration is JSON-driven ([apps/api/nodes.example.json](apps/api/nodes.example.json)); copy it to `nodes.json` and adjust credentials/MACs for each host.
- `.env` exposes `NODE_CONFIG_PATH` — keep it relative so DietPi deployments can reside under `/opt/command-and-control/apps/api`.

### Run locally (DietPi or dev workstation)
```pwsh
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
Copy-Item nodes.example.json nodes.json
$Env:FLASK_APP = "src.app:create_app"
flask run --host 0.0.0.0 --port 5000
```

Expose the service via Cloudflare Tunnel, WireGuard, or another ingress so Cloudflare Pages can reach it from the public Internet.

## Nuxt Frontend (apps/frontend)
- Nuxt 4 + Tailwind CSS (via `@nuxtjs/tailwindcss`) + [Nuxt UI](https://ui.nuxt.com) drive the dashboard visuals; design tokens live in [assets/css/tailwind.css](apps/frontend/assets/css/tailwind.css) and gradients/overlays in [assets/styles/theme.css](apps/frontend/assets/styles/theme.css).
- Server routes under [apps/frontend/server/api](apps/frontend/server/api) proxy every request back to the Flask API using `NUXT_API_BASE_URL`, so the browser only talks to Cloudflare.
- `nuxt.config.ts` defaults to the Cloudflare Pages preset, but setting `NUXT_DEPLOY_TARGET=workers` switches the build to a Worker site.

### Development workflow
```pwsh
npm install # installs workspaces (frontend)
npm run dev:frontend
```
The dev server boots on `http://localhost:3100` while proxying data to whichever API base you set via `NUXT_API_BASE_URL` (falls back to `http://127.0.0.1:5000`).

### Cloudflare deployment
1. Build locally: `npm run build:frontend` (outputs to `apps/frontend/.output`).
2. Deploy with Wrangler or the Pages UI. The provided [apps/frontend/wrangler.toml](apps/frontend/wrangler.toml) sets `pages_build_output_dir = ".output/public"`.
3. Configure environment variables in Pages:
   - `NUXT_API_BASE_URL` — public HTTPS URL for the DietPi API (often via Cloudflare Tunnel).
   - `NUXT_PUBLIC_API_DOCS_URL` — optional link straight to `/docs`.

## Shared npm workspace
The root [package.json](package.json) registers `apps/frontend` as a workspace so you can run helper scripts:

- `npm run dev:frontend`
- `npm run build:frontend`
- `npm run preview:frontend`

## Next Steps
- Add authentication + mTLS to the Flask API before opening it to the Internet.
- Extend the Nuxt UI with historical charts once the API exposes RRD/task history.
- Consider a GitHub Action that builds the Nuxt app and rsyncs the Flask API to DietPi over SSH.
  "nodes": [

