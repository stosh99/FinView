import numpy as np
import pandas as pd
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from backend.db import make_engine

engine = make_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI()


def load_daily_closes():
    """Daily closes for every tracked ETF, as a date x ticker frame."""
    # noinspection SqlDialectInspection
    query = """
    SELECT p.date, p.ticker, p.close
    FROM prices p
    INNER JOIN sector_etfs s ON s.symbol = p.ticker
    WHERE s.category IN ('benchmark', 'sector')
      AND p.date > CURRENT_DATE - INTERVAL '3 years'
      AND p.close IS NOT NULL
    """
    with SessionLocal() as db:
        df = pd.read_sql(query, db.bind)

    if df.empty:
        print("No price rows loaded.")
        return None

    df["date"] = pd.to_datetime(df["date"])
    pivot_df = df.pivot_table(
        index="date", columns="ticker", values="close", aggfunc="last"
    )
    pivot_df = pivot_df.sort_index().ffill()
    print(f"Loaded {len(pivot_df)} daily rows for {len(pivot_df.columns)} tickers.")
    return pivot_df


def build_tails(rs_ratio, rs_momentum, tail_length, tail_interval=1):
    """Turn aligned RS-Ratio / RS-Momentum frames into per-ticker tails.

    tail_interval thins the series before the tail is taken, so a daily series
    can be shown with weekly spacing while still ending on the newest point.
    """
    rs_ratio = rs_ratio.replace([np.inf, -np.inf], np.nan)
    rs_momentum = rs_momentum.replace([np.inf, -np.inf], np.nan)

    rrg_data = []
    for ticker in rs_ratio.columns:
        ticker_df = pd.DataFrame(
            {
                "rs_ratio": rs_ratio[ticker],
                "rs_momentum": rs_momentum[ticker],
            }
        ).dropna()

        if tail_interval > 1:
            # Thin from the newest end so the last point is always the latest.
            ticker_df = ticker_df.iloc[::-1].iloc[::tail_interval].iloc[::-1]

        if len(ticker_df) < tail_length:
            continue

        tail_df = ticker_df.tail(tail_length).reset_index()
        tail = [
            {
                "date": row["date"].strftime("%Y-%m-%d"),
                "rs_ratio": round(float(row["rs_ratio"]), 4),
                "rs_momentum": round(float(row["rs_momentum"]), 4),
            }
            for _, row in tail_df.iterrows()
        ]

        rrg_data.append(
            {
                "ticker": ticker,
                "latest": tail[-1],
                "tail": tail,
            }
        )

    print(f"Returning {len(rrg_data)} RRG tails.")
    return rrg_data


def calculate_rrg_data():
    benchmark = "SPY"

    # JdK-style RRG. The published RS-Ratio / RS-Momentum formulas are
    # proprietary; this is the z-score construction commonly used to
    # reproduce them:
    #   RS-Ratio    = 100 + z-score(100 * sector / benchmark), smoothed
    #   RS-Momentum = 100 + z-score(rate of change of RS-Ratio), smoothed
    # Momentum must come from the *change* in RS-Ratio. Deriving it from the
    # level of RS-Ratio makes both axes carry the same signal and collapses
    # every tail onto the diagonal.
    zscore_window = 52  # weeks of history each z-score is measured against
    ratio_smoothing = 10  # EMA span applied to RS-Ratio
    momentum_lookback = 4  # weeks spanned by the RS-Ratio rate of change
    momentum_smoothing = 3  # EMA span applied to RS-Momentum
    tail_length = 12

    pivot_df = load_daily_closes()
    if pivot_df is None or benchmark not in pivot_df.columns:
        return []

    # RRGs are usually evaluated on weekly data. Use the last available close
    # in each week so every point in the tail represents one week.
    weekly_prices = pivot_df.resample("W-FRI").last().ffill()
    print(f"Weekly price table created with {len(weekly_prices)} rows.")

    benchmark_prices = weekly_prices[benchmark].replace(0, np.nan)
    sector_prices = weekly_prices.drop(columns=[benchmark])

    def normalize(frame):
        """Centre a frame on 100, in units of its own rolling std deviation."""
        rolling = frame.rolling(window=zscore_window)
        return 100 + (frame - rolling.mean()).div(rolling.std())

    relative_strength = 100 * sector_prices.div(benchmark_prices, axis=0)

    rs_ratio = (
        normalize(relative_strength).ewm(span=ratio_smoothing, adjust=False).mean()
    )

    ratio_roc = 100 * rs_ratio.div(rs_ratio.shift(momentum_lookback)) - 100
    rs_momentum = normalize(ratio_roc).ewm(span=momentum_smoothing, adjust=False).mean()

    return build_tails(rs_ratio, rs_momentum, tail_length)


def calculate_openbb_rrg_data():
    """OpenBB's RRG construction, kept alongside the JdK-style one.

    Mirrors openbb_technical/relative_rotation.py:
        RS-Ratio    = (sector / benchmark) * 100, z-scored
        RS-Momentum = ln(1 + r_long) - ln(1 + r_short) of that ratio, z-scored
    Daily data, no smoothing, quadrants centred on 0 rather than 100.

    The z-score is deliberately full-sample because that is what OpenBB does,
    which means a historical point is normalised using data recorded after it.
    Fine for drawing today's picture; not safe to backtest on.
    """
    benchmark = "SPY"
    long_period = 252  # trading days in a year
    short_period = 21  # trading days in a month
    tail_length = 12
    tail_interval = 5  # trading days between tail points, i.e. weekly spacing

    pivot_df = load_daily_closes()
    if pivot_df is None or benchmark not in pivot_df.columns:
        return []

    benchmark_prices = pivot_df[benchmark].replace(0, np.nan)
    sector_prices = pivot_df.drop(columns=[benchmark])

    ratio = 100 * sector_prices.div(benchmark_prices, axis=0)
    momentum = np.log1p(ratio.pct_change(long_period)) - np.log1p(
        ratio.pct_change(short_period)
    )

    def zscore(frame):
        """Full-sample standardisation, matching OpenBB's implementation."""
        return (frame - frame.mean()) / frame.std()

    return build_tails(
        zscore(ratio), zscore(momentum), tail_length, tail_interval=tail_interval
    )


@app.get("/api/rrg-data")
def get_rrg_data():
    return calculate_rrg_data()


@app.get("/api/rrg-openbb-data")
def get_openbb_rrg_data():
    return calculate_openbb_rrg_data()


# Display order for the charts page; matches the basket table in
# docs/ALLOCATION_DESIGN.md. Every category in the sector_etfs check
# constraint must appear here or its ETFs sort last.
CHART_CATEGORY_ORDER = [
    "benchmark",
    "sector",
    "small_cap",
    "international",
    "real_asset",
    "currency",
    "cash",
]

# FRED series charted for cash ETFs: 3-month T-bill rate, percent.
CASH_RATE_SERIES = "DTB3"


@app.get("/api/sector-chart-data")
def get_sector_chart_data():
    """
    Get 1 year of OHLC data with technical indicators for every tracked ETF.
    Returns a list ordered by category (CHART_CATEGORY_ORDER), then symbol, so
    the order survives JSON. Each entry carries its category for grouping.
    """
    query = """
    SELECT
        p.ticker,
        s.name,
        s.category,
        p.date,
        p.open,
        p.high,
        p.low,
        p.close,
        p.volume,
        t.sma50,
        t.sma200,
        t.ema21,
        t.boll_up,
        t.boll_dn
    FROM prices p
    INNER JOIN sector_etfs s ON p.ticker = s.symbol
    LEFT JOIN technical_indicators t ON p.ticker = t.ticker AND p.date = t.date
    WHERE p.date >= CURRENT_DATE - INTERVAL '1 year'
    ORDER BY p.ticker, p.date
    """

    with SessionLocal() as db:
        df = pd.read_sql(query, db.bind)

    def sort_key(group):
        ticker, category = group
        rank = (
            CHART_CATEGORY_ORDER.index(category)
            if category in CHART_CATEGORY_ORDER
            else len(CHART_CATEGORY_ORDER)
        )
        return rank, ticker

    groups = sorted(df.groupby("ticker")["category"].first().items(), key=sort_key)

    result = []
    for ticker, category in groups:
        ticker_df = df[df["ticker"] == ticker].copy()
        ticker_df["date"] = ticker_df["date"].astype(str)

        # Forward fill technical indicators
        indicator_cols = ["sma50", "sma200", "ema21", "boll_up", "boll_dn"]
        ticker_df[indicator_cols] = ticker_df[indicator_cols].ffill()

        # Replace all NaN with None (converts to null in JSON)
        ticker_df = ticker_df.replace({np.nan: None})

        result.append(
            {
                "ticker": ticker,
                "name": ticker_df["name"].iloc[0] or "",
                "category": category,
                "dates": ticker_df["date"].tolist(),
                "ohlc": ticker_df[["open", "high", "low", "close"]].values.tolist(),
                "volume": ticker_df["volume"].tolist(),
                "sma50": ticker_df["sma50"].tolist(),
                "sma200": ticker_df["sma200"].tolist(),
                "ema21": ticker_df["ema21"].tolist(),
                "boll_up": ticker_df["boll_up"].tolist(),
                "boll_dn": ticker_df["boll_dn"].tolist(),
            }
        )

    # Cash is charted as a yield, not a price: a T-bill fund's price just
    # creeps up. DTB3 keeps its own dates because FRED lags prices by a day
    # or two; forward-filling it onto price dates would fake the latest values.
    rate_query = """
    SELECT date, value FROM rates
    WHERE series_id = :series_id
      AND date >= CURRENT_DATE - INTERVAL '1 year'
    ORDER BY date
    """
    with SessionLocal() as db:
        rate_df = pd.read_sql(
            text(rate_query), db.bind, params={"series_id": CASH_RATE_SERIES}
        )
    rate = {
        "series_id": CASH_RATE_SERIES,
        "dates": rate_df["date"].astype(str).tolist(),
        "values": rate_df["value"].tolist(),
    }
    for entry in result:
        if entry["category"] == "cash":
            entry["rate"] = rate

    return result


if __name__ == "__main__":
    import subprocess
    import sys
    import time
    import webbrowser
    from pathlib import Path

    # Get the frontend directory path
    frontend_dir = Path(__file__).parent.parent / "frontend"

    print("🚀 Starting FinView application...")
    print("=" * 50)

    # Start the frontend in a subprocess
    try:
        print(f"📦 Starting frontend (Vue/Vite) from {frontend_dir}...")
        frontend_process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        print("✓ Frontend process started")
    except Exception as e:
        print(f"❌ Failed to start frontend: {e}")
        sys.exit(1)

    # Give frontend a moment to start
    time.sleep(2)

    # Start the backend (this process)
    print("🔧 Starting backend (FastAPI)...")
    print("=" * 50)
    print("\n📊 Backend running at: http://localhost:8010")
    print("🌐 Frontend running at: http://localhost:5173")
    print("\nPress Ctrl+C to stop both servers\n")
    print("=" * 50)

    # Open browser to frontend after a short delay
    time.sleep(1)
    try:
        webbrowser.open("http://localhost:5173")
    except:
        pass  # Browser opening is optional

    try:
        import uvicorn

        uvicorn.run(app, host="0.0.0.0", port=8010)
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down servers...")
        frontend_process.terminate()
        frontend_process.wait()
        print("✓ Both servers stopped")
    except Exception as e:
        print(f"\n❌ Backend error: {e}")
        frontend_process.terminate()
        frontend_process.wait()
        sys.exit(1)
