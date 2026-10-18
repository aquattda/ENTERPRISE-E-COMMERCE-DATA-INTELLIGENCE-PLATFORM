# Architecture Memory

## Current intent and deployment
- Latest user correction2026-10-17: ONLY a simple source connection/data retrieval web app.
  No business analytics/statistics/P&L UI. No Docker, no accounts. Real company APIs will arrive later.
- Production https://cdip-business-demo.vercel.app; Vercel project cdip-business-demo under
  luong-tuans-projects-a65355dc. Existing CLI authentication; never output credentials.
- apps/vercel/main.py: homepage/assets, POST /api/sources/read, GET /api/sources/example and health.
  No business report/session/cost/simulation endpoints in cloud. No database/background jobs.
- apps/vercel/sources.py: request-only secrets, supported read operations, source JSON/CSV parsing.
  Website HTTPS GET with none/bearer/header auth; public/private Sheets; Shopee signed GET shop/orders;
  TikTok signed GET shops and POST order search. Fixed official marketplace hosts and operations.
- DNS resolves all addresses, rejects non-global, pins checked IP in TLS connection with original hostname.
  HTTPS443 only, no arbitrary redirects; limited Google CSV redirects revalidated.1MB/5000rows cap.
- No persistent secrets/results. Errors avoid reflecting credentials; token fields/values masked on output.
  Browser CSV escapes formula text. POST requires same-origin header; no universal write proxy.
- apps/vercel/static: standalone simple UI: four cards -> connection form -> preview/download.
  Nonsecret presets only in localStorage; no query/fragment URL persistence. Credentials reentered.
  100-row/60-column preview; downloads entire current response; manual marketplace next-page cursor
  with fixed time window. No auto pagination/refresh/OAuth authorization/scheduler yet.
- scripts/prepare_vercel.py: allowlisted ~65KB package in deploy/vercel; removes old generated analytics
  artifacts and preserves .vercel. Dependencies fastapi/pydantic/uvicorn only. CLI prod deploy existingproject.
- Old backend/analytics source retained locally for history; excluded from deploy and homepage.

## Verification / references
-96 unit tests (25 source-connection focused), Ruff and mypy37 modules passed.
- tests/browser/check_connections.cjs: local/cloud source selection, sample, presets without credentials,
  safe HTML, CSV formula handling, failure state, responsive UI. Mock outbound responses in UI tests.
- Real deployed outbound requests: JSONPlaceholder200/3rows; Google's public quickstart sheet200/30rows.
- Marketplace signing/private Sheets tested with fixtures, not real company credentials. No claim of
  live Shopee/TikTok validation. docs/source-connections.md contains official API references and limits.
- README + docs/operations.md + docs/source-connections.md are current. Other business docs historical.

## Local environment
- Docker removed at user's request; no container configuration or services. Do not reinstall.
- .env and .local ignored; never output/commit secrets. .local/pre-uninstall-backup retains CDIP SQL and
  tiny upload archive. Old retail archive explicitly deleted2026-10-17 at user request.
- Local optional preview: uvicorn apps.vercel.main:app port8010; stop owned preview when done.
- Existing .venv and .local/ui-qa Playwright available; avoid installing heavy tooling.

- Final hosted browser smoke also verified unmocked form submission for website3rows/Google30rows and CSV download.

- User-requested creator attribution: visible footer “Người tạo: Luong Thanh Tuan” and HTML author metadata.
