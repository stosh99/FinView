# FinView

FinView is a local sector-analysis dashboard with a weekly Relative Rotation
Graph and one-year candlestick charts for SPY and the eleven Select Sector
SPDR ETFs.

## Databases

Both databases live on the VPS's main PostgreSQL cluster (port 5432), each
owned by its own login role:

| Database       | Role           | Used by                                   |
|----------------|----------------|-------------------------------------------|
| `finview_prod` | `finview_prod` | the VPS deployment                        |
| `finview_dev`  | `finview_dev`  | local development, through an SSH tunnel  |

The dev machine reaches `finview_dev` through the `finview-dev-db-tunnel`
systemd user service, which forwards `127.0.0.1:55435` to the VPS's
`127.0.0.1:5432`:

```bash
systemctl --user status finview-dev-db-tunnel
```

The app, the loader and Alembic all read `DATABASE_URL` from `.env` and refuse
to start without it. Use the psycopg 3 driver: `postgresql+psycopg://...`.

## Schema migrations (Alembic)

Schema changes are hand-written Alembic migrations in `alembic/versions/`
(there are no ORM models, so no autogenerate). Apply them with:

```bash
./scripts/bootstrap_database.sh      # = alembic upgrade head
```

Create a new migration with `alembic revision -m "describe change"`, test it
on `finview_dev`, then run the same command on the VPS against `finview_prod`.

## Local setup

Requirements: Python 3.12, Node.js and npm, and the dev-database tunnel above.

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env              # then fill in the finview_dev password
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
