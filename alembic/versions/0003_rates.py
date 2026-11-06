"""Add rates: daily interest-rate series from FRED.

First series: DTB3, the 3-month Treasury bill secondary-market rate
(percent, discount basis). It is the backtest's cash return before BIL
(SPDR 1-3 Month T-Bill ETF) starts trading in May 2007.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-06
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rates",
        sa.Column("series_id", sa.Text(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("value", sa.Double(), nullable=False),
        sa.PrimaryKeyConstraint("series_id", "date", name="rates_pkey"),
    )


def downgrade() -> None:
    op.drop_table("rates")
