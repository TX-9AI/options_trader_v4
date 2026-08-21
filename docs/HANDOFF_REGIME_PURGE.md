# HANDOFF — REGIME PURGE, PHASE B
**For: Fable · From: the r57 thread · options_trader_v4 · 2026-08-21**
**Phase A is landed. Start from otv4 main AFTER r57, not from 2da1e89.**

---

## WHAT YOU ARE BEING ASKED TO DELIVER

Two things, same standard as Phase A:

1. **A landable tarball** — `otv4_<descriptor>_r58.tar.gz`, changed files only,
   rooted at `otv4/`, with a land command. Not a patch set, not a description of
   changes. Something the operator pastes into Termius on his phone.
2. **A written audit** — what you found, what you changed, what you could not
   change and why, and what remains owed. The Phase A equivalent is
   `REGIME_PURGE.md`; match that depth.

The operator reads on mobile through Termius. One-line commands, semicolons, no
walls of code in chat. `WORKING_AGREEMENT.md` §§ on delivery are binding — read
them before shipping anything.

---

## THE SITUATION IN FIVE LINES

· v4 deleted the regime classifier. `assemble_market_state` hardcodes
  `primary_regime = Regime.UNKNOWN` (main.py, ~line 1188) and always will.
· v3's gates came across anyway. **They vetoed on exactly that value**, so they
  were true on every tick — the fleet's first live session produced **zero
  trades on all 15 boxes with relaxed entry ON**.
· Phase A (r57) deleted every gate. `tests/check_no_regime.py` is now tree-wide
  and green: **no regime label GATES anything.**
· What remains is **carried** — values riding on a dead object, labels written
  to records, fields pushed to S3, strings printed in status. 36 references
  across 8 files.
· **Operator's direction, verbatim: "No regime references anywhere with fully
  functioning GEX and other derived overlays. If 'regime' is to be revived it
  has to be under a different phrase or it will get confused as an artifact."**

---

## YOUR DEFINITION OF DONE

`python3 tests/check_no_regime.py` prints **PHASE B PENDING with zero entries**
and the `PHASE_B` / `PHASE_B_FILES` dicts in that file are **empty**.

That checker is your worklist and your proof. It is keyed on source-line TEXT,
not line numbers — an earlier draft used `(file, lineno)` and every entry went
stale the moment a deletion above it shifted the file. Do not reintroduce line
numbers.

---

## THE WORK, IN DEPENDENCY ORDER

### B1 — Reroute the live values, THEN delete `RegimeState`

`RegimeState` is hardcoded UNKNOWN but **it is not empty**. It carries real
measurements that other code reads. Delete the type without rerouting these and
you silently zero them — which is this project's entire failure class.

| Value | Real source, already in `ctx` |
|---|---|
| `.adx` | `trend.primary_adx` |
| `.atr_normalized` | `vol.atr_normalized` |
| `.bb_width_pct` | `vol.bb_width_pct` |
| `.trend_direction` | `trend.overall_direction` |
| `.structure_sequence` | `structure.structure_sequence` |
| `.sweep_recent` / `.sweep_age_bars` | `liq_map` |
| `.conviction` | **nothing — v4 has no conviction.** Drop the write |

`adx_at_entry` on every trade record comes through `.adx`. Verify it still
lands non-zero after the reroute, on a real tick, not by reading the code.

**Three sites are pinned in `PHASE_B` and are the hard ones:**
- `getattr(state, "current_regime", None)` — the gap measure wants the PRIOR
  TICK's trend direction. It needs somewhere to live that is not RegimeState.
- `regime=getattr(_r, "primary_regime", None)` — passed into `chain_snapshot`.
- `else (regime.primary_regime if regime else None)` — passed into
  `position_manager`.

### B2 — `analysis/trade_readiness.py` (8 sites, whole file exempted)

**LOG-ONLY — main.py's own doctrine says it "Gates NOTHING".** But its label
comparisons take the else branch every tick, so the graded readiness R it
journals is **silently wrong**. Real defect, observability severity. Rebuild its
conditions on measured structure or delete the label arms.

### B3 — Persistence. **THIS ONE IS THE OPERATOR'S CALL, NOT YOURS.**

- `database/trade_logger.py`: `trades.regime`, `trades.regime_conviction`,
  and the whole `regime_log` TABLE
- `analysis/signal_journal.py`: `regime_ctx()` helper, ~6 call sites in main
- `analysis/chain_snapshot.py`: the `"regime"` field
- `warehouse/s3_push.py`: `regime_log` as a pushed stream
- `eod_summary.py`, `query.py`, `status.py`: read them for display

Dropping a column rewrites history. Keeping it means the word survives in every
trade row and in S3 forever. **Present the options; do not pick one.** A
reasonable middle — stop writing, leave the columns for existing rows, drop
`regime_log` from the S3 stream list since it can never gain another row — but
that is a recommendation to make, not a decision to take.

⚠️ Phase A already changed one write: `main.py` used to stamp
`regime="RANGING"` on every non-TCS trade. **A label nothing measured, on every
row.** It now writes `""`. If B3 keeps the column, that is the honest value.

### B4 — `vix_regime` is NOT the artifact. RENAME, do not purge.

`data/macro_data.py` is exempted with a stated reason. `macro.vix_regime` ∈
{LOW, NORMAL, ELEVATED, CRISIS} is a **live VIX-band measurement computed from
the VIX itself**. It works. `risk/setup_scorer.py` branches on it and
**`SessionGuard`'s VIX-crisis lockout reads it** — deleting it deletes a live
risk rule.

It only carries the poisoned word. Suggested `vix_band`. Removing that exemption
from the checker is the last step of the rename.

---

## THINGS THAT WILL BITE YOU

⚠️ **A CHECK WRITTEN FROM THE IMPLEMENTATION'S ASSUMPTION CANNOT FALSIFY IT.**
Earlier the same day, `test_candle_routing.py` asserted an inverted `tho` table
and certified a live bug green for six days. Separately, `check_no_regime` was
scoped to `strategy/` — the right rule aimed at the wrong files — which is why
the fleet-stopping gate in `main.py` went unseen. When you write a check, plant
the bug it should catch and watch it go red.

⚠️ **THE CHECKER MISSED THE MOST IMPORTANT LINE IN ITS FIRST DRAFT.**
`main.py`'s gate was written `getattr(regime, "primary_regime", None)` — a
dynamic read, invisible to an Attribute-node rule. If you add rules, ask what
spelling of the same idea you have not covered.

⚠️ **`import` IS NOT `execute`.** Three defects this month were invisible to
`import main`. Run the path.

⚠️ **A GUARD OUTLIVES THE THING IT GUARDED.** r55 (the QQQ crash loop) and r57
are the same lesson at different scales: deleting a feature without deleting its
validation leaves a live veto over a value nothing computes.

⚠️ **DO NOT INVENT A REPLACEMENT GATE.** Phase A deliberately put nothing in
place of the deleted vetoes. If you believe dispatch needs a precondition, say
so in the audit and let the operator decide. Substituting your own rule in the
spot that just cost a session is not a fix.

⚠️ **NEVER SHIP `docs/GENESIS.md` IN A TARBALL.** Append-only on the box.

---

## VERIFY LIKE THIS, NOT BY READING

- All eleven checks green: `check_imports check_gates check_no_regime
  check_condor_spec check_dispatch stress_entry_path check_exit_executes
  test_candle_routing check_feed_always_on check_configure_relaxed
  check_ext_polarity`, plus `gen_file_map.py --check`
- `python3 -c "import main"` with a hostile env
- **`adx_at_entry` non-zero on a real trade record after the reroute**
- The Phase B countdown empty

---

## STATE AS OF THIS HANDOFF

Landed today: r53 (feed gate), r54 (configure.sh), r55 (`_REGIME_ENGINE`
assert), r56 (`_is_ext_of` polarity — the whole intraday tape was being dropped
fleet-wide), r57 (this). **Next revision is r58.** day_trader_pro is at r199,
market_brief at r1 — separate sequences, never continue one into another.

Also open, not yours unless asked: plain `SYM` 1h received the EXTENDED tape and
`SYM_EXT` received RTH from v3.16 until r56 — treat 1h from that window as
suspect on both routes.
