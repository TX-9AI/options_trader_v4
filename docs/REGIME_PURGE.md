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
