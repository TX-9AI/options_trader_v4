"""
strategy/sweep_credit_spread.py  v5.3
v5.3  2026-09-04  r241 — 🔴 THE AGE GATE IS REMOVED, NOT RAISED.
      Operator, 2026-09-04: *"I don't give a rat's ass how old the level is,
      it's still a level. Why are we still measuring the age of them?"* Because
      I only half-shipped his 2026-08-11 ruling — SWP.5 said LIVENESS REPLACES
      THE CLOCK, r230 found it had never reached the code, and I raised the
      ceiling 6 → 48 instead of deleting the gate. My call, not his.
      🔑 AGE MEASURES THE RAID, NOT THE LEVEL. A level swept at 09:45 that has
      held since is the SAME LEVEL at 13:00, arguably better for having held
      longer — and levels are swept all day; the morning's is not the only one
      on the board.
      🔴 MEASURED FLEET-WIDE 08-31..09-04: `age` failed 46,791 of 61,641 (76%)
      and on 333 ticks — 26% of every tick that was ONE gate short — it was the
      ONLY thing refusing. Complete setups, declined for being old.
      ⚠️ `invalidated` ALREADY ANSWERS THIS CORRECTLY: has price ACCEPTED back
      through the level. It fails 73%, a market fact rather than a defect.
      `age` was a second, worse proxy for a question that gate settles — two
      rules for one thing, §35's rot.
      ⚠️ THE MEASUREMENT SURVIVES. `sig.sweep_age_bars` still carries it to the
      row: knowing how old a level was is useful for FITTING, deciding with it
      is what was ruled out.
      ⚠️ AND UNMEASURABLE IS NOT OLD. `bars_ago` absent yields the 999 sentinel
      and refuses under its own name — a data fault, not a staleness judgement,
      and admitting it silently would be absent-is-not-zero again.
v5.2  2026-09-03  r234 — GATED ON THE STOP BASIS, AND THE
      SURVIVABILITY DENOMINATOR WAS 4.15x WRONG. This computed
      `credit * MAX_LOSS_PCT` — 15% OF CREDIT, the inverted rule r155 deleted —
      and fed it to `stop_survivable`, while `exit_engine:1818` fires at 15%
      OF RISK. 0.1455 against 0.6045 on the measured median, and the
      forensics' own "risk-anchored room: median $0.605" matches the ENGINE.
      Survivability was judged against a stop four times tighter than the one
      that exists. Both now read `criteria.stop_distance`. `r_expiry` rides
      record-only and the narration names BOTH bases (r219's lesson: printing
      one and labelling it the other is how it stays invisible).
v5.1  2026-09-03  r233 — 🔴 THE STRIKE MUST CLEAR THE TESTED RANGE, AND THE
      NEAREST LIVE LEVEL WINS. Operator, 2026-09-03: *"the strike cannot sit
      at any level that is part of the testing range... I don't want to get
      stopped out by another retest. It has to be just beyond that, if only a
      little bit"*, and *"the level in question needs to be the closest to the
      current price."*
      🔴 THE HOLE r107 DID NOT SEE, AND ITS OWN DOCSTRING STATES BOTH SIDES OF
      IT three paragraphs apart: *"it sits FURTHER from spot than anything
      price reached"* (the intent) and *"nearest is 7635 — the strike price
      traded THROUGH"* (the deep-pierce case, documented without noticing the
      contradiction). PROVEN AT bd6f25e on the header's own example: pool
      7639.01, wick 7633 gave 7635, which sits BETWEEN them. The candidate
      bound was the POOL when it needed to be the WICK EXTREME; the intent was
      right all along.
      ⚠️ AND IT IS THE NEAREST OF WHAT IS BEYOND — `min(cand)` / `max(cand)`,
      never `min(abs(k - sweep_price))`, which is precisely what let an inside
      strike win. "Just beyond, if only a little bit."
      ⚠️ THE POOL BOUND IS KEPT AND IS NOW IMPLIED — a wick is beyond its pool
      by definition — because it DOCUMENTS the invariant. P4 pins that it never
      binds, so it is known inert rather than assumed so.
      🔑 SELECTION MOVES FROM RECENCY TO DISTANCE. Both branches picked the
      freshest raid — this one by `min(bars_ago)`, the fallback by the map's
      `recent_sweep` — so a level three points out beat one 0.6 points out if
      it landed a bar sooner, and selling the cusp of a distant level is still
      distant. Freshness survives as the TIE-BREAK, which is the only question
      distance cannot answer. `level_rank` is EXTRACTED to module level so the
      checker drives it and not a copy (C.23).
      ⚠️ THE FALLBACK IS NO LONGER `recent_sweep`: leaving it would have put
      leg two on distance and the primary entry on recency — one rule with two
      answers. It survives only when NO candidate carries a usable pool price,
      and says so at INFO.
      ⚠️ THIS RETIRES THE CROSS-TIMEFRAME UNIT BUG AT THIS SITE rather than
      fixing it; SWEEP.6 stays OPEN for the other selector and the mapper.
      ⚠️ MEASURED SCOPE, STATED UP FRONT: `pierce_depth` ran a 0.0032 median
      against a 0.5685 max, so shallow pierces dominate and this re-prices only
      the deep tail. `pierce_pts`, `level_dist_pts` and `level_dist_pct` ride
      the plan RECORD-ONLY so how often it fires is a query, not an argument.
      ⚠️ AND IT DOES NOT FIX THE MEASURED LOSSES. Panel 1 of the 08-25..09-03
      forensics: price never reached the strike on 22 of 22, and the stops were
      mark-driven (r219). A real hole, correctly closed, on a failure mode this
      sample never showed.
v5.0  2026-09-03  r231 — 🔴 `or 999` MADE THE FRESHEST SWEEP THE STALEST.
      `bars_ago` is an int field defaulting to 0 and SWP.10 counts it from the
      RECLAIM bar, so a sweep that reclaimed on the CURRENT bar is 0 — and
      `0 or 999` is 999. Twenty-six lines above, the selection loop takes
      `min(bars_ago)`: it hunts the freshest sweep on the board and this line
      converted exactly that winner into the stale sentinel and refused it.
      One function contradicting itself, invisibly — 999 reads as missing data
      rather than as the best setup there was. Absent stays 999; ZERO stays 0.
      Also: the geometry call now passes `price_now`, so a pool price has
      already traversed is invalidated rather than merely failing a soft
      condition. `side_of_pool` is UNTOUCHED and now tests the same fact
      twice — recorded as SWEEP.7, not folded in unruled.
v4.9  2026-09-03  r230 — 🔴 SWP.5 WAS RULED ON 2026-08-11 AND NEVER REACHED
      THIS FILE. Its ruling: "LIVENESS REPLACES THE CLOCK", measured over 90
      symbol-days — of the stale sweeps the age gate refused, 32.9% still had
      a LIVE thesis (price had never accepted back through the raided level),
      ~9.5 valid setups discarded per symbol-day on a clock. It set a
      deliberate 48-bar backstop and landed `SWEEP_STALE_HARD_BARS` in
      config. This file never read it. It read `SWEEP_CS_MAX_AGE_BARS`, a
      name defined NOWHERE in the tree, so the ceiling was the getattr
      DEFAULT of 6 — a quarter of the old constant and an eighth of the ruled
      one — for three weeks.
      ⚠️ THE OPERATIVE CEILING WAS 18, NOT 6, AND THE DISTINCTION MATTERS.
      The whole fleet is running RELAXED by operator decision (2026-09-03,
      to observe tick-by-tick progression), so `widen(6, 3.0)` gave 18. Ages
      of 33-48 refused ANYWAY. Recording 6 alone would have understated the
      gate and left the next reader unable to reproduce the refusal.
      🔑 NET EFFECT ON A RELAXED FLEET: 18 -> 48, a LOOSENING of 2.7x even
      though relaxed no longer applies here. The alternative (keeping x3 on
      48) gives 144 bars against a 78-bar RTH session - unreachable, which
      is not a backstop at all.
      🔑 MEASURED 2026-09-03 from plan_check: `age` FAILED 761/761 on QQQ
      (33-48 bars) and 934/934 on SPX. Every QQQ evaluation clears at 48.
      ⚠️ OPERATOR RULING 2026-09-03: eliminate `relaxed` entirely from the age
      question. The widen call is GONE, not pinned to factor 1.0: the pinned
      idiom `check_gates` recognises (r196) is implemented for `window()`
      ONLY and would have gone red on a pinned `widen()`. Removing the call
      and declaring MAX_AGE_BARS FOUNDATIONAL is STRONGER — the checker now
      refuses any future relax call on it rather than tolerating a pinned
      one. Matches r208, which removed relaxed from the butterfly outright.
      ⚠️ THE LIVENESS TEST IS `invalidated`, ALREADY WIRED AND ALREADY
      CORRECT — it fired 934/934 on SPX today. Age stops being the primary
      filter and becomes the backstop SWP.5 intended. Nothing else moves;
      the sweep's other dials stay loose per the r208 ruling.
v4.8  2026-09-02  r219 — 🔴 THE ENTRY AND THE MARK WERE ON DIFFERENT SIDES OF THE QUOTE.
      `search_wing` priced the credit as short.BID - long.ASK and that number
      became `sig.entry_premium` — the position's entry of record — while
      `position_manager._fetch_current_premium` marks a credit vertical at
      short.MARK - long.MARK. The gap is BOTH HALF-SPREADS, present the
      instant the position opens, and for a credit vertical a higher mark is a
      LOSS. Measured on the fleet's shape: judged $0.37, booked $0.97, gap
      $0.60 — against a lone stop carrying 60.5 cents of room. The position
      was born at its stop.
      🔑 SWEEP FORENSICS 2026-08-25..09-02 SAYS THE UNDERLYING NEVER DID IT:
      38 of 41 stopped, price NEVER reached the short strike on any of 22
      measurable trades, and moved 0.63 points toward it — implying a spread
      delta of 0.96, which a 5-wide cannot carry.
      ⚠️ OPERATOR RULING 2026-09-02: "I have a ladder for live offers, all
      paper needs to fill at mark, period." The MARK is booked. The BID/ASK
      credit is kept for the R hurdle — deciding on the conservative number
      and booking the mark refuses trades that only clear R when priced
      optimistically, so the error runs in the safe direction.
      ⚠️ AND THE OLD BEHAVIOUR HAD A PASSING TEST: check_plan_prepares S2
      asserted net_credit == 1.30, the bid/ask figure, so the suite certified
      the mismatch. Re-derived to 1.33.
v4.7  2026-08-27  r163 — A FORK TINE IS A MOVING LEVEL THIS STRATEGY MAY USE,
      ON A TOUCH. Operator, 2026-08-27: *"it's basically a moving level that
      sweep is allowed to use, but with a touch, not a reject. The plan would
      still need to select a strike beyond the move that caused the touch."*
      And: *"it's allowed to be the 1st leg of a condor too, but again as a
      touch not identical to sweep which requires rejection."*
      The mapper (liquidity_mapper v4.2) publishes each tine as a moving
      named pool and emits a TOUCH event shaped like a sweep (born ready,
      `touch=True`, `sweep_price` = the extreme of the touching move). This
      plan treats it as any other sweep EXCEPT: (1) under the condor's
      AUTHORIZATION (leg two) a touch is NEVER selected — leg two requires a
      rejection at the site; (2) the spent-level lock is keyed by NAME for a
      moving level, since its price drifts every bar; (3) the signal's
      `condor_trigger_source` is `{tf}_fork`, so a tine-touch leg one is
      classed as a fork under Rule 4. The daily-fork strategy is retired —
      its whole job is now the mapper's publication plus this plan.
v4.6  2026-08-27  r160 — THE PLAN PREPARES, THE STRATEGY EXECUTES WITH THE
      PLAN'S VARIABLES. Operator, 2026-08-27, read back and confirmed: the
      plan "evaluates the current tick what would need to be true on the
      next tick for the active strategies to execute — strike selection,
      wing width, stop placement, minimum R"; the strategy declares its
      conditions and executes. `prepare()` is the plan: in the slot, every
      tick, it picks the sweep this spec would trade (the freshest of the
      AUTHORIZED side when the condor narrows it, else the map's most
      recent), evaluates each declared CONDITION with its current reading,
      SELECTS the short beyond the sweep, the wing to R_FLOOR (search_wing),
      the bid/ask credit, the stop and its survivability, and writes the
      row: DORMANT outside the slot · NO PLAN naming a missing input ·
      DECLINE on a STRUCTURAL fault (spent, geometry, no wing clears R, no
      credit, stop inside the spread) · HOLD "PREPARED — <trade>. Waiting
      on: <conditions>" · and on all-true the strategy `generate_signal()`
      executes THAT trade. The strategy no longer touches the chain.
      `required_level` is gone — an authorization narrows the SIDE, it never
      hands this strategy a level (operator: the condor selects nothing).
v4.5  2026-08-27  r154-r158 (RECORDED RETROACTIVELY in r160 — 254 lines
      changed with no title bump and no entry): the spent-level lock
      (mark_spent/is_spent), stop_survivable before entry, the wing searched
      to R_FLOOR via credit_vertical.search_wing (R no longer muted for credit
      spreads), `_sweep_at_level` and the required_side/required_level
      inputs from the condor's permission.
v4.4  2026-08-26  r146 — THE PLAN IS WIRED. Six `_gate()` rungs and fifteen
      bare `return None`s (window, ATR, boundary side, chain, wing, credit …)
      all go through `self.planner` (strategy/plan.py) and write a DECLINE row
      naming the gate; `_gate()` is retained as a thin alias into the plan's
      edge-triggered reporter so nothing that called it breaks. NEW: the
      reclaimed pool is checked against the SHARED SESSION MAP
      (analysis/session_map.py) — a ceiling below the 5-minute opening range,
      or a floor above it, is INVALIDATED BY GEOMETRY per the operator's
      2026-08-25 ruling, before any strike is priced. `orb_high`/`orb_low`
      are new optional kwargs; absent, geometry records n/a and the spec
      proceeds. The what-if is priced off the REAL spread (short at the first
      strike beyond the sweep, wing at WING_WIDTH, credit from bid-ask):
      R = credit / (width - credit). The R hurdle is consulted: STRICT refuses
      below the floor, RELAXED records and proceeds.
v4.3  2026-08-24  r107 THE SHORT STRIKE IS THE FIRST STRIKE BEYOND THE SWEEP
      EXTREME — pierced if there is one, the next one out if there is not, never
      one inside. Operator, 2026-08-24: "It swept. That's legitimately a sweep.
      Sell the 7635." The old rule required a strike to have been TRADED
      THROUGH, which collides with §2's preference for a SHALLOW pierce and
      silently disabled the sweep on the seven 5-wide symbols. Strikes now come
      from the LIVE CHAIN, not STRIKE_INCREMENT: SPX 0DTE is 5-wide near the
      money and 25-wide in the tails, so one constant cannot be right.
v4.2  2026-08-24  r100 — the short-strike anchor no longer falls back to the
      POOL when the pierce cleared no strike. The pool is a price level, so the
      anchor could not resolve against the chain and every SPX fire died at
      "no priced put contract at the pierced strike 7639.01" — a strike that
      does not exist. pierced_strike's own contract says None means there is
      nothing to sell; now that is what happens, with its own log line.
v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

A named pool was swept and rejected. Sell the boundary it just became.

v4.0  2026-08-19  Built at the OTV4 split. The second v4 entry rule.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

════════════════════════════════════════════════════════════════════════════
THE STRUCTURE, AND WHY IT IS A CREDIT SPREAD AND NOT A LONG CONTRACT
════════════════════════════════════════════════════════════════════════════
    sweep UP into a pool, rejected   -> that pool is now a CEILING
                                     -> CALL credit spread, short at/beyond it
                                     -> price must stay BELOW the ceiling
    sweep DOWN into a pool, rejected -> that pool is now a FLOOR
                                     -> PUT credit spread, short at/beyond it
                                     -> price must stay ABOVE the floor

**The sweep direction decides which kind of boundary the pool became**, and the
spread follows from that. `LiquiditySweep.kind` already records it -
`high_sweep` means highs were taken and rejected DOWN, so the pool is a ceiling.
Nothing needs inferring.

⚠️ WHY CREDIT AND NOT LONG - THIS IS THE POINT OF THE WHOLE STRUCTURE.
A long reversal contract needs price to TRAVEL. `tests/entry_profile.py`
measured that **155 of 190 directionally-CORRECT ContinuationStrategy entries -
82% - never reached +25% MFE.** The read was right and the position did not pay.
`tests/chain_feasibility.py` explains it from the other side: a 0.30-0.60 delta
0DTE contract needs a **0.90% underlying move** to pay +25% after the round-trip
spread, and the tape delivers that in a specified direction on **22%** of
90-bar windows.

**A credit spread does not need magnitude. It needs the level to hold.** That is
a far weaker ask, and the tape agrees: the base rate for a 0.5% move in 90
minutes is only **24-35%**, so roughly two thirds of windows stay put.
**The swept pool is the natural short strike because it is the level that just
FAILED to hold price** - it rejected once, in evidence, not in forecast.

════════════════════════════════════════════════════════════════════════════
WHY v3's SWEEP NEVER FIRED, AND WHAT WAS FIXED
════════════════════════════════════════════════════════════════════════════
`tests/sweep_term_census.py`, 269,027 named-pool rows across 27 sessions:
  · **95.9% HARD-VETOED to 0.000** before scoring - 67% of those by
    `veto_accept`, the `closes_beyond >= 2` rule. Of 25,792 vetoed ticks
    post-08-11, **100% were RECLAIMED and 0% were genuine acceptance**: the veto
    window and the confirmation window were the SAME WINDOW, so the sweep bar's
    own close counted as acceptance. SWP.11 fixed it.
  · Of the 4.1% that survived, `age_decay` median **0.062** - about **12 bars,
    ~60 MINUTES** - while `trend_opp` sat at 1.000. Age was the sole binding
    damper, and it counted from the SWEEP bar rather than the RECLAIM, charging
    the signal for confirmation latency it could not act inside. SWP.10 fixed it.
  · Median surviving score ~0.031 against a 0.05 dispatch floor: **the survivors
    did not clear their own gate.**

⚠️ THIS FILE READS NEITHER. No `age_decay`, no multiplicative damper chain, no
setup score. The sweep either reclaimed and is young, or it is not a setup.
v3's grammar - a product of two soft-necessaries and a weighted corroborator sum
- capped SWEEP at 0.171 out of 1.0 while TRENDING pinned at 1.00, so it could
never win an argmax regardless of evidence.

directional predictor in this data. This rule does not predict a direction; it
sells a boundary that has already rejected price once.

════════════════════════════════════════════════════════════════════════════
GATE CATEGORIES — required by WA §36. Only SELECTION is ever relaxed.
════════════════════════════════════════════════════════════════════════════
**FOUNDATIONAL — never relaxed. Relax one and this stops being the trade.**
  · the pool is NAMED. An unnamed swing high is not a liquidity pool; the name
    is what makes it a level other participants are watching.
  · it RECLAIMED - a bar CLOSED back inside. **A wick through a level is a
    touch, not a decision.** Without the reclaim there is no boundary, only a
    level price is currently through.
  · it is NOT INVALIDATED. Reclaimed-then-accepted-through is a BREAKOUT, and
    selling a boundary that has already given way is the worst version of this.
  · price is ALREADY on the profitable side. Otherwise the spread opens tested.

**SELECTION — relaxed, and each was measured on 2,169 sweep events.**
  · window 13:00-15:00  -> 09:45-15:30   (39% survival vs 26% before 10:30)
  · pierce ceiling 0.25% -> 0.75%        (33-34% survival vs 19-21% deeper)
  · max age 6 bars      -> 18 bars       (age is measured from the RECLAIM)

**FEASIBILITY — never relaxed.**
  · ATR <= 0.20%. Above 0.20% the tape produced a 0.5% move on **92% of 90-bar
    windows** - a boundary does not hold in that, so the trade cannot win no
    matter how clean the setup looks.
"""

import logging
import math
from typing import Optional

import config
from strategy import relaxed
from strategy import credit_vertical as cv     # r97 — shared spread math
from strategy.base_strategy import OptionsSignal as Signal
from strategy.criteria import (stop_survivable, R_FLOOR, R_FLOOR_STOP,
                              stop_distance as _stop_distance_of)
from strategy.plan import Plan, _n
from utils.math_utils import safe_float

logger = logging.getLogger(__name__)


def _gate(name: str, reason: str) -> None:
    """r73 — report this rung, edge-triggered. NEVER changes the verdict.

    v4.4 — kept as an alias for any caller outside this file; inside it the
    rungs now go through `PlanTick.refuse()`, which reports the same way AND
    writes the plan_check row the reporter never could.
    """
    try:
        from analysis.gate_report import get_gate_reporter
        from config import INSTRUMENT
        r = get_gate_reporter(INSTRUMENT)
        if r is not None:
            r.blocked("SweepCreditSpread", name, reason)
    except Exception:                                           # noqa: BLE001
        pass

# ⚠️ STATED PRIORS AWAITING MEASUREMENT. v3's sweep book is 34 trades - far too
# thin to fit anything - so these are reasoned, not calibrated, and are
# config-overridable. `tests/sweep_discriminator.py` is the tool that will
# replace them with numbers.
# 🔴 r230 — SWP.5's OWN CONSTANT, IMPORTED DIRECTLY. NOT `getattr` WITH A
# DEFAULT: a getattr default is exactly what let a name defined nowhere
# govern fifteen boxes silently. A missing constant must raise at import on
# the first box that pulls it, not fall back to a number nobody chose.
# 🔴 r241 — `MAX_AGE_BARS` IS GONE. Not raised, not pinned: REMOVED. r230
# raised it 6 -> 48 and that was the half-measure; the operator's 08-11 ruling
# was that liveness replaces the clock, and `invalidated` is the liveness test.
# ⚠️ WHAT REPLACES IT IS NOT A THRESHOLD. The 999 sentinel means `bars_ago`
# could not be read at all, which is a DATA fault and not a staleness one, so
# it refuses by its own name rather than through an age ceiling.
_AGE_UNMEASURABLE = 999
# ⚠️ WAS 0.002 (0.20%) - A PRE-MEASUREMENT GUESS THE DATA CONTRADICTS. Combined
# with the new 0.25% ceiling it left a 0.20-0.25% sliver and EXCLUDED the
# shallow bucket that measured BEST: <0.10% pierces survived on 33%, and
# 0.10-0.25% on 34%, both above the 30% base. The floor exists only to reject a
# level that was never really touched, so it belongs far lower.
MIN_REJECTION_PCT = getattr(config, "SWEEP_CS_MIN_REJECTION_PCT", 0.0002)

# ── MEASURED 2026-08-20, tests/sweep_discriminator.py ──────────────────────
# 2,169 PDH/PDL sweep-and-reclaim events across the banked tape, ONE outcome per
# sweep. Outcome = the boundary held to the bell AND was never breached far
# enough to have taken the 15% stop (adverse < 0.35% of the level).
#
#   BASE RATE, all sweeps:                    30% survived
#
#   BY TIME OF THE RECLAIM        n     survived   p50 adverse
#     before 10:30              927        26%        0.84%   below base
#     10:30 - 13:00             758        29%        0.58%   same as base
#     13:00 - 14:30             223        39%        0.30%   BEATS base
#     after 14:30               261        39%        0.32%   BEATS base
#
# **The afternoon nearly doubles survival and HALVES the adverse excursion.**
# Window moved from 10:00-15:00 to 13:00-15:00.
#
# ⚠️ THE `SESSION TIME REMAINING` TABLE IS THE SAME FINDING, NOT A SECOND ONE.
# "after 13:00" and "fewer than 150 bars left" select largely the same events;
# less session remaining means less time for the boundary to be tested. Treating
# them as independent confirmation would be double-counting one effect.
EARLIEST_ET = getattr(config, "SWEEP_CS_EARLIEST_ET", "13:00")
# 🔴 r98 (2026-08-24) — 15:00 WAS TOO LATE AND RELAXED MADE IT 15:30.
# Operator: "Close the window on sweep to 1400 also. That entry is way too
# late." A credit vertical opened at 15:00 has 45 minutes to the 15:45 hard
# close: it cannot collect the theta it exists to collect, and it is judged on
# a boundary test the session has no time to deliver. `relaxed.window` widened
# the late side to 15:30, which is worse still — 15:30 collides with the 15:40
# flatten ladder, so a relaxed sweep could open a position that is closed ten
# minutes later by the clock rather than by its thesis.
LATEST_ET = getattr(config, "SWEEP_CS_LATEST_ET", "14:00")

# ── AND A CEILING ON THE PIERCE DEPTH ──────────────────────────────────────
#   BY REJECTION DEPTH            n     survived   p50 adverse
#     shallow < 0.10%           746        33%        0.46%   BEATS base
#     0.10 - 0.25%              817        34%        0.53%   BEATS base
#     0.25 - 0.50%              368        21%        0.75%   below base
#     deep > 0.50%              238        19%        1.28%   below base
#
# ⚠️ THE MECHANISM IS IN THE ADVERSE COLUMN, and it is the opposite of the
# intuition that a big rejection is a strong rejection. A DEEP pierce means the
# level barely rejected at all - price was willing to go there, and it comes
# back: 1.28% median adverse against 0.46% for a shallow pierce. **Depth of
# pierce measures the level's WEAKNESS, not the strength of its defence.**
MAX_REJECTION_PCT = getattr(config, "SWEEP_CS_MAX_REJECTION_PCT", 0.0025)

# ⚠️ WHAT THIS DOES NOT ESTABLISH. The best cell is ~39-40% survival. A spread
# that wins when the boundary holds and loses 15% when it does not needs the
# CREDIT to exceed roughly 1.5x the loss to break even at that rate. **These are
# entry conditions, not a profitability finding** - that depends on credit
# received against the stop, which is a chain question and has not been asked.
# ⚠️ AND POOL TYPE DID NOTHING: PDH 32%, PDL 28%, both at base. The stated grade
# priors in level_grade.py get NO support from this measurement.
ATR_MAX_PCT = getattr(config, "SWEEP_CS_ATR_MAX_PCT", 0.20)

# ── EXITS: exactly two, and no others ──────────────────────────────────────
# Operator, 2026-08-20: *"The only 2 ways I want out of this trade is a 15% loss
# (thesis invalidated) or a session hard close."*
#   · 15% stop - the thesis is that the swept pool HOLDS as a boundary. A 15%
#     loss says it did not, and there is nothing further to wait for.
#   · 15:45 hard close - held to the bell, EXEMPT from the 15:40 flatten
#     ladder like every credit vertical. `strategy/structure.py` routes it there
#     by DERIVING from persisted columns (strategy / setup_type), never a flag:
#     `is_trend_credit` was written as a field with NO COLUMN and crash-looped
#     NFLX every 15 seconds.
# ⚠️ NO TRAIL AND NO PROFIT TARGET. Measured: v3's condor backtest found a TP
# was WORSE AT EVERY LEVEL on 28 condor legs, and on 18 standalone legs TP@25%
# turned -$242.77 into -$8.43. A credit vertical is EARNING from decay; closing
# it early buys back the theta it was opened to collect.
MAX_LOSS_PCT = getattr(config, "SWEEP_CS_MAX_LOSS_PCT", 0.15)
WING_WIDTH = getattr(config, "SWEEP_CS_WING_WIDTH", 5.0)

# ── GATE CATEGORIES AS DATA (WA §36) ───────────────────────────────────────
# ⚠️ CHECKED BY `tests/check_gates.py`, WHICH READS THE CODE. The prose block in
# the header explains WHY each gate is what it is; this dict is what makes the
# rule enforceable - the checker refuses any `relaxed.widen()` or
# `relaxed.window()` call on a constant not marked SELECTION.
GATES = {
    # SELECTION - measured preferences. A looser one gives a WORSE example of
    # the same trade, which is what a debug session wants.
    "EARLIEST_ET":        "SELECTION",
    "LATEST_ET":          "SELECTION",
    "MAX_REJECTION_PCT":  "SELECTION",
    "MIN_REJECTION_PCT":  "SELECTION",
    # FOUNDATIONAL - r230, operator ruling 2026-09-03. SWP.5's own words:
    # "a level that still holds at 5 hours is a DIFFERENT trade from a fresh
    # raid" - which is the §36 definition of foundational, not selection. It
    # has NO relax call at all now, so the checker refuses any future one.
    # FEASIBILITY - above 0.20% ATR the tape produced a 0.5% move on 92% of
    # 90-bar windows. A boundary does not hold in that.
    "ATR_MAX_PCT":        "FEASIBILITY",
    # FOUNDATIONAL conditions are not constants - they are the named pool, the
    # reclaim, the non-invalidation and price being on the profitable side, all
    # tested inline. **They have no knob to relax, which is the safest form a
    # foundational gate can take.**
}


def level_rank(sw, price_now: float):
    """Sort key for choosing WHICH swept level to prepare, or None if unusable.

    🔴 r233 — DISTANCE FROM SPOT FIRST, FRESHNESS ONLY AS THE TIE-BREAK.
    Operator, 2026-09-03: *"the level in question needs to be the closest to
    the current price."* Both selection branches used recency, so a raid on a
    level three points out beat one 0.6 points out if it landed a bar sooner —
    and selling the cusp of a distant level is still distant.

    ⚠️ EXTRACTED TO MODULE LEVEL SO THE CHECKER DRIVES THIS AND NOT A COPY.
    As a closure inside `prepare()` it was unimportable, and a test that
    re-implements the ranking it pins tests itself — C.23, the r181 sizing
    checker that stayed green for two days doing exactly that.

    ⚠️ None IS UNUSABLE, NEVER A LARGE DISTANCE. A sweep with no pool price
    must drop out of the ranking rather than sort last, or a missing field
    becomes a far-away level and the caller cannot tell the two apart.
    """
    try:
        _p = float(getattr(sw, "pool_price", 0.0) or 0.0)
        _n = float(price_now or 0.0)
    except (TypeError, ValueError):
        return None
    if _p <= 0 or _n <= 0:
        return None
    return (abs(_p - _n), int(getattr(sw, "bars_ago", 999) or 0))


def strike_beyond_sweep(sweep_price: float, pool_price: float, ceiling: bool,
                        contracts=None, increment: float = 0.0) -> Optional[float]:
    """🔴 r107 — THE FIRST STRIKE BEYOND THE SWEEP EXTREME. Operator's ruling,
    2026-08-24: "It swept. That's legitimately a sweep. Sell the 7635."

    ⚠️ WHY THE OLD RULE DECLINED A GOOD TRADE. `pierced_strike` returned the
    nearest strike price actually TRADED THROUGH, and None when the pierce
    cleared none — reasonable prose that collided with the selection spec on
    every wide-strike symbol. SPX 2026-08-24: NY Low 7639.01, price traded to
    7638.17 and closed back inside — a valid sweep of a named pool by 0.84 pts.
    The strikes below are 7635 and 7630; price never reached either, so no
    strike was pierced and a fully-qualified setup was declined. 608 fires died
    that way on one box in one session.
    ⚠️ AND THE TWO RULES PULL OPPOSITE WAYS. §2 PREFERS a shallow pierce —
    ceiling 0.25%, and "a deep pierce means a WEAK level, not a strong
    rejection" (1.28% median adverse vs 0.46%). A strike rule that requires a
    DEEP pierce therefore refuses exactly the sweeps the selection rule likes,
    and it refuses them only on 5-wide symbols: seven of the fifteen boxes. A
    selection effect invisible as "no setups".
    ⚠️ THE OPERATOR'S RULE KEEPS THE INTENT AND DROPS THE PRECONDITION. The
    short strike is the first strike BEYOND the sweep extreme — the pierced one
    when the sweep cleared it, the next one out when it did not. Either way it
    sits FURTHER from spot than anything price reached, so the position is
    threatened only by price going somewhere it has not been. Never a strike
    INSIDE the pierce: that is a level that already failed, and selling it is
    the "worst version of this" §2 warns about.

    ⚠️ STRIKES COME FROM THE LIVE CHAIN, NOT FROM A CONSTANT. `STRIKE_INCREMENT`
    is one number per symbol from a hardcoded map; SPX 0DTE is 5-wide near the
    money and 25-wide in the tails, so no single number is right everywhere —
    and FRC.2's own notes call that class of list "unverified — a broker/OCC
    fact, not derivable here". The chain is the fact. `increment` remains as the
    fallback for a caller with no chain.

    Returns None only when there is genuinely no strike beyond the sweep — an
    extreme past the end of the chain, which is a missing chain, not a trade.
    """
    sweep_price = safe_float(sweep_price)
    pool_price = safe_float(pool_price)
    if not sweep_price or not pool_price:
        return None

    ks = []
    for c in (contracts or []):
        try:
            k = float(getattr(c, "strike", 0.0) or 0.0)
            if k > 0:
                ks.append(k)
        except (TypeError, ValueError):
            continue
    # THE RULE, ONE LINE: among strikes AT OR BEYOND THE POOL, take the one
    # NEAREST THE SWEEP EXTREME.
    # ⚠️ IT UNIFIES BOTH CASES AND CHANGES ONLY THE ONE THE OPERATOR RULED ON.
    # Deep pierce, pool 7639.01, extreme 7633: strikes beyond the pool are
    # 7635, 7630, ...; nearest to 7633 is 7635 — the strike price traded
    # THROUGH, which is the original rule, unchanged. Shallow pierce, extreme
    # 7638.17: nearest is still 7635, which is now the first strike BEYOND
    # rather than a decline. One expression, both readings.
    # ⚠️ "AT OR BEYOND THE POOL" IS THE GUARD THAT MATTERS. Without it the
    # nearest strike to a shallow extreme could be 7640 — INSIDE the pool, on
    # the spot side of a boundary price never broke. Selling that is selling a
    # level the sweep did not establish.
    def _pick(strikes):
        if ceiling:
            # \U0001f534 r233 - AT OR BEYOND THE **WICK EXTREME**, NOT MERELY THE POOL.
            # Operator, 2026-09-03: *"the strike cannot sit at any level that is
            # part of the testing range. I do not want to get stopped out by
            # another retest. It has to be just beyond that, if only a little
            # bit."*
            # \u26a0\ufe0f THIS CLOSES A HOLE r107 DID NOT SEE, and its own docstring
            # states BOTH sides of it three paragraphs apart: "it sits FURTHER
            # from spot than anything price reached" (the intent) and "nearest
            # is 7635 - the strike price traded THROUGH" (the deep-pierce case).
            # PROVEN AT bd6f25e on the header's own two examples: pool 7639.01,
            # shallow wick 7638.17 -> 7635, beyond the wick, correct; DEEP wick
            # 7633.00 -> 7635, which sits BETWEEN the wick and the pool. Price
            # traded clean through 7635 on its way to 7633, so a second test of
            # the same size takes the position out. The intent was right; the
            # candidate bound was the pool when it needed to be the extreme.
            # \u26a0\ufe0f THE POOL BOUND IS KEPT AND IS NOW IMPLIED - a wick is beyond
            # its pool by definition, so this can only ever narrow the set. It
            # stays because it DOCUMENTS the invariant, and check_strike_beyond
            # P3 pins that it never binds; a guard proven inert is different
            # from one deleted on the assumption that it is.
            cand = [k for k in strikes
                    if k >= pool_price - 1e-9 and k >= sweep_price - 1e-9]
        else:
            cand = [k for k in strikes
                    if k <= pool_price + 1e-9 and k <= sweep_price + 1e-9]
        if not cand:
            return None
        # "just beyond, if only a little bit" - the NEAREST of what is beyond,
        # never the nearest in absolute terms, which is what let an inside
        # strike win on a deep pierce.
        best = min(cand) if ceiling else max(cand)
        # ⚠️ A TRUNCATED CHAIN MUST NOT BECOME A WILD STRIKE. "Nearest" always
        # returns something; if the extreme lies past the end of the chain the
        # nearest strike can be hundreds of points away, and selling it would be
        # a trade nobody described. Bound it to a few grid steps of the extreme
        # and decline beyond that — a chain that does not reach the tape is a
        # DATA problem and says so.
        gaps = [b - a for a, b in zip(cand, cand[1:])] if len(cand) > 1 else []
        step = min(gaps) if gaps else (safe_float(increment) or 0.0)
        if step and abs(best - sweep_price) > 3.0 * step:
            logger.warning(
                "[sweep_cs] nearest strike %.2f is %.2f from the sweep extreme "
                "%.2f (grid ~%.2f) — the chain does not reach the tape; "
                "declining rather than selling a strike nobody chose",
                best, abs(best - sweep_price), sweep_price, step)
            return None
        return round(best, 4)

    if ks:
        return _pick(sorted(set(ks)))

    # No chain — fall back to the grid. Same rule, one assumed increment.
    increment = safe_float(increment)
    if not increment or increment <= 0:
        return None
    import math as _m
    if ceiling:
        grid = [_m.floor(sweep_price / increment) * increment,
                _m.ceil(sweep_price / increment) * increment]
    else:
        grid = [_m.floor(sweep_price / increment) * increment,
                _m.ceil(sweep_price / increment) * increment]
    return _pick(sorted(set(grid)))


def pierced_strike(sweep_price: float, pool_price: float, ceiling: bool,
                   increment: float) -> Optional[float]:
    """The NEAREST STRIKE PRICE ACTUALLY PIERCED. Operator's rule, 2026-08-20.

    Not the pool level - the nearest strike price traded THROUGH on the sweep.
    Ceiling: pool 600, price ran to 601.20, retreated to 599.50 -> sell the 601.
    Floor: mirrored downward.

    WHY THIS AND NOT THE POOL. The pierce high is FURTHER from current price
    than the pool is, so the short strike sits further out: less credit, more
    room. **With a 15% stop that is the correct side to err on** - the position
    is threatened only if price returns all the way to a level it already
    visited and failed at, rather than merely back to the boundary.

    ⚠️ ON A SHALLOW PIERCE THE STRIKE COLLAPSES TO THE POOL, and that is
    correct rather than a special case: if price ran to 600.30 with $1 strikes,
    the nearest strike it actually pierced IS the 600. The rule degrades to
    "sell the boundary" exactly when the pierce was too small to clear another
    strike, which is the same trade the boundary framing describes.

    Returns None when the sweep cleared NO strike - price poked past the pool
    without reaching a strike price. There is nothing to sell, and inventing a
    strike here would sell a level that was never tested.
    """
    # ⚠️ math.floor(nan) RAISES "cannot convert float NaN to integer". The
    # truthiness test above passes a NaN happily - `not nan` is False - so the
    # guard read as present and was not.
    sweep_price = safe_float(sweep_price)
    pool_price = safe_float(pool_price)
    increment = safe_float(increment)
    if not sweep_price or not pool_price or not increment or increment <= 0:
        return None
    if ceiling:
        # highest strike at or below the sweep extreme, and at/above the pool
        k = math.floor(sweep_price / increment) * increment
        if k < pool_price:
            return None
        return round(k, 4)
    k = math.ceil(sweep_price / increment) * increment
    if k > pool_price:
        return None
    return round(k, 4)


def boundary_from_sweep(kind: str) -> Optional[tuple]:
    """(boundary, option_side) from the sweep direction.

    `high_sweep` - highs taken and rejected DOWN - makes the pool a CEILING, so
    the trade is a CALL credit spread and price must stay below it.
    `low_sweep` makes it a FLOOR: a PUT credit spread, price stays above.
    """
    k = (kind or "").lower()
    if k.startswith("high"):
        return ("ceiling", "call")
    if k.startswith("low"):
        return ("floor", "put")
    return None


# ═══ SPENT LEVELS — A POOL THAT STOPPED US OUT IS FINISHED ════════════════
# 🔴 OPERATOR, 2026-08-27, watching CVX re-enter the SAME 198/192 pool four
# times in five minutes for -$104: *"The stop isn't too tight, the level that we
# just attempted a sweep on is finished."*
#
# ⚠️ MEASURED: entries at 11:43, 11:46, 11:47, 11:48 — all sell=198 buy=192,
# all stopped within a minute, all on the same pool. Nothing in the strategy
# remembered the previous attempt, so the level re-qualified every time price
# wandered back to the right side of it.
#
# ⚠️ THE ONLY INVALIDATION THAT EXISTED WAS PRICE-BASED. `LiquiditySweep
# .invalidated` (LIQ.3) is recomputed EVERY TICK from closes beyond the pool —
# it answers "has price accepted through this level", which is a fact about the
# TAPE. It cannot answer "did we already try this and lose", which is a fact
# about US. Both are needed and only one existed.
#
# ⚠️ THIS IS THE STRATEGY'S OWN DOCTRINE, FINALLY ENFORCED. Its docstring
# already says *"selling a boundary that has already given way is the worst
# version of this"* — a stop-out IS the boundary giving way, measured with real
# money rather than inferred from closes.
#
# KEYED BY (symbol, side, rounded pool) so the two sides of one price are
# separate levels, and cleared daily — a level that failed this morning is not
# thereby dead tomorrow.
_SPENT: dict = {}
_SPENT_DAY: str = ""


def _spent_key(symbol: str, side: str, pool: float) -> tuple:
    # ⚠️ ROUNDED TO THE CENT. The pool is recomputed per tick and drifts in the
    # last decimal; an exact-float key would never match itself and the lock
    # would silently never fire — the same class of dead gate as a name that
    # does not resolve.
    return (symbol or "", side or "", round(float(pool or 0.0), 2))


def mark_spent(symbol: str, side: str, pool: float, why: str = "") -> None:
    """Record that a trade on this level closed at a loss. Called from the
    exit path, not from here — the strategy cannot see its own outcome."""
    global _SPENT_DAY
    from datetime import datetime
    try:
        from config import ET
        today = datetime.now(ET).strftime("%Y-%m-%d")
    except Exception:                                          # noqa: BLE001
        today = datetime.now().strftime("%Y-%m-%d")
    if today != _SPENT_DAY:
        _SPENT.clear()
        _SPENT_DAY = today
    k = _spent_key(symbol, side, pool)
    if k not in _SPENT:
        _SPENT[k] = why or "a trade on this level was stopped out"
        logger.info("[sweep_cs] LEVEL SPENT %s %s %.2f — %s",
                    symbol, side, pool or 0.0, _SPENT[k])


def is_spent(symbol: str, side: str, pool: float):
    """(spent, why). Day-scoped: cleared on the first call of a new day."""
    from datetime import datetime
    try:
        from config import ET
        today = datetime.now(ET).strftime("%Y-%m-%d")
    except Exception:                                          # noqa: BLE001
        today = datetime.now().strftime("%Y-%m-%d")
    if today != _SPENT_DAY:
        return False, ""
    k = _spent_key(symbol, side, pool)
    return (k in _SPENT), _SPENT.get(k, "")


def _sweep_at_level(liq_map, level: float, side: str = ""):
    """The sweep on a SUPPLIED level — an input the plan gathered, r158.

    ⚠️ `liq_map.sweeps` IS THE FULL LIST; `recent_sweep` is only the latest one.
    (Checked against LiquidityMap's own fields, not assumed — the week's other
    defects were all names that did not exist.) When a plan supplies a level,
    the strategy evaluates THAT sweep rather than whichever happens to be most
    recent.

    ⚠️ RETURNS None WHEN THE FEED HAS NO SWEEP THERE, and the caller reports it
    as STARVED rather than proceeding on the wrong level. A supplied input that
    cannot be found is missing data, not a refusal — the distinction matters
    because starvation names the absent input and a refusal blames the setup.
    """
    if not level:
        return None
    want_side = (side or "").lower()
    best = None
    for sw in (getattr(liq_map, "sweeps", None) or []):
        try:
            pool = float(getattr(sw, "pool_price", 0.0) or 0.0)
        except (TypeError, ValueError):
            continue
        if not pool or abs(pool - float(level)) > 0.01:
            continue
        if want_side:
            # a swept LOW is defended with puts; a swept HIGH with calls
            kind = str(getattr(sw, "kind", "") or "")
            if want_side == "put" and kind != "low_sweep":
                continue
            if want_side == "call" and kind != "high_sweep":
                continue
        # freshest match wins — `bars_ago` is the real field (r135)
        if best is None or (getattr(sw, "bars_ago", 999)
                            < getattr(best, "bars_ago", 999)):
            best = sw
    return best


class SweepPreparation:
    """What the PLAN hands the STRATEGY on every tick of its slot.

    ⚠️ NOTHING HERE IS EXECUTABLE. It is the answer to "if the trigger fires on
    the next tick, what is the trade" — the level, every declared condition
    with its current reading, and every selected variable. The strategy
    decides whether its conditions are met and, if so, executes THESE.
    """
    __slots__ = ("tick", "sweep", "name", "pool", "side", "boundary", "conditions",
                 "unmet", "structural", "starved", "short", "long", "credit",
                 # r219 — `judged` is the BID/ASK credit R was tested on;
                 # `credit` is the MARK credit that gets BOOKED. __slots__ is
                 # why this needs declaring: assigning an undeclared attribute
                 # raises rather than silently creating one, which is the slot
                 # doing its job.
                 "judged",
                 "width", "stop_prem", "stop_dist", "r", "r_min", "r_stop_disp", "swept_px",
                 "age", "rej", "ready")

    def __init__(self, tick):
        self.tick = tick
        self.sweep = None
        self.name, self.pool, self.side, self.boundary = "", 0.0, "", ""
        self.conditions = {}      # name -> (current, required, met)
        self.unmet = []           # trigger conditions not yet true
        self.structural = []      # (name, why) — untradeable even if the trigger fires
        self.starved = []         # inputs the plan could not find
        self.short = self.long = None
        self.credit = self.width = self.stop_prem = self.stop_dist = None
        self.judged = None
        # \U0001f534 r234 - THE NARRATION NAMES THE BASIS IT WAS GATED ON. r219's
        # lesson one layer over: the plan line printed `credit N (bid/ask)`
        # while N had become the mark, and *"printing one and labelling it the
        # other is how this stayed invisible for the life of the strategy."*
        # The gate moved to the stop basis; the line said R and meant expiry.
        self.r, self.r_min = None, R_FLOOR_STOP
        self.r_stop_disp = None
        self.swept_px, self.age, self.rej = 0.0, 0, 0.0
        self.ready = False

    def cond(self, name, current, required, met):
        self.conditions[name] = (current, required, bool(met))
        if not met:
            self.unmet.append(name)
        self.tick.check(name, current if isinstance(current, (int, float)) else None, bool(met))

    def trade_line(self) -> str:
        if not self.ready:
            return "no trade prepared"
        # 🔑 TWO CREDITS, BOTH NAMED. `credit` is what gets BOOKED (mark, the
        # operator's fill ruling); `judged` is what R was tested on (bid/ask).
        # Printing one and labelling it the other is how the basis mismatch
        # stayed invisible for the life of the strategy.
        _j = getattr(self, "judged", None)
        _jtxt = f" (judged {_j:.2f} bid/ask)" if _j is not None else ""
        return (f"sell {self.short.strike:g}{self.side[0].upper()} / buy "
                f"{self.long.strike:g}{self.side[0].upper()}  credit "
                f"{self.credit:.2f} (mark){_jtxt}  stop {self.stop_prem:.2f}"
                f"  R {self.r_stop_disp:.2f} on the stop "
                f"(min {self.r_min:.2f}; {self.r:.2f} at expiry)"
                if self.r_stop_disp is not None else
                f"  R {self.r:.2f} at expiry (stop basis unpriceable)")


class SweepCreditSpreadStrategy:
    """THE SPEC. Declares its conditions, executes with the plan's variables.

    🔴 THE SPLIT (operator, 2026-08-27, read back and confirmed): the plan is
    ANTICIPATORY — on tick t it evaluates what would need to be true on tick
    t+1 for this strategy to execute, and selects every variable of that
    trade. The strategy is CONFIRMATORY — it checks its declared conditions
    against the tick and, if all are true, executes the prepared trade. The
    strategy holds no chain and picks no strike. Which layer decides? These
    CONDITIONS do; the plan reads them and reports.
    """
    name = "SweepCreditSpread"

    # ── THE DECLARED CONDITIONS — what must be true for this spec to fire ──
    # name -> what "true" means. The plan evaluates each against the feed and
    # reports (current, required, met). Thresholds are this file's GATES.
    CONDITIONS = {
        "named":        "the swept level is a NAMED pool",
        "reclaimed":    "a bar has CLOSED back inside the pool (a wick is a touch) — "
                        "or the level is a MOVING tine, whose TOUCH is the trigger",
        "invalidated":  "price has NOT accepted through it after the reclaim",

        "rejection":    f"rejection >= {MIN_REJECTION_PCT*100:.3f}%",
        "pierce_depth": f"pierce <= {MAX_REJECTION_PCT*100:.3f}% (relaxed x3)",
        "side_of_pool": "price is on the profitable side of the pool",
        "entry_window": f"{EARLIEST_ET}-{LATEST_ET} ET (relaxed extends)",
        "atr_pct":      f"ATR <= {ATR_MAX_PCT:.2f}% or unmeasured",
    }
    # structural — untradeable even if every condition is true
    STRUCTURAL = ("geometry", "spent_level", "short_anchor", "wing_r_best",
                  "credit", "stop_vs_spread")
    PLAN_CHECKS = tuple(CONDITIONS) + STRUCTURAL + (
        "sweep", "contract", "wing", "width", "risk", "r", "r_expiry",
        # r233 record-only telemetry - gates nothing, exists to be fitted
        "pierce_pts", "level_dist_pts", "level_dist_pct")

    def __init__(self):
        self.planner = Plan(self.name, self.PLAN_CHECKS)

    # ══════════════════════════════════════════════════════════════════════
    # THE PLAN — reads the feed, evaluates the declared conditions, SELECTS
    # every variable, narrates. Returns a SweepPreparation or None (dormant).
    # ══════════════════════════════════════════════════════════════════════
    def prepare(self, *, liq_map, price_now, now_et, atr_pct=None, chain=None,
                orb_high=None, orb_low=None, required_side: str = "",
                **_ignored) -> SweepPreparation:
        t = self.planner.tick(price_now)
        prep = SweepPreparation(t)

        # ── the slot: outside it the plan is DORMANT, one row, no narration ─
        _early, _late = relaxed.window(EARLIEST_ET, LATEST_ET, relaxed_latest=LATEST_ET)
        in_window = (not now_et) or (_early <= now_et <= _late)
        if not in_window:
            # ⚠️ TIME-INVARIANT reason (check_plan_signal PS7): the dormant row
            # is edge-triggered on its text; a clock in it defeats the dedupe.
            t.dormant("entry_window", f"outside the sweep slot {_early}-{_late}")
            return prep                       # dormant: nothing prepared
        prep.cond("entry_window", None, self.CONDITIONS["entry_window"], True)

        # ── the level: the sweep this spec would trade ─────────────────────
        # With an authorization (the condor: "only a complementary-side sweep
        # may fire") the plan prepares the freshest sweep of THAT side; without
        # one, the map's most recent sweep. The plan chooses which level to
        # PREPARE; the strategy's conditions decide whether it FIRES.
        # ⚠️ PRICE IS VALIDATED FIRST NOW: r233 selects the level BY DISTANCE
        # from spot, so the selector cannot run before the thing it ranks on.
        price_now = safe_float(price_now)
        if not price_now or price_now <= 0 or price_now > 1e7:
            prep.starved.append("price_now")
            t.starved("price_now")
            return prep
        # 🔴 r233 - THE NEAREST LIVE LEVEL WINS, NOT THE MOST RECENT RAID.
        # Operator, 2026-09-03: *"the level in question needs to be the closest
        # to the current price that's ever held."* Both branches used RECENCY:
        # this one took min(bars_ago) across every level, and the fallback took
        # `recent_sweep`, the map's minutes-normalised freshest. So a raid on a
        # level three points out beat one 0.6 points out if it landed a bar
        # sooner - and selling the cusp of a distant level is still distant,
        # which is what makes this the change that gives the strike rule its
        # meaning.
        # ⚠️ RECENCY IS NOT DISCARDED, IT IS DEMOTED TO THE TIE-BREAK. Two
        # levels at the same distance are separated by freshness, which is the
        # only question distance cannot answer.
        # ⚠️ AND THIS RETIRES THE CROSS-TIMEFRAME UNIT BUG AT THIS SITE RATHER
        # THAN FIXING IT: `bars_ago` is counted in each sweep's OWN timeframe,
        # so comparing a 15m sweep's 4 against a 5m sweep's 6 compared 60
        # minutes against 30 (SWEEP.6). Distance carries no units problem.
        # The tie-break can still see it, so SWEEP.6 stays OPEN for the other
        # site and for liquidity_mapper.
        sweep = None
        if required_side:
            # ⚠️ LEG TWO REQUIRES A REJECTION AT THE SITE. A tine TOUCH is not
            # one (operator, 2026-08-27), so touch events are never selected
            # here - only a real sweep of the authorized side.
            want_kind = "low_sweep" if required_side == "put" else "high_sweep"
            _cands = [sw for sw in (getattr(liq_map, "sweeps", None) or [])
                      if str(getattr(sw, "kind", "") or "") == want_kind
                      and not getattr(sw, "touch", False)]
            t.direction = required_side
        else:
            # ⚠️ THE FALLBACK IS NO LONGER `recent_sweep`. That field is the
            # MAP's pick and is chosen by minutes, so leaving it here would
            # have left the primary entry path on recency while leg two moved
            # to distance - one rule with two answers, which is the split this
            # repo keeps finding. Touch events stay eligible here (a tine
            # TOUCH is a valid trigger outside leg two, r163).
            _cands = list(getattr(liq_map, "sweeps", None) or [])
        _ranked = [(r, sw) for r, sw in
                   ((level_rank(s, price_now), s) for s in _cands)
                   if r is not None]
        if _ranked:
            sweep = min(_ranked, key=lambda rs: rs[0])[1]
        elif not required_side:
            # every candidate had an unusable pool price - fall back to the
            # map's own pick rather than going blind, and say so.
            sweep = getattr(liq_map, "recent_sweep", None)
            if sweep is not None:
                logger.info("[sweep_cs] no candidate carried a usable pool "
                            "price; falling back to the map's recent_sweep")
        if not sweep:
            t.hold(f"no {required_side + ' ' if required_side else ''}sweep on the "
                   f"liquidity map to prepare — waiting for a named pool to be swept")
            return prep
        prep.sweep = sweep
        _touch = bool(getattr(sweep, "touch", False))
        t.check("sweep", 2.0 if _touch else 1.0, True)   # 2 = a tine TOUCH

        # ── the declared conditions, each with its current reading ─────────
        name = str(getattr(sweep, "swept_named_level", "") or "")
        prep.name = name or "unnamed"
        prep.cond("named", 1.0 if name else 0.0, self.CONDITIONS["named"], bool(name))
        reclaimed = bool(getattr(sweep, "reclaimed", False))
        prep.cond("reclaimed", 1.0 if reclaimed else 0.0, self.CONDITIONS["reclaimed"], reclaimed)
        inval = bool(getattr(sweep, "invalidated", False))
        prep.cond("invalidated", 1.0 if inval else 0.0, self.CONDITIONS["invalidated"], not inval)
        # 🔴 r231 — `or 999` MADE THE FRESHEST SWEEP THE STALEST. `bars_ago`
        # is an int field defaulting to 0 and SWP.10 counts it from the
        # RECLAIM bar, so a sweep that reclaimed on the CURRENT bar is 0 —
        # and `0 or 999` is 999. Twenty-six lines above, the selection loop
        # takes `min(bars_ago)`: it hunts the freshest sweep on the board and
        # this line converted exactly that winner into the stale sentinel and
        # refused it. The two halves of one function contradicted each other,
        # and 999 reads as missing data rather than as the best setup there
        # was. Absent stays 999; ZERO now stays zero.
        _ba = getattr(sweep, "bars_ago", None)
        age = 999 if _ba is None else int(_ba)
        prep.age = age
        # 🔴 r241 - THE AGE GATE IS GONE. Operator, 2026-09-04: *"I don't give a
        # rat's ass how old the level is, it's still a level. Why are we still
        # measuring the age of them?"* Because I only half-shipped his 08-11
        # ruling: SWP.5 said LIVENESS REPLACES THE CLOCK, r230 found it had
        # never reached the code, and I raised the ceiling from 6 to 48 instead
        # of removing the gate. That was my call, not his.
        # 🔑 AGE MEASURES THE RAID, NOT THE LEVEL. A level swept at 09:45 that
        # has held ever since is the SAME LEVEL at 13:00 - arguably a better
        # one, having held longer. And levels are swept all day; the morning's
        # is not the only one on the board.
        # ⚠️ `invalidated` ALREADY ANSWERS THIS AND ANSWERS IT CORRECTLY - has
        # price ACCEPTED back through the level. It fails 73% of the time,
        # which is a market fact rather than a defect. `age` was a second,
        # worse proxy for a question that gate already settles: two rules for
        # one thing, which is the rot §35 names.
        # 🔴 MEASURED FLEET-WIDE, 08-31..09-04: age failed 46,791 of 61,641
        # (76%), and on 333 ticks - 26% of every tick that was ONE gate short -
        # it was the ONLY thing refusing. Those are complete setups declined
        # for being old.
        # ⚠️ THE UNMEASURABLE CASE SURVIVES ON ITS OWN TERMS. `bars_ago` absent
        # yields the 999 sentinel, and an unmeasurable sweep is NOT an old one:
        # it refuses because the reclaim cannot be located at all, which is a
        # data fault, not a staleness judgement. Silently admitting it would be
        # the absent-is-not-zero failure this repo keeps paying for.
        if age >= _AGE_UNMEASURABLE:
            prep.structural.append(("sweep_unmeasurable",
                f"bars_ago is the {_AGE_UNMEASURABLE} sentinel - the reclaim "
                f"cannot be located, so this sweep is UNMEASURED rather than "
                f"stale"))
            return prep
        rej = float(getattr(sweep, "rejection_pct", 0.0) or 0.0)
        prep.rej = rej
        prep.cond("rejection", rej, self.CONDITIONS["rejection"], rej >= MIN_REJECTION_PCT)
        _max_rej = relaxed.widen(MAX_REJECTION_PCT, 3.0, name="pierce_ceiling")
        prep.cond("pierce_depth", rej, f"<= {_max_rej*100:.3f}%", rej <= _max_rej)
        # \U0001f511 r233 RECORD-ONLY - HOW OFTEN THE DEEP CASE ACTUALLY FIRES, and
        # how far the chosen level sat from spot. Both GATE NOTHING and are
        # written so the r233 rulings can be FITTED against outcomes instead of
        # defended (WA \u00a731; same shape as r198's wing_stretch and r215's
        # pin_dist_pct). `pierce_pts` is the width of the TESTED RANGE the
        # strike must now clear; `level_dist_pts` is what the nearest-level
        # rule was chosen on. Points AND percent, because points alone are not
        # comparable across an $83 NFLX and a $7,700 SPX.
        try:
            _pp = float(getattr(sweep, "pool_price", 0.0) or 0.0)
            _sx = float(getattr(sweep, "sweep_price", 0.0) or 0.0)
            if _pp > 0 and _sx > 0:
                t.check("pierce_pts", round(abs(_pp - _sx), 4), None)
                t.check("level_dist_pts", round(abs(_pp - price_now), 4), None)
                t.check("level_dist_pct",
                        round(abs(_pp - price_now) / price_now * 100.0, 4), None)
        except (TypeError, ValueError, ZeroDivisionError):
            pass
        b = boundary_from_sweep(getattr(sweep, "kind", ""))
        if not b:
            t.refuse("boundary", f"sweep kind '{getattr(sweep, 'kind', '')}' names no boundary")
            prep.structural.append(("boundary", "unknown sweep kind"))
            return prep
        boundary, side = b
        prep.boundary, prep.side = boundary, side
        t.direction = side
        pool = float(getattr(sweep, "pool_price", 0.0) or 0.0)
        if pool <= 0:
            prep.starved.append("pool_price")
            t.starved("pool_price")
            return prep
        prep.pool = pool
        t.anchor(trigger=pool, invalidation=pool)
        _on_side = (price_now < pool) if boundary == "ceiling" else (price_now > pool)
        prep.cond("side_of_pool", price_now - pool, self.CONDITIONS["side_of_pool"], _on_side)
        _atr = safe_float(atr_pct)
        prep.cond("atr_pct", _atr, self.CONDITIONS["atr_pct"],
                  _atr is None or _atr <= ATR_MAX_PCT)

        # ── structural: untradeable regardless of the trigger ─────────────
        # a moving level's price drifts every bar: the lock is keyed by NAME
        _spent, _spent_why = is_spent(_symbol_of(), side,
                                      pool if not _touch else _name_key(name))
        t.check("spent_level", 1.0 if _spent else 0.0, not _spent)
        if _spent:
            prep.structural.append(("spent_level", f"{name} {pool:.2f} is SPENT — {_spent_why}"))
        _geo = t.level(pool, boundary, name or "pool", orb_high, orb_low,
                       price_now)
        if _geo is False:
            prep.structural.append(("geometry", t.last_why))

        # ── SELECTION — the trade, if the trigger fires next tick ──────────
        if chain is None:
            prep.starved.append("chain")
        else:
            _inc = float(getattr(config, "STRIKE_INCREMENT", 1) or 1)
            prep.swept_px = float(getattr(sweep, "sweep_price", 0.0) or 0.0)
            try:
                _side_contracts = chain.puts if side == "put" else chain.calls
            except Exception:                                  # noqa: BLE001
                _side_contracts = None
            _contracts = _side_contracts
            if not _contracts:
                prep.starved.append("chain")
            else:
                _ps = strike_beyond_sweep(prep.swept_px, pool, boundary == "ceiling",
                                          contracts=_side_contracts, increment=_inc)
                if _ps is None:
                    prep.structural.append(("short_anchor",
                        f"{name} swept to {prep.swept_px:.2f} and the {side} chain has no "
                        f"strike beyond it — a chain problem, not a setup one"))
                else:
                    t.check("short_anchor", _ps, True)
                    _short = cv.find_contract_at_strike(_contracts, _ps)
                    if _short is None or not (getattr(_short, "mark", 0) or 0) > 0:
                        prep.structural.append(("contract",
                            f"no priced {side} contract at the pierced strike {_ps:.2f} — "
                            f"the anchor is the trade"))
                    else:
                        t.check("contract", _short.strike, True)
                        # 🔴 r219 — TWO CREDITS. `_credit` (bid/ask) is what R
                        # is JUDGED on; `_fill` (mark) is what gets BOOKED.
                        # Operator ruling 2026-09-02: "I have a ladder for live
                        # offers, all paper needs to fill at mark, period."
                        # \U0001f534 r234 - READ BY NAME. r219 added a fifth value and
                        # missed two guard returns that still returned four,
                        # so a short leg with no bid raised ValueError into
                        # `_safe_strategy` and read as a clean DECLINE. A
                        # NamedTuple makes that unrepresentable.
                        _w = cv.search_wing(_contracts, _short, side, R_FLOOR,
                                            r_floor_stop=R_FLOOR_STOP)
                        _best_r, _long, _credit = _w.r, _w.long, _w.credit
                        _bw, _fill = _w.width, _w.fill
                        # \U0001f511 GATED ON THE STOP BASIS. The stop IS this trade's
                        # designed exit (operator: "the only 2 ways I want out
                        # is a 15% loss or a session hard close"), so R is
                        # judged against the risk actually taken. `r_expiry`
                        # rides alongside, record-only, so the basis change is
                        # auditable from the tape rather than argued.
                        t.check("r_expiry", _best_r, None)
                        t.check("wing_r_best", _w.r_stop,
                                _w.r_stop is not None and _w.r_stop >= R_FLOOR_STOP)
                        if _long is None:
                            # \u26a0\ufe0f r234 - NAME WHICH RUNG REFUSED IT. The bracket
                            # can reject every candidate for SURVIVABILITY or
                            # for the stop floor, and reporting that as "no
                            # priceable wing" would blame the chain for a
                            # decision the gate made.
                            prep.structural.append(
                                (_w.why_key or "wing",
                                 (_w.why or f"no priceable protective wing beyond "
                                            f"{_short.strike:.2f}")))
                        elif _w.r_stop is None or _w.r_stop < R_FLOOR_STOP:
                            prep.structural.append(("wing_r_best",
                                f"no wing clears stop-basis R {R_FLOOR_STOP:.2f} — best is "
                                f"{('n/a' if _w.r_stop is None else f'{_w.r_stop:.2f}')} "
                                f"({_bw:.2f} wide, credit ${_credit:.2f}, expiry-basis R "
                                f"{_best_r:.2f}){(' — ' + _w.why) if _w.why else ''}; "
                                f"structure, not selection — relaxed does not waive it"))
                        else:
                            t.check("wing", _long.strike, True)
                            t.credit_spread(_short.strike, _long.strike, _credit,
                                            invalidation=pool, trigger=pool)
                            if _credit <= 0:
                                prep.structural.append(("credit",
                                    f"{side} {_short.strike:.2f}/{_long.strike:.2f} pays no credit"))
                            elif _fill is None:
                                # ⚠️ NO MARK ON A LEG IS NOT A REASON TO BOOK
                                # THE BID/ASK NUMBER. Substituting it is the
                                # exact defect r219 removes, so refuse instead.
                                prep.structural.append((
                                    "fill_mark",
                                    f"{side} {_short.strike:.2f}/"
                                    f"{_long.strike:.2f} has no usable mark on "
                                    f"one leg — the fill price is unknown"))
                            else:
                                # ⚠️ THE STOP IS DERIVED FROM WHAT WAS BOOKED,
                                # not from the hurdle. A stop measured off a
                                # credit the position never had is the same
                                # basis error one layer down.
                                # \U0001f534 r234 - THE ENGINE'S STOP, NOT A SECOND ONE.
                                # This computed `credit * MAX_LOSS_PCT` - 15%
                                # OF CREDIT - and fed it to stop_survivable,
                                # while exit_engine:1818 fires at 15% OF RISK.
                                # On the measured median that is 0.1455 against
                                # 0.6045, 4.15x apart, and the forensics'
                                # "risk-anchored room: median $0.605" matches
                                # the ENGINE. Survivability was judged against
                                # a stop four times tighter than the one that
                                # exists, refusing structures that survive.
                                # \u26a0\ufe0f AND THE CREDIT-ANCHORED FORM IS THE RULE
                                # r155 DELETED - exit_engine's own fallback
                                # warning names it: "15% OF CREDIT, which is
                                # the inverted rule r155 replaced. The trade
                                # will stop on noise."
                                _stop_dist = _stop_distance_of(_bw, _fill)
                                if _stop_dist is None:
                                    _stop_dist = 0.0
                                _stop_prem = _fill + _stop_dist
                                _sv_ok, _sv_why = stop_survivable(
                                    _stop_dist, getattr(_short, "bid", 0.0),
                                    getattr(_short, "ask", 0.0))
                                t.check("stop_vs_spread", round(_stop_dist, 4), _sv_ok, _sv_why)
                                if not _sv_ok:
                                    prep.structural.append(("stop_vs_spread", _sv_why))
                                else:
                                    prep.short, prep.long = _short, _long
                                    # `prep.credit` becomes sig.entry_premium
                                    # (line ~889) and therefore the booked
                                    # fill. It is the MARK credit now.
                                    prep.credit, prep.width = _fill, _bw
                                    # ⚠️ BOTH NUMBERS RIDE THE PLAN. The line
                                    # said "credit N (bid/ask)" and after r219
                                    # N is the MARK — a label that is now a lie
                                    # unless the judged credit travels with it.
                                    prep.judged = _credit
                                    prep.stop_prem, prep.stop_dist = _stop_prem, _stop_dist
                                    prep.r = t.r
                                    prep.r_stop_disp = _w.r_stop
                                    prep.ready = True

        # ── the narration: which of the three states is this tick ──────────
        head = (f"{prep.name} {boundary} {pool:.2f} ({side} spread"
                f"{', TOUCH of a moving tine' if _touch else ''})")
        if prep.starved:
            t.starved(*prep.starved)
            return prep
        if prep.structural:
            gate, why = prep.structural[0]
            t.refuse(gate, f"{head}: {why}")
            return prep
        if prep.unmet:
            cur = "; ".join(f"{n}={_n(prep.conditions[n][0]) if isinstance(prep.conditions[n][0], (int, float)) else 'no'}"
                            f" (need {prep.conditions[n][1]})" for n in prep.unmet)
            t.hold(f"{head}: PREPARED — {prep.trade_line()}. Waiting on: {cur}")
            return prep
        t.note(f"{head}: all {len(self.CONDITIONS)} conditions true — {prep.trade_line()}")
        return prep

    # ══════════════════════════════════════════════════════════════════════
    # THE STRATEGY — checks its conditions, executes the plan's variables.
    # ══════════════════════════════════════════════════════════════════════
    def generate_signal(self, *, liq_map, price_now: float, now_et: str,
                        atr_pct: float = None, chain=None,
                        orb_high: float = None, orb_low: float = None,
                        required_side: str = "", **_ignored) -> Optional[Signal]:
        """`required_side` is the condor's AUTHORIZATION (one vertical open ->
        only the complementary-side sweep may fire). It narrows; it never
        selects a level for this strategy."""
        prep = self.prepare(liq_map=liq_map, price_now=price_now, now_et=now_et,
                            atr_pct=atr_pct, chain=chain, orb_high=orb_high,
                            orb_low=orb_low, required_side=required_side)
        if not prep.ready or prep.unmet or prep.structural or prep.starved:
            return prep.tick.already()       # the plan wrote this tick's row
        if required_side and prep.side != required_side:
            return prep.tick.refuse("authorized_side",
                                    f"only a {required_side} sweep is authorized "
                                    f"while the other vertical is open; this is "
                                    f"a {prep.side}")

        # ── EXECUTE the prepared trade — every variable is the plan's ───────
        sig = Signal(
            strategy_name=self.name,
            setup_type="sweep_credit_spread",
            direction="short" if prep.side == "call" else "long",
            option_side=prep.side,
            underlying_entry=float(price_now),
        )
        sig.short_anchor = prep.short.strike
        sig.pierced_strike = prep.short.strike
        sig.pool_price = prep.pool
        sig.boundary = prep.boundary
        sig.swept_level_name = prep.name
        sig.sweep_age_bars = prep.age
        sig.rejection_pct = prep.rej
        sig.atr_pct_at_entry = atr_pct
        sig.max_loss_pct = MAX_LOSS_PCT
        # a tine touch is classed as a FORK trigger under Rule 4; a real
        # sweep as sweep_reversal. Leg two can only ever be the latter.
        if getattr(prep.sweep, "touch", False):
            sig.condor_trigger_source = f"{getattr(prep.sweep, 'timeframe', '') or '1h'}_fork"
            sig.touch_of_tine = True
        else:
            sig.condor_trigger_source = "sweep_reversal"
        sig.is_credit_vertical = True
        sig.net_credit = prep.credit
        if prep.side == "call":
            sig.short_call_contract, sig.long_call_contract = prep.short, prep.long
        else:
            sig.short_put_contract, sig.long_put_contract = prep.short, prep.long
        sig.strike = prep.short.strike
        sig.expiry = getattr(prep.short, "expiry", "")
        sig.entry_premium = prep.credit
        sig.contract = prep.short
        sig.stop_premium = prep.stop_prem
        relaxed.tag(sig)
        logger.info("[sweep_cs] FIRE  %s swept -> %s  %s  age %d bars  rejection %.3f%%",
                    prep.name, prep.boundary, prep.trade_line(), prep.age, prep.rej * 100.0)
        return prep.tick.take(sig)


def _name_key(name: str) -> float:
    """A stable numeric key for a MOVING level's spent lock: the level's price
    drifts every bar, so `mark_spent`/`is_spent` (keyed by rounded price) are
    given a hash of the NAME instead. Deterministic across restarts."""
    import zlib
    return float(zlib.crc32((name or "").encode("utf-8")) % 1_000_000)


def _symbol_of() -> str:
    try:
        from config import INSTRUMENT
        return str(INSTRUMENT)
    except Exception:                                          # noqa: BLE001
        return ""
