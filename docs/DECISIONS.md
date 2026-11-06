# Decisions

One line per decision, newest first, tagged by area. Grep for your area tag
before changing code. Allocation-method design lives in
`docs/ALLOCATION_DESIGN.md`; this file is the dated log.

- 2026-11-06 [data] BIL's missing Oct/Nov 2026 distributions confirmed as a Yahoo-side gap (dividend list ends 2026-09-01; SGOV has the same gap) — must be fixed before the backtest trusts 2026 cash returns.
- 2026-11-06 [data] Not adding SGOV, VUSXX or SWVXX — BIL plus DTB3 already covers cash; Yahoo has no usable history for money market funds (flat $1.00, no dividends), and SGOV only starts in 2020.
- 2026-11-06 [web] Cash (BIL) is charted as the FRED DTB3 3-month T-bill yield, not candlesticks — a T-bill fund's price just creeps up, so candles and moving averages say nothing.
- 2026-11-06 [web] Charts page shows the whole basket on one page, grouped by category with filter chips (unsaved), nav label "ETF Charts" — the basket ranks as one flat pool, so it should be seen together. Provisional: confirm with user tests.
