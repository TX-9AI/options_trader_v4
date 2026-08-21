# REGIME PURGE — inventory and rerouting plan
**otv4 @ 2da1e89 · built 2026-08-21 by AST walk, not grep**

216 live references (non-comment, non-docstring) across 24 files.
**25 of them are control-flow gates**, in 8 files. Everything else carries,
logs, persists or displays.

`primary_regime` is hardcoded `Regime.UNKNOWN` at `main.py:1188`. So **every
gate below that tests a regime LABEL is dead by construction** — it can only
take one branch, forever.

---

## A — GATES THAT ARE PERMANENTLY FALSE (delete)

These are the Frankenstein残 — v3 vetoes that outlived their classifier.

| File | Line | What it does today |
|---|---|---|
| `main.py` | 1951 | **THE FLEET-STOPPER.** Vetoes all dispatch unless label is real or ORB is already confirmed. Fires every tick on every box. |
| `execution/exit_engine.py` | 1413 | `regime_flip_exit` for the butterfly — can never fire |
| `execution/exit_engine.py` | 1606–1610 | Adverse-trend exit for calls/puts — can never fire |
| `execution/exit_engine.py` | 1945 | `still_trending` branch — unreachable |
| `analysis/orb_engine.py` | 639, 664 | `SWEEP_REVERSAL` block, already double-negated by `ORB_FIRES_REGARDLESS_OF_REGIME` |
| `main.py` | 2027, 2040 | `ORB_BLOCK_RANGING` and its sibling |
| `main.py` | 2173, 2234 | continuation / runaway blocks |
| `main.py` | 2684, 2776 | journal + record paths that branch on `regime is None` |
| `status.py` | 252 | displays "UNKNOWN" specially |

⚠️ **The exit_engine three are the serious ones after 1951.** They are exit
rules, not entry rules — the butterfly's regime-flip exit and the adverse-trend
exit have been dead since the port. F0 was "every exit was dead code"; these are
three more exits that never ran, hiding behind a label instead of a bisected
class.

`config.ORB_FIRES_REGARDLESS_OF_REGIME` and `config.ORB_BLOCK_RANGING` become
meaningless once these go — delete the constants with them.

---

## B — LIVE VALUES RIDING ON THE REGIME OBJECT (reroute, do not delete)

`RegimeState` is hardcoded UNKNOWN but it is **not empty**. It carries real
measurements that other things read. Deleting the type without rerouting these
silently zeroes them.

| Value | Read at | Real source |
|---|---|---|
| `.adx` | `main.py:1526` (`adx_at_entry` on the trade record) | `trend.primary_adx` |
| `.conviction` | `main.py:1528` (`regime_conviction` column) | **nothing — v4 has no conviction.** Drop the column write |
| `.atr_normalized` | built at 1191 | `vol.atr_normalized` |
| `.bb_width_pct` | built at 1192 | `vol.bb_width_pct` |
| `.trend_direction` | built at 1193 | `trend.overall_direction` |
| `.structure_sequence` | built at 1194 | `structure.structure_sequence` |
| `.sweep_recent` / `.sweep_age_bars` | built at 1195–1196 | `liq_map` |

**Each of these already has a direct source.** `RegimeState` is a middleman that
adds a dead label to live data. Point the readers at the source and the type
deletes cleanly.

---

## C — `vix_regime` IS NOT THE ARTIFACT (rename, keep)

`risk/setup_scorer.py:344–350` and `data/macro_data.py` branch on
`macro.vix_regime` ∈ {LOW, NORMAL, ELEVATED, CRISIS}. That is a **live VIX-band
measurement**, computed from the VIX itself — nothing to do with the retired
classifier. It works.

It still carries the poisoned word. Per the operator's rule — *if it is revived
it has to be under a different phrase or it will get confused as an artifact* —
this is the one thing that should be **renamed rather than purged**. Suggest
`vix_band`. Same values, same logic, no collision with the dead concept.

⚠️ `SessionGuard`'s VIX-crisis lockout reads this. Renaming touches it; deleting
it would delete a live risk rule.

---

## D — PERSISTENCE (schema decisions, not code deletions)

| Where | What |
|---|---|
| `database/trade_logger.py` | `trades.regime` column, `trades.regime_conviction`, and the whole `regime_log` TABLE |
| `analysis/signal_journal.py:236` | `regime_ctx()` helper, called from 6 sites in main |
| `analysis/chain_snapshot.py:164` | `"regime"` field in the snapshot record |
| `warehouse/s3_push.py` | `regime_log` listed as a pushed stream |
| `eod_summary.py`, `query.py` | read those columns for display |

**These need a call, not a default.** Dropping a column rewrites history;
keeping it means the word survives in every trade row and in S3. Middle path:
stop WRITING them, leave the columns for the existing rows, and drop
`regime_log` from the S3 stream list since it will never gain another row.

---

## E — DISPLAY ONLY (cosmetic, last)

`status.py` (18), `query.py` (6), `notifications/alert_manager.py` (3). These
print it. They change when D changes and not before.

---

## SEQUENCING

**A alone unblocks trading.** It is ~10 line deletions plus two config
constants, and it is the whole reason the fleet has zero trades today.

**B must land with A or immediately after** — nothing in A depends on B, but
once `RegimeState` is unreferenced by gates, leaving it constructed is exactly
the "guard outlives the thing" shape one level down.

**C, D, E are not session-critical** and D contains a decision that is the
operator's, not mine.

⚠️ **`tests/check_no_regime.py` SCANS `strategy/` ONLY.** That is why all of
this stayed green. Extending it tree-wide is what makes the purge stick — and
it must be extended BEFORE the deletions, so it goes red on exactly the list
above and green only when the list is empty.

---

# PHASE B — executed 2026-08-21, ships as r58
**otv4 @ 03196c3 → r58 · every claim below verified by EXECUTION**

**Definition of done, met:** `check_no_regime` reports **zero carries across 70
files**, the `PHASE_B` / `PHASE_B_FILES` dicts are **empty**, and — hardened
during this phase — **a carry is now a RED, not a warning** (see The Checker,
below). All eleven checks green, file map current, `import main` clean under a
hostile env.

## B1 — the reroutes, and two things that were already broken

| carrier | destination | verified |
|---|---|---|
| `.adx` → `adx_at_entry` | unchanged path; `MarketState.adx` still sourced from `trend.primary_adx` | EXECUTED: synthetic ctx → `assemble_market_state` → `.adx == 27.3` → `adx_at_signal` lands non-zero |
| prior-tick direction (gap measure) | **`BotState.prev_trend_direction`**, committed at the END of each analysis pass | EXECUTED: BULLISH → prior_dir 1 |
| `.conviction` | **write dropped** (`regime_conviction` column stops being written; column stays — B3) | field deleted from the type; nothing produces it |
| chain_snapshot `regime=` | kwarg no longer passed; `snapshot()` keeps the default-None param so the schema question stays B3's | field writes None from r58 |
| position_manager `regime=` | passes None; the exit label arms went with it | see exit_engine v4.2 |
| `vix_regime` | **`vix_band`** everywhere (macro_data, setup_scorer ×4, signal_journal, main ×2, market_state) — SessionGuard's crisis lockout reads the renamed field | grep-clean; EXECUTED through assemble |

🔴 **DISCOVERY 1 — the gap measure was already blind.** `state.current_regime`
was **assigned NOWHERE** in the tree. The 1106 read — whose own comment warns
that a silent constant is "exactly the failure this whole week has been
about" — has returned None on every tick since the split: `prior_dir` was a
silent 0 and `gap_class` permanently UNDIRECTED. The rehoming does not
preserve behaviour; it **creates** the behaviour the comment claimed existed.

🔴 **DISCOVERY 2 — the sweep score was a guard over nothing.** `ctx["l1"]` is
set nowhere in v4 — the L1 scorer was never ported — so `_sweep_setup` has
been a silent 0.0 and the "PLTR protection" the block's doctrine describes
**does not exist in this repo**. The read is deleted with that stated; if the
protection is wanted, it must be REBUILT from structure, not resurrected by
name. Same discovery, third scale: r55 (engine assert), r57 (label gates),
r58 (score read) — a guard outliving its producer each time.

Consequence of 2: `regime_ctx()` had been journalling `label=UNKNOWN` plus
axes decomposed from that same never-set source — **every section it ever
wrote in v4 was an empty vocabulary**. Helper deleted, 7 call sites removed;
`journal()` takes sections generically, so no schema change.

## B2 — trade_readiness rebuilt on measured inputs

Every label arm either now reads a **measurement** or is an **honest
constant**: direction/trending from `trend.overall_direction` (descriptive
feed — the module gates nothing, per main's own doctrine); sweep-ness from
`liq_map.recent_sweep`; `ranging`/`coil_val` are 0.0 — which is the value the
dead arms produced on every tick anyway, now stated instead of implied.
**Structural flatness/squeeze inputs are OWED** (operator scope — a threshold
here would be an invented number). The journal read at ~1115 uses the written
`dir` factor, uniform across eras (pre-r58 rows computed it from the label at
write time). The `__main__` harness feeds the VOTE, not labels. Note for any
R-series study: **R's value changes at r58** — direction was previously always
empty; window-tag accordingly.

## B3 — persistence: the options, presented not taken

What r58 already does (forced by the countdown): **nothing writes a label
anywhere** — trades get `""` (Phase A precedent), condor rolls get `""`,
chain snapshots get None, shadow rows drop the two dead keys (pre-r58 rows
carry `UNKNOWN`/0.0; absent keys mean r58+), TCS signals get `""`.

Still yours, untouched by r58:
1. **Drop `trades.regime` + `trades.regime_conviction` + the `regime_log`
   table** — the word leaves history; rewrites every existing row's shape.
2. **Keep the columns** — history intact; the word survives in every row and
   in S3 forever, value `""`/0 from r58 on.
3. **Middle (my recommendation): keep columns, drop `regime_log` from
   `warehouse/s3_push.py`'s stream list** — it can never gain another row, so
   pushing it nightly ships a fossil. `s3_push.py` is untouched in r58.
`eod_summary.py` / `query.py` / `status.py` display-only reads follow
whichever call you make (E-class, unchanged).

## B4 — vix_band

Renamed at the source and every reader; the checker exemption is **removed**.
The value set (LOW/NORMAL/ELEVATED/CRISIS), the classifier and the crisis
lockout are byte-identical — only the word changed.

## THE CHECKER (v4.2) — and the bug I planted in it

Emptying the dicts exposed a shape flaw: **carries printed a warning and
exited 0.** I planted `getattr(None, "vix_regime", "")` in a scanned file and
the board stayed green — a report, not a guard. Post-Phase-B a carry is a
REGRESSION, so carries now **fail**. Replanted: red. Removed: green. (The
handoff's plant-the-bug rule caught its own checker; that is the rule working.)

## OWED / NOT DONE, stated

- `_evaluate_continuation` in exit_engine is **dead-routed wholesale** (no v4
  writer of "ContinuationStrategy") — its label arms are gone (v4.2) but the
  function's deletion is a separate decision.
- `RegimeState` the ALIAS survives as the type-hint spelling across ~50
  annotations; it aliases `MarketState`, which no longer carries a label,
  conviction, or the old name's meaning. Retiring the alias is mechanical and
  owed, not risky.
- Structural `ranging`/`coil` inputs for readiness (B2, above).
- The B3 schema call, and whether the `regime` **column name** itself is an
  artifact under the operator's phrase rule.
