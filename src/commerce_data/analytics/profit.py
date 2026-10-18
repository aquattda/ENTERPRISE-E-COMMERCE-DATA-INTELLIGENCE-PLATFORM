"""Traceable contribution-profit arithmetic, independent of vendor fee schedules."""

from collections import defaultdict
from decimal import Decimal
from typing import Any, cast

from commerce_data.analytics.contracts import COST_FIELDS, OrderLine, UnitCost

ZERO = Decimal(0)


def calculate_line(line: OrderLine, costs: list[UnitCost]) -> dict:
    missing = []
    unit_cost = line.unit_cost
    cost_date = None
    if unit_cost is None:
        eligible = [
            c
            for c in costs
            if c.sku == line.sku
            and c.shop_id in (line.shop_id, "*")
            and c.currency == line.currency
            and c.effective_from <= line.business_date
        ]
        if eligible:
            specific = [c for c in eligible if c.shop_id == line.shop_id]
            eligible = specific or eligible
            latest = max(c.effective_from for c in eligible)
            candidates = [c for c in eligible if c.effective_from == latest]
            if len({c.unit_cost for c in candidates}) == 1:
                unit_cost = candidates[0].unit_cost
                cost_date = latest.isoformat()
            else:
                missing.append("conflicting_unit_cost")
    if unit_cost is None:
        missing.append("unit_cost")
    cogs = (
        None
        if unit_cost is None
        else (line.quantity_dispatched - line.quantity_restocked) * unit_cost
    )
    revenue_fields = ("seller_discount", "refund_amount", "shipping_income", "other_income")
    missing.extend(field for field in revenue_fields if getattr(line, field) is None)
    missing.extend(field for field in COST_FIELDS if getattr(line, field) is None)
    revenue = (
        None
        if any(getattr(line, field) is None for field in revenue_fields)
        else (
            line.gross_sales
            - cast(Decimal, line.seller_discount)
            - cast(Decimal, line.refund_amount)
            + cast(Decimal, line.shipping_income)
            + cast(Decimal, line.other_income)
        )
    )
    known_costs = sum(
        (getattr(line, field) for field in COST_FIELDS if getattr(line, field) is not None), ZERO
    )
    complete_costs = all(getattr(line, field) is not None for field in COST_FIELDS)
    profit = revenue - cogs - known_costs if revenue is not None and cogs is not None else None
    if not line.refunds_final:
        missing.append("refunds_final")
    if not line.settlement_final:
        missing.append("settlement_final")
    if line.status == "open":
        missing.append("order_not_final")
    if line.allocation != "direct":
        missing.append(
            "allocated_costs" if line.allocation == "allocated" else "allocation_unresolved"
        )
    difference = None
    if line.expected_payout is not None and line.actual_payout is not None:
        difference = line.actual_payout - line.expected_payout
        reconciliation = "matched" if difference == ZERO else "mismatch"
    else:
        reconciliation = "missing"
    if reconciliation != "matched":
        missing.append("settlement_" + reconciliation)
    confidence = "verified" if not missing and complete_costs else "incomplete"
    return {
        **line.model_dump(),
        "unit_cost_used": unit_cost,
        "unit_cost_effective_from": cost_date,
        "cogs": cogs,
        "net_revenue": revenue,
        "known_costs": known_costs,
        "profit_provisional": profit,
        "profit_actual": profit if confidence == "verified" else None,
        "margin_percent": profit / revenue * 100 if profit is not None and revenue else None,
        "confidence": confidence,
        "missing": list(dict.fromkeys(missing)),
        "reconciliation": reconciliation,
        "payout_difference": difference,
        # Payouts are a separate reconciliation: never subtract fees from them again.
    }


def aggregate(rows: list[dict], dimension: str) -> list[dict]:
    groups: dict[tuple[Any, ...], list[dict]] = defaultdict(list)
    for row in rows:
        key: tuple[Any, ...]
        if dimension == "order":
            key = (row["channel"], row["shop_id"], row["order_id"], row["currency"])
        else:
            value = row.get(dimension)
            if not value:
                continue
            key = (value, row["currency"])
        groups[key].append(row)
    result = []
    for key, members in groups.items():
        complete = all(r["confidence"] == "verified" for r in members)
        revenue_complete = all(r["net_revenue"] is not None for r in members)
        revenue = sum((r["net_revenue"] for r in members), ZERO) if revenue_complete else None
        profit = sum((r["profit_actual"] for r in members), ZERO) if complete else None
        result.append(
            {
                "key": list(key),
                "label": key[2] if dimension == "order" else key[0],
                "currency": key[-1],
                "line_count": len(members),
                "incomplete_lines": sum(r["confidence"] != "verified" for r in members),
                "net_revenue": revenue,
                "profit_actual": profit,
                "margin_percent": profit / revenue * 100
                if profit is not None and revenue
                else None,
                "ad_cost": sum((r["ad_cost"] for r in members), ZERO)
                if all(r["ad_cost"] is not None for r in members)
                else None,
                "confidence": "verified" if complete else "incomplete",
            }
        )
    return result
