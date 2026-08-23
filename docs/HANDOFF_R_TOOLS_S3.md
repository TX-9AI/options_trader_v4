# HANDOFF_R_TOOLS_S3.md — make the R suite control-side and conductor-driven

**To:** Fable
**From:** Claude, 2026-08-23, after landing otv4 r86
**Repos:** `options_trader_v4` @ r86 (`7eaf23f`), `day_trader_pro` @ r222

The R suite is good and it landed clean — born-red pin, C5 failure control,
pre-registered bar, positive control in `exit_replay`. **One thing blocks it
from running: it reads box-side sqlite.**

---

## The blocker

`r_ledger.DEFAULT_DB` and `edge_scan.DEFAULT_DERIVED` both resolve to
`~/options-trader/…` — the TRADING BOX's local stores. The conductor runs on
CONTROL, where that path does not exist, and as of 2026-08-23 control no longer
pulls anything from the boxes.

## 🔴 The operator's architectural requirement — this is not negotiable

Stated 2026-08-23, verbatim in effect:

> **"I want those reports to be run by control and the target to be the S3
> bucket. That is a baseline requirement. There is going to be no data
> collection or reporting done on the trading instances, and we are absolutely
> not going to go back to pulling data onto control to digest."**

Three prohibitions fall out, and each one has a history behind it:

1. **NOTHING RUNS ON A TRADING BOX.** Not via fan-out, not "just for this
   report", not as a fallback when S3 is slow. A box that is reporting is a box
   doing something other than trading, and the fleet is stopped outside RTH
   anyway — a report that needs a box up is a report that costs EC2 time to
   read.
2. **NOTHING IS PULLED TO CONTROL.** The 15:55 harvest timer was retired
   2026-08-23 precisely to end the dual-write. Do not reintroduce an scp, an
   rsync, or a "cache the db locally" step. **S3 is the read path.**
3. **CONTROL IS THE ONLY PLACE THESE RUN.** It already has the IAM role for
   read, and it is the only host that sees the whole fleet at once — R across
   the book is the question, not R per symbol.

⚠️ **PER-BOX R IS THE WRONG ANSWER ANYWAY.** Running `r_ledger` on fifteen
boxes yields fifteen R figures over 5–15 trades each. The number the operator
needs is one R across the fleet's book, which only exists where the trades are
pooled — the warehouse.

---

## What already exists on control (use it, do not rebuild it)

- `warehouse_reader.py::build(date)` — returns the fleet_trades bundle
  **assembled from S3**, in `consolidate_trades`' shape. Already the source for
  `eod_analysis`'s CONSOLIDATE phase.
- `warehouse_reader.read_prefix(s3, datatype, date)` and `latest_per_trade()` —
  ⚠️ **DEDUPE IS MANDATORY.** A trade is pushed on every state change, so S3
  holds several objects per `trade_id`; without `latest_per_trade` a trade that
  opened, updated and closed counts three times and inflates every ratio in the
  suite silently.
- `pnl_s3.py` — a working, landed example of exactly this pattern (day or
  range, reads S3, boxes off). Copy its shape.
- **`push_series` (your r86)** — the seven manifold series tables now warehouse.
  This is what makes `exit_replay` possible on control at all.

## What is asked for

**1. An S3 source for all four tools.**
`r_ledger`, `stop_sweep`, `edge_scan`, `exit_replay` take `--date` /
`--from` / `--to` and read the warehouse. Keep `--db` as an escape hatch for
local debugging if you want, but **the default path must be S3**, because a
default that reaches for a box-side file will silently produce an empty report
on control rather than an error.

⚠️ **AND SAY WHICH SOURCE IT USED, IN THE OUTPUT.** "0 trades" from an empty
day and "0 trades" from a path that does not exist must not look alike — that
conflation has cost this project twice this week.

**2. The conductor owns the timing.** The operator: *"give it to the conductor
to handle."* Not new systemd timers — the fleet went from six EOD timers to two
on 2026-08-23 and adding more undoes that. `eod_conductor_v2` already invokes
`eod_analysis` after takedown; these hang off the same call.

- **`r_ledger` — NIGHTLY**, a phase in `eod_analysis`, warn-never-stop like the
  rest. **Telegram the HEADLINE ONLY** — R and capture ratio, not the table. A
  nightly report that gets read beats one that gets scrolled past, and the
  standing rule is that Telegram is an emergency channel.
- **`edge_scan` — WEEKLY, Fridays.** Its bar needs 10 sessions and 200 trades
  per side; nightly it would print NOT YET five times a week and teach the
  operator to ignore it. **Silent unless something clears the bar** — that is
  the whole point of a pre-registered threshold.
- **`stop_sweep` and `exit_replay` — NOT SCHEDULED.** They are decision tools,
  run when a specific question is being asked. Devtools items, on demand.
  `exit_replay` in particular reads quote history per trade; it is the
  expensive one and it answers "would a different trail have done better on
  THESE trades", which is not a recurring question.

**3. Two devtools items** in `day_trader_pro` for the on-demand pair, following
the existing pattern (date or range prompt, optional Telegram).

---

## Constraints that apply to the delivery

- `<repo>_<descriptor>_r<N>.tar.gz`, rooted at the **repo directory name** —
  otv4 tarballs root at `otv4/`, dtp at `day_trader_pro/`. ⚠️ Your last dtp
  archive rooted at `dtp/` and the land command failed on it; not a defect,
  just a lost minute.
- **NO `docs/GENESIS.md`** — append-only on the box.
- Changed files only. Headers AND dated changelog entries both bumped; title
  line must equal the newest changelog entry.
- Tests are **plain scripts, never pytest**.
- Any new check **born red** at r86 / r222.
- All standing checks green; file map and write map regenerate clean.

## Honest notes from this side

- `eod_analysis`'s phases are already warn-never-stop with the traceback's last
  line kept. Follow that; a report failure must not change the close's verdict.
- The conductor's `--dry-run` **fabricates its verification** and is labelled as
  such. If you add phases, do not let the dry run imply they succeeded.
- **`edge_scan`'s job for the next several weeks is to say NOT YET.** Please do
  not soften the bar to produce output. The operator's own framing: the fit
  comes later, on an honest discretionary split, and it will address position
  size — never gates.
