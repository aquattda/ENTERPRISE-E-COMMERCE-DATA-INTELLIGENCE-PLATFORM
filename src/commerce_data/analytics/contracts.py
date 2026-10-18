"""Explicit line-level economics; unknown costs must never become zero."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Money = Annotated[Decimal, Field(allow_inf_nan=False, max_digits=24, decimal_places=6)]
PositiveMoney = Annotated[
    Decimal, Field(ge=0, allow_inf_nan=False, max_digits=24, decimal_places=6)
]
COST_FIELDS = (
    "platform_fee",
    "payment_fee",
    "shipping_cost",
    "return_shipping_cost",
    "voucher_fee",
    "ad_cost",
    "affiliate_cost",
    "packaging_cost",
    "tax_cost",
    "other_cost",
)


class OrderLine(BaseModel):
    model_config = ConfigDict(extra="ignore")
    channel: Literal["shopee", "tiktok_shop", "online", "offline"]
    shop_id: str = Field(min_length=1, max_length=160)
    order_id: str = Field(min_length=1, max_length=160)
    line_id: str = Field(min_length=1, max_length=160)
    sku: str = Field(min_length=1, max_length=160)
    product_name: str = Field(default="", max_length=300)
    currency: str = Field(default="VND", pattern=r"^[A-Z]{3}$")
    business_date: date
    status: Literal["open", "completed", "refunded", "cancelled"]
    quantity_dispatched: PositiveMoney
    quantity_restocked: PositiveMoney = Decimal(0)
    gross_sales: PositiveMoney
    seller_discount: PositiveMoney | None = None
    refund_amount: PositiveMoney | None = None
    shipping_income: Money | None = None
    other_income: Money | None = None
    unit_cost: PositiveMoney | None = None
    platform_fee: Money | None = None
    payment_fee: Money | None = None
    shipping_cost: Money | None = None
    return_shipping_cost: Money | None = None
    voucher_fee: Money | None = None
    ad_cost: Money | None = None
    affiliate_cost: Money | None = None
    packaging_cost: Money | None = None
    tax_cost: Money | None = None
    other_cost: Money | None = None
    expected_payout: Money | None = None
    actual_payout: Money | None = None
    settlement_final: bool = False
    refunds_final: bool = False
    allocation: Literal["direct", "allocated", "unresolved"] = "unresolved"
    campaign_id: str | None = Field(default=None, max_length=160)
    promotion_id: str | None = Field(default=None, max_length=160)

    @model_validator(mode="after")
    def coherent_amounts(self):
        if self.quantity_restocked > self.quantity_dispatched:
            raise ValueError("Restocked quantity exceeds dispatched quantity")
        if self.seller_discount is not None and self.seller_discount > self.gross_sales:
            raise ValueError("Seller discount exceeds gross sales")
        return self

    @property
    def identity(self):
        return self.channel, self.shop_id, self.order_id, self.line_id


class UnitCost(BaseModel):
    model_config = ConfigDict(extra="ignore")
    sku: str = Field(min_length=1, max_length=160)
    shop_id: str = Field(min_length=1, max_length=160)
    currency: str = Field(default="VND", pattern=r"^[A-Z]{3}$")
    effective_from: date
    unit_cost: PositiveMoney
