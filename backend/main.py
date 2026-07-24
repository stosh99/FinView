
import os
import pandas as pd
import numpy as np
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2:///finview")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI()

def calculate_rrg_data():
    benchmark = "SPY"
    window = 14
    tail_length = 12

    # noinspection SqlDialectInspection
    query = """
    SELECT p.date, p.ticker, p.close
    FROM prices p
    INNER JOIN sector_etfs s ON s.symbol = p.ticker
    WHERE p.date > CURRENT_DATE - INTERVAL '2 years'
      AND p.close IS NOT NULL
    """
    with SessionLocal() as db:
        df = pd.read_sql(query, db.bind)
        print(f"Initial data loaded with {len(df)} rows.")

    if df.empty:
        return []

    df['date'] = pd.to_datetime(df['date'])

    # Pivot the table to get tickers as columns
    pivot_df = df.pivot_table(index='date', columns='ticker', values='close', aggfunc='last')
    pivot_df = pivot_df.sort_index().ffill()
    print(f"Pivot table created with {len(pivot_df)} daily rows.")

    if benchmark not in pivot_df.columns:
        print(f"{benchmark} data not found in prices.")
        return []

    # RRGs are usually evaluated on weekly data. Use the last available close
    # in each week so every point in the tail represents one week.
    weekly_prices = pivot_df.resample('W-FRI').last().ffill()
    print(f"Weekly price table created with {len(weekly_prices)} rows.")

    benchmark_prices = weekly_prices[benchmark].replace(0, np.nan)
    sector_prices = weekly_prices.drop(columns=[benchmark])

    # Directional approximation of RRG calculations:
    # 1. Relative strength is sector price divided by benchmark price.
    # 2. RS-Ratio is relative strength normalized around its rolling mean.
    # 3. RS-Momentum is RS-Ratio normalized around its rolling mean.
    relative_strength = sector_prices.div(benchmark_prices, axis=0)
    rs_ratio = 100 * relative_strength.div(relative_strength.rolling(window=window).mean())
    rs_momentum = 100 * rs_ratio.div(rs_ratio.rolling(window=window).mean())

    rs_ratio = rs_ratio.replace([np.inf, -np.inf], np.nan)
    rs_momentum = rs_momentum.replace([np.inf, -np.inf], np.nan)

    if rs_ratio.empty or rs_momentum.empty:
        print("No data after RRG calculations.")
        return []

    rrg_data = []
    for ticker in rs_ratio.columns:
        ticker_df = pd.DataFrame({
            'rs_ratio': rs_ratio[ticker],
            'rs_momentum': rs_momentum[ticker],
        }).dropna()

        if len(ticker_df) < tail_length:
            continue

        tail_df = ticker_df.tail(tail_length).reset_index()
        tail = [
            {
                'date': row['date'].strftime('%Y-%m-%d'),
                'rs_ratio': round(float(row['rs_ratio']), 4),
                'rs_momentum': round(float(row['rs_momentum']), 4),
            }
            for _, row in tail_df.iterrows()
        ]
        latest = tail[-1]

        rrg_data.append({
            'ticker': ticker,
            'latest': latest,
            'tail': tail,
        })

    print(f"Returning {len(rrg_data)} RRG tails.")
    return rrg_data

@app.get("/api/rrg-data")
def get_rrg_data():
    return calculate_rrg_data()

@app.get("/api/sector-chart-data")
def get_sector_chart_data():
    """
    Get 1 year of OHLC data with technical indicators for all sector ETFs.
    Returns data for candlestick charts with SMA50, SMA200, EMA21, BolUp, BolDown.
    """
    # First get the ETF names
    names_query = """
    SELECT symbol, name FROM sector_etfs
    """

    with SessionLocal() as db:
        etf_names_df = pd.read_sql(names_query, db.bind)

    etf_names = dict(zip(etf_names_df['symbol'], etf_names_df['name']))

    query = """
    WITH sector_symbols AS (
        SELECT symbol FROM sector_etfs
        ORDER BY CASE WHEN symbol = 'SPY' THEN 0 ELSE 1 END, symbol
    )
    SELECT
        p.ticker,
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
    INNER JOIN sector_symbols s ON p.ticker = s.symbol
    LEFT JOIN technical_indicators t ON p.ticker = t.ticker AND p.date = t.date
    WHERE p.date >= CURRENT_DATE - INTERVAL '1 year'
    ORDER BY p.ticker, p.date
    """

    with SessionLocal() as db:
        df = pd.read_sql(query, db.bind)

    # Convert to dict grouped by ticker
    result = {}
    for ticker in df['ticker'].unique():
        ticker_df = df[df['ticker'] == ticker].copy()
        ticker_df['date'] = ticker_df['date'].astype(str)

        # Forward fill technical indicators
        ticker_df['sma50'] = ticker_df['sma50'].ffill()
        ticker_df['sma200'] = ticker_df['sma200'].ffill()
        ticker_df['ema21'] = ticker_df['ema21'].ffill()
        ticker_df['boll_up'] = ticker_df['boll_up'].ffill()
        ticker_df['boll_dn'] = ticker_df['boll_dn'].ffill()

        # Replace all NaN with None (converts to null in JSON)
        ticker_df = ticker_df.replace({np.nan: None})

        result[ticker] = {
            'name': etf_names.get(ticker, ''),
            'dates': ticker_df['date'].tolist(),
            'ohlc': ticker_df[['open', 'high', 'low', 'close']].values.tolist(),
            'volume': ticker_df['volume'].tolist(),
            'sma50': ticker_df['sma50'].tolist(),
            'sma200': ticker_df['sma200'].tolist(),
            'ema21': ticker_df['ema21'].tolist(),
            'boll_up': ticker_df['boll_up'].tolist(),
            'boll_dn': ticker_df['boll_dn'].tolist(),
        }

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
            text=True
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
