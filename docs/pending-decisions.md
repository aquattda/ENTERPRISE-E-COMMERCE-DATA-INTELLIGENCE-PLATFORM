# Pending decisions and integration work

## Business decisions required before employee KPI implementation

- Revenue recognition event: placed, paid, delivered or another approved event.
- Gross/net definitions, shipping/tax/discount treatment, cancellation and partial-refund timing.
- Currency separation and approved exchange-rate conversion policy; never sum mixed currencies.
- Attribution across multiple employees, weights, roles, reassignment effective dates and history.
- Employee identity mapping authority, ambiguous aliases and manual approval workflow.
- Business timezone, day/hour cutoffs, late-arrival windows and historical correction policy.
- Versioned target definitions and formula effective dates; unknown/null does not mean zero.
- Tombstone interpretation, retention, PII access and acceptable freshness/reconciliation thresholds.

## External access not provided

Shopee, TikTok Shop and Shopify need approved API documentation/version, app credentials, scopes,
shop authorization, quota and webhook signature contracts. No endpoints for those platforms have
been invented. `apps/mock_api` is an explicitly synthetic generic source.

Google Sheets needs a service-account JSON secret (and spreadsheet sharing) or a managed OAuth
token, configured bounded ranges, stable business keys and a publication/snapshot consistency policy.
Live Google access has not been tested. PostgreSQL source needs a read-only account/replica, a stable
non-null `(updated_at, shop_id, id)` extraction order and supporting indexes. MySQL/SQL Server/CDC
are not implemented.

## Phase backlog

3. Polars/DuckDB profiling, data contracts, quality rule severity/actions, per-batch reports,
   quarantine, schema drift/freshness/volume analysis and audited normalization.
4. Core tables/migrations, employee identities, order/item/refund histories, temporal attribution,
   configurable versioned KPI formulas and precise affected-partition recalculation.
5. Verified employee/team/shop KPI APIs, hourly/daily marts and dashboard provisioning.
6. Provider abstraction, constrained read-only analysis tools, PII masking, structured evidence,
   proposal approval lifecycle and prompt-injection defenses. No LLM calls are made today.
7. Expanded failures/security/load tests, measured 100K/300K/1M benchmarks, external alert delivery,
   retention/archival, backup restore drills and production deployment review.

The current implementation is an ingestion foundation, not a claim that the full master prompt
or a production-ready enterprise analytics platform is complete.
