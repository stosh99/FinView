# FinView

FinView is a local sector-analysis dashboard with a weekly Relative Rotation
Graph and one-year candlestick charts for SPY and the eleven Select Sector
SPDR ETFs.

## Local setup

Requirements:

- PostgreSQL 16 listening on the standard local port, 5432
- Python 3.12
- Node.js and npm

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
./scripts/bootstrap_database.sh
python -m backend.load_market_data
npm --prefix frontend install
```

Run the two development servers in separate terminals:

```bash
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8010
```

```bash
npm --prefix frontend run dev
```

Open <http://localhost:5173>. FastAPI's interactive API documentation is at
<http://localhost:8010/docs>.

## Refreshing prices

Run the idempotent loader whenever you want to refresh daily market data:

```bash
source .venv/bin/activate
python -m backend.load_market_data
```

The loader downloads three years of adjusted daily OHLCV data and recalculates
SMA50, SMA200, EMA21, and 20-day Bollinger Bands.
