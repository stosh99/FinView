"""Baseline schema: sector_etfs, prices, technical_indicators.

Matches the former backend/schema.sql exactly (including constraint and index
names), so databases created from that file can be stamped at this revision.

Revision ID: 0001
Revises:
Create Date: 2026-11-06
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sector_etfs",
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("symbol", name="sector_etfs_pkey"),
    )

    op.create_table(
        "prices",
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("open", sa.Double()),
        sa.Column("high", sa.Double()),
        sa.Column("low", sa.Double()),
        sa.Column("close", sa.Double(), nullable=False),
        sa.Column("volume", sa.BigInteger()),
        sa.PrimaryKeyConstraint("ticker", "date", name="prices_pkey"),
        sa.ForeignKeyConstraint(
            ["ticker"],
            ["sector_etfs.symbol"],
            name="prices_ticker_fkey",
            ondelete="CASCADE",
        ),
    )
    op.create_index("prices_date_idx", "prices", ["date"])

    op.create_table(
        "technical_indicators",
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("sma50", sa.Double()),
        sa.Column("sma200", sa.Double()),
        sa.Column("ema21", sa.Double()),
        sa.Column("boll_up", sa.Double()),
        sa.Column("boll_dn", sa.Double()),
        sa.PrimaryKeyConstraint("ticker", "date", name="technical_indicators_pkey"),
        sa.ForeignKeyConstraint(
            ["ticker", "date"],
            ["prices.ticker", "prices.date"],
            name="technical_indicators_ticker_date_fkey",
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    op.drop_table("technical_indicators")
    op.drop_index("prices_date_idx", table_name="prices")
    op.drop_table("prices")
    op.drop_table("sector_etfs")
