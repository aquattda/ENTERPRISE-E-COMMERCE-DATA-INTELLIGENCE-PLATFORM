"""User-controlled pricing scenario; no marketplace rate assumptions."""

from decimal import ROUND_CEILING, Decimal

from pydantic import BaseModel, ConfigDict, Field

from commerce_data.analytics.contracts import PositiveMoney


class PriceScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    price: PositiveMoney
    unit_cost: PositiveMoney
    fixed_cost: PositiveMoney
    ad_cost: PositiveMoney
    fee_percent: Decimal = Field(ge=0, le=100, allow_inf_nan=False, max_digits=10, decimal_places=6)
    discount_percent: Decimal = Field(
        ge=0, le=100, allow_inf_nan=False, max_digits=10, decimal_places=6
    )
    target_margin_percent: Decimal = Field(
        ge=0, le=100, allow_inf_nan=False, max_digits=10, decimal_places=6
    )


def simulate(s: PriceScenario):
    revenue_factor = 1 - s.discount_percent / 100
    fee_factor = 1 - s.fee_percent / 100
    net = s.price * revenue_factor
    fixed = s.unit_cost + s.fixed_cost + s.ad_cost
    profit = net * fee_factor - fixed
    denominator = revenue_factor * (fee_factor - s.target_margin_percent / 100)
    break_even = fixed / (revenue_factor * fee_factor) if revenue_factor * fee_factor > 0 else None
    target = fixed / denominator if denominator > 0 else None
    return {
        "net_revenue": net,
        "profit": profit,
        "margin_percent": profit / net * 100 if net else None,
        "break_even_price": break_even.quantize(Decimal(1), rounding=ROUND_CEILING)
        if break_even is not None
        else None,
        "target_price": target.quantize(Decimal(1), rounding=ROUND_CEILING)
        if target is not None
        else None,
        "assumptions_only": True,
        "currency": "VND",
    }
