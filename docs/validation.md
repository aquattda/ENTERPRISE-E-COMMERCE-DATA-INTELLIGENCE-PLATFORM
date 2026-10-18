# Validation results — 2026-10-14

Environment: Windows host, Python 3.12.10; Docker Desktop Linux/WSL2
(`Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.36`), PostgreSQL 16.10.
No production systems or real marketplace/Google credentials were accessed.

| Check | Measured result |
|---|---|
| `pytest tests/unit -q` on Windows | **30 passed**, 1.67 s |
| `docker compose --profile test run --rm tests` | **45 passed**: 30 unit + 15 PostgreSQL integration, 11.37 s |
| Ruff lint and format check | Passed |
| mypy | Passed, 24 application source files |
| Alembic upgrade; downgrade-to-base/upgrade roundtrip | Passed on disposable `cdip_test` |
| Docker stack | 7 long-running services healthy; migration exited 0 |
| Prefect deployment | `cdip-dispatch/source-schedules` served; scheduled flow runs Completed |
| Live API → worker → PostgreSQL | 10,000 mock orders + 3 CSV employees persisted |
| Repeat sync | 301 orders in lookback + 3 CSV rows fetched, **0 inserted**, raw total unchanged |
| Backup/restore | pg_dump/pg_restore into `cdip_restore_check`: 10,003 versions, correct Alembic revision |

One upstream warning remains: Starlette deprecates its httpx TestClient integration in favor of
httpx2. It did not fail tests. Alembic path separator and container pytest cache warnings were fixed.
The checked-in GitHub Actions workflow has not been executed on GitHub in this session.

## Measured ingestion timing

Initial live REST mock run: 10,000 rows inserted in **10.007 seconds**; CSV: 3 rows in **0.032 seconds**.
An unchanged manual replay took **0.186 seconds** for 301 order rows and **0.023 seconds** for 3 CSV rows.
These are job durations from PostgreSQL run timestamps, excluding queue wait and initial image startup.

Separate synthetic-connector → Bronze benchmark, batch size 500, PostgreSQL test database:

| Metric | Observed |
|---|---:|
| Rows | 10,000 |
| Initial ingestion | 8.074 s |
| Throughput | 1,238.48 rows/s |
| Idempotent full replay | 5.431 s |
| Batch p95, insertion and replay combined | 0.493 s |
| Peak benchmark process RSS | 92.21 MiB |

This microbenchmark excludes HTTP latency, KPI refresh and database-process memory. It is a single
local measurement while the development stack is running, not a production capacity guarantee.
Use batch size 500 and one worker as a starting point for further measurement; source advisory locks
permit additional workers for independent sources. Do not infer 100K/300K/1M performance from this run.

To reproduce after migrations on a disposable test database:

```powershell
docker compose --profile test run --rm tests python scripts/benchmark.py --rows 10000
# Supported, not measured in this session: --rows 100000 / 300000 / 1000000
```

## Coverage boundaries

Tests cover paging, Retry-After and error retry budgets, resume with frozen pagination filters,
byte limits, exact decimal parsing, atomic rollback of records/checkpoints, scoped dedup, late
raw version preservation, snapshot add/modify/delete/re-add/reorder/duplicate handling, queued/running
recovery, PostgreSQL source read-only/keyset extraction, concurrent enqueue/source locks, scheduling
and reconciliation, generic webhook durability/auth/idempotency, RBAC, validation redaction,
secret-safe worker errors, read-only BI/runtime grants and OpenAPI contract presence.

No claims are made about Silver current-state resolution, quarantine, refunds/employee attribution,
KPI correctness, real source OAuth/signature integration, live Google Sheets, AI, employee dashboards,
production load/security readiness, or the full master prompt being complete. Those remain later phases.


## Internal UI verification — 2026-10-16

- 41 unit tests pass on Windows. Docker test database: 59 pass (41 unit + 18 PostgreSQL).
- Ruff lint/format, mypy (26 application modules), JavaScript syntax check pass.
- Edge browser regression against isolated SQLite preview: direct shared entry, CSV preview,
  duplicate-key rejection, escaped HTML values, queued receipt, completed worker result, schedule
  change, pause/resume, manual update, source filter and empty results, missing Google setup guidance.
- Visual checks at 1440px and 390px; all four mobile sections fit the viewport. Source/history tables
  become cards on mobile. Menu opens/closes; CSV dialog remains within the viewport. No page JS errors.
- Live Compose rollout completed with healthy services; browser opens without login. Existing two
  demo sources and 10,003 raw versions preserved. Deployed JS/CSS hashes match local files.
- API writes and worker reads the shared upload volume as the runtime user; verification marker removed.
- CSV end-to-end ingestion/dedup covered by SQLite and PostgreSQL tests; browser mutations ran only on
  the isolated preview, so they did not add test sources to the shared live workspace.
- One upstream Starlette/httpx deprecation warning remains. Live Google credentials and network-wide
  deployment were not tested. File-volume backup procedure is documented but has no restore drill yet.

Reproduce browser checks in two terminals from the repository root:

```powershell
# Terminal 1: isolated synthetic fixture; never uses the shared database.
.venv/Scripts/python.exe -m tests.browser.preview_server
# Terminal 2: optional QA dependency only, not required by the application.
npm install --prefix .local/ui-qa --no-audit --no-fund playwright
$env:CDIP_BROWSER_PATH='C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
node tests/browser/check_ui.cjs
```

Set CDIP_BROWSER_PATH to an installed Chromium-based browser, or install Playwright Chromium and
omit the override. Stop the preview server after testing. Fixture uploads stay under .local/ui-fixtures.

## Business demo verification — 2026-10-16

- User scope: a working presentation before joining the company; no real API credentials required for demo.
- 71 Windows unit tests and 92 Docker tests (71 unit + 21 PostgreSQL) pass. After expanding CSV columns,
  all 30 business unit tests passed again. Ruff and mypy (33 modules) pass.
- Migration 0002_cost_book downgrade/upgrade roundtrip passed on disposable cdip_test.
- Browser regression and business checks pass on isolated port8010: direct entry, upload/worker flows,
  sources, mobile menu/guide, demo/company separation, order details, filters, CSV download, cost entry,
  price simulation including infeasible target, six mobile business sections. No browser JS errors.
- Desktop/mobile screenshots visually inspected: responsive readable cards, channel chart and alert list.
- Compose rollout completed: all seven services healthy, migration exited successfully. Live health200;
  app.js/business.js/business.css hashes match local files; public demo returns18 synthetic rows.
- Shared database preserved: 2 sources,10,003 raw versions; cost book remains empty. Demo does not write it.
- Demo engine: revenue3,133,000VND, verified contribution profit799,000VND on14 complete rows;4 incomplete.
- Missing/allocated/unsettled/mismatched costs block confirmed profit; unit tests cover refund/restock,
  cost dates/currency, duplicate source identities, latest versions and malformed rows.
- CSV/Power Query are reporting handoffs only: no workbook/PBIX created, no actual Excel/PowerBI run,
  no cloud refresh. No native Shopee/TikTok adapter or real-marketplace figures are claimed.

Run business browser checks with `node tests/browser/check_business.cjs` while isolated preview is running.
Final live browser check also passed at localhost:8000: demo opens without login, five-minute guide renders,
company mode has no business rows, no page errors. Temporary preview server was stopped after QA.

## Vercel migration and machine cleanup — 2026-10-16
- Production https://cdip-business-demo.vercel.app: anonymous API/assets/root200,18 synthetic rows,
  verified contribution799000VND. Browser checks run against the deployed origin passed incl mobile.
-75 unit tests pass, Ruff pass, mypy36 modules pass. New4 tests target stateless demo routes, no company
  writes, filtering/export and price simulation. No PostgreSQL tests rerun after Docker removal.
- Deployment package explicit allowlist ~160KB; no secrets/backups/database or ingestion dependencies.
- Browser cost entries are localStorage-only and labeled as such; company report remains empty.
- Docker Desktop official uninstall returned0. Docker distro removed; residual folders explicitly
  resolved and deleted; no Docker processes, command or installed-app entry found afterwards.
- FreeC disk increased from2.48GiB to19.76GiB, net17.28GiB. Backups retained in .local/pre-uninstall-backup:
  CDIP SQL4.2MB, stopped retail PGDATA tar.gz231.9MB, uploads193bytes. Gzip fully read/verified;
  tar entries and SQL completion checked. Restore not performed for these new backups.
- Compose/Dockerfile/.dockerignore/container init script removed; CI has no container service.

Final measurement after deployment verification: C free18.30GiB versus2.48GiB at start (net15.82GiB).
Disk free space fluctuated during work; all verified Docker directories remain absent.

Update 2026-10-17: At the user's explicit request, the old retail project backup
`.local/pre-uninstall-backup/retail-postgres-data.tar.gz` was deleted.
Previous references to its retention are historical; it no longer exists.


## Source-connection scope replacement — 2026-10-17
- User explicitly narrowed the product to API/Sheets retrieval. Replaced analytics homepage/routes with
  four-source selection, credentials, read, preview and JSON/CSV download. No Docker or new heavy stack.
-96 unit tests passed (25 cloud-source tests), Ruff pass, mypy37 modules pass. Tests include signature
  construction, stable pagination windows, private Sheets shape, credential masking, same-origin/validation,
  public-only DNS and pinned TLS address, redirects/response size/auth errors, CSV duplicate column handling.
- UI tests local and production pass: source cards, marked example, presets excluding secrets/query,
  table/JSON, CSV formula handling, error states and mobile layout. Outbound cases mocked in that UI suite.
- Additional unmocked hosted browser smoke passed: JSONPlaceholder3 rows, Google public sample30 rows,
  real button submissions and CSV download; no browser JS errors. No company credentials used.
- Deployment dpl_BDCv7X1VE7NCFQAPSoT4K9mcA2RE READY, alias https://cdip-business-demo.vercel.app.
- Marketplace signatures/private Sheets are fixture-tested only. No live Shopee/TikTok/private Google
  credentials available; no OAuth one-click, token refresh, durable storage or background scheduling.
