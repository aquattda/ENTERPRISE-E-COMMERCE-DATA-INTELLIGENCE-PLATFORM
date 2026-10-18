"""Synthetic business scenarios for demonstrations; never written into company data."""

from datetime import UTC, date, datetime
from typing import Any

from commerce_data.analytics.contracts import COST_FIELDS, OrderLine
from commerce_data.analytics.profit import calculate_line
from commerce_data.analytics.summary import summarize


def demo_lines() -> list[OrderLine]:
    cases: list[tuple[str, str, str, dict[str, Any]]] = [
        ("shopee", "AO-DEN-M", "Áo thun đen M", {}),
        (
            "shopee",
            "AO-DEN-M",
            "Áo thun đen M",
            {"quantity_dispatched": 2, "gross_sales": 360000, "unit_cost": 60000},
        ),
        (
            "tiktok_shop",
            "BINH-500",
            "Bình giữ nhiệt 500ml",
            {"gross_sales": 250000, "unit_cost": 90000, "ad_cost": 30000},
        ),
        (
            "tiktok_shop",
            "TUI-VAI",
            "Túi vải canvas",
            {"gross_sales": 99000, "unit_cost": 55000, "ad_cost": 45000, "seller_discount": 15000},
        ),
        (
            "online",
            "AO-DEN-M",
            "Áo thun đen M",
            {"gross_sales": 190000, "platform_fee": 0, "affiliate_cost": 0},
        ),
        (
            "offline",
            "AO-TRANG-L",
            "Áo thun trắng L",
            {
                "gross_sales": 180000,
                "platform_fee": 0,
                "payment_fee": 0,
                "shipping_cost": 0,
                "ad_cost": 0,
                "affiliate_cost": 0,
            },
        ),
        ("shopee", "PHU-KIEN-A", "Phụ kiện mới", {"unit_cost": None, "gross_sales": 120000}),
        (
            "tiktok_shop",
            "BINH-500",
            "Bình giữ nhiệt 500ml",
            {"gross_sales": 250000, "unit_cost": 90000, "actual_payout_delta": -3500},
        ),
        (
            "shopee",
            "TUI-VAI",
            "Túi vải canvas",
            {
                "status": "refunded",
                "refund_amount": 170000,
                "quantity_restocked": 1,
                "return_shipping_cost": 20000,
            },
        ),
        (
            "online",
            "AO-TRANG-L",
            "Áo thun trắng L",
            {
                "status": "refunded",
                "refund_amount": 170000,
                "return_shipping_cost": 25000,
                "quantity_restocked": 0,
            },
        ),
        (
            "offline",
            "BINH-750",
            "Bình giữ nhiệt 750ml",
            {
                "gross_sales": 260000,
                "unit_cost": 90000,
                "platform_fee": 0,
                "payment_fee": 0,
                "shipping_cost": 0,
                "ad_cost": 0,
                "affiliate_cost": 0,
            },
        ),
        ("tiktok_shop", "AO-DEN-M", "Áo thun đen M", {"allocation": "allocated", "ad_cost": 17000}),
        (
            "shopee",
            "AO-TRANG-L",
            "Áo thun trắng L",
            {
                "status": "open",
                "settlement_final": False,
                "actual_payout": None,
                "refunds_final": False,
            },
        ),
        (
            "online",
            "TUI-VAI",
            "Túi vải canvas",
            {"gross_sales": 130000, "unit_cost": 55000, "ad_cost": 60000, "platform_fee": 0},
        ),
        (
            "offline",
            "AO-DEN-M",
            "Áo thun đen M",
            {
                "quantity_dispatched": 3,
                "gross_sales": 540000,
                "seller_discount": 40000,
                "platform_fee": 0,
                "payment_fee": 0,
                "shipping_cost": 0,
                "ad_cost": 0,
                "affiliate_cost": 0,
            },
        ),
        (
            "shopee",
            "BINH-500",
            "Bình giữ nhiệt 500ml",
            {
                "gross_sales": 0,
                "seller_discount": 0,
                "quantity_dispatched": 0,
                "status": "cancelled",
                "platform_fee": 0,
                "payment_fee": 0,
                "shipping_cost": 15000,
                "ad_cost": 0,
                "affiliate_cost": 0,
            },
        ),
        (
            "tiktok_shop",
            "TUI-VAI",
            "Túi vải canvas",
            {
                "gross_sales": 149000,
                "unit_cost": 55000,
                "seller_discount": 20000,
                "voucher_fee": 8000,
                "ad_cost": 25000,
            },
        ),
        (
            "online",
            "BINH-750",
            "Bình giữ nhiệt 750ml",
            {
                "gross_sales": 260000,
                "unit_cost": 90000,
                "platform_fee": 0,
                "affiliate_cost": 0,
                "ad_cost": 20000,
            },
        ),
    ]
    result = []
    for i, (channel, sku, name, changes) in enumerate(cases):
        payload: dict[str, Any] = dict(
            channel=channel,
            shop_id="DEMO-" + channel,
            order_id=f"DEMO-{i + 1:04}",
            line_id=f"DEMO-LINE-{i + 1:04}",
            sku=sku,
            product_name=name,
            currency="VND",
            business_date=date(2026, 10, 1 + i % 14),
            status="completed",
            quantity_dispatched=1,
            quantity_restocked=0,
            gross_sales=180000,
            seller_discount=10000,
            refund_amount=0,
            shipping_income=0,
            other_income=0,
            unit_cost=60000,
            settlement_final=True,
            refunds_final=True,
            allocation="direct",
            **dict.fromkeys(COST_FIELDS, 0),
        )
        payload.update(
            platform_fee=6000,
            payment_fee=3000,
            shipping_cost=15000,
            ad_cost=15000,
            affiliate_cost=5000,
            packaging_cost=3000,
            tax_cost=1000,
            other_cost=2000,
        )
        changes = dict(changes)
        delta = changes.pop("actual_payout_delta", 0)
        payload.update(changes)
        net = payload["gross_sales"] - payload["seller_discount"] - payload["refund_amount"]
        expected = net - sum(
            payload[k]
            for k in [
                "platform_fee",
                "payment_fee",
                "shipping_cost",
                "return_shipping_cost",
                "voucher_fee",
                "affiliate_cost",
                "tax_cost",
            ]
        )
        payload["expected_payout"] = expected
        if "actual_payout" not in payload:
            payload["actual_payout"] = expected + delta
        payload["campaign_id"] = ("DEMO-ADS-" + channel) if payload["ad_cost"] else None
        payload["promotion_id"] = "DEMO-SALE-10" if payload["seller_discount"] else None
        result.append(OrderLine.model_validate(payload))
    return result


def demo_report(start=None, end=None, channel=None, currency="VND"):
    rows = []
    for line in demo_lines():
        if line.currency != currency or (channel and line.channel != channel):
            continue
        if (start and line.business_date < start) or (end and line.business_date > end):
            continue
        row = calculate_line(line, [])
        row.update(
            record_id=line.line_id,
            source_id="demo",
            source_name="Dữ liệu minh họa, không phải cửa hàng thật",
            received_at=datetime(2026, 10, 15, tzinfo=UTC),
        )
        rows.append(row)
    result = summarize(rows, [], 0, 0, 4, start, end, channel, currency)
    result.update(
        mode="demo",
        demo=True,
        demo_period="01–14/10/2026",
        notice=(
            "Dữ liệu và mức phí hoàn toàn giả lập để trình diễn. "
            "Không phải báo giá hoặc mức phí của sàn."
        ),
    )
    return result
