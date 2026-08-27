"""
strategy/sweep_credit_spread.py  v4.6
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
from strategy.criteria import stop_survivable, R_FLOOR
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
MAX_AGE_BARS = getattr(config, "SWEEP_CS_MAX_AGE_BARS", 6)
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
    "MAX_AGE_BARS":       "SELECTION",
    "MIN_REJECTION_PCT":  "SELECTION",
    # FEASIBILITY - above 0.20% ATR the tape produced a 0.5% move on 92% of
    # 90-bar windows. A boundary does not hold in that.
    "ATR_MAX_PCT":        "FEASIBILITY",
    # FOUNDATIONAL conditions are not constants - they are the named pool, the
    # reclaim, the non-invalidation and price being on the profitable side, all
    # tested inline. **They have no knob to relax, which is the safest form a
    # foundational gate can take.**
}


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
            cand = [k for k in strikes if k >= pool_price - 1e-9]
        else:
            cand = [k for k in strikes if k <= pool_price + 1e-9]
        if not cand:
            return None
        best = min(cand, key=lambda k: abs(k - sweep_price))
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
                 "width", "stop_prem", "stop_dist", "r", "r_min", "swept_px",
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
        self.r, self.r_min = None, R_FLOOR
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
        return (f"sell {self.short.strike:g}{self.side[0].upper()} / buy "
                f"{self.long.strike:g}{self.side[0].upper()}  credit {self.credit:.2f} "
                f"(bid/ask)  stop {self.stop_prem:.2f}  R {self.r:.2f} "
                f"(min {self.r_min:.2f})")


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
        "reclaimed":    "a bar has CLOSED back inside the pool (a wick is a touch)",
        "invalidated":  "price has NOT accepted through it after the reclaim",
        "age":          f"reclaimed within MAX_AGE_BARS ({MAX_AGE_BARS}; relaxed x3)",
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
        "sweep", "contract", "wing", "width", "risk", "r")

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
        sweep = None
        if required_side:
            want_kind = "low_sweep" if required_side == "put" else "high_sweep"
            best = None
            for sw in (getattr(liq_map, "sweeps", None) or []):
                if str(getattr(sw, "kind", "") or "") != want_kind:
                    continue
                if best is None or (getattr(sw, "bars_ago", 999) < getattr(best, "bars_ago", 999)):
                    best = sw
            sweep = best
            t.direction = required_side
        else:
            sweep = getattr(liq_map, "recent_sweep", None)
        price_now = safe_float(price_now)
        if not price_now or price_now <= 0 or price_now > 1e7:
            prep.starved.append("price_now")
            t.starved("price_now")
            return prep
        if not sweep:
            t.hold(f"no {required_side + ' ' if required_side else ''}sweep on the "
                   f"liquidity map to prepare — waiting for a named pool to be swept")
            return prep
        prep.sweep = sweep
        t.check("sweep", 1.0, True)

        # ── the declared conditions, each with its current reading ─────────
        name = str(getattr(sweep, "swept_named_level", "") or "")
        prep.name = name or "unnamed"
        prep.cond("named", 1.0 if name else 0.0, self.CONDITIONS["named"], bool(name))
        reclaimed = bool(getattr(sweep, "reclaimed", False))
        prep.cond("reclaimed", 1.0 if reclaimed else 0.0, self.CONDITIONS["reclaimed"], reclaimed)
        inval = bool(getattr(sweep, "invalidated", False))
        prep.cond("invalidated", 1.0 if inval else 0.0, self.CONDITIONS["invalidated"], not inval)
        age = int(getattr(sweep, "bars_ago", 999) or 999)
        _max_age = relaxed.widen(MAX_AGE_BARS, 3.0, name="max_age_bars")
        prep.age = age
        prep.cond("age", age, f"<= {_max_age:g} bars", age <= _max_age)
        rej = float(getattr(sweep, "rejection_pct", 0.0) or 0.0)
        prep.rej = rej
        prep.cond("rejection", rej, self.CONDITIONS["rejection"], rej >= MIN_REJECTION_PCT)
        _max_rej = relaxed.widen(MAX_REJECTION_PCT, 3.0, name="pierce_ceiling")
        prep.cond("pierce_depth", rej, f"<= {_max_rej*100:.3f}%", rej <= _max_rej)
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
        _spent, _spent_why = is_spent(_symbol_of(), side, pool)
        t.check("spent_level", 1.0 if _spent else 0.0, not _spent)
        if _spent:
            prep.structural.append(("spent_level", f"{name} {pool:.2f} is SPENT — {_spent_why}"))
        _geo = t.level(pool, boundary, name or "pool", orb_high, orb_low)
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
                        _best_r, _long, _credit, _bw = cv.search_wing(
                            _contracts, _short, side, R_FLOOR)
                        t.check("wing_r_best", _best_r, _best_r >= R_FLOOR)
                        if _long is None:
                            prep.structural.append(("wing",
                                f"no priceable protective wing beyond {_short.strike:.2f}"))
                        elif _best_r < R_FLOOR:
                            prep.structural.append(("wing_r_best",
                                f"no wing clears R {R_FLOOR:.2f} — best is {_best_r:.2f} "
                                f"({_bw:.2f} wide, credit ${_credit:.2f}); "
                                f"structure, not selection — relaxed does not waive it"))
                        else:
                            t.check("wing", _long.strike, True)
                            t.credit_spread(_short.strike, _long.strike, _credit,
                                            invalidation=pool, trigger=pool)
                            if _credit <= 0:
                                prep.structural.append(("credit",
                                    f"{side} {_short.strike:.2f}/{_long.strike:.2f} pays no credit"))
                            else:
                                _stop_prem = _credit * (1.0 + MAX_LOSS_PCT)
                                _stop_dist = _stop_prem - _credit
                                _sv_ok, _sv_why = stop_survivable(
                                    _stop_dist, getattr(_short, "bid", 0.0),
                                    getattr(_short, "ask", 0.0))
                                t.check("stop_vs_spread", round(_stop_dist, 4), _sv_ok, _sv_why)
                                if not _sv_ok:
                                    prep.structural.append(("stop_vs_spread", _sv_why))
                                else:
                                    prep.short, prep.long = _short, _long
                                    prep.credit, prep.width = _credit, _bw
                                    prep.stop_prem, prep.stop_dist = _stop_prem, _stop_dist
                                    prep.r = t.r
                                    prep.ready = True

        # ── the narration: which of the three states is this tick ──────────
        head = f"{prep.name} {boundary} {pool:.2f} ({side} spread)"
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


def _symbol_of() -> str:
    try:
        from config import INSTRUMENT
        return str(INSTRUMENT)
    except Exception:                                          # noqa: BLE001
        return ""
