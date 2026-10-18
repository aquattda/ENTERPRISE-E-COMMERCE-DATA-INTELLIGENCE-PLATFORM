"""Read-only business projection over explicitly contracted ingestion sources."""

from collections import Counter, defaultdict
from datetime import date

from pydantic import ValidationError
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from commerce_data.analytics.contracts import OrderLine, UnitCost
from commerce_data.analytics.profit import calculate_line
from commerce_data.analytics.summary import summarize
from commerce_data.storage.models import Record, Run, SkuCost, Source

ENTITY = "profit_line_v1"
MAX_LINES = 50000


def current_costs(session: Session) -> list[UnitCost]:
    seen = set()
    result = []
    for row in session.scalars(
        select(SkuCost).order_by(SkuCost.created_at.desc(), SkuCost.id.desc())
    ):
        key = row.shop_id, row.sku, row.currency, row.effective_from
        if key not in seen:
            seen.add(key)
            result.append(
                UnitCost(
                    sku=row.sku,
                    shop_id=row.shop_id,
                    currency=row.currency,
                    effective_from=row.effective_from,
                    unit_cost=row.unit_cost,
                )
            )
    return result


def report(
    session: Session,
    start: date | None = None,
    end: date | None = None,
    channel: str | None = None,
    currency: str = "VND",
) -> dict:
    sources = {s.id: s for s in session.scalars(select(Source)).all()}
    order_clock = case(
        (Source.kind.in_(["csv", "sheets"]), Record.received_at),
        else_=func.coalesce(Record.source_updated_at, Record.received_at),
    )
    ranked = (
        select(
            Record.id,
            func.row_number()
            .over(
                partition_by=(
                    Record.source_id,
                    Record.entity,
                    Record.shop_key,
                    Record.business_key,
                ),
                order_by=(order_clock.desc(), Record.received_at.desc(), Record.id.desc()),
            )
            .label("position"),
        )
        .join(Source, Source.id == Record.source_id)
        .where(Record.entity == ENTITY)
        .subquery()
    )
    records = session.scalars(
        select(Record)
        .join(ranked, ranked.c.id == Record.id)
        .where(ranked.c.position == 1, Record.deleted.is_(False))
        .limit(MAX_LINES + 1)
    ).all()
    if len(records) > MAX_LINES:
        raise ValueError("report_capacity_exceeded")
    parsed = []
    invalid = []
    for record in records:
        mapping = sources[record.source_id].config.get("field_mapping", {})
        payload = dict(record.payload)
        for target, original in mapping.items():
            payload[target] = record.payload.get(original)
        # An empty spreadsheet cell is unknown, never a zero.
        payload = {
            key: None if value == "" and key != "product_name" else value
            for key, value in payload.items()
        }
        try:
            line = OrderLine.model_validate(payload)
        except ValidationError as error:
            invalid.append(
                {
                    "record_id": record.id,
                    "source_id": record.source_id,
                    "fields": [str(e["loc"][0]) for e in error.errors()],
                }
            )
            continue
        parsed.append((line, record))
    identities = Counter(line.identity for line, _ in parsed)
    costs = current_costs(session)
    costs_by_sku = defaultdict(list)
    for cost in costs:
        costs_by_sku[cost.sku].append(cost)
    latest_runs = select(
        Run.source_id,
        Run.status,
        func.row_number()
        .over(partition_by=Run.source_id, order_by=(Run.created_at.desc(), Run.id.desc()))
        .label("rank"),
    ).subquery()
    unfinished = set(
        session.scalars(
            select(latest_runs.c.source_id).where(
                latest_runs.c.rank == 1, latest_runs.c.status != "succeeded"
            )
        )
    )
    rows = []
    conflicts = 0
    for line, record in parsed:
        if identities[line.identity] > 1:
            conflicts += 1
            continue
        if line.currency != currency or (channel and line.channel != channel):
            continue
        if (start and line.business_date < start) or (end and line.business_date > end):
            continue
        row = calculate_line(line, costs_by_sku[line.sku])
        if record.source_id in unfinished:
            row["confidence"] = "incomplete"
            row["profit_actual"] = None
            row["missing"].append("source_sync_unfinished")
        row.update(
            record_id=record.id,
            source_id=record.source_id,
            source_name=sources[record.source_id].name,
            received_at=record.received_at,
        )
        rows.append(row)
    if invalid or conflicts:
        for row in rows:
            row["profit_actual"] = None
            row["confidence"] = "incomplete"
            row["missing"].append("dataset_quality")
    return summarize(
        rows,
        invalid,
        conflicts,
        sum(s.config.get("entity") == ENTITY for s in sources.values()),
        len(costs),
        start,
        end,
        channel,
        currency,
    )
