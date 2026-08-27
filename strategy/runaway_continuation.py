"""
strategy/runaway_continuation.py  v4.2
v4.2  2026-08-26  r146 — THE PLAN IS WIRED, AND THE SIGNAL CAN NOW TRADE.
      (1) Every refusal goes through `self.plan` (strategy/plan.py): four
      bare `return None`s that logged nothing — window, price, ATR floor,
      ORB direction, the runaway itself — now write a DECLINE row naming
      the gate. This strategy had ZERO `_gate()` call sites (handoff table).
      (2) 🔴 P0 — THE SIGNAL WAS ALWAYS INVALID. `target_delta` was written
      here and READ NOWHERE (`grep target_delta` — one writer, zero readers,
      the r97 sweep defect exactly). The signal carried no strike, premium or
      contract, so `OptionsSignal.is_valid`'s single-leg arm (`strike > 0 and
      entry_premium > 0`) was False on every fire and main.py logged
      `Invalid signal from RunawayContinuation` and returned. The flagship v4
      entry rule could never place a trade. The contract is now resolved
      HERE against the chain the dispatcher already passes, by the existing
      delta-nearest selector, and the plan prices the what-if off that real
      contract: stop = the ORB boundary, target = the stop distance
      mirrored, R from delta/gamma over those distances.
      (3) The R hurdle is consulted: STRICT refuses below the floor, RELAXED
      records and proceeds (strategy/criteria.py owns the switch).
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
from strategy.plan import Plan, _n

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
    # 🔴 `target_50pct` — THE ONLY NAME THAT EXISTS (r149). The strategy asked
    # for `tp50` and `underlying_tp50`; NEITHER is a field on the ORB dataclass
    # (orb_engine.py:311 declares `target_50pct`, set at 1043/1064). Both
    # getattr calls returned None, so this function's `if not tp50` guard
    # refused EVERY runaway — the plan row read "no 1m close beyond the 50% TP
    # n/a", and `n/a` was the tell: the level was never read, not never crossed.
    # ⚠️ MEASURED: 2026-08-27, eight boxes sat on INVALIDATED/runaway through
    # the open (AMZN CRM CVX GOOGL META NFLX PLTR TSLA) and every one declined
    # here. r148 unblocked the direction lookup two lines up and this refused
    # them at the very next gate — the SAME defect twice in one function.
    tp50 = (getattr(orb, "target_50pct", None)
            or getattr(orb, "tp50", None)
            or getattr(orb, "underlying_tp50", None))
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

    # The plan is the INFORMER: it prices what this spec would buy, applies
    # the R hurdle, and records every check. The spec below is the decision.
    PLAN_CHECKS = ("entry_window", "price", "atr_pct", "orb_direction",
                   "runaway_confirmed", "contract", "debit", "delta",
                   "stop_distance", "target_distance", "r")

    def __init__(self):
        self.planner = Plan(self.name, self.PLAN_CHECKS)

    def generate_signal(self, *, orb, atr_pct: float, price_now: float,
                        prev_close: float, now_et: str, chain=None,
                        **_ignored) -> Optional[Signal]:
        t = self.planner.tick(price_now)
        # ── 1. window ────────────────────────────────────────────────────────
        # A runaway confirmed at 11:29 still fires; theta is survivable that
        # early and the move is in evidence. After the cutoff it is not.
        # ⚠️ RELAXED EXTENDS THE CUTOFF ONLY. The ATR gate below is NOT
        # relaxed: below 0.05% ATR the required move was reached on 0% of 5,517
        # bars. A trade that cannot pay teaches nothing about stops and only
        # adds noise to the log this mode exists to read.
        _cut = relaxed.window("00:00", CUTOFF_ET, "00:00", "14:00")[1]
        if now_et and now_et >= _cut:
            return t.refuse("entry_window",
                            f"{now_et} ET is past the debit cutoff {_cut}")
        t.check("entry_window", None, True)

        # ── 2. the ATR gate, BEFORE anything else ────────────────────────────
        # Checked first deliberately: if the tape cannot pay, nothing about the
        # setup's quality matters and the rest of the evaluation is wasted.
        price_now = safe_float(price_now)
        prev_close = safe_float(prev_close)
        if not price_now or price_now <= 0 or price_now > 1e7:
            return t.refuse("price", f"price unusable ({price_now})")
        t.check("price", price_now, True)
        delta = target_delta(atr_pct)
        t.check("atr_pct", safe_float(atr_pct), delta is not None)
        if delta is None:
            logger.debug(
                "[runaway] no trade: ATR %.3f%% below the reachable floor "
                "(%.2f%%). Measured: below 0.05%% NO strike was reached on "
                "5,517 bars.", atr_pct or 0.0, ATR_FLOOR_PCT)
            return t.refuse("atr_pct",
                            f"ATR {_n(atr_pct, '.3f')}% below the reachable floor "
                            f"{ATR_FLOOR_PCT:.2f}% (0 of 5,517 bars reached the "
                            f"required move below 0.05%)")

        # ── 3. direction comes from the ORB, not from a prediction ──────────
        # 🔴 AN INVALIDATED-BY-RUNAWAY ORB *IS* THIS STRATEGY'S TRIGGER (r148).
        # ⚠️ THE BUG THIS REPLACES DISABLED THE STRATEGY ON THE EXACT SETUP IT
        # EXISTS FOR. Direction was read by string-matching "LONG"/"SHORT"
        # inside `orb.state`. When price runs to the 50% TP without a retest the
        # engine sets `state = INVALIDATED` and `invalidation_reason =
        # "runaway"` (orb_engine.py:1134-1172) — and "INVALIDATED" contains
        # neither word, so this fell to the else and returned before step 4
        # ever asked whether a runaway had happened.
        # Measured live: NFLX 2026-08-27, broke the ORB low 80.08 at 09:41 and
        # ran to the 50% TP at 79.52 with no retest — a textbook runaway. The
        # gate read: "ORB state 'INVALIDATED' carries no direction."
        # ⚠️ THE ENGINE HAD ALREADY RECORDED EVERYTHING NEEDED. `break_direction`
        # is set at break time (orb_engine.py:1032/1055), is never cleared by
        # the INVALIDATED branch, and survives save/load (601, 542). This reads
        # the field that carries the information instead of the one that
        # happens to be a string — the same class of defect as `all()` vs
        # `all_rails()` and `oi` vs `open_interest`.
        # ⚠️ ONLY reason=="runaway" QUALIFIES. `close_inside` is the OPPOSITE
        # tape — price came back into the range — and must keep refusing here.
        state = str(getattr(orb, "state", "") or "")
        _inval_reason = str(getattr(orb, "invalidation_reason", "") or "")
        _break_dir = str(getattr(orb, "break_direction", "") or "").lower()
        if "LONG" in state.upper():
            direction, side = "long", "call"
        elif "SHORT" in state.upper():
            direction, side = "short", "put"
        elif _inval_reason == "runaway" and _break_dir in ("long", "short"):
            direction = _break_dir
            side = "call" if _break_dir == "long" else "put"
            logger.info("[runaway] ORB INVALIDATED by runaway — direction %s "
                        "taken from break_direction; this is the handoff, not "
                        "a disqualifier", direction)
        else:
            return t.refuse("orb_direction",
                            f"ORB state '{state or 'none'}'"
                            + (f" (invalidated: {_inval_reason})"
                               if _inval_reason else "")
                            + " carries no direction")
        t.direction = direction
        t.check("orb_direction", 1.0 if direction == "long" else -1.0, True)

        # ── 4. the runaway itself ────────────────────────────────────────────
        tp50 = (getattr(orb, "target_50pct", None)      # r149 — the real field
                    or getattr(orb, "tp50", None)
                    or getattr(orb, "underlying_tp50", None))
        boundary = (getattr(orb, "orb_high", None) if direction == "long"
                    else getattr(orb, "orb_low", None))
        t.anchor(trigger=tp50, invalidation=boundary)
        if not runaway_confirmed(orb, price_now, prev_close, direction):
            t.check("runaway_confirmed", 0.0, False)
            return t.refuse("runaway_confirmed",
                            f"no 1m close beyond the 50% TP {_n(tp50)} holding at "
                            f"this tick (prev close {_n(prev_close)}, now "
                            f"{price_now:.2f})")
        t.check("runaway_confirmed", 1.0, True)

        # ── 5. THE CONTRACT — resolved here, off the chain the dispatcher
        # passes, so the signal is executable and the plan prices the real
        # thing. (v4.2: `target_delta` had no reader; see the header.)
        if chain is None:
            return t.starved("chain")
        contract = None
        try:
            from data.options_chain import get_chain_fetcher
            # delta-nearest OTM selector (mark > 0.05, |delta| <= 0.55); it
            # logs under the sweep's name because that is where it was born
            contract = get_chain_fetcher().select_sweep_strike(
                chain, direction, delta)
        except Exception as exc:                                # noqa: BLE001
            logger.warning("[runaway] strike selection raised: %s", exc)
            contract = None
        if contract is None or not (getattr(contract, "mark", 0) or 0) > 0:
            t.check("contract", None, False)
            return t.refuse("contract",
                            f"no liquid {side} near |delta| {delta:.2f} on the "
                            f"chain (mark > 0.05, |delta| <= 0.55)")
        t.check("contract", contract.strike, True)

        # ── 6. THE WHAT-IF. Stop = the ORB boundary (the structure that
        # proved the move); target = the stop distance MIRRORED, no fitted
        # multiple. R from delta/gamma over those two distances.
        stop_d = (abs(price_now - float(boundary)) if boundary else None)
        if not stop_d or stop_d <= 0:
            t.check("stop_distance", stop_d, False)
            return t.refuse("stop_distance",
                            f"price {price_now:.2f} is at/inside the ORB boundary "
                            f"{_n(boundary)} — no risk distance, so no target")
        prem = float(getattr(contract, "ask", 0) or getattr(contract, "mark", 0) or 0)
        t.debit_directional(prem, getattr(contract, "delta", 0.0),
                            getattr(contract, "gamma", 0.0), stop_d, stop_d,
                            invalidation=boundary, trigger=tp50)
        ok, why = t.executable()
        if not ok:
            return t.refuse("r", why)
        t.note(why)

        sig = Signal(
            strategy_name=self.name,
            setup_type="runaway_continuation",
            direction=direction,
            option_side=side,
            underlying_entry=price_now,
            underlying_stop=float(boundary),
            underlying_target=(price_now + stop_d if direction == "long"
                               else price_now - stop_d),
            orb_range_high=getattr(orb, "orb_high", 0.0),
            orb_range_low=getattr(orb, "orb_low", 0.0),
            strike=contract.strike,
            expiry=getattr(contract, "expiry", ""),
            entry_premium=contract.mark,
            contract=contract,
        )
        # Recorded so the reachability decision is auditable after the fact
        # rather than inferred from the fill.
        sig.target_delta = delta
        sig.atr_pct_at_entry = atr_pct
        sig.disarms_retest = True

        relaxed.tag(sig)
        logger.info(
            "[runaway] FIRE %s %s %g mark=%.2f delta=%.3f  ATR=%.3f%% -> target "
            "delta %.2f  stop %.2f target %.2f  R %s  "
            "(retest DISARMED - price never came back for it)",
            direction, side, contract.strike, contract.mark,
            abs(float(getattr(contract, "delta", 0) or 0)), atr_pct, delta,
            float(boundary), sig.underlying_target, _n(t.r))
        return t.take(sig)
