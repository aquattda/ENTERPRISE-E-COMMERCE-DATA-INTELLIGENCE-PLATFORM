# Metabase setup ? monitoring only

Metabase runs at http://localhost:3000 and stores its metadata in a dedicated PostgreSQL database.
Complete its first-run administrator setup. Add a PostgreSQL data connection:

- Host `postgres`, port `5432`, database `cdip`.
- User `cdip_reader`; password is `CDIP_BI_PASSWORD` in the private `.env`.
- Schema filter: `mart`.
- Internal local Compose network has no TLS; use TLS for a production database connection.

Use `mart.pipeline_status_summary` for a table grouped by source, latest status, last successful
sync, rows fetched/inserted, duplicates, retries and rate-limit responses. Configure a monitoring
dashboard to refresh every minute. Its credentials cannot read raw payloads or source config.

Example saved query:

```sql
SELECT source_id, name, kind, latest_status, last_success_at,
       rows_fetched, rows_inserted, duplicates, retries, rate_limits
FROM mart.pipeline_status_summary
ORDER BY name;
```

Employee KPIs are **not available** until Phase 4 defines and verifies attribution, revenue timing,
refund semantics, timezone and target versions. Do not present raw order totals as employee
performance. The same mart views can be consumed by Power BI through a read-only PostgreSQL role.
Automatic dashboard provisioning and employee dashboards are Phase 5 work.
