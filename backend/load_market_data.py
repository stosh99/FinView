"""Load ETF prices and technical indicators into FinView's database.

Downloads each ETF's full price history every run. Prices are dividend-
adjusted (auto_adjust), and adjusted history shifts every time a fund pays a
distribution, so a full reload is what keeps the stored series consistent.
"""

import logging
import sys
from datetime import date, timedelta

import pandas as pd
import yfinance as yf
from sqlalchemy import text

from backend.db import make_engine

logger = logging.getLogger(__name__)

# Earliest date requested; each ETF's history starts at its own inception.
HISTORY_START = date(1993, 1, 1)

# symbol -> (name, category). Categories are documented in
# alembic/versions/0002_etf_category.py.
ETFS = {
    # Benchmark for the RRG; not an allocation competitor.
    "SPY": ("SPDR S&P 500 ETF Trust", "benchmark"),
    # US sectors
    "XLB": ("Materials Select Sector SPDR Fund", "sector"),
    "XLC": ("Communication Services Select Sector SPDR Fund", "sector"),
    "XLE": ("Energy Select Sector SPDR Fund", "sector"),
    "XLF": ("Financial Select Sector SPDR Fund", "sector"),
    "XLI": ("Industrial Select Sector SPDR Fund", "sector"),
    "XLK": ("Technology Select Sector SPDR Fund", "sector"),
    "XLP": ("Consumer Staples Select Sector SPDR Fund", "sector"),
    "XLRE": ("Real Estate Select Sector SPDR Fund", "sector"),
    "XLU": ("Utilities Select Sector SPDR Fund", "sector"),
    "XLV": ("Health Care Select Sector SPDR Fund", "sector"),
    "XLY": ("Consumer Discretionary Select Sector SPDR Fund", "sector"),
    # US small cap
    "IWM": ("iShares Russell 2000 ETF", "small_cap"),
    # International
    "VGK": ("Vanguard FTSE Europe ETF", "international"),
    "EWJ": ("iShares MSCI Japan ETF", "international"),
    "VWO": ("Vanguard FTSE Emerging Markets ETF", "international"),
    # Real assets
    "GLD": ("SPDR Gold Shares", "real_asset"),
    "PDBC": (
        "Invesco Optimum Yield Diversified Commodity Strategy No K-1 ETF",
        "real_asset",
    ),
    # Currency
    "UUP": ("Invesco DB US Dollar Index Bullish Fund", "currency"),
    # Cash: where unfilled allocation slots are parked; not a competitor.
    "BIL": ("SPDR Bloomberg 1-3 Month T-Bill ETF", "cash"),
}

# FRED series stored in the rates table (public CSV endpoint, no API key).
# DTB3 = 3-month T-bill rate, percent; the cash return before BIL exists.
FRED_SERIES = ["DTB3"]
FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"


def download_fred_series(series_id: str) -> list[dict]:
    """Full history of one FRED series; FRED's blank holiday rows are dropped."""
    frame = pd.read_csv(
        FRED_CSV_URL.format(series_id=series_id),
        na_values=["."],
        parse_dates=["observation_date"],
    )
    frame = frame.rename(columns={"observation_date": "date", series_id: "value"})
    frame = frame.dropna(subset=["value"])
    if frame.empty:
        raise RuntimeError(f"No data returned from FRED for {series_id}")
    frame["date"] = frame["date"].dt.date
    frame["series_id"] = series_id
    return frame[["series_id", "date", "value"]].to_dict("records")


def load_rates(engine) -> list[str]:
    """Load every FRED series; returns the series that failed."""
    statement = text(
        """
        INSERT INTO rates (series_id, date, value)
        VALUES (:series_id, :date, :value)
        ON CONFLICT (series_id, date) DO UPDATE SET value = EXCLUDED.value
        """
    )
    failed = []
    for series_id in FRED_SERIES:
        logger.info("Downloading FRED %s", series_id)
        try:
            rows = download_fred_series(series_id)
            with engine.begin() as connection:
                connection.execute(statement, rows)
        except Exception:
            logger.exception("FRED %s failed; keeping the stored series", series_id)
            failed.append(series_id)
            continue
        logger.info(
            "Loaded %d rows for %s through %s", len(rows), series_id, rows[-1]["date"]
        )
    return failed


def calculate_indicators(prices: pd.DataFrame) -> pd.DataFrame:
    close = prices["close"]
    rolling_20 = close.rolling(20)
    result = prices[["ticker", "date"]].copy()
    result["sma50"] = close.rolling(50).mean()
    result["sma200"] = close.rolling(200).mean()
    result["ema21"] = close.ewm(span=21, adjust=False).mean()
    result["boll_up"] = rolling_20.mean() + 2 * rolling_20.std()
    result["boll_dn"] = rolling_20.mean() - 2 * rolling_20.std()
    return result


def download_prices(ticker: str, start: date) -> pd.DataFrame:
    frame = yf.download(
        ticker,
        start=start.isoformat(),
        end=(date.today() + timedelta(days=1)).isoformat(),
        auto_adjust=True,
        progress=False,
        actions=False,
    )
    if frame.empty:
        raise RuntimeError(f"No market data returned for {ticker}")

    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)

    frame = frame.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    ).reset_index()
    date_column = "Date" if "Date" in frame.columns else "Datetime"
    frame = frame.rename(columns={date_column: "date"})
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame["ticker"] = ticker
    frame["volume"] = frame["volume"].fillna(0).astype("int64")
    return frame[["ticker", "date", "open", "high", "low", "close", "volume"]]


def upsert_rows(connection, table: str, columns: list[str], rows: list[dict]) -> None:
    if not rows:
        return
    assignments = ", ".join(
        f"{column} = EXCLUDED.{column}"
        for column in columns
        if column not in {"ticker", "date"}
    )
    statement = text(
        f"""
        INSERT INTO {table} ({", ".join(columns)})
        VALUES ({", ".join(f":{column}" for column in columns)})
        ON CONFLICT (ticker, date) DO UPDATE SET {assignments}
        """
    )
    connection.execute(statement, rows)


def main() -> int:
    """Load everything; returns the process exit code (1 if anything failed).

    One ticker failing doesn't stop the run: each ticker is its own
    transaction, so a failure leaves that ticker's stored rows untouched and
    the rest still load. The non-zero exit makes systemd mark the run failed.
    """
    engine = make_engine()

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO sector_etfs (symbol, name, category)
                VALUES (:symbol, :name, :category)
                ON CONFLICT (symbol) DO UPDATE
                SET name = EXCLUDED.name, category = EXCLUDED.category
                """
            ),
            [
                {"symbol": symbol, "name": name, "category": category}
                for symbol, (name, category) in ETFS.items()
            ],
        )

    failed = []
    for ticker in ETFS:
        logger.info("Downloading %s", ticker)
        try:
            load_ticker(engine, ticker)
        except Exception:
            logger.exception("%s failed; keeping its stored rows", ticker)
            failed.append(ticker)

    failed += load_rates(engine)

    if failed:
        logger.error("Load finished with failures: %s", ", ".join(failed))
        return 1
    logger.info("FinView market data is up to date.")
    return 0


def load_ticker(engine, ticker: str) -> None:
    prices = download_prices(ticker, HISTORY_START)
    indicators = calculate_indicators(prices)
    with engine.begin() as connection:
        upsert_rows(
            connection,
            "prices",
            ["ticker", "date", "open", "high", "low", "close", "volume"],
            prices.to_dict("records"),
        )
        upsert_rows(
            connection,
            "technical_indicators",
            ["ticker", "date", "sma50", "sma200", "ema21", "boll_up", "boll_dn"],
            indicators.where(pd.notna(indicators), None).to_dict("records"),
        )
    logger.info(
        "Loaded %d rows for %s through %s", len(prices), ticker, prices["date"].max()
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    sys.exit(main())
