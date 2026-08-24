"""
strategy/sweep_credit_spread.py  v4.2
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
from utils.math_utils import safe_float

logger = logging.getLogger(__name__)


def _gate(name: str, reason: str) -> None:
    """r73 — report this rung, edge-triggered. NEVER changes the verdict.

    ⚠️ THE RUNGS WERE ALREADY WELL-WRITTEN AND ALREADY WRONG-LEVELLED. Every
    line below was a logger.debug, so on 2026-08-21 the fleet declined every
    setup all session and could not say which rung said no. This does not
    rewrite the reasons — it makes them visible and queryable.
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


class SweepCreditSpreadStrategy:
    """Sell the boundary a swept pool just became.

    ⚠️ THE ORDER OF THE GATES IS THE CHEAPEST-FIRST ORDER, and the first two are
    the ones v3 got wrong in opposite directions: it vetoed on acceptance
    measured DURING the rejection, and it aged the signal from the sweep rather
    than the reclaim.
    """

    name = "SweepCreditSpread"

    def generate_signal(self, *, liq_map, price_now: float, now_et: str,
                        atr_pct: float = None, chain=None,
                        **_ignored) -> Optional[Signal]:
        sweep = getattr(liq_map, "recent_sweep", None)
        # ⚠️ COERCE BEFORE ANY COMPARISON. A NaN price passed `price_now >= pool`
        # (False) and then `price_now <= pool` (also False), so BOTH side checks
        # let it through and the strategy fired on nan, -1.0 and -inf.
        price_now = safe_float(price_now)
        if not sweep or not price_now or price_now <= 0 or price_now > 1e7:
            return None

        # ── 1. it must be a NAMED pool ───────────────────────────────────────
        # An unnamed swing high is not a liquidity pool. The name is what makes
        # the level a place other participants are watching - PDH/PDL, overnight
        # high/low, session extremes - and `level_grade` ranks them by type.
        name = str(getattr(sweep, "swept_named_level", "") or "")
        if not name:
            return None

        # ── 2. it must have RECLAIMED and NOT been accepted through ─────────
        # ⚠️ BOTH CONDITIONS, AND THEY ARE NOT THE SAME. `reclaimed` says price
        # closed back inside. `invalidated` says price has SINCE accepted beyond
        # - the level failed after all. A reclaimed-then-invalidated sweep is a
        # BREAKOUT, and selling a boundary that has already given way is the
        # worst version of this trade.
        if not getattr(sweep, "reclaimed", False):
            return None
        if getattr(sweep, "invalidated", False):
            logger.debug("[sweep_cs] no trade: %s reclaimed then INVALIDATED - "
                         "price accepted through; that is a breakout", name)
            _gate("invalidated", f"{name} reclaimed then invalidated - "
                                 f"price accepted through; that is a breakout")
            return None

        # ── 3. it must be YOUNG - measured from the RECLAIM ─────────────────
        # SWP.10: `bars_ago` now counts from the reclaim bar, not the sweep bar.
        # Under v3 it counted from the sweep, so the signal was charged for the
        # 5-20 minutes of confirmation latency the pipeline itself imposed, and
        # the median scored sweep was an HOUR old.
        age = int(getattr(sweep, "bars_ago", 999) or 999)
        if age > relaxed.widen(MAX_AGE_BARS, 3.0, name="max_age_bars"):
            logger.debug("[sweep_cs] no trade: %s reclaimed %d bars ago "
                         "(max %d)", name, age, MAX_AGE_BARS)
            _gate("age", f"{name} reclaimed {age} bars ago (max {MAX_AGE_BARS})")
            return None

        # ── 4. the rejection must be real ───────────────────────────────────
        rej = float(getattr(sweep, "rejection_pct", 0.0) or 0.0)
        if rej < MIN_REJECTION_PCT:
            return None
        # ⚠️ AND NOT TOO DEEP. A deep pierce is a WEAK level, not a strong
        # rejection - measured: >0.50% pierces survived on 19% against 33-34%
        # for shallow ones, with 1.28% median adverse against 0.46%.
        if rej > relaxed.widen(MAX_REJECTION_PCT, 3.0, name="pierce_ceiling"):
            logger.debug("[sweep_cs] no trade: %s pierced %.3f%% - too deep, "
                         "the level barely rejected (19%% survival measured)",
                         name, rej * 100.0)
            _gate("pierce_depth",
                  f"{name} pierced {rej*100:.3f}% - too deep; a deep pierce is "
                  f"a WEAK level (19% survival measured)")
            return None

        # ── 5. which boundary did the pool become? ──────────────────────────
        b = boundary_from_sweep(getattr(sweep, "kind", ""))
        if not b:
            return None
        boundary, side = b
        pool = float(getattr(sweep, "pool_price", 0.0) or 0.0)
        if pool <= 0:
            return None

        # ⚠️ PRICE MUST ALREADY BE ON THE PROFITABLE SIDE OF THE BOUNDARY. If it
        # is not, the reclaim has not actually happened from this strategy's
        # point of view and the spread would be opened already tested.
        if boundary == "ceiling" and price_now >= pool:
            return None
        if boundary == "floor" and price_now <= pool:
            return None

        # ── 6. window and volatility ────────────────────────────────────────
        # ⚠️ RELAXED WIDENS THE WINDOW AND THE DEPTH BAND - SELECTION gates,
        # measured to favour the afternoon and a shallow pierce. It does NOT
        # widen the ATR ceiling below: that is a FEASIBILITY veto and a boundary
        # does not hold in tape that moved 0.5% on 92% of 90-bar windows.
        # ⚠️ r98 — RELAXED MAY WIDEN THE EARLY SIDE, NEVER THE LATE ONE.
        # Passing LATEST_ET as `relaxed_latest` makes the 14:00 close a HARD
        # ceiling: `max(latest, relaxed_latest)` can no longer push it out. The
        # early side stays relaxable because opening earlier only produces a
        # worse-selected example of the same trade, which is what a debug
        # session wants; opening LATER produces a trade the session has no time
        # to judge, which is a different and unmeasurable thing.
        _early, _late = relaxed.window(EARLIEST_ET, LATEST_ET,
                                       relaxed_latest=LATEST_ET)
        if now_et and not (_early <= now_et <= _late):
            return None
        # ⚠️ SHORT-VOL CONDITION, inverted from the runaway trade. A credit
        # spread needs the level to HOLD. From tests/magnitude_estimator.py:
        # above 0.20% ATR the tape produced a 0.5% move on 92% of 90-bar
        # windows - a boundary does not survive that.
        # ⚠️ A NaN ATR does NOT satisfy `> MAX`, so the ceiling did not refuse.
        # Unknown ATR is permitted (the gate is optional); NON-FINITE is not.
        _atr = safe_float(atr_pct)
        if atr_pct is not None and _atr is None:
            return None
        if _atr is not None and _atr > ATR_MAX_PCT:
            logger.debug("[sweep_cs] no trade: ATR %.3f%% too hot for a "
                         "boundary to hold", atr_pct)
            return None

        sig = Signal(
            strategy_name=self.name,
            setup_type="sweep_credit_spread",
            direction="short" if side == "call" else "long",
            option_side=side,
            underlying_entry=price_now,
        )
        # the swept pool IS the short strike anchor; strike selection resolves
        # it against the live chain increment.
        # ⚠️ THE SHORT STRIKE IS THE NEAREST STRIKE PIERCED, NOT THE POOL.
        # Falls back to the pool when the sweep cleared no further strike -
        # which IS the pool on a shallow pierce, by construction.
        _inc = float(getattr(config, "STRIKE_INCREMENT", 1) or 1)
        _swept_px = float(getattr(sweep, "sweep_price", 0.0) or 0.0)
        _ps = pierced_strike(_swept_px, pool, boundary == "ceiling", _inc)
        # 🔴 r100 — NO FALLBACK TO THE POOL. The pool is a PRICE LEVEL, not a
        # strike: SPX's NY Low sat at 7639.01 on a 5-wide chain, so the anchor
        # could never resolve and r97's exact-strike lookup reported "no priced
        # put contract at the pierced strike 7639.01" on 230 consecutive ticks
        # (2026-08-24) — a log line naming a strike that does not exist.
        # ⚠️ AND `pierced_strike` ALREADY SAYS WHAT None MEANS: "the sweep
        # cleared NO strike ... there is nothing to sell, and inventing a strike
        # here would sell a level that was never tested." The fallback
        # contradicted the function it called, one line later.
        # ⚠️ THIS REMOVES TRADES, DELIBERATELY. A sweep that pierces no strike
        # is now declined with its own reason instead of dying downstream on a
        # confusing one. Counted, so the frequency is a fact rather than a guess.
        if _ps is None:
            logger.info("[sweep_cs] %s swept but the pierce cleared NO strike "
                        "(pool %.2f, sweep extreme %.2f, increment %g) - SKIP. "
                        "The short strike is the nearest strike ACTUALLY "
                        "pierced; the pool is a price, not a strike.",
                        name, pool, _swept_px, _inc)
            return None
        sig.short_anchor = _ps
        sig.pierced_strike = _ps
        sig.pool_price = pool
        sig.boundary = boundary
        sig.swept_level_name = name
        sig.sweep_age_bars = age
        sig.rejection_pct = rej
        sig.atr_pct_at_entry = atr_pct
        sig.max_loss_pct = MAX_LOSS_PCT      # 15%, tighter than the fleet 0.25

        # ── 🔴 r97 — RESOLVE THE ANCHOR INTO A REAL SPREAD ───────────────────
        # ⚠️ UNTIL NOW THIS STRATEGY COULD NOT PRODUCE A TRADEABLE SIGNAL AT
        # ALL. It set `short_anchor` and returned. `grep short_anchor` across
        # the tree found ONE writer and ZERO readers: nothing ever converted it
        # into a strike, a premium or a contract. So `is_valid` fell to the
        # default arm, needed `strike > 0 and entry_premium > 0`, and got 0.0
        # for both — every fire died one step later at main.py's
        # `Invalid signal from SweepCreditSpread`. Measured 2026-08-24: SPX 231
        # times, GOOGL 90, CRM 1.
        # ⚠️ AND IT CLAIMED THE DISPATCH SLOT ON THE WAY DOWN, because
        # `signal = sc_sig` runs ~240 lines before validation and everything
        # after it is gated on `if signal is None`. So each of those 231 SPX
        # ticks also cost the butterfly and all four credit-vertical triggers.
        # The slot half is fixed in main.py; this half builds the trade.
        #
        # Built with `credit_vertical`'s shared helpers — the module that exists
        # precisely so credit-spread math is owned by neither strategy — and in
        # `trend_credit_spread`'s idiom: short at the anchor, protective wing at
        # a fixed width, credit from short.bid - long.ask (never marks, which
        # would book a credit no fill can achieve).
        _contracts = None
        try:
            _contracts = chain.puts if side == "put" else chain.calls
        except Exception:                                      # noqa: BLE001
            _contracts = None
        if not _contracts:
            logger.info("[sweep_cs] no %s contracts on the chain - SKIP", side)
            return None

        _short = cv.find_contract_at_strike(_contracts, sig.short_anchor)
        if _short is None or not (getattr(_short, "mark", 0) or 0) > 0:
            logger.info("[sweep_cs] no priced %s contract at the pierced strike "
                        "%.2f - SKIP (the anchor is the trade; a different "
                        "strike is a different trade)", side, sig.short_anchor)
            return None

        _long_strike = (_short.strike - WING_WIDTH if side == "put"
                        else _short.strike + WING_WIDTH)
        _long = cv.find_contract_at_strike(_contracts, _long_strike)
        if _long is None or _long.strike == _short.strike:
            logger.info("[sweep_cs] no protective wing at %.2f - SKIP "
                        "(undefined risk is never sold)", _long_strike)
            return None

        # bid/ask, never mark: the credit has to be one the market would pay.
        _credit = max(0.0, (getattr(_short, "bid", 0.0) or 0.0)
                      - (getattr(_long, "ask", 0.0) or 0.0))
        if _credit <= 0:
            logger.info("[sweep_cs] %s %.2f/%.2f pays no credit (bid %.2f vs "
                        "wing ask %.2f) - SKIP", side, _short.strike,
                        _long.strike, getattr(_short, "bid", 0.0) or 0.0,
                        getattr(_long, "ask", 0.0) or 0.0)
            return None

        sig.is_credit_vertical = True
        sig.net_credit = _credit
        if side == "call":
            sig.short_call_contract, sig.long_call_contract = _short, _long
        else:
            sig.short_put_contract, sig.long_put_contract = _short, _long
        # The default `is_valid` arm and the sizer both read these.
        sig.strike = _short.strike
        sig.expiry = getattr(_short, "expiry", "")
        sig.entry_premium = _credit
        sig.contract = _short

        relaxed.tag(sig)
        logger.info("[sweep_cs] FIRE  %s swept -> %s  short %.2f / long %.2f  "
                    "credit %.2f  (pool %.2f, pierced to %.2f)  %s credit "
                    "spread  age %d bars  rejection %.3f%%",
                    name, boundary, _short.strike, _long.strike, _credit,
                    pool, _swept_px, side.upper(), age, rej * 100.0)
        return sig
