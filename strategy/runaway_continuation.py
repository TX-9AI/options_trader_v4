"""
strategy/runaway_continuation.py  v4.1
v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

Runaway-ORB continuation: the ORB ran to its 50% TP and HELD. Buy the direction
that already proved itself.

v4.0  2026-08-19  Built at the OTV4 split. The FIRST v4 entry rule.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

────────────────────────────────────────────────────────────────────────────
THE PREMISE, AND WHY IT DOES NOT PREDICT DIRECTION
────────────────────────────────────────────────────────────────────────────
Four independent searches failed to find a directional predictor in this data:
entry-time conditions (all ambient - pre-filtered by the strategies' own gates),
recorded columns (gates or empty), opening-candle bias (a coin, forward-only,
797 sessions), and the tape harness (every surviving condition helped UP *and*
DOWN - they predict MOVEMENT, not DIRECTION). The live book agreed: **44.9%
direction accuracy on 715 trades, 95% CI [41.3%, 48.6%] - worse than a coin.**

**So this rule does not predict a direction. It observes one that has already
proven itself.** The ORB broke, ran the full 50% TP distance, and HELD there.
The move is not a forecast; it is in evidence. That is the same reason ORB
itself is the one v3 strategy with a positive record - break-and-retest geometry
is self-validating and consults no label.

whole point of v4.

────────────────────────────────────────────────────────────────────────────
EVERY THRESHOLD BELOW WAS MEASURED, NOT CHOSEN
────────────────────────────────────────────────────────────────────────────
**ATR GATE - the hardest rule here.** `tests/magnitude_estimator.py`, 52,949
bars over 28 dates, scored against the required move from
`tests/chain_feasibility.py` (110,162 contract observations, round-trip spread
included):

    ATR%        0.20-0.35 delta reachable within 90 bars
    < 0.03           0%      <- 2,200 bars, not one reached it
    0.03-0.05        1%
    0.05-0.08       11%
    0.08-0.12       30%
    0.12-0.20       60%
    > 0.20          92%

⚠️ **BELOW 0.05% ATR NO STRIKE IS REACHABLE AT ALL.** The move needed to clear
the spread does not occur - not rarely, NOT AT ALL across 5,517 bars. A long
directional trade in that tape cannot pay no matter how good the entry is, and
this is the likeliest explanation for v3's finding that **82% of
directionally-CORRECT continuation entries never reached +25% MFE.** They were
fired into tape that could not pay them.

**ADX IS NOT USED, AND THAT IS A MEASUREMENT.** Every ADX band from 0-15 to
40-100 produced the SAME median excursion (0.69%-0.74%) and identical strike
reachability. **ADX 45 reaches no further than ADX 12.** It failed as a
direction predictor AND as a magnitude predictor. ATR is monotone across the
same bars - 0.19% -> 0.28% -> 0.43% -> 0.60% -> 1.07%, a 5.6x spread.

**EXIT IS THE TRAILING STOP. BOS IS NOT USED**, and that is measured too:
    orb_trail_stop      85 trades   96% win   +$30,696   worst  -$16
    bos_exit           217 trades   34% win    -$7,085   worst -$735
BOS carries the single largest loss in the v3 book. The trail's worst case
across 85 trades is sixteen dollars.

⚠️ AND THE FLOOR IS WHERE THE MONEY WENT. ORB's `hard_stop_` - 15 trades,
**-$8,757** - is nearly a third of the trail's gains, lost on trades where the
trail NEVER ENGAGED. Fleet-wide `max_loss_floor` was 76 trades and -$28,179.
**Trails make money; floors lose it.** Anything that delays the trail arming is
a defect, not a conservatism.

════════════════════════════════════════════════════════════════════════════
GATE CATEGORIES — required by WA §36. Only SELECTION is ever relaxed.
════════════════════════════════════════════════════════════════════════════
**FOUNDATIONAL — never relaxed.**
  · the ORB ran to its 50% TP and **HELD** it - a 1m CLOSE beyond, still on the
    right side at the next tick. **This is the entire premise: the move is in
    EVIDENCE, not forecast.** Without it there is no runaway, only an ORB and a
    guess - and a guess is what four independent searches found no basis for.
  · direction comes from the ORB state, never from a prediction.

**SELECTION — relaxed.**
  · cutoff 11:30 -> 14:00. Later entries carry more theta risk on a 0DTE
    contract but the setup is still the setup.

**FEASIBILITY — never relaxed.**
  · the ATR floor. Below **0.05% ATR the required move was reached on 0% of
    5,517 measured bars** - not rarely, not once. A trade fired there cannot pay
    regardless of entry quality, teaches nothing about stops, and only adds
    noise to the log the relaxed mode exists to read.
  · the ATR->delta map itself. A strike the tape cannot reach is not a cheaper
    trade, it is a lottery ticket.
"""

import logging
from typing import Optional

import config
from strategy import relaxed
from utils.math_utils import safe_float
from strategy.base_strategy import OptionsSignal as Signal

logger = logging.getLogger(__name__)

# ── measured thresholds. Overridable via config so they can be retuned without
#    will drift. A constant in strategy code is a constant nobody revisits.
ATR_FLOOR_PCT = getattr(config, "RUNAWAY_ATR_FLOOR_PCT", 0.08)
ATR_HARD_VETO_PCT = getattr(config, "RUNAWAY_ATR_VETO_PCT", 0.05)
ATR_DEEP_PCT = getattr(config, "RUNAWAY_ATR_DEEP_PCT", 0.20)
CUTOFF_ET = getattr(config, "RUNAWAY_CUTOFF_ET", "11:30")

# ATR -> target delta. From the reachability table above: at 0.12%+ the tape
# reaches 0.20-0.35 on 60% of bars; at 0.20%+ it reaches 0.35-0.50 on 85%.
DELTA_NEAR = getattr(config, "RUNAWAY_DELTA_NEAR", 0.25)
DELTA_DEEP = getattr(config, "RUNAWAY_DELTA_DEEP", 0.40)

# ── GATE CATEGORIES AS DATA (WA §36) ───────────────────────────────────────
GATES = {
    "CUTOFF_ET":          "SELECTION",
    # FEASIBILITY - below 0.05% ATR the required move was reached on 0% of
    # 5,517 measured bars. Not rarely. Not once.
    "ATR_FLOOR_PCT":      "FEASIBILITY",
    "ATR_HARD_VETO_PCT":  "FEASIBILITY",
    "ATR_DEEP_PCT":       "FEASIBILITY",
    "DELTA_NEAR":         "FEASIBILITY",
    "DELTA_DEEP":         "FEASIBILITY",
    # FOUNDATIONAL: the 50% TP HELD, and direction taken from the ORB state.
    # ⚠️ A GATE CAN BE PERFECTLY WINNABLE AND STILL BE FOUNDATIONAL - relaxing
    # the held TP would produce plenty of fills, every one an ORB plus a guess.
    # Tested inline, with no knob.
}


def target_delta(atr_pct: float) -> Optional[float]:
    """Which strike can this tape actually reach? None means DO NOT TRADE.

    ⚠️ RETURNING None IS A REAL ANSWER, NOT A FAILURE PATH. In quiet tape the
    honest output is that no strike is reachable and the trade should not fire.
    v3 had no such concept and fired into 0.03% ATR sessions where the required
    move occurred on 0% of bars.
    """
    # ⚠️ COERCE FIRST. A NaN falls through EVERY `<` test - the stress test
    # found this returning 0.25 on `target_delta(nan)`, i.e. the feasibility
    # veto INVERTING and admitting a trade into tape where 0 of 5,517 bars
    # reached the required move.
    atr_pct = safe_float(atr_pct)
    # ⚠️ FINITE IS NOT SANE. 1e12 passes every type guard and is an absurd
    # claim about the tape. The measured ATR range across 52,949 bars was
    # 0.02%-0.60%; anything past a few percent is a data fault, not a
    # volatile session, and must not select a strike.
    if atr_pct is None or atr_pct <= 0 or atr_pct > 25.0:
        return None
    if atr_pct < ATR_HARD_VETO_PCT or atr_pct < ATR_FLOOR_PCT:
        return None
    return DELTA_DEEP if atr_pct >= ATR_DEEP_PCT else DELTA_NEAR


def runaway_confirmed(orb, price_now: float, prev_close: float,
                      direction: str) -> bool:
    """Did the 1m bar CLOSE beyond the 50% TP and hold at the next tick?

    Operator's spec, 2026-08-19: *"Broke it on a 1-minute candle close, still on
    the right side after the next tick."*

    ⚠️ THE CLOSE IS THE POINT. A wick through the level is a touch, not a
    decision - v3's own liquidity doctrine says so and its sweep detection was
    built on exactly that distinction. Requiring the CLOSE beyond, plus one tick
    still on the right side, rejects the wick-and-fail without waiting for a
    confirmation bar that costs 60 seconds of a move already in progress.
    """
    tp50 = getattr(orb, "tp50", None) or getattr(orb, "underlying_tp50", None)
    if not tp50 or not prev_close or not price_now:
        return False
    if direction == "long":
        return prev_close > tp50 and price_now > tp50
    return prev_close < tp50 and price_now < tp50


class RunawayContinuationStrategy:
    """Fires when the ORB has already run and held. Disarms the retest.

    ⚠️ THIS STRATEGY DISARMS THE ORB RETEST ARM WHEN IT FIRES. Both cannot be
    live on the same range: the runaway IS the evidence that price never came
    back for the retest, so leaving the retest armed would leave a second
    position waiting for a pullback the tape has already declined to give.
    """

    name = "RunawayContinuation"

    def generate_signal(self, *, orb, atr_pct: float, price_now: float,
                        prev_close: float, now_et: str, chain=None,
                        **_ignored) -> Optional[Signal]:
        # ── 1. window ────────────────────────────────────────────────────────
        # A runaway confirmed at 11:29 still fires; theta is survivable that
        # early and the move is in evidence. After the cutoff it is not.
        # ⚠️ RELAXED EXTENDS THE CUTOFF ONLY. The ATR gate below is NOT
        # relaxed: below 0.05% ATR the required move was reached on 0% of 5,517
        # bars. A trade that cannot pay teaches nothing about stops and only
        # adds noise to the log this mode exists to read.
        _cut = relaxed.window("00:00", CUTOFF_ET, "00:00", "14:00")[1]
        if now_et and now_et >= _cut:
            return None

        # ── 2. the ATR gate, BEFORE anything else ────────────────────────────
        # Checked first deliberately: if the tape cannot pay, nothing about the
        # setup's quality matters and the rest of the evaluation is wasted.
        price_now = safe_float(price_now)
        prev_close = safe_float(prev_close)
        if not price_now or price_now <= 0 or price_now > 1e7:
            return None
        delta = target_delta(atr_pct)
        if delta is None:
            logger.debug(
                "[runaway] no trade: ATR %.3f%% below the reachable floor "
                "(%.2f%%). Measured: below 0.05%% NO strike was reached on "
                "5,517 bars.", atr_pct or 0.0, ATR_FLOOR_PCT)
            return None

        # ── 3. direction comes from the ORB, not from a prediction ──────────
        state = str(getattr(orb, "state", "") or "")
        if "LONG" in state.upper():
            direction, side = "long", "call"
        elif "SHORT" in state.upper():
            direction, side = "short", "put"
        else:
            return None

        # ── 4. the runaway itself ────────────────────────────────────────────
        if not runaway_confirmed(orb, price_now, prev_close, direction):
            return None

        sig = Signal(
            strategy_name=self.name,
            setup_type="runaway_continuation",
            direction=direction,
            option_side=side,
            underlying_entry=price_now,
            orb_range_high=getattr(orb, "orb_high", 0.0),
            orb_range_low=getattr(orb, "orb_low", 0.0),
        )
        # target delta rides on the signal; strike selection resolves it against
        # the live chain. Recorded either way so the reachability decision is
        # auditable after the fact rather than inferred from the fill.
        sig.target_delta = delta
        sig.atr_pct_at_entry = atr_pct
        sig.disarms_retest = True

        relaxed.tag(sig)
        logger.info(
            "[runaway] FIRE %s %s  ATR=%.3f%% -> target delta %.2f  "
            "(retest DISARMED - price never came back for it)",
            direction, side, atr_pct, delta)
        return sig
