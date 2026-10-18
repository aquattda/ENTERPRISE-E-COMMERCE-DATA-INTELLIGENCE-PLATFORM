from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from commerce_data.analytics.contracts import COST_FIELDS, OrderLine, UnitCost
from commerce_data.analytics.profit import aggregate, calculate_line
from commerce_data.analytics.service import report
from commerce_data.ingestion.engine import enqueue
from commerce_data.storage.models import Batch, Record, SkuCost, Source, SyncState
from tests.unit.test_ui import workspace


def line(**changes):
    value = dict(
        channel="shopee",
        shop_id="shop-1",
        order_id="order-1",
        line_id="line-1",
        sku="SKU-A",
        currency="VND",
        business_date="2026-10-01",
        status="completed",
        quantity_dispatched="2",
        gross_sales="200000",
        seller_discount="20000",
        refund_amount="0",
        shipping_income="0",
        other_income="0",
        unit_cost="50000",
        expected_payout="160000",
        actual_payout="160000",
        settlement_final=True,
        refunds_final=True,
        allocation="direct",
        **dict.fromkeys(COST_FIELDS, "0"),
    )
    value.update(platform_fee="10000", shipping_cost="10000", ad_cost="10000")
    value.update(changes)
    return OrderLine.model_validate(value)


def test_profit_does_not_subtract_settlement_fees_twice():
    result = calculate_line(line(), [])
    assert result["net_revenue"] == Decimal("180000")
    assert result["cogs"] == Decimal("100000")
    assert result["profit_actual"] == Decimal("50000")
    assert result["payout_difference"] == 0
    assert result["confidence"] == "verified"


@pytest.mark.parametrize("missing", ["unit_cost", *COST_FIELDS, "refund_amount", "seller_discount"])
def test_unknown_never_zero_or_verified(missing):
    result = calculate_line(line(**{missing: None}), [])
    assert result["profit_actual"] is None
    assert missing in result["missing"]


def test_refund_restocking_and_cancelled_costs():
    # Refund does not reverse COGS until the merchandise is actually restocked.
    damaged = calculate_line(line(refund_amount="180000", status="refunded"), [])
    returned = calculate_line(
        line(refund_amount="180000", quantity_restocked="2", status="refunded"), []
    )
    assert damaged["profit_actual"] == Decimal("-130000")
    assert returned["profit_actual"] == Decimal("-30000")
    assert returned["margin_percent"] is None
    cancelled = calculate_line(
        line(
            status="cancelled",
            gross_sales=0,
            seller_discount=0,
            quantity_dispatched=0,
            shipping_cost=5000,
            platform_fee=0,
            ad_cost=0,
        ),
        [],
    )
    assert cancelled["profit_actual"] == Decimal("-5000")


def test_effective_costs_currency_scope_and_conflicts():
    costs = [
        UnitCost(
            sku="SKU-A", shop_id="*", currency="VND", effective_from="2026-09-01", unit_cost=40000
        ),
        UnitCost(
            sku="SKU-A", shop_id="*", currency="VND", effective_from="2026-11-01", unit_cost=99999
        ),
        UnitCost(
            sku="SKU-A", shop_id="shop-2", currency="VND", effective_from="2026-09-01", unit_cost=1
        ),
        UnitCost(
            sku="SKU-A", shop_id="shop-1", currency="USD", effective_from="2026-09-01", unit_cost=1
        ),
    ]
    result = calculate_line(line(unit_cost=None), costs)
    assert result["cogs"] == 80000 and result["profit_actual"] == 70000
    costs.append(
        UnitCost(
            sku="SKU-A", shop_id="*", currency="VND", effective_from="2026-09-01", unit_cost=41000
        )
    )
    result = calculate_line(line(unit_cost=None), costs)
    assert result["profit_actual"] is None and "conflicting_unit_cost" in result["missing"]


@pytest.mark.parametrize(
    "changes",
    [
        {"allocation": "allocated"},
        {"settlement_final": False},
        {"refunds_final": False},
        {"status": "open"},
        {"actual_payout": None},
        {"actual_payout": "159999"},
    ],
)
def test_provisional_and_reconciliation(changes):
    result = calculate_line(line(**changes), [])
    assert result["profit_actual"] is None
    assert result["profit_provisional"] == 50000


def test_group_total_requires_every_line_and_keeps_currencies_separate():
    rows = [calculate_line(line(), []), calculate_line(line(line_id="line-2", ad_cost=None), [])]
    assert aggregate(rows, "sku")[0]["profit_actual"] is None
    assert aggregate(rows, "order")[0]["line_count"] == 2
    rows = [calculate_line(line(), []), calculate_line(line(currency="USD"), [])]
    assert len(aggregate(rows, "sku")) == 2


def test_reject_invalid_quantities_and_nonfinite_money():
    with pytest.raises(ValidationError):
        line(quantity_restocked=3)
    with pytest.raises(ValidationError):
        line(gross_sales="NaN")
    with pytest.raises(ValidationError):
        line(seller_discount="200001")


def add_business_source(db, settings, payloads, name="Business test"):
    with Session(db) as session, session.begin():
        source = Source(
            name=name,
            kind="rest",
            config={
                "kind": "rest",
                "base_url": "https://mock.test",
                "entity": "profit_line_v1",
                "key_field": "line_id",
                "shop_field": "shop_id",
                "updated_field": None,
            },
        )
        session.add(source)
        session.flush()
        session.add(SyncState(source_id=source.id))
        source_id = source.id
        run = enqueue(session, source_id)
        run.status = "succeeded"
        session.flush()
        batch = Batch(source_id=source_id, run_id=run.id, row_count=len(payloads))
        session.add(batch)
        session.flush()
        for i, payload in enumerate(payloads):
            session.add(
                Record(
                    source_id=source_id,
                    batch_id=batch.id,
                    entity="profit_line_v1",
                    shop_key="shop-1",
                    business_key=payload.get("line_id", "invalid"),
                    version_hash=str(i),
                    payload=payload,
                    received_at=datetime.now(UTC) + timedelta(seconds=i),
                )
            )
    return source_id


def test_business_api_cost_history_projection_export(db, settings):
    client = workspace(db, settings)
    empty = client.get("/api/v1/business/report").json()
    assert empty["profit_actual"] is None and empty["line_count"] == 0
    cost = {
        "sku": "SKU-A",
        "unit_cost": "50000",
        "effective_from": "2026-09-01",
        "note": "Initial purchase",
    }
    assert client.post("/api/v1/business/costs", json=cost).status_code == 201
    assert (
        client.post("/api/v1/business/costs", json={**cost, "unit_cost": "40000"}).status_code
        == 201
    )
    assert len(client.get("/api/v1/business/costs").json()["items"]) == 1
    with Session(db) as session:
        assert len(session.scalars(select(SkuCost)).all()) == 2
    add_business_source(db, settings, [line(unit_cost=None).model_dump(mode="json")])
    result = client.get("/api/v1/business/report").json()
    assert Decimal(result["profit_actual"]) == 70000
    assert result["by_order"][0]["label"] == "order-1"
    assert client.get("/api/v1/business/report?channel=offline").json()["line_count"] == 0
    assert client.get("/api/v1/business/report?currency=USD").json()["line_count"] == 0
    assert client.get("/api/v1/business/report?start=2026-11-01").json()["line_count"] == 0
    assert client.get("/api/v1/business/report?start=2026-11-01&end=2026-10-01").status_code == 422
    exported = client.get("/api/v1/business/export")
    assert exported.status_code == 200 and "70000" in exported.text
    assert "record_id" in exported.text


def test_latest_version_not_double_counted_and_duplicate_source_blocked(db, settings):
    add_business_source(
        db,
        settings,
        [line().model_dump(mode="json"), line(ad_cost="20000").model_dump(mode="json")],
    )
    with Session(db) as session:
        result = report(session)
        assert result["line_count"] == 1 and result["profit_actual"] == 40000
    add_business_source(db, settings, [line().model_dump(mode="json")], name="Conflicting source")
    with Session(db) as session:
        result = report(session)
        assert result["conflicting_lines"] == 2 and result["profit_actual"] is None


def test_invalid_business_data_blocks_verified_total(db, settings):
    add_business_source(db, settings, [line().model_dump(mode="json"), {"line_id": "bad"}])
    with Session(db) as session:
        result = report(session)
        assert result["invalid_count"] == 1 and result["profit_actual"] is None
        assert result["rows"][0]["confidence"] == "incomplete"


def test_explicit_business_contract_excludes_synthetic_technical_sources(db, settings, source):
    with Session(db) as session:
        result = report(session)
        assert result["line_count"] == 0 and result["business_source_count"] == 0


def test_demo_is_explicit_and_never_written_to_company_data(db, settings):
    client = workspace(db, settings)
    result = client.get("/api/v1/business/report?mode=demo").json()
    assert result["demo"] is True and result["line_count"] == 18
    assert result["verified_lines"] == 14
    assert result["loss_lines"] >= 4
    assert result["profit_actual"] is None
    assert Decimal(result["verified_profit"]) > 0
    assert len(result["by_channel"]) == 4
    assert any(r["reconciliation"] == "mismatch" for r in result["rows"])
    assert client.get("/api/v1/business/report?mode=company").json()["line_count"] == 0
    with Session(db) as session:
        assert not session.scalars(select(Record)).all()
    filtered = client.get("/api/v1/business/report?mode=demo&channel=offline").json()
    assert filtered["profit_actual"] is not None
    assert all(row["channel"] == "offline" for row in filtered["rows"])
    exported = client.get("/api/v1/business/export?mode=demo")
    assert "data_mode" in exported.text and "demo," in exported.text
    assert client.get("/api/v1/demo/business/report").json()["demo"] is True


def test_simulation_is_decimal_based_and_handles_impossible_target(db, settings):
    client = workspace(db, settings)
    body = dict(
        price="180000",
        unit_cost="60000",
        fixed_cost="31000",
        ad_cost="15000",
        fee_percent="5",
        discount_percent="5",
        target_margin_percent="20",
    )
    result = client.post("/api/v1/business/simulate", json=body).json()
    assert Decimal(result["profit"]) == 56450
    assert Decimal(result["break_even_price"]) == 117452
    assert result["assumptions_only"] is True
    assert (
        client.post(
            "/api/v1/business/simulate", json={**body, "target_margin_percent": "99"}
        ).json()["target_price"]
        is None
    )
    assert (
        client.post("/api/v1/business/simulate", json={**body, "price": "NaN"}).status_code == 422
    )
