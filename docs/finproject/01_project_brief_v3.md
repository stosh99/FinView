# FinProject — Consolidated Project Brief v3

**Updated:** 2026-11-06
**Supersedes:** `personal_equity_research_platform_consolidated_brief_v2.md`
(2026-07-22) and folds in `fable_comments.md` (2026-06-09) plus the
October–November 2026 FinView decisions.
**Status:** Building. FinView exists and runs (dev on the 5090, prod DB on the
VPS). Current focus: the ETF rotation strategy.

---

## 1. What this is

A **personal research and decision-support platform** for US equities, ETFs,
options, and Stosh's own portfolios. It informs decisions; it never places
trades.

**FinView is the platform.** Everything built this year that belongs to
investing lands on one site (planned domain: **finviewhq.com**), built as
separate modules behind one FastAPI backend and one UI.

### Two goals (tag work items with which one they serve)

1. **Investing edge** — better allocation, income, and trade decisions.
2. **Learning / portfolio** — Python, agentic programming, Claude Code
   mastery; a body of work usable for contracting.

Both are valid. Blurring them is how the project becomes the hobby instead of
the investing (Fable, June).

### Trading style (corrected in June — design must fit it)

Wide-net, story/catalyst-driven, macro and thematic. Not a concentrated
10–30-ticker watchlist trader. News and theme detection are core, not
accessories. Separately: three-bucket portfolio (income, core, growth), a
rotation strategy for a defined sum of money, and an active covered-call
program.

---

## 2. Modules and status

| # | Module | Purpose | Status (2026-11-06) |
|---|--------|---------|---------------------|
| M1 | Market data | Daily adjusted prices, indicators, rates | **Built.** 20 ETFs full history (yfinance), SMA/EMA/Bollinger, FRED DTB3 |
| M2 | Charts and RRG | Weekly RRG (sectors); candlestick charts for the whole basket, grouped by category; cash shown as the DTB3 yield | **Built** (full-basket charts added 2026-11-06 on branch `feat/basket-etf-charts`; not on `main` until merged) |
| M3 | ETF rotation / allocation | Monthly allocation of a defined sum across the basket | **Priorities 1–3** (D-020). Design in `../ALLOCATION_DESIGN.md` |
| M4 | Backtesting engine (`allockit`) | Test allocation rules honestly | **Priority 2** — next after prod DB |
| M5 | Holdings & income | IBKR (read-only) positions, dividend/interest history and projections, bond ladder | Not started |
| M6 | Trade journal + decision log | Legs are the truth; thesis, plan, outcome; acted/avoided/ignored | Not started (concept: Nov 2025, May–June 2026) |
| M7 | Valuation (`dcfkit`) | Deterministic DCF engine behind the company-review-dcf skill; runs + scorecard in Postgres | Designed Oct 2026, not built |
| M8 | News / story detection | Ingest broadly → entities → story clusters → novelty → themes in brief | Prior POC: `news_three_tier` (VPS) |
| M9 | Daily brief | Pre-market / daily Markdown or email artifact; grows section by section | Not started |
| M10 | Macro regime layer | VIX structure, credit, curve, DXY (FRED) | Partial (DTB3 only) |
| M11 | EDGAR | Filings for positions/watchlist; special situations | Deferred |
| M12 | MCP / conversational access | Tools over the same backend functions | Deferred until core queries are stable |

---

## 3. Current priorities (set 2026-11-06, revised same day — D-020)

Driven by a current need: a rotation strategy for a specific pool of money.

1. **Working database + nightly load.** Bring `finview_prod` current
   (migrations 0002–0003), schedule the loader on the VPS weekdays after the
   close, with logging so failures are visible.
2. **Backtesting methodology** (`allockit`): monthly rebalance, eligibility as
   ETFs come into existence, DTB3 cash before BIL, costs, baselines. Settles
   the allocation rules with evidence (questions listed in §8). Fix the BIL
   missing-distribution gap first (§5).
3. **Signal + current-allocation view.** Per ETF: momentum rank and trend
   status; what the rules chosen in step 2 would hold today. Comes after the
   backtest so the page never shows an untested strategy's picks.
4. **Data vendors** — later. Yahoo daily data, overwritten nightly, is
   accepted for now.

Not now: holdings/income, journal, DCF, news. (Charts for the full basket
were already added on 2026-11-06.)
Real money follows the strategy only after a backtest — or a paper / small
allocation run first.

---

## 4. Architecture as built

- **Prod:** VPS (`stosh99@66.220.29.98`) — PostgreSQL 16 main cluster (5432),
  always-on services, nightly jobs. Prod app not yet deployed as a service.
- **Dev:** the 5090 Ubuntu machine — all development; reaches the shared dev
  DB on the VPS through an SSH-tunnel user service (`127.0.0.1:55435`).
- **Databases:** `finview_prod` / `finview_dev`, one login role each.
  Same topology as MediaHub and the lottery tracker.
- **Stack:** FastAPI, SQLAlchemy 2.0, psycopg 3, Alembic (hand-written
  migrations), Vue 3 + Vite + ECharts, Python 3.12, `.venv` + pip.
- **Engines as packages:** `allockit` (allocation/backtest) and `dcfkit`
  (valuation) — deterministic, CLI-first, no web dependencies; FinView calls
  them. Same code path from terminal and web page.
- **AI as sidecar:** models analyze, critique, and draft; deterministic
  pipelines own canonical data. AI writes only to staging, never canonical
  tables.
- **Tools:** Claude Code is the primary implementer (`CLAUDE.md` in repo);
  another model may review. Design discussions in chat; decisions recorded
  here.
- **The 5090** is free for local-LLM work; GPU inference joins the platform
  only when a module demonstrably needs it.

---

## 5. Data

- **Prices:** yfinance, dividend-adjusted daily OHLCV from each ETF's
  inception. Full history reloaded every run (adjusted history shifts on every
  distribution). Accepted temporarily — see decision log D-019.
- **Rates:** FRED `DTB3` (3-month T-bill, 1954–present).
- **Known Yahoo gap:** BIL (and SGOV) distributions after 2026-09-01 are
  missing from Yahoo, so 2026 cash returns are understated. Fix before the
  backtest trusts 2026 cash.
- **Not usable from Yahoo:** money-market funds (flat $1.00 NAV, dividends
  missing → 0% return). Cash is BIL plus DTB3 (D-022); MMF yields only from fund sites.
- **Later (vendor phase):** point-in-time history, corporate actions,
  delisted securities, historical options archive (ORATS-type), 10-minute
  equity bars, permanent retention rights. EODHD to be re-evaluated (July
  note: retention terms looked poor — recheck).

---

## 6. Principles (retained from v2 and Fable, still binding)

- Decision support only; no automated execution. IBKR access read-only.
- PostgreSQL is the system of record; deterministic pipelines own it.
- Prod changes require Stosh's explicit go-ahead in the current session.
- Avoid false precision: scores are features to be validated, not
  recommendations.
- Backtest honesty: no lookahead, costs and slippage, walk-forward, year-by-
  year tables, parameter-sensitivity checks, baselines.
- **Narrative-engine hazard:** for a story-driven trader, an LLM will supply
  fluent stories daily. Pair every synthesis with disconfirming evidence and
  base rates.
- Start with what gets used; gate each new module on the previous one being
  used. Always-on surface budget ~8–10 items (each costs 1–2 hrs/week forever).
- Know which items are decisions and which are sediment — re-check anchored
  assumptions periodically.

**Known deviation:** v2's provenance rule (raw inputs preserved, append-only
snapshots, reproduce yesterday's report) is not met by the current loader.
Accepted for the rotation work; revisit trigger in D-019.

---

## 7. Reconciliations (v2 brief vs June Fable comments vs reality)

| Topic | v2 (July) | Fable (June) | Resolution (Nov) |
|-------|-----------|--------------|------------------|
| Universe | Initial ~10 tickers | Wide net: S&P 500 minimum | Rotation uses an 18-ETF basket; equity research keeps the wide-net requirement. **Open** for M8. |
| FinBERT | Feature generator | Anchoring artifact — drop as named dependency | **Dropped.** Requirement is story/theme detection; implementation TBD. |
| Dashboard | Start with Markdown/email; dashboard later | OpenBB Workspace as POC frontend | FinView's own Vue dashboard already exists and is kept. OpenBB: optional evaluation only. |
| Backtesting timing | Stage 3, after data foundation | Deferred until provenance discipline exists | **Moved up** for ETF rotation (daily adjusted ETF prices, low point-in-time risk). Single-stock/options backtests still wait for vendor data. |
| Daily brief | Stage 1 | Week 1 — the spine | Still wanted; after rotation priorities 1–3. |
| Journal | Start almost immediately | Week 1, with acted/avoided log | Still wanted; not yet started. Overdue by both plans. |
| Next.js | Superseded as early requirement | — | Superseded by Vue 3 + Vite (as built). |
| uv | Recommended | — | Not adopted; `.venv` + pip in use. Low stakes. |

---

## 8. Open decisions

### ETF rotation (to be answered by backtest)
1. Number of slots (3–6)
2. Momentum lookback: 3, 6, 12 months, or blend
3. Trend filter, if any: golden cross (50/200), price > 10-month / 200-day
   SMA, 12-month return > 0, or none (D-018 — candidates are ideas only)
4. Rebalance frequency: monthly vs quarterly
5. Sector cap (2–3 of N slots) vs free competition
6. Equal vs inverse-volatility weighting
7. Whether UUP earns its place (see D-014)

Robustness standard: a setting that works across a neighborhood of values and
in the 2008-onward sub-period, not one best combination.

### Platform
8. Data vendors (equity history, options archive, corporate actions)
9. Point-in-time fundamentals source
10. When to add raw snapshotting / reproducibility to the loader
11. First daily-brief format (email vs Markdown vs web page)
12. Journal schema and first UI
13. IB connection: library (ib_async vs other), paper vs live, Gateway on VPS
14. Story-detection design for M8
15. Cloud-model budget and escalation thresholds
16. Domain: finviewhq.com (preferred, not yet registered)
17. Python tooling: move from `requirements.txt` + pip to `pyproject.toml`
    (ruff, pytest configured; uv) — Stosh's standard for new projects.
    Natural point: before `allockit/` starts.

---

## 9. Success criteria for the current phase

- `finview_prod` current and loaded nightly; failures visible.
- A page or report shows today's signal and the strategy's holdings.
- A backtest run reproduces from stored parameters and reports CAGR, max
  drawdown, Sharpe, turnover, and a year-by-year table vs SPY, equal weight,
  and published baselines.
- The chosen rules are written into `../ALLOCATION_DESIGN.md` with the
  evidence that chose them.
- No component can place a trade.

---

## 10. Source index (Google Drive: FinProject)

| File | Date | Role |
|------|------|------|
| `equity_research_platform.md` | 2026-05-07 | Original architecture |
| `equity_research_project_plan.md` | 2026-05-07 | Original 64-week plan |
| `01_chatgpt_proposal.md` | 2026-05-20 | Lab/notebook proposal |
| `02_claude_critique.md`, `03_claude_critique_of_platform_docs.md` | 2026-05-20 | Claude critiques |
| `04_chatgpt_critique.md`, `05_gemini_critique.md` | 2026-05-20 | Other model critiques |
| `06_synthesis.md`, `07_codex_meta_commentary_and_next_steps.md` | 2026-05-20 | Synthesis and next steps |
| `FinProjectColabMD.txt` | 2026-05-20 | Multi-model lab file structure |
| `databroker_convo_claude_05202026.md` | 2026-05-20 | Data-vendor discussion |
| `fable_comments.md` | 2026-06-09 | Corrections: trading style, FinBERT, priorities |
| `personal_equity_research_platform_consolidated_brief_v2.md` | 2026-07-22 | v2 brief (superseded by this) |
| `equity_research_platform_anti_resurrection_log.md` | 2026-07-22 | v2 log (superseded by `03_…`) |

Related chats: "MCP servers for Interactive Brokers and Schwab" (Nov 2025,
journal concept); "DCF methodology comparison" (Oct 2026, dcfkit, rotation
basket); FinView session 2026-11-06 (topology, migrations, basket, DTB3).
