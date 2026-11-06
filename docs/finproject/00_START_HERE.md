# START HERE — FinProject (the FinView platform)

FinProject is Stosh's personal investment research and decision-support
platform. **FinView is its implementation** (this repository; planned domain
finviewhq.com). These documents are the project's shared memory for any
model or tool (Claude, Claude Code, ChatGPT, Codex, Gemini, local models).

## Read in this order

1. `01_project_brief_v3.md` — what the project is, scope, priorities,
   architecture as built, principles, open decisions.
2. `02_decision_log.md` — what has been decided, when, and why.
3. `03_anti_resurrection_log.md` — what was rejected/deferred and what would
   justify reopening it. Check here before proposing a "new" idea.
4. Module design records, e.g. `../ALLOCATION_DESIGN.md` (ETF rotation).
5. `../../CLAUDE.md` — how to work in this repo (environments, commands, rules).

## Rules for any model working on this project

- Treat these files as the source of truth, not a fresh conversation.
- They record working choices, not fixed commitments: the project is built
  module by module and decisions get revised as it goes. Update the docs
  when a choice changes rather than working around them.
- Distinguish facts, assumptions, estimates, and judgment calls; state
  uncertainty.
- Do not reopen a rejected or superseded approach without following the
  reversal rule in `03_anti_resurrection_log.md` (what changed, new evidence,
  cost, measurable test).
- Decision support only: nothing in this project places trades.
- End a useful session with one of: a brief update, a decision-log entry, an
  open-question change, or a short handoff note.

## History

The original planning documents (May–July 2026: architecture, 64-week plan,
multi-model critiques, synthesis, Fable comments, v2 brief) remain in the
Google Drive folder **FinProject**. They are superseded by v3 but kept for
reference; see the source index at the end of `01_project_brief_v3.md`.

Last updated: 2026-11-06
