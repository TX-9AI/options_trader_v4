# AUDIT HANDOFF — options_trader_v4

**For an adversarial reviewer. Written 2026-08-20 at HEAD.**
**Go hard. Assume everything below is wrong until you have made it prove
itself.**

---

## 0. The one thing to understand first

This repo exists because **v3's central premise was measured false.**
`tests/direction_skill.py`, 715 closed directional trades over 16 sessions: the
regime classifier picked the correct **side** on **44.9%**, 95% CI
**[41.3%, 48.6%]** — the interval sits entirely below a coin flip. Puts were
**34.2%**. The strategy most dependent on it lost **$5,872** across 660 trades.

What made money was regime-independent: `orb_trail_stop` 96% / 85 trades /
**+$30,696**, worst case **−$16**. What lost it was the floors and BOS:
`max_loss_floor` 76 trades / **−$28,179**, `bos_exit` 217 trades / **−$7,085**
carrying the single largest loss in the book.

**So the thesis under audit is:** *entries decided by structure, not by labels;
exits kept because they were measured; and every threshold traceable to a
number.*

⚠️ **THE FAILURE CLASS THIS PROJECT KEEPS FINDING IS NOT BAD CODE. IT IS
PLAUSIBLE SILENCE.** In every case something computed a value, used it, and
looked correct while being meaningless:
- `open_interest` — a declared field with **no producer**, 0 on every contract,
  so GEX fell to `oi_proxy = 1000 × gamma` and multiplied by gamma again.
  **GEX was a gamma-squared surface for the life of v3.** The "pin" always sat
  at spot, because gamma peaks there.
- `max_liq` — summed OI + volume, both constant across the sample, so "most
  liquid strike" silently resolved to "nearest the floor" for weeks.
- `vix_at_entry` — real default 0.0 on **58% of the book**; a separation probe
  read that as a measured value and reported "no separation."
- `peak_close` — the true excursion, tracked every tick to drive the trail, and
  **discarded at close**, so the book could not answer how fast a winner
  declared itself.
- `_leg_order_from_slope` — a helper with **no caller** for three weeks while
  the docs described it as live logic.
- A confluence gate requiring 2 factors, with 2 added **unconditionally** above
  it. **A gate that cannot refuse.**

**Hunt for the next one. That is the highest-value thing you can do here.**

---

## 1. What to attack, in priority order

### 1.1 Both entry modes — normal AND relaxed

Every strategy must be exercised **twice**: with `OT_RELAXED_ENTRY` off, and on
(with `OT_PAPER_TRADING=1`, which is required — a config default deliberately
does not satisfy it).

`strategy/relaxed.py` claims three properties. **Break them:**
1. **SELECTION gates loosen.** Verify each declared one actually does.
2. **FOUNDATIONAL and FEASIBILITY never loosen.** `tests/check_gates.py` reads
   the AST and refuses a `relaxed.widen()` on a non-SELECTION constant — **but
   the foundational conditions are tested INLINE with no constant at all**, so
   the checker cannot see them. Verify by hand that no relaxed path admits a
   sweep that never reclaimed, an ORB that never held its 50% TP, or a
   butterfly whose apex is off the pin.
3. **Paper only.** `is_live()` fails closed. Try to find a configuration where
   relaxed entries reach a live box.

⚠️ **AND CHECK THE TAG SURVIVES TO THE DATABASE.** `relaxed_entry=1` and the
`_relaxed` setup suffix are the only thing keeping a deliberately-junk
population separable. **If the tag is set on the signal and dropped before the
insert, six weeks from now somebody fits a threshold to a book half of which was
debug traffic.** Trace it end to end.

### 1.2 Every exit path

The exits are the measured winners and they are the least-changed code in the
repo — **which makes them the most likely place for a v3 assumption to have
survived a context that no longer holds.**

- **The 15%/25% split.** Leg 1 of a condor stops at 15% while unhedged, 25% once
  leg 2 fills. Verify the widening cannot happen before the fill.
- **The condor ladder: roll → invert → stop-and-page.** Rung 2 (invert to a
  butterfly) is **the operator's discretionary practice with NO measured
  sample** — v3 never did it. It is declared as such in `docs/TRADES.md`.
  Attack the arithmetic: `total_credit_collected >= tested_side_width` makes the
  tested side risk-free. **What happens when the buy-back costs more than the
  roll collects?** What if the chain gaps between the close and the open?
- **`condor_roll` v1.1** exists because a missing mark caused a **silent**
  refusal to roll. Verify every decline is now loud.
- **The 15:40 flatten ladder vs `VERTICAL_HOLD_TO_ET` 15:45.** Credit verticals
  are exempt; debits are not. Routing is by DERIVATION from persisted columns
  (`strategy`, `setup_type`) in `strategy/structure.py`, **never a flag** —
  because `is_trend_credit` was once written as a field with no column and
  **crash-looped NFLX every 15 seconds.** Verify an unknown structure fails
  closed to DIRECTIONAL.
- **No TP, no trail, no BOS on credit structures.** Measured: on 18 standalone
  legs a TP@25% turned −$242.77 into −$8.43; on 28 condor legs a TP was worse
  **at every level.** Verify nothing reintroduces one.
- **15:45–16:00 retry loop.** A failed close must page, not silently leave a
  position open overnight.

### 1.3 Ladders and ratchets — CONFIRM EVERY CLAIM

`execution/entry_ladder.py` claims three composed rules. **Each is a claim, not
a fact, until you have made it fail:**
1. **RATCHET** — the rung index only advances; a refused price never returns
   even if the market moves back through it. v3 recomputed every rung from the
   live quote each cycle and **re-offered refused prices.**
2. **REPRICE** — each attempt recomputes from the *current* mark.
3. **MARK FLOOR** — never post worse than mark; if the ratchet would, take mark.

Worked examples that must reproduce: bid 1.50 / ask 2.50, selling —
`0.05` increments → `2.25 2.20 2.15 2.10 2.05 2.00`;
`0.10` increments → `2.20 2.10 2.00`. **Granularity comes from the venue
increment, not a fraction list.**

⚠️ **AND THE INCREMENT SOURCE IS ITSELF SUSPECT.** `execution/tick_size.resolve`
prefers a venue rule, then proves penny-eligibility from the observed quote,
then falls back to `PENNY_CLASSES` — **whose own log calls it "the path that
should never price a live order."** How often does the fallback fire? An
unpostable limit is either rejected or **silently adjusted by the venue, which
is a fill at a price nobody chose with nothing in the logs to explain it.**

Also confirm: `CONDOR_RATCHET_BE_AT` / `_LOCK_AT` / `_LOCK_PCT` — are they
reachable, and do they do what their names say?

### 1.4 Management, restart and orphan handling

- **`report_orphaned_plan`** — `IronCondorStrategy._plan` is **process-local**.
  A restart orphans a live structure: legs open at the broker, no plan in
  memory. Verify the detection fires, pages, and that a leg is **never**
  cancelled by it.
- **`_condor_leg_open_without_plan`** — same fault from the other side.
- **`_seed_trail_from_record`** — a mid-trail restart must not forget the locked
  level. Verify the seed reconstructs it from persisted state.
- **Journal integrity.** `signal_journal` is the only record of why a trade did
  *not* happen. Verify every gate writes a disposition, and that a journal
  failure can never reach the trading loop **while still being visible** — a
  bare `except: pass` makes "deliberate" and "accidental" indistinguishable to
  an audit, which was `v-audibleabandon`'s whole finding.
- **Loud failures.** Hunt silent handlers. The swallow census found a Tier-1
  silent handler **the morning after it shipped.**

### 1.5 Crash loops and circular logic

- **Crash loops.** `is_trend_credit` crash-looped NFLX every 15 seconds by
  writing a field with no column. **Any write to a record must have a column and
  a migration entry.** New this revision: `relaxed_entry`, `mfe_premium`,
  `mfe_bars`, `mae_premium`, `mae_bars`. Verify all five exist in both the
  `CREATE TABLE` and the migration list, and that `log_exit` actually persists
  them — a parameter nothing passes is a column nothing fills.
- **Circular logic.** The runaway fires on ORB's state and **disarms the
  retest**; ORB `mark_triggered()` is called by both. Verify no path re-arms
  something the other just disarmed, and that a runaway can never fire twice on
  one range.
- **Dispatch mutual exclusion.** The chain is `if signal is None and ...`.
  Verify no two strategies can claim the same tick, and that the 11:30
  structure cutoff cannot be bypassed by a strategy absent from
  `_STRUCTURE_BY_NAME` — it should **fail closed to `long_debit`**.

---

## 2. Where I already know the ground is soft

Stated so you do not waste tokens rediscovering it:

- **`iron_condor_strategy.generate_signal` is a 2-statement stub.** That is not
  the interface the condor uses — it goes through `decide()` then a leg state
  machine. I called it "no actionable logic" earlier and **that was wrong**;
  verify which of us is right.
- **The GEX butterfly is PARKED** (`ENABLED=False`) and wired anyway, so its
  plumbing is audited now rather than on the day it unparks. Its thresholds are
  **stated priors, not measurements** — `PIN_CONC_MIN=0.25` has no sample behind
  it, and `GEX_PIN_CONCENTRATION=0.15` in `gex_data` was tuned against the
  gamma-squared surface and means nothing for real positioning.
- **`tests/tine_order_study.py` is n=15.** Suggestive, not settled. An earlier
  version of it **fabricated an 81% result** by extrapolating a 60-bar slope
  across 330 bars; the tell was `breached=100%` on **both** arms. Do not quote
  the old number if you find it in git history.
- **`tests/fork_respect_study.py` uses a regression channel, not
  `build_fork_contained`.** Its result — a rail RESPECTED on 5% of 738 sessions,
  broken on 54% — is why the condor is now a nice-to-have. **The real fork has
  not been measured** and that is owed work.
- **`tests/orb_bleed_study.py` joined 191/191.** An earlier version silently
  scanned from the session open when a timestamp format disagreed, producing
  "1.00% excursion at bar 0." It now names every drop and refuses below 50%.
- **`config.py` is ~800 lines of constants.** Many were tuned for v3 conditions
  that no longer hold. Any constant with no traceable measurement is fair game.

---

## 3. What has already been checked (so you can attack the checkers instead)

Six standing checks, all plain scripts with exit codes — **deliberately not
pytest, because the first version broke the land command on a box whose venv had
no pytest, and a red that means "environment" teaches an operator to ignore
reds.**

| check | what it asserts |
|---|---|
| `check_imports` | every runtime module imports |
| `check_gates` | every strategy declares GATES; no `relaxed.widen()` on a non-SELECTION constant |
| `check_no_regime` | no strategy decides on a regime label |
| `check_condor_spec` | the condor's code matches `docs/TRADES.md` §5 |
| `check_dispatch` | order, scope, and that each `generate_signal` **executes** |
| `stress_entry_path` | 119 hostile-input cases |

⚠️ **ATTACK THESE FIRST. A checker that cannot fail is worse than none**, and I
have shipped two: one asserted that the *words* "FOUNDATIONAL/SELECTION/
FEASIBILITY" appeared in a docstring — proving somebody wrote the right words,
not that the code respects them — and one ended in `or True`. Both were caught
and replaced. **Assume a third is still in there.**

⚠️ AND `check_gates` **skipped any strategy that did not import `relaxed`** —
so ORB, the one strategy with a positive record, was invisible to it by
omission. Fixed. **Look for the same shape elsewhere: an exemption that is the
default for anything new.**

---

## 4. The stress test found 18 bugs an hour ago. Here is the pattern.

`tests/stress_entry_path.py`, first run: **97 passed, 18 failed.**

**The worst: a NaN ATR INVERTED the feasibility veto.** Every comparison against
NaN is False, so `if atr < FLOOR: return None` **does not refuse** —
`target_delta(nan)` returned a strike, admitting trades into exactly the tape
where **0 of 5,517 measured bars** reached the required move. The same bug sat
in the sweep's ATR ceiling. **I had written a comment warning about this failure
directly above the function that had it.**

Four more of the same family: NaN, −inf and negative prices fired signals,
because `price >= pool` and `price <= pool` are **both False** for NaN so both
side-checks passed it through; `math.floor(NaN)` raised inside `pierced_strike`
where `not nan` had read as a present guard; and a NaN mark became the MFE peak,
since the first call has no incumbent to compare against.

**All fixed via `utils.math_utils.safe_float`. Verify the guard is applied
EVERYWHERE it is needed, not just where the stress test happened to look** —
the test proves the cases it covers, and its coverage is my judgement, which is
the thing under audit.

⚠️ **AND FINITE IS NOT SANE.** `1e12` passes every type guard and is an absurd
claim about the tape. Range checks and type checks are different defences and
both are needed.

---

## 5. Rules of engagement

- **Report absence as absence.** If a thing cannot be measured, say so. This
  project's most expensive errors came from a null and a missing measurement
  looking identical.
- **A finding needs a mechanism**, not a suspicion. "This looks wrong" costs a
  day; "this is wrong because X is called before Y is assigned, at line N" is
  actionable.
- **Prefer executing to reading.** Three defects this week were invisible to
  `import main` and to review, and were caught by running the path.
- **Nothing is sacred, including the exits.** They are the measured winners, but
  they were measured under v3's entries. A stop calibrated for a complete
  structure is being applied to a single leg somewhere; find it.
- **`docs/GENESIS.md` is the revision-by-revision record with the corrections
  kept.** Six of the first twenty-five revisions exist because an earlier one
  was wrong, and **in every case the measuring instrument failed before the code
  did.** Read it — the corrections tell you where I am weakest.
