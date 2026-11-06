# Decisions (code and UI)

One line per decision made while building, newest first, tagged by area
(`[web]`, `[api]`, `[loader]`...). Grep for your area tag before changing
code. Project, strategy and data-source decisions go in
`docs/finproject/02_decision_log.md` (D-numbers) instead — link, don't copy.
Nothing here is permanent; a new line can replace an old one.

- 2026-11-06 [web] Cash (BIL) is charted as the FRED DTB3 3-month T-bill yield, not candlesticks — a T-bill fund's price just creeps up, so candles and moving averages say nothing. Money-market funds and SGOV not added: see D-022.
- 2026-11-06 [web] Charts page shows the whole basket on one page, grouped by category with filter chips (unsaved), nav label "ETF Charts" — the basket ranks as one flat pool, so it should be seen together. Provisional: confirm with user tests.
