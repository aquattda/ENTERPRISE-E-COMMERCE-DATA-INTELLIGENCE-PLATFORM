"""Shared business reports and append-only SKU cost entry."""

import csv
import io
from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response
from pydantic import Field
from sqlalchemy.orm import Session

from commerce_data.analytics.contracts import COST_FIELDS, UnitCost
from commerce_data.analytics.demo import demo_report
from commerce_data.analytics.service import current_costs, report
from commerce_data.analytics.simulation import PriceScenario, simulate
from commerce_data.storage.models import Audit, SkuCost


class CostEntry(UnitCost):
    shop_id: str = Field(default="*", min_length=1, max_length=160)
    note: str = Field(default="", max_length=500)


def encode(data):
    return jsonable_encoder(data, custom_encoder={Decimal: str})


def install_business(app: FastAPI, authorized, admin, session_dependency):
    def data(start, end, channel, currency, session, mode="company"):
        if start and end and start > end:
            raise HTTPException(422, "invalid_date_range")
        if mode == "demo":
            return demo_report(start, end, channel, currency)
        try:
            result = report(session, start, end, channel, currency)
            return {**result, "mode": "company", "demo": False}
        except ValueError:
            raise HTTPException(422, "report_capacity_exceeded") from None

    @app.get("/api/v1/business/report", dependencies=[Depends(authorized)], tags=["business"])
    def business_report(
        start: date | None = None,
        end: date | None = None,
        channel: Literal["shopee", "tiktok_shop", "online", "offline"] | None = None,
        currency: str = Query("VND", pattern=r"^[A-Z]{3}$"),
        mode: Literal["company", "demo"] = "company",
        session: Session = Depends(session_dependency),
    ):
        return JSONResponse(encode(data(start, end, channel, currency, session, mode)))

    @app.get("/api/v1/business/export", dependencies=[Depends(authorized)], tags=["business"])
    def export_report(
        start: date | None = None,
        end: date | None = None,
        channel: Literal["shopee", "tiktok_shop", "online", "offline"] | None = None,
        currency: str = Query("VND", pattern=r"^[A-Z]{3}$"),
        mode: Literal["company", "demo"] = "company",
        session: Session = Depends(session_dependency),
    ):
        rows = data(start, end, channel, currency, session, mode)["rows"]
        columns = [
            "data_mode",
            "business_date",
            "channel",
            "shop_id",
            "order_id",
            "line_id",
            "sku",
            "currency",
            "gross_sales",
            "seller_discount",
            "refund_amount",
            "shipping_income",
            "other_income",
            "quantity_dispatched",
            "quantity_restocked",
            "unit_cost_used",
            "unit_cost_effective_from",
            *COST_FIELDS,
            "net_revenue",
            "cogs",
            "known_costs",
            "profit_actual",
            "profit_provisional",
            "confidence",
            "reconciliation",
            "expected_payout",
            "actual_payout",
            "payout_difference",
            "missing",
            "record_id",
        ]
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(columns)
        for row in rows:
            values = []
            for column in columns:
                value = mode if column == "data_mode" else row.get(column)
                if isinstance(value, list):
                    value = ";".join(value)
                # Formula injection prevention for spreadsheet text; keep numeric costs numeric.
                if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
                    value = "'" + value
                values.append(value)
            writer.writerow(values)
        return Response(
            stream.getvalue().encode("utf-8-sig"),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="profit-report.csv"'},
        )

    @app.get("/api/v1/business/costs", dependencies=[Depends(authorized)], tags=["business"])
    def costs(session: Session = Depends(session_dependency)):
        return JSONResponse(
            encode({"items": [cost.model_dump() for cost in current_costs(session)]})
        )

    @app.post("/api/v1/business/costs", status_code=201, tags=["business"])
    def add_cost(
        body: CostEntry, actor: str = Depends(admin), session: Session = Depends(session_dependency)
    ):
        entry = SkuCost(**body.model_dump())
        session.add(entry)
        session.flush()
        session.add(Audit(actor=actor, action="sku_cost.append", resource_id=entry.id))
        session.commit()
        return {"id": entry.id, "saved": True}

    @app.get("/api/v1/demo/business/report", tags=["demo"])
    def public_demo():
        # Public synthetic data only: useful for local Power BI / Excel demonstrations.
        return JSONResponse(encode(demo_report()))

    @app.post("/api/v1/business/simulate", dependencies=[Depends(authorized)], tags=["business"])
    def price_scenario(body: PriceScenario):
        return JSONResponse(encode(simulate(body)))
