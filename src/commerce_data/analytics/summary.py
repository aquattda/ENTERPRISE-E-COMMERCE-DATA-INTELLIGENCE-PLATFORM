"""Pure report aggregation, shared by local and serverless demos."""

from collections import Counter
from decimal import Decimal

from commerce_data.analytics.profit import aggregate


def summarize(
    rows,
    invalid,
    conflicts,
    business_source_count,
    cost_count,
    start=None,
    end=None,
    channel=None,
    currency="VND",
):
    rows.sort(key=lambda row: (row["business_date"], row["order_id"], row["line_id"]), reverse=True)
    complete = bool(rows) and all(row["confidence"] == "verified" for row in rows)
    actual = sum((row["profit_actual"] for row in rows), Decimal(0)) if complete else None
    revenue = (
        sum((row["net_revenue"] for row in rows), Decimal(0))
        if rows and all(row["net_revenue"] is not None for row in rows)
        else None
    )
    alerts = []
    missing_counts = Counter(field for row in rows for field in row["missing"])
    for field, count in missing_counts.items():
        alerts.append({"kind": "missing", "field": field, "count": count})
    losses = [r for r in rows if r["profit_actual"] is not None and r["profit_actual"] < 0]
    for row in losses[:10]:
        alerts.append(
            {
                "kind": "loss",
                "order_id": row["order_id"],
                "sku": row["sku"],
                "amount": row["profit_actual"],
                "currency": row["currency"],
            }
        )
    return {
        "currency": currency,
        "from": start,
        "to": end,
        "channel": channel,
        "line_count": len(rows),
        "order_count": len({(r["channel"], r["shop_id"], r["order_id"]) for r in rows}),
        "verified_profit": sum(
            (r["profit_actual"] for r in rows if r["profit_actual"] is not None), Decimal(0)
        )
        if any(r["profit_actual"] is not None for r in rows)
        else None,
        "verified_lines": sum(r["confidence"] == "verified" for r in rows),
        "loss_lines": len(losses),
        "net_revenue": revenue,
        "profit_actual": actual,
        "rows": rows,
        "by_order": aggregate(rows, "order"),
        "by_sku": aggregate(rows, "sku"),
        "by_channel": aggregate(rows, "channel"),
        "by_campaign": aggregate(rows, "campaign_id"),
        "by_promotion": aggregate(rows, "promotion_id"),
        "alerts": alerts,
        "invalid_count": len(invalid),
        "invalid_records": invalid[:20],
        "conflicting_lines": conflicts,
        "business_source_count": business_source_count,
        "cost_count": cost_count,
        "scope": "Order contribution after recorded costs; not company net income",
        "formula_version": "profit-line-v1",
    }
