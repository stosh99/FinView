"""Add sector_etfs.category so the table can hold the full allocation basket.

Existing rows become 'sector', except SPY which becomes 'benchmark'.
Categories:
  benchmark      SPY: RRG benchmark, not an allocation competitor
  sector         the 11 Select Sector SPDRs
  small_cap      US small cap (IWM)
  international  Europe, Japan, emerging markets
  real_asset     gold, broad commodities
  currency       US dollar (UUP)
  cash           where unfilled slots are parked (BIL), not a competitor

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-06
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

CATEGORIES = (
    "benchmark",
    "sector",
    "small_cap",
    "international",
    "real_asset",
    "currency",
    "cash",
)


def upgrade() -> None:
    op.add_column(
        "sector_etfs",
        sa.Column("category", sa.Text(), nullable=False, server_default="sector"),
    )
    op.execute("UPDATE sector_etfs SET category = 'benchmark' WHERE symbol = 'SPY'")
    op.alter_column("sector_etfs", "category", server_default=None)
    allowed = ", ".join(f"'{c}'" for c in CATEGORIES)
    op.create_check_constraint(
        "sector_etfs_category_check", "sector_etfs", f"category IN ({allowed})"
    )


def downgrade() -> None:
    op.drop_constraint("sector_etfs_category_check", "sector_etfs", type_="check")
    op.drop_column("sector_etfs", "category")
