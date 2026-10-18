"""Append-only dated SKU cost book for the shared business workspace."""

import sqlalchemy as sa
from alembic import op

revision = "0002_cost_book"
down_revision = "0001_ingestion"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sku_cost_book",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("sku", sa.String(160), nullable=False),
        sa.Column("shop_id", sa.String(160), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("unit_cost", sa.Numeric(24, 6), nullable=False),
        sa.Column("note", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("unit_cost >= 0", name="ck_unit_cost_nonnegative"),
        schema="ops",
    )
    op.create_index(
        "ix_cost_lookup",
        "sku_cost_book",
        ["shop_id", "sku", "currency", "effective_from"],
        schema="ops",
    )
    op.execute("""DO $grant$ BEGIN
      IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='cdip_app') THEN
        GRANT SELECT, INSERT ON ops.sku_cost_book TO cdip_app;
      END IF;
    END $grant$""")


def downgrade():
    op.drop_table("sku_cost_book", schema="ops")
