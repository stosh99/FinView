# ETF allocation system — design record

Goal: use FinView to choose ETFs for a monthly (possibly quarterly) allocation,
then backtest the method honestly before any real money follows it.

Order of work: (1) establish the ETF basket — **done**, (2) backtest to choose
the allocation method, (3) signal view, visualizations and method-testing UI.
Project-wide priorities: D-020 in `finproject/02_decision_log.md`.

Decisions below are current working choices, revised as the work goes;
items marked **open** are undecided.

## Basket

One flat basket where every competitor ranks against every other (not separate
sleeves). Categories match `sector_etfs.category`.

| Category      | ETFs | Role |
|---------------|------|------|
| benchmark     | SPY | RRG benchmark only — not a competitor (it is the sum of the sectors) |
| sector        | XLK XLV XLF XLY XLP XLE XLI XLB XLU XLRE XLC | competitors |
| small_cap     | IWM | competitor |
| international | VGK (Europe), EWJ (Japan), VWO (emerging) | competitors; "Asia" split because Japan and EM are different trades |
| real_asset    | GLD, PDBC | competitors; keep both — gold and broad commodities trend at different times. PDBC chosen over DBC (no K-1) |
| currency      | UUP | competitor; the only asset that wins when the dollar runs. Commodity pool, issues a K-1 (fine in an IRA) |
| cash          | BIL | **park, not a competitor** — where unfilled slots go |

**Excluded deliberately:**
- **Fixed income** (IEF, TLT, TIP, credit): Stosh's separate income portfolio,
  including a bond ladder, already covers it. Consequence: inside this system
  only GLD, UUP and cash can win slots in a sell-off.
- Leveraged ETFs, single countries beyond Japan, crypto.

## Allocation mechanics

- **Fixed slots with a cash fallback.** Pick N slots (4–6 to test). Each
  rebalance, rank competitors by momentum and take the top N. **Open:**
  whether winners must also pass a trend filter, and which — candidates
  (ideas only, to be chosen by backtest, D-018): golden cross (SMA50 >
  SMA200), price above its 10-month SMA, positive 12-month return, or no
  filter. If a filter is used, a slot whose asset fails goes to cash — it is
  **not** refilled by the next-ranked asset. The portfolio can range from 100%
  invested to 100% cash.
- Why not "everything into whatever passes": when only one or two assets pass
  it is usually a stress period and the survivors are narrow trades;
  concentrating then defeats the drawdown control. Test both anyway.
- Equal weight within slots to start; inverse-volatility is a later variant.
- New money joins the current allocation at the next rebalance.
- **Open:** sector crowding. 11 of 18 competitors are US sectors and will fill
  the top slots whenever the US trends. Candidates: cap sectors (e.g. max 3
  slots), reduce to 4–5 independently rotating sectors (XLE, XLU, XLK, XLF,
  XLP), or accept it. Let the backtest decide.

## History and eligibility

- Each ETF joins the competition when it has enough history for the signal
  (e.g. 12 months for 12-month momentum), not on its first trading day. The
  basket grows over time — no proxy splicing.
- Inception dates in the data: SPY 1993; 9 original sectors Dec 1998; EWJ 1996;
  IWM May 2000; GLD Nov 2004; VGK, VWO Mar 2005; UUP Mar 2007; BIL May 2007;
  PDBC Nov 2014; XLRE Oct 2015; XLC Jun 2018.
- So 2000–2005 is effectively a US-sector strategy plus Japan. Report results
  for the full period **and** 2008-onward separately.

## Cash series

- Before BIL exists (May 2007), cash return comes from FRED **DTB3**
  (3-month T-bill rate, `rates` table, 1954–present), accrued daily.
- Check against BIL, 2008–2026: BIL trails the DTB3-implied return by about
  0.17%/yr on average (≈ fees). Apply ~0.15%/yr drag to the DTB3 series so
  pre-2007 cash isn't flattered.
- **Open:** BIL's 2026 year-to-date return trails DTB3 by ~0.8%. Cause
  confirmed (Nov 6 2026): Yahoo's dividend list for BIL stops at 2026-09-01,
  so the Oct and Nov distributions aren't adjusted out — the adjusted close
  drops on 2026-10-01 (−0.23) and 2026-11-02 (−0.29), ~0.57% together. SGOV
  shows the same gap, so it is Yahoo-side, not BIL-specific. Before the
  backtest trusts BIL for 2026: reload once Yahoo catches up, or apply the
  missing distributions from issuer data.

## Backtest honesty rules

- Adjusted closes (dividends included).
- Signal on the close, trade at the next open — no lookahead.
- Include transaction costs and a slippage allowance.
- Walk-forward: tune on the early period, test on the later period untouched.
- Report CAGR, max drawdown, Sharpe, turnover, and a **year-by-year** table vs
  SPY and a static allocation of the same basket.
- Parameter-sensitivity heatmap: a method that works only at exactly one
  lookback is noise.
- For this use the objective is **drawdown control** first; expect trend
  methods to lag buy-and-hold in long bull markets.

## Baselines to beat

1. Equal weight across the basket, rebalanced quarterly (the null).
2. Faber's 10-month SMA trend model.
3. Antonacci's dual momentum (relative + absolute).
4. Relative-momentum top-N (12-1 month), monthly.

If a custom method (including RRG-quadrant rotation) can't beat these
out-of-sample, use the baseline. RRG is a visualization of momentum, not a
strategy — test whether it adds anything over plain momentum.

## Deployment path (from the Oct 2026 discussion)

Build → backtest → shadow-trade 2–4 quarters against the static allocation it
would replace → deploy a fraction → scale on evidence. Point it at growth money
before core money. IRA placement means monthly turnover has no tax cost.

## Architecture

- Engine as a package with a CLI, deterministic, no web dependencies
  (`allockit/`, same pattern planned for the DCF engine `dcfkit/`).
- Backtest from the database, not live downloads.
- Store each run in Postgres with a parameters hash; FinView renders equity
  curves, drawdowns, the year table and the sensitivity heatmap.
