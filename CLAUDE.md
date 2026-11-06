# FinView — project guide

FinView is the implementation of **FinProject**: Stosh's personal investment
research and decision-support platform (holdings, income, trade journal,
valuation, ETF rotation, news, daily brief — on one site, built as modules).

## Read first

- `docs/finproject/00_START_HERE.md` → project brief, decision log,
  anti-resurrection log (what was rejected and why; don't re-propose without
  the reversal rule).
- `docs/ALLOCATION_DESIGN.md` — ETF rotation design; read before touching
  anything signal- or backtest-related.
- `docs/DECISIONS.md` — one-line code/UI decisions, tagged by area
  (`[web]`, `[data]`...). Grep for your area before changing code.

Where to record a decision: project, strategy or data-source choices →
`docs/finproject/02_decision_log.md` (D-numbers); code and UI choices made
while building → `docs/DECISIONS.md`. Never both — link instead.

## Stack

- Backend: FastAPI + SQLAlchemy 2.0 + **psycopg 3** + Alembic, Python 3.12
- Frontend: Vue 3 + Vite + ECharts (`frontend/`)
- Data: yfinance (dividend-adjusted daily prices), FRED CSV (rates)

## Machines and environments

- **Dev = the 5090 machine** (`stoshai`, `~/PyCharmProjects/FinView`).
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

Prod nightly load (VPS): systemd `finview-market-data.timer` → `.service`,
weekdays 18:30 ET; unit files in `deploy/systemd/` (copy to
`/etc/systemd/system/`, then `daemon-reload`). Check with
`journalctl -u finview-market-data -n 50` and `systemctl list-timers finview*`.
The loader exits 1 if any ticker or series failed (others still load).

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
- The RRG endpoints filter to `category IN ('benchmark', 'sector')` so new
  basket ETFs don't appear there unless deliberately added. The chart
  endpoint (`/api/sector-chart-data`) returns every ETF, ordered by
  `CHART_CATEGORY_ORDER` in `backend/main.py` — add any new category there.

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

## Status and priorities

- Priorities: D-020 in the decision log; module status: brief §2–3.
- **Prod is behind dev** (`finview_prod` on migration 0001, older VPS code).
  Don't assume prod matches dev.
