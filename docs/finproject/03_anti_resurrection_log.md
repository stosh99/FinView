# FinProject — Anti-Resurrection Log

**Updated:** 2026-11-06 (v2 dated 2026-07-22, plus June and November changes)

Purpose: remember what was considered and why it was set aside, so attractive
ideas aren't re-debated from scratch.

Status labels: **Rejected** (don't return without a material change) ·
**Superseded** (replaced) · **Deferred** (valuable after a stated trigger) ·
**Experiment backlog** (hypothesis, not a requirement) · **Not selected**
(investigated, no commitment).

## Reversal rule

To reopen anything below, record in `02_decision_log.md`: (1) what materially
changed, (2) the new evidence, (3) which former objection no longer applies,
(4) the cost of reversing, (5) the measurable test of success.
Example: D-014 (currency ETF).

---

## 1. Rejected

| Approach | Why | Revisit only if |
|---|---|---|
| Platform places trades automatically | Operational, model, security, and behavioral risk; blurs analysis and action | Mission changes and a separate execution/risk architecture is designed |
| Agent (Hermes or other) as canonical workflow / system of record | Drift, nondeterminism, weak audit, uncertain cost | Agents become as reproducible and auditable as the deterministic pipeline |
| Agent writes canonical tables without staging/validation | Hallucinated or overwritten data, silent reinterpretation | Never for unvalidated output |
| FinBERT as primary analyst — and since June, as a named dependency | Sentiment/triage only; per-headline sentiment isn't how Stosh trades | Not expected |
| A single sentiment or 1–10 impact score as a trade recommendation | False precision; hides horizon, uncertainty, context | Embedded in an evidence-linked, validated decision framework |
| OpenBB owning canonical history, provenance, journal, or backtest lineage | The durable asset is Stosh's own data model and record | OpenBB offers stronger self-hosted guarantees without loss of ownership |
| Forking OpenBB upstream as the production build | Needless coupling before requirements are proven | A required capability can't be built otherwise |
| IBKR as the sole source of a 10-year options history | Can't reconstruct expired contracts / point-in-time chains | IBKR changes its historical data retention |
| Local model fully replacing cloud reasoning | Hard synthesis still needs stronger models | Local models match on the project's own benchmark |
| Day-trading / intraday execution focus | Not the style: swing/position, options, nightly batch | Trading style changes |
| Inferring corporate actions from price history | Corrupts backtests | Never; requires an explicit event pipeline |
| Choosing a data vendor because it's cheap | Coverage, delisted names, licensing, retention matter more | — |
| **Yahoo prices for money-market funds** (Nov) | Flat $1.00 NAV, dividends missing → shows 0% return | Yahoo starts carrying MMF distributions |
| **Proxy splicing to extend ETF history** (Nov) | Adds judgment calls; the basket grows as ETFs come into existence instead (D-016) | A specific test needs pre-inception history and a defensible proxy |

## 2. Superseded

| Earlier choice | Replacement |
|---|---|
| Follow the 64-week sequence as written | Capability map only; build used vertical slices |
| Morning brief at weeks 41–44 | Early, ugly-but-useful brief (after rotation priorities) |
| Trade journal at weeks 17–22 | Start early, manual — still overdue |
| PyCharm as the required environment | Claude Code primary; PyCharm optional |
| Next.js dashboard | Vue 3 + Vite + ECharts (as built in FinView) |
| "Dashboard only after data and lineage are trustworthy" (v2) / OpenBB Workspace as POC frontend (June) | FinView's own dashboard exists and is kept; OpenBB is an optional evaluation. Still applies in spirit: don't let charts outrun data quality |
| 11 nightly sector agents | One nightly cross-feed theme synthesis + on-demand sector queries (June) |
| "Shrink the universe to 10–30 tickers" | Wide net for research (D-007) |
| psycopg2 + `schema.sql` | psycopg 3 + Alembic (D-011) |
| Separate FinView DB `finview` / `newsdb` on port 5433 | `finview_prod` / `finview_dev` on 5432 (D-010) |
| Named libraries as fixed commitments (ib_insync, pandas-ta, cron, …) | Starting candidates; revalidate at implementation |
| Backtesting deferred until full provenance exists (June) | Moved up for ETF rotation only (D-020); single-stock/options backtests still wait |

## 3. Deferred / conditional

| Capability | Trigger to reconsider |
|---|---|
| Russell 5000 screening tier | S&P 500 research is used regularly and misses justify expansion |
| Full daily S&P 500 options chains | Written retention policy, cost estimate, research need |
| Broad options ingestion in early milestones | Small-universe collector runs reliably |
| GB10 purchase | Benchmarks show the 5090 limits real workloads |
| MCP / mobile conversational layer | Core queries stable and used manually (June moved MCP earlier; still after the core loop) |
| Behavioral / pattern agents | Dozens of comparable journal entries |
| GEX, charm, vanna, dispersion, etc. | A concrete strategy or risk question needs them |
| Voice memos, anomaly polish, wish-list items | Real usage reveals a problem they solve |
| Elaborate local/cloud model routing | Real workload, cost, and quality data |
| Multi-model debate on every item | High-impact ambiguous cases show measurable benefit |
| **Raw snapshotting / reproducible reports in the loader** (Nov) | Vendor selection, single-stock/options backtests, or reproducing a past report (D-019) |
| **Money-market yield history tracking** (Nov) | A cash-management feature needs it; source must be fund sites, not Yahoo |

## 4. Data vendors / sources not selected

| Candidate | Status / reason |
|---|---|
| IBKR alone for historical backtests | Not selected — incomplete for expired options and a clean 10-year archive |
| Robinhood | Not selected — no advantage over IBKR |
| Alpaca | Not selected as primary; may serve a narrow role |
| EODHD (buy once, cancel, keep) | Not selected in July — retention terms looked poorly aligned. **Recheck terms** before relying on this (raised again 2026-11-06) |
| Leaning (not decided) | FirstRate Data (equity bars), ORATS-type archive (options), IBKR (prospective nightly) |

## 5. Experiment backlog (not platform requirements)

| Idea | Note |
|---|---|
| Fibonacci "golden zone" pullbacks | Level-generation/watchlist feature; must be defined and backtested |
| Sunday-night ES/MES premium selling | Needs timestamp-accurate futures/options data and realistic fills |
| Monday-morning SPY vs Sunday futures entry | Empirical comparison, not architecture |
| 10-delta, 7–10 DTE short strangles | Delta/DTE alone don't define risk |
| The wheel | Compare against simple long-equity exposure |
| Nightly 1–10 article-strength score | Kept as triage workflow, not a truth metric |
| Autonomous opportunity-discovery agents | Read-only staged output, evaluated against outcomes first |
| **RRG-quadrant rotation** (Oct) | Test whether it beats plain momentum; RRG is a visualization of momentum, not a strategy |

## 6. Unresolved (not rejected)

Exact equity and options vendors · options retention policy · IB library and
paper vs live · first daily-brief format · journal schema/UI · first EDGAR
filing type · OpenBB's role · local model/serving stack · cloud-model budget ·
story-detection design · rotation parameters (see brief §8).
