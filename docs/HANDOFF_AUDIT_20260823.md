# HANDOFF_AUDIT_20260823.md — adversarial audit request

**To:** Fable
**From:** Claude, end of the 2026-08-22/23 weekend session
**Scope:** `TX-9AI/options_trader_v4` @ **r82 (`fe832ae`)** and
`TX-9AI/day_trader_pro` @ **r221**
**Deliverables:** a BUG LOG and a landable fix tarball. Details at the bottom.

---

## Why you are being asked

Twenty-two revisions landed across two repos in about thirty hours, most of it
written and shipped the same evening it was designed. **Almost none of it has
run against a live market.** Monday 2026-08-24 is the first session with any of
it in place.

The last two adversarial audits each found a **P0 that every checker passed**:

- the **bisected `ExitEngine`** — `evaluate` and 33 evaluators became nested
  locals of a telemetry function. File compiled, import passed, every checker
  green, and no stop/trail/theta ladder ran at all.
- the **missing singletons** — `_alert_manager` declared `global` with no
  module-level binding. Import succeeded; the `NameError` existed only at CALL
  time. Every box crash-looped on boot, AVGO at `NRestarts=23`.

Both were invisible to `import` and to a green board. That is the class of
finding this repo produces, and it is why a second reader is worth the tokens.

**I also shipped four real defects in the last 30 hours and caught them only by
running things.** They are listed below under "my own errors" — treat them as a
sample of my blind spots, not an exhaustive list.

---

## What changed, in one page

### otv4 r61 → r82

| rev | what |
|---|---|
| r61–r64 | **The feed manifold.** 10/10 event types captured (was 3). `greeks_series` and `quote_series` at full fidelity, `prints` with `aggressor_side`, extended candles on all 5 tenors. Nothing conditional, nothing overwritten. |
| r62–r63 | **The derived layer.** `/derived`, one engine per store. `base.py` enforces contributor-never-gate structurally: `run()` wraps `derive()`, `run_all()` wraps `run()` — **both guards mutation-proven separately**, because an earlier draft passed with either one removed. |
| r65 | **The exorcism** (yours). The retired classifier's vocabulary gone tree-wide; schema physically dropped so a query RAISES. |
| r66 | Strategy notes (one row per evaluation, **fired AND declined**) + the flow-exit counterfactual, which journals WOULD_HAVE_FIRED and never acts. |
| r67 | **The fleet unbreak** — three missing module-level singletons; `check_singletons.py` now CALLS 27 accessors. |
| r68 | Manifold health board — per-stream bulbs, four states (green/stale/missing/**idle**), rollup into `status.py`. |
| r69–r70 | **Plan ledger.** Intent persisted with its justification. The condor plan lived only in memory, so a restart at `LEG1_FILLED` left a leg live at the broker with no memory a second was planned. `WIPED_BY_RESTART` is its own terminal category. |
| r71 | `WRITE_MAP.md` — generated, gated. Who owns which of 22 tables. |
| r72 | **ORB rescue** — if today's 09:30 5m bar is missing between 09:36 and the 11:00 cutoff, unsubscribe 5m and resubscribe from the open. Once per session, date-guarded. |
| r73 | **No silent gates** — every refusal rung reports at INFO and into `gate_disposition`, **edge-triggered**. |
| r74 | Docs corrected (fleet count, project state, reading order). |
| r75 | **CHARACTER** — two measured axes, no scoring. |
| r76–r78 | `query.py` market half; GEX label; fork slope normalised by ATR. |
| r79–r81 | **Box-side self-close** at 16:45 + retention purge (dry by default). |
| r82 | **`--reconcile` was erasing the push offsets.** See P0 below. |

### day_trader_pro r200 → r221

Hotfix launcher · SENSORS section (10 reports over the derived stores) ·
Retire/Emergency-stop scoping · banner derives its version · **the dtp
exorcism (298 → 0)** · **conductor v2** · S3 sweep · P&L from the warehouse ·
EOD analysis split · fit readiness · notify test-mode guard.

---

## The four rulings that govern the new code

Check the code against these, not against your own priors:

1. **CAPTURE EVERYTHING.** *"Stop discarding information. It comes in like a
   fire hose — design the manifold that gets everything where it needs to go."*
   Nothing conditional, nothing overwritten. Storage is cheap.
2. **DERIVERS CONTRIBUTE, THEY NEVER GATE.** A missing derived port is NOT a
   contract error. Only RAW ports can be hard requirements. This is the rule
   the retired classifier violated and it is why it was retired.
3. **COLLECTION WITHOUT CONSUMERS IS AN INVESTMENT.** *"We already learned the
   hard way what happens when you realize that data you needed all along has
   been pruned and there is no getting it back."* `WRITE_MAP.md` is an ASSET
   REGISTER — the "no external reader" list exists so the asset is visible,
   never so it can be trimmed.
4. **CHARACTER IS A STATE; SWEEPS AND BREAKOUTS ARE EVENTS.** They coexist and
   are stored separately. **No scoring, no conviction, no consensus** — the
   specific temptation to refuse is combining the two axes into one strength
   number, which is `_combine()` under a new name.

---

## 🔴 THE P0 OF THE WEEKEND — read this before anything else

`warehouse/s3_push.py`, fixed in r82. **One word.**

```python
save_ledger(counters, LEDGER_PATH)      # was
save_ledger(counters, COUNTERS_PATH)    # is
```

`chain_ledger.json` maps **source path → lines already pushed**.
`prefix_counters.json` maps **S3 prefix → objects confirmed**. Same shape,
different meaning, one helper. `--reconcile` wrote the counters over the
offsets, so the next `push_file` looked up its source path, **found nothing,
resumed at line 0 and re-pushed the entire file** — and `--verify` drains
first, so every reconcile destroyed the record of what had been sent and the
next verify re-sent everything.

**Observed live: 222 → 300 → 370 → 395 while S3 held 74–79. It got worse every
time we tried to fix it.** Nothing was lost (content-hashed keys overwrote
identical objects) but the fleet re-uploaded itself repeatedly.

**The failure class is what I want you looking for elsewhere: two state files
with the same shape and different meanings, written through one helper that
cannot tell them apart.** `save_ledger(x, PATH)` accepts either dict happily.
There is no type, no signature, no assertion between the mistake and the
consequence. **Where else does this pattern exist in either repo?**

---

## My own errors from these 30 hours — your calibration sample

Each was caught by RUNNING something, never by reading:

- **`s3_sweep` proposed deleting `NVDA_EXT`, `SPX_EXT`, `QQQ_EXT`, `AMD_EXT`
  and VIX** — 321,835 objects including the extended-hours tape of every panel
  symbol. The panel guard did an exact string match, so `"NVDA_EXT" != "NVDA"`
  passed through. A guard that matches a name FORMAT rather than an IDENTITY is
  not a guard. **Only caught because the operator insisted on scanning the
  bucket before deleting.**
- **A manifest lost its provenance** — dead streams delete by PREFIX, but
  `--from-manifest` re-applied the SYMBOL guard and refused 359,123 keys. Half
  a purge silently did not happen.
- **`test_conductor_recovery` was paging the operator's phone on every commit**
  — it drives a partial-failure branch on purpose, that branch sends a
  Telegram, and it stubbed `harvest` but not `notify`. It runs in every deploy
  gate. The dates in the alert were the test's own fixture literals.
- **The conductor's `--verify` died at 22 seconds** — `ssh_util.ssh_run` uses
  `SSH_CONNECT_TIMEOUT`(12)+10, and a verify walks 200+ prefixes. A box
  returned `NO_ANSWER` because the TRANSPORT gave up, **which is
  indistinguishable from a silent box.**
- I wrote the retired classifier's word into two changelogs while describing
  its removal. `check_no_regime` caught both.

---

## Where I would look first

**These are suggestions, not scope. Follow what you find.**

### otv4

1. **`derived/character_engine.py` + `analysis/character.py`** — newest code in
   the repo, ~4 hours old. Does the hysteresis actually prevent boundary
   flapping under real jitter, or only under my synthetic drive? Is the
   nameless middle band reachable in a way that strands a box with no
   character all session? **Acceptance gate: 1–3 transitions per symbol-day**
   (the operator's 20-year prior; the retired engine produced ~20).
2. **`warehouse/self_close.py`** — it HALTS THE MACHINE. Never run live. If
   `--verify` returns something my parser mis-reads, a box either halts on
   unverified data or never halts at all. The retention purge runs inside it,
   after verification and before the halt.
3. **`warehouse/retention_purge.py`** — deletes rows. `NEVER_PURGE` is
   hard-coded; confirm nothing routes around it, and that the derived-store
   trim cannot reach a lifecycle table.
4. **`derived/plan_ledger.py` + its wiring in the condor** — every hook is
   wrapped so bookkeeping cannot raise into the state machine. Verify that is
   true at every call site, and that `LEG1_FILLED` genuinely survives a
   restart.
5. **`analysis/gate_report.py`** — edge-triggered. Does a strategy that
   oscillates between two rungs produce one line per flip? That would be
   240/hour, which is the noise problem it exists to prevent.
6. **`data/candle_feed.py` ORB rescue** — it unsubscribes then resubscribes 5m.
   If the unsubscribe fails and the resubscribe succeeds, two live
   subscriptions write the same rows. I log it; I do not prevent it.

### day_trader_pro

7. **`eod_conductor_v2.py`** — never done a live takedown. Quiesce stops
   `s3-push.timer` and `candle-logger.timer` and re-arms in a `finally`; if
   that finally is ever skipped, boxes stop warehousing silently. The hold rule
   distinguishes COUNTER DRIFT from real loss by **string-matching the
   verifier's own output** — fragile, and I know it.
8. **`s3_sweep.py`** — I shipped two guard bugs in it in one evening. A third
   is plausible. It has DELETE on the bucket.
9. **`pnl_s3.py`** — dedupe correctness. Without `latest_per_trade` a trade
   that opened, updated and closed counts three times and inflates P&L
   silently.
10. **`fit_readiness.py`** — the verdict thresholds (`MIN_FIRED` 30,
    `MIN_DECLINED` 50, `MAX_RUNG_SHARE` 0.70) are **guesses**, stated as such
    in the file. They have never seen data.

---

## What is deliberately inert — do not "fix" it

- **`config.py` RETENTION_DAYS / RETENTION_DAYS_ARTIFACTS are COMMENTED OUT.**
  Written down before a purge existed to read them, on the operator's
  instruction. The gate asserts they stay commented.
- **`PRUNE_KEEP_ROWS = 0`** — pruning on the boxes is off and stays off.
- **`OT_RETENTION_APPLY` unset** — the purge is dry fleet-wide by design; the
  numbers are arithmetic from `EMA_ANCHOR=200`, not measurements.
- **`dtp-eod-analysis.timer` is installed but DISABLED** — the conductor orders
  the reports; the unit exists for manual re-runs and rollback.
- **The `--dry-run` conductor preview FABRICATES its verification.** It is
  labelled as such. Do not make it look trustworthy; make it louder if
  anything.

---

## State of the world at handoff

- **Day-zero parity reached** 2026-08-23: `NVDA OK short=0 local=35370
  s3=35370`. The other 14 boxes were reconciled with the fixed code but **have
  not been verified** — that is the one open item before Monday's close.
- Bucket: **1,148,645 → ~634,000 objects.** `raw/shadow` (never installed) and
  `raw/regime_log` (retired) deleted; 177,270 culled-symbol objects deleted;
  12,003 legacy-hash duplicates deleted.
- Fleet: 15 boxes on `fe832ae`, all services active.
- EOD: **two timers** where there were six. Conductor 16:05 (control),
  self-close 16:45 (each box).
- Every derived table has **zero rows** until Monday.

---

## Deliverables

**1. A BUG LOG**, one entry per finding:

```
SEVERITY   P0 | P1 | P2 | P3      ("measures wrong" is its own severity)
FILE       path:line
MECHANISM  what actually happens, not what looks wrong
EVIDENCE   the command or reasoning that establishes it
FIX        the change
BLAST      what breaks if it is not fixed, and what breaks if it is
```

**Please include a CLEAN section** — what you executed and found correct. A
finding list without it reads as "everything is broken", and I would rather
know which of these I got right.

**2. A FIX TARBALL**, per this project's contract:

- `<repo>_audit_fixes_20260823_r<N>.tar.gz`, rooted at the repo name, **changed
  files only**
- **NO `docs/GENESIS.md`** — it is append-only on the box and shipping it
  clobbers the ledger
- no scaffolding files, no reformatting, no new dependencies
- **headers AND dated changelog entries both bumped**; title line must equal
  the newest changelog entry
- tests are **plain scripts, never pytest** (pytest is not in otv4's venv and
  breaks the land command)
- **all checks must pass**, and any new check should be **born red** at the
  pristine HEAD — if it cannot fail against the bug, it does not prove anything
- fail closed and state the direction

**3. If you find nothing above P2, say so plainly.** A clean audit is a
result. I would rather have an honest "these six things are fine" than a
manufactured finding.

---

## Two things I would ask you to be sceptical of specifically

**My doctrine comments.** I wrote a great deal of prose into these files this
weekend. Some of it explains a real constraint; some of it is me being certain
at 11pm. **Where a comment asserts a measurement, check the measurement.**

**My checkers.** The 2026-08-21 lesson was that `test_candle_routing`
**asserted the inverted table and certified the bug green** — written from the
same wrong belief as the parser it checked. Several checkers here are new and
were written by the same person who wrote the code they check. That is the
weakest link in everything I shipped this weekend.
