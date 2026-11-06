# FinProject — Decision Log

Format: **ID — title** · date · status · confidence. Then decision, why,
alternatives, and revisit trigger where relevant. Status values: Decided,
Proposed (to be tested), Deferred, Reversed, Temporary.

Earlier decisions (May–July) are condensed from the v2 brief and Fable
comments; see those Drive files for full reasoning.

This log holds project, strategy and data-source decisions. Code and UI
choices made while building (one line each, tagged by area) go in
`docs/DECISIONS.md` instead — link, don't copy.

Decisions are working choices for a project built module by module, not
commitments. Change one by adding or revising an entry with the date and
reason; the reversal rule applies only to what the anti-resurrection log
rejected.

---

## Platform foundations

**D-001 — Decision support only; no automated trading** · 2026-05 · Decided · High
The platform researches, journals, and reviews risk. It never places orders.
Broker access (IBKR) is read-only. Revisit only if the mission changes and a
separate execution/risk-control architecture is designed.

**D-002 — PostgreSQL is the system of record** · 2026-05 · Decided · High
All canonical data, runs, and journal records live in Postgres on the VPS.

**D-003 — Deterministic pipelines own canonical data; AI is a sidecar** · 2026-07 · Decided · High
Ingestion, scoring, and state are deterministic and versioned. Models
analyze and critique; they write only to staging/anomaly queues. Alternative
rejected: an autonomous agent (e.g. Hermes) as the pipeline or bookkeeper.

**D-004 — Re-baseline around a used vertical slice** · 2026-05/07 · Decided · High
The original 64-week plan is a capability map, not a schedule. Build what
gets used, gate each module on its predecessor being used.

**D-005 — Options modeled at the leg level** · 2026-05 · Decided · High
"Legs are the truth; strategy is metadata." Applies to the journal and P&L.

**D-006 — FinBERT dropped as a named dependency** · 2026-06-09 · Decided · Medium
It was an anchoring artifact, not a decision. The requirement is story/theme
detection with novelty scoring; implementation TBD (LLM triage, embedding
clustering, etc.).

**D-007 — Wide-net universe for equity research** · 2026-06-09 · Decided · Medium
Trading style is wide-net and catalyst-driven: S&P 500 minimum, Russell
screener tier later. Supersedes v2's "initial ten tickers" for research
modules. (The ETF rotation uses its own fixed basket — D-013.)

## FinView as the platform

**D-008 — FinView is the platform; one site, modular** · 2026-10/11 · Decided · High
Holdings, income, journal, valuation, rotation, news, and briefs converge on
FinView, built as separate modules behind one backend. Planned scope
confirmed 2026-11-06.

**D-009 — Engines are standalone packages** · 2026-10-15 · Decided · High
`dcfkit` (valuation) and `allockit` (allocation/backtest): deterministic,
CLI-first, no web dependencies, called by FinView. DCF inputs as versioned
JSON in the repo; runs and scorecards in Postgres.

**D-010 — Dev/prod topology** · 2026-11-06 · Decided · High
Prod DB `finview_prod` and dev DB `finview_dev` on the VPS main cluster, one
role each. Development on the 5090 through SSH tunnel `127.0.0.1:55435`
(systemd user service `finview-dev-db-tunnel`). Matches MediaHub and the
lottery tracker.

**D-011 — psycopg 3 + Alembic** · 2026-11-06 · Decided · High
Replaced psycopg2 and `schema.sql`. Baseline migration 0001 verified
identical to the prior schema by diff. `DATABASE_URL` required, no default.

**D-012 — Claude Code is the primary implementer** · 2026-11-06 · Decided · High
Development moves to Claude Code on the 5090, guided by `CLAUDE.md` and these
docs. Design discussion continues in chat; decisions land here.

## ETF rotation

**D-013 — Rotation basket** · 2026-11-06 · Decided · Medium
Competitors: 11 sector SPDRs, IWM, VGK, EWJ, VWO, GLD, PDBC, UUP (18).
Cash park: BIL (not a competitor). SPY is the benchmark only. Stored with a
`category` column (migration 0002).

**D-014 — Add a currency ETF (UUP)** · 2026-11-06 · Decided (reversal) · Medium
**Reversal** of the 2026-10-15 recommendation to leave currency ETFs out.
Per the reversal rule:
- *What changed:* fixed income was removed from the basket (D-015), leaving
  only gold and cash as defensive competitors; Stosh chose to include a
  dollar position.
- *Former objection:* overlaps the basket's existing dollar exposure; low
  volatility means it rarely ranks; K-1 and ~0.75% cost. Still partly valid.
- *Cost of reversal:* one ticker, negligible.
- *Measurable test:* in the backtest, does UUP ever earn slots, and does its
  presence reduce drawdown versus the same rules without it?

**D-015 — Exclude fixed income from the rotation** · 2026-11-06 · Decided · High
Stosh's separate income portfolio, including a Treasury/CD ladder, already
holds fixed income. Consequence accepted: inside this system only GLD, UUP,
and cash can win slots in a sell-off.

**D-016 — ETFs join as they come into existence; no proxy splicing** · 2026-11-06 · Decided · High
An ETF becomes eligible once it has enough history for the signal. Report
the full period and 2008-onward separately (pre-2006 is effectively US
sectors plus Japan).

**D-017 — DTB3 as cash before BIL** · 2026-11-06 · Decided · Medium
FRED 3-month T-bill rate accrued daily, with ~0.15%/yr drag (BIL trailed
DTB3 by ~0.17%/yr, 2008–2026). BIL's 2026 YTD gap (~0.8%) is confirmed as a
Yahoo-side gap: its dividend list ends 2026-09-01 (SGOV has the same gap).
Fixed 2026-11-06 — see D-023.

**D-018 — Trend filter: to be chosen by backtest** · 2026-11-06 · Proposed · Low
Whether a slot winner must also pass a trend filter, and which one, is open.
Candidates are ideas, not settled: golden cross (SMA50 > SMA200), price >
10-month / 200-day SMA, positive 12-month return, or no filter at all. If a
filter is used it is checked at the rebalance date, not daily. A filter only
screens; momentum rank still chooses among the ETFs that pass. (Revised
2026-11-06: originally proposed the golden cross specifically.)

**D-023 — Patch Yahoo's missing distributions from issuer data** · 2026-11-06 · Decided · High
Yahoo's BIL dividend list stops at 2026-09-01, so the Oct 1 ($0.263176) and
Nov 2 ($0.308493) ex-dates showed as price drops and BIL's 1-year return read
3.06% instead of 3.70%. Amounts taken from State Street's historical
distributions file (matching YCharts / Market Chameleon). The loader keeps
them in `MISSING_DISTRIBUTIONS` and back-adjusts with Yahoo's own factor
(1 − amount / previous unadjusted close) only while Yahoo lacks a dividend
within 3 days of that ex-date; it then logs that the entry can be removed.
Checked 2026-11-06: every other basket ETF's latest SSGA payout is in Yahoo.
Alternatives: wait for Yahoo (no timeline), or keep a full distributions table
(more upkeep than one gap justifies). **Revisit trigger:** gaps recur often
enough that a hand-kept list becomes a chore → a distributions table or a
data vendor (D-019).

**D-019 — Yahoo data, full overwrite nightly (temporary)** · 2026-11-06 · Temporary · High
Accepted for the rotation work despite the provenance principle (raw
snapshots, reproducible reports). Adjusted daily ETF prices carry little
point-in-time risk. **Revisit trigger:** choosing a data vendor, adding
single-stock or options backtests, or any need to reproduce a past report.

**D-020 — Priority order** · 2026-11-06 · Decided · High
(1) prod DB + nightly load, (2) backtest methodology (`allockit`),
(3) signal + current-allocation view, (4) data vendors. Driven by a current
need for the rotation strategy. Real money follows only after a backtest, or
a paper / small run.
*Revised 2026-11-06:* backtest moved ahead of the signal view. A view showing
what an untested strategy "would hold today" invites acting on it before the
rules are chosen; after the backtest, the view shows the chosen rules' picks.
*Progress 2026-11-06:* (1) done — prod on migration 0003, nightly load
running. Next: (2).

## Other

**D-021 — Domain finviewhq.com** · 2026-11-06 · Proposed · Medium
Preferred over finviewdashboard/finviewdash (dashboard undersells the scope)
and finview.dev. Available as of 2026-11-06; not yet registered. finview.com
and most extensions are taken; note name proximity to Finviz.

**D-022 — Money-market funds are not tracked from Yahoo** · 2026-11-06 · Decided · High
Yahoo shows VUSXX/SWVXX at a flat $1.00 with no dividends (0% return).
Use BIL and DTB3 for cash; SGOV, VUSXX and SWVXX are not added (SGOV only
starts in 2020). MMF yields only from fund sites.
