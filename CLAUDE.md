# FinView — project guide

Sector-ETF dashboard (weekly RRG, candlestick charts) growing into an ETF
allocation/backtesting system and, later, the home of the DCF engine.
Design decisions for the allocation work live in `docs/ALLOCATION_DESIGN.md`
— read it before touching anything backtest-related.

## Stack

- Backend: FastAPI + SQLAlchemy 2.0 + **psycopg 3** + Alembic, Python 3.12
- Frontend: Vue 3 + Vite + ECharts (`frontend/`)
- Data: yfinance (dividend-adjusted daily prices), FRED CSV (rates)
- PostgreSQL 16 on the VPS

## Machines and environments

- **Dev = the 5090 machine** (`stoshai`, `~/PyCharmProjects/FinView`). All
  development happens here.
- **Prod = the VPS** (`stosh99@66.220.29.98`, `~/projects/FinView`). Not yet
  deployed as a service (no systemd unit / nginx site).
- Both databases live on the VPS's main cluster (port 5432), one role each:

| Database       | Role           | Reached from                                   |
|----------------|----------------|------------------------------------------------|
| `finview_dev`  | `finview_dev`  | 5090 machine via SSH tunnel `127.0.0.1:55435`  |
| `finview_prod` | `finview_prod` | VPS only, `127.0.0.1:5432`                     |

- The tunnel is the systemd **user** service `finview-dev-db-tunnel`. From a
  non-login shell, set `XDG_RUNTIME_DIR=/run/user/$(id -u)` before
  `systemctl --user ...`.
- `DATABASE_URL` comes from `.env` (gitignored) and is **required** —
  `backend/db.py` refuses to start without it and rejects non-psycopg-3 URLs.
  Format: `postgresql+psycopg://user:pass@host:port/db`.

## Commands (from the repo root on the 5090)

```bash
# backend API (port 8010) and frontend (port 5173, proxies /api to 8010)
.venv/bin/uvicorn backend.main:app --reload --port 8010
npm --prefix frontend run dev

# refresh all market data: every ETF's full history + FRED rates (~1 min)
.venv/bin/python -m backend.load_market_data

# migrations
.venv/bin/alembic upgrade head          # or ./scripts/bootstrap_database.sh
.venv/bin/alembic revision -m "desc"    # hand-written; no ORM models, no autogenerate
.venv/bin/alembic current
```

## Data model

- `sector_etfs(symbol, name, category)` — every tracked ETF (name is
  historical; it holds the whole basket). `category` is one of
  `benchmark` (SPY), `sector` (11 SPDRs), `small_cap`, `international`,
  `real_asset`, `currency`, `cash` (BIL — the parking slot, not a competitor).
  Enforced by a check constraint.
- `prices(ticker, date, open, high, low, close, volume)` — adjusted daily OHLCV
  from each ETF's inception.
- `technical_indicators(ticker, date, sma50, sma200, ema21, boll_up, boll_dn)`.
- `rates(series_id, date, value)` — FRED series; `DTB3` (3-month T-bill, %).
- The ETF list lives in `ETFS` in `backend/load_market_data.py`. To add an ETF:
  add it there with a valid category, then run the loader.
- The RRG and sector-chart endpoints filter to `category IN ('benchmark',
  'sector')` so new basket ETFs don't appear there unless deliberately added.

## Rules

- **Prod requires an explicit go-ahead.** Never run migrations, loads, or any
  write against `finview_prod`, or change files on the VPS, without Stosh
  saying so in the current session. Rehearse every migration on `finview_dev`
  first.
- Schema changes only through Alembic migrations — never ad-hoc DDL.
- **Never `git add -A`.** Stage files by name; `.env` and backups must never be
  committed.
- `.env` files and `~/.config/finview/db-passwords` hold secrets — don't print
  them; mask passwords in any output.
- The loader reloads full history on purpose: adjusted prices shift whenever a
  fund pays a distribution.
- **npm gotcha:** this machine has `NODE_ENV=production` set globally, so a
  plain `npm install` skips devDependencies (Vite). Use
  `npm install --include=dev`, and don't commit incidental
  `package-lock.json` churn.
- ECharts candlestick data order is `[open, close, low, high]`; the API sends
  `[open, high, low, close]` and `SectorCharts.vue` reorders it. Keep that in
  mind for any new candlestick chart.
- Verify, don't assume: after a change, hit the endpoint or look at the page;
  after a load, query the table.

## Current status / next step

- Done (Nov 2026): psycopg 3 + Alembic (migrations 0001–0003), dev/prod DB
  split, allocation basket loaded into `finview_dev` with full history, FRED
  DTB3 loaded.
- **Prod is behind:** VPS code is at an older commit and `finview_prod` is on
  migration 0001. Updating it (pull, `alembic upgrade head`, full load) needs
  Stosh's go-ahead.
- **Next:** add charts for the new basket ETFs (IWM, VGK, EWJ, VWO, GLD, PDBC,
  UUP, BIL) to the charts page — decide whether they share the sector page or
  get their own section/filter, and widen the endpoint's category filter
  accordingly.
