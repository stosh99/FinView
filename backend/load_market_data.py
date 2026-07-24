"""Load sector ETF prices and technical indicators into FinView's database."""

import os
from datetime import date, timedelta

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


SECTOR_ETFS = {
    "SPY": "SPDR S&P 500 ETF Trust",
    "XLB": "Materials Select Sector SPDR Fund",
    "XLC": "Communication Services Select Sector SPDR Fund",
    "XLE": "Energy Select Sector SPDR Fund",
    "XLF": "Financial Select Sector SPDR Fund",
    "XLI": "Industrial Select Sector SPDR Fund",
    "XLK": "Technology Select Sector SPDR Fund",
    "XLP": "Consumer Staples Select Sector SPDR Fund",
    "XLRE": "Real Estate Select Sector SPDR Fund",
    "XLU": "Utilities Select Sector SPDR Fund",
    "XLV": "Health Care Select Sector SPDR Fund",
    "XLY": "Consumer Discretionary Select Sector SPDR Fund",
}


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


def main() -> None:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL", "postgresql+psycopg2:///finview")
    engine = create_engine(database_url, pool_pre_ping=True)
    start = date.today() - timedelta(days=3 * 366)

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO sector_etfs (symbol, name)
                VALUES (:symbol, :name)
                ON CONFLICT (symbol) DO UPDATE SET name = EXCLUDED.name
                """
            ),
            [{"symbol": symbol, "name": name} for symbol, name in SECTOR_ETFS.items()],
        )

    for ticker in SECTOR_ETFS:
        print(f"Downloading {ticker}...")
        prices = download_prices(ticker, start)
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
        print(f"Loaded {len(prices)} rows for {ticker}.")

    print("FinView market data is up to date.")


if __name__ == "__main__":
    main()
