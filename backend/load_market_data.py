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

# Distributions Yahoo hasn't recorded, taken from the issuer. Without them the
# adjusted close drops on the ex-date as if the payout were a loss. Each entry
# is applied only while Yahoo still lacks a dividend near that ex-date; once
# Yahoo catches up the loader skips it and logs that the entry can be removed.
# (ticker, ex-date, amount per share, source)
MISSING_DISTRIBUTIONS = [
    ("BIL", date(2026, 10, 1), 0.263176, "SSGA historical distributions xlsx"),
    ("BIL", date(2026, 11, 2), 0.308493, "SSGA historical distributions xlsx"),
]
# How far apart Yahoo's date and the issuer's ex-date may be and still count
# as the same distribution.
DISTRIBUTION_MATCH_DAYS = 3

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
    """Dividend-adjusted daily OHLCV, plus any MISSING_DISTRIBUTIONS applied.

    Downloads unadjusted prices with Yahoo's adjusted close and dividends, then
    adjusts the same way yfinance's auto_adjust does (scale OHLC by
    adj close / close). The raw close and dividend list are needed to apply
    distributions Yahoo is missing.
    """
    frame = yf.download(
        ticker,
        start=start.isoformat(),
        end=(date.today() + timedelta(days=1)).isoformat(),
        auto_adjust=False,
        progress=False,
        actions=True,
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
            "Adj Close": "adj_close",
            "Volume": "volume",
            "Dividends": "dividends",
        }
    ).reset_index()
    date_column = "Date" if "Date" in frame.columns else "Datetime"
    frame = frame.rename(columns={date_column: "date"})
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame["ticker"] = ticker
    frame["volume"] = frame["volume"].fillna(0).astype("int64")

    frame["raw_close"] = frame["close"]
    ratio = frame["adj_close"] / frame["close"]
    for column in ["open", "high", "low", "close"]:
        frame[column] = frame[column] * ratio
    apply_missing_distributions(ticker, frame)
    return frame[["ticker", "date", "open", "high", "low", "close", "volume"]]


def apply_missing_distributions(ticker: str, frame: pd.DataFrame) -> None:
    """Back-adjust frame (in place) for distributions Yahoo hasn't recorded.

    Same factor Yahoo uses: every row before the ex-date is scaled by
    1 - amount / unadjusted close of the previous trading day.
    """
    yahoo_dates = pd.to_datetime(frame.loc[frame["dividends"] > 0, "date"])
    for dist_ticker, ex_date, amount, source in MISSING_DISTRIBUTIONS:
        if dist_ticker != ticker:
            continue
        gap = (yahoo_dates - pd.Timestamp(ex_date)).abs()
        if (gap <= pd.Timedelta(days=DISTRIBUTION_MATCH_DAYS)).any():
            logger.warning(
                "Yahoo now has %s's %s distribution; remove it from "
                "MISSING_DISTRIBUTIONS",
                ticker,
                ex_date,
            )
            continue
        before = frame["date"] < ex_date
        if not before.any() or not (frame["date"] >= ex_date).any():
            continue  # ex-date outside the downloaded range
        previous_close = frame.loc[before, "raw_close"].iloc[-1]
        factor = 1 - amount / previous_close
        for column in ["open", "high", "low", "close"]:
            frame.loc[before, column] *= factor
        logger.info(
            "Applied missing %s distribution %s of %.6f (%s), factor %.6f",
            ticker,
            ex_date,
            amount,
            source,
            factor,
        )


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
