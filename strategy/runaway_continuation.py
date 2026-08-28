"""
strategy/runaway_continuation.py  v4.4
v4.4  2026-08-27  r165 — THE PLAN PREPARES, GAMMA DOES THE HEAVY LIFTING, THE
      STRATEGY BUYS. Operator, 2026-08-27: *"the symbol did not even
      entertain coming back for a retest, it just broke out & ran. We want in
      on the move, but it needs to be over quickly … purchase and wait for
      our trailing stop"* and *"Make gamma do the heavy lifting. Try to get
      just enough OTM to really leverage gamma based on the intensity of the
      move."* `prepare()` is the plan (the sweep's v4.6 shape): dormant past
      the cutoff; each declared CONDITION with its reading (ATR reachable,
      ORB broken with a direction, 1m close beyond the 50% TP and holding);
      the contract SELECTED by `gamma_leverage_pick` — over the run price has
      already made from the ORB boundary (the move's intensity, mirrored as
      the expected continuation), every liquid OTM contract's modelled gain
      δ·run + ½γ·run² per dollar of premium, the highest leverage among
      strikes reachable within the run, else the first OTM. The delta-band
      selector (DELTA_NEAR/DEEP by ATR) is retired for selection; ATR keeps
      its one job — the reachability floor. The R hurdle stays muteable here
      (a debit, no wing to search): strict vetoes, relaxed records.
      `generate_signal()` buys the prepared contract and touches no chain.
      Stops are not encoded in this revision by the operator's instruction.
v4.3  2026-08-27  r148/r149 (RECORDED RETROACTIVELY in r165): two field-name
      defects in r146's wiring fixed — `break_direction` for the handoff
      after the engine invalidates on "runaway", and `target_50pct` (the only
      name that exists; `tp50` printed "50% TP n/a" for a session).
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
    # r165: DELTA_NEAR/DEEP no longer select the strike — gamma leverage over
    # the move's own run does. Kept as the recorded prior band; not read by
    # the plan. ATR_DEEP_PCT likewise only feeds that retired band.
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
    # ⚠️ NO FALLBACK NAMES. `tp50`/`underlying_tp50` exist on NOTHING; keeping
    # them as a chain leaves the ghost in the file for the next reader to copy,
    # and check_attr_fidelity flags them. One name, the real one.
    tp50 = getattr(orb, "target_50pct", None)
    if not tp50 or not prev_close or not price_now:
        return False
    if direction == "long":
        return prev_close > tp50 and price_now > tp50
    return prev_close < tp50 and price_now < tp50


def gamma_leverage_pick(contracts, direction: str, spot: float, run: float):
    """THE STRIKE GAMMA PAYS MOST OVER THE MOVE'S OWN INTENSITY.

    Operator, 2026-08-27: *"Make gamma do the heavy lifting. Try to get just
    enough OTM to really leverage gamma based on the intensity of the move."*

    `run` is the distance price has ALREADY travelled from the ORB boundary —
    the move that proved itself — and is taken as the distance it is expected
    to keep travelling (mirrored, no fitted multiple). For every liquid OTM
    contract on the side of the move, the modelled gain over `run` is
        gain = δ·run + ½·γ·run²
    and the score is gain per dollar of premium — the leverage. The winner is
    the highest leverage among strikes REACHABLE within `run`
    (strike − spot ≤ run, "just enough OTM"); if the increments leave nothing
    inside that band, the first OTM strike. Ties go to the nearer strike.

    Returns (contract, score, candidates_considered) or (None, 0.0, 0).
    ⚠️ Reads only fields that exist on OptionContract: strike, mark, ask,
    delta, gamma (check_attr_fidelity, r150).
    """
    try:
        spot = float(spot)
        run = abs(float(run))
    except (TypeError, ValueError):
        return None, 0.0, 0
    if run <= 0:
        return None, 0.0, 0
    cands = []
    for c in contracts or []:
        try:
            k = float(c.strike)
            prem = float(getattr(c, "ask", 0) or 0) or float(getattr(c, "mark", 0) or 0)
            d = abs(float(getattr(c, "delta", 0) or 0))
            g = float(getattr(c, "gamma", 0) or 0)
        except (TypeError, ValueError, AttributeError):
            continue
        otm = (k > spot) if direction == "long" else (k < spot)
        if not otm or prem <= 0.05 or d <= 0:
            continue
        dist = abs(k - spot)
        gain = d * run + 0.5 * g * run * run
        cands.append((gain / prem, -dist, dist, c))
    if not cands:
        return None, 0.0, 0
    inside = [x for x in cands if x[2] <= run]
    pool = inside if inside else [min(cands, key=lambda x: x[2])]
    best = max(pool, key=lambda x: (x[0], x[1]))
    return best[3], best[0], len(cands)


class _RunawayPreparation:
    """What the plan hands the strategy each tick of the slot — never executable."""
    __slots__ = ("tick", "direction", "side", "tp50", "boundary", "run", "contract",
                 "premium", "leverage", "considered", "r", "conditions", "unmet",
                 "structural", "starved", "ready")

    def __init__(self, tick):
        self.tick = tick
        self.direction = self.side = ""
        self.tp50 = self.boundary = None
        self.run = 0.0
        self.contract = None
        self.premium = self.leverage = self.r = None
        self.considered = 0
        self.conditions, self.unmet, self.structural, self.starved = {}, [], [], []
        self.ready = False

    def cond(self, name, current, required, met):
        self.conditions[name] = (current, required, bool(met))
        if not met:
            self.unmet.append(name)
        self.tick.check(name, current if isinstance(current, (int, float)) else None, bool(met))

    def trade_line(self):
        if not self.ready:
            return "no trade prepared"
        c = self.contract
        return (f"buy {c.strike:g}{self.side[0].upper()} at {self.premium:.2f}  "
                f"δ {abs(float(getattr(c, 'delta', 0) or 0)):.2f} γ "
                f"{float(getattr(c, 'gamma', 0) or 0):.3f}  over a {self.run:.2f} run "
                f"-> {self.leverage:.2f}x leverage ({self.considered} strikes considered)  "
                f"stop {self.boundary:.2f} (ORB)  R {_n(self.r)}")


class RunawayContinuationStrategy:
    """Fires when the ORB has already run and held. Disarms the retest.

    🔴 THE PREMISE (operator, 2026-08-27): *"the symbol did not even entertain
    coming back for a retest, it just broke out & ran. We want in on the move,
    but it needs to be over quickly … purchase and wait for our trailing stop
    to take it off."* So the plan has the contract CHOSEN before the move
    confirms; the fire is a purchase, not a deliberation. Stops are a later
    conversation and are not encoded here.

    ⚠️ THIS STRATEGY DISARMS THE ORB RETEST ARM WHEN IT FIRES. Both cannot be
    live on the same range: the runaway IS the evidence that price never came
    back for the retest, so leaving the retest armed would leave a second
    position waiting for a pullback the tape has already declined to give.
    """
    name = "RunawayContinuation"

    CONDITIONS = {
        "entry_window":      f"before the debit cutoff {CUTOFF_ET} ET (relaxed to 14:00)",
        "atr_pct":           f"ATR >= {ATR_FLOOR_PCT:.2f}% — a move this tape can pay",
        "orb_direction":     "the ORB has BROKEN with a direction",
        "runaway_confirmed": "a 1m close beyond the 50% TP, still beyond it at this tick",
    }
    STRUCTURAL = ("contract", "stop_distance", "r")
    PLAN_CHECKS = tuple(CONDITIONS) + STRUCTURAL + (
        "price", "run", "leverage", "considered", "debit", "delta",
        "target_distance")

    def __init__(self):
        self.planner = Plan(self.name, self.PLAN_CHECKS)

    # ══════════════════════════════════════════════════════════════════════
    # THE PLAN — evaluates the declared conditions, SELECTS the contract.
    # ══════════════════════════════════════════════════════════════════════
    def prepare(self, *, orb, atr_pct, price_now, prev_close, now_et, chain=None,
                **_ignored) -> _RunawayPreparation:
        t = self.planner.tick(price_now)
        prep = _RunawayPreparation(t)
        _cut = relaxed.window("00:00", CUTOFF_ET, "00:00", "14:00")[1]
        if now_et and now_et >= _cut:
            t.dormant("entry_window", f"past the debit cutoff {_cut} — dormant until tomorrow")
            return prep
        prep.cond("entry_window", None, self.CONDITIONS["entry_window"], True)
        price_now = safe_float(price_now)
        prev_close = safe_float(prev_close)
        if not price_now or price_now <= 0 or price_now > 1e7:
            prep.starved.append("price_now")
            t.starved("price_now")
            return prep
        t.check("price", price_now, True)
        _atr = safe_float(atr_pct)
        reachable = target_delta(atr_pct) is not None
        prep.cond("atr_pct", _atr, self.CONDITIONS["atr_pct"], reachable)

        state = str(getattr(orb, "state", "") or "")
        _inval_reason = str(getattr(orb, "invalidation_reason", "") or "")
        _break_dir = str(getattr(orb, "break_direction", "") or "").lower()
        direction = ""
        if "LONG" in state.upper():
            direction = "long"
        elif "SHORT" in state.upper():
            direction = "short"
        elif _inval_reason == "runaway" and _break_dir in ("long", "short"):
            direction = _break_dir
        prep.cond("orb_direction", (1.0 if direction == "long" else -1.0) if direction else 0.0,
                  f"a broken ORB (now state {state or 'none'}"
                  f"{', invalidated: ' + _inval_reason if _inval_reason else ''})",
                  bool(direction))
        if not direction:
            # ⚠️ NAME THE INVALIDATION REASON (check_runaway_handoff RW9): a
            # disarm and a handoff look identical without it.
            t.hold(f"ORB {state or 'none'}"
                   + (f" (invalidated: {_inval_reason})" if _inval_reason else "")
                   + " carries no direction — nothing to prepare until it breaks")
            return prep
        side = "call" if direction == "long" else "put"
        prep.direction, prep.side = direction, side
        t.direction = direction
        tp50 = getattr(orb, "target_50pct", None)
        boundary = (getattr(orb, "orb_high", None) if direction == "long"
                    else getattr(orb, "orb_low", None))
        if not tp50 or not boundary:
            miss = [n for n, v in (("target_50pct", tp50), ("orb_boundary", boundary)) if not v]
            prep.starved.extend(miss)
            t.starved(*miss)
            return prep
        prep.tp50, prep.boundary = float(tp50), float(boundary)
        t.anchor(trigger=prep.tp50, invalidation=prep.boundary)
        confirmed = runaway_confirmed(orb, price_now, prev_close, direction)
        prep.cond("runaway_confirmed", 1.0 if confirmed else 0.0,
                  f"1m close beyond the 50% TP {prep.tp50:.2f} and still beyond now "
                  f"(prev close {_n(prev_close)}, now {price_now:.2f})", confirmed)

        # ── SELECTION — the contract gamma pays most over the move's run ──
        run = abs(price_now - prep.boundary)
        prep.run = run
        t.check("run", run, run > 0)
        if run <= 0:
            prep.structural.append(("stop_distance",
                f"price {price_now:.2f} is at/inside the ORB boundary {prep.boundary:.2f} — "
                f"no run to lever, no risk distance"))
        elif chain is None:
            prep.starved.append("chain")
        else:
            contracts = chain.calls if side == "call" else chain.puts
            c, lev, n = gamma_leverage_pick(contracts, direction, price_now, run)
            t.check("considered", n, n > 0)
            if c is None:
                prep.structural.append(("contract",
                    f"no liquid OTM {side} on the chain to lever a {run:.2f} run "
                    f"(mark > 0.05, delta > 0)"))
            else:
                prem = float(getattr(c, "ask", 0) or getattr(c, "mark", 0) or 0)
                t.check("contract", c.strike, True)
                t.check("leverage", lev, lev > 0)
                t.debit_directional(prem, getattr(c, "delta", 0.0), getattr(c, "gamma", 0.0),
                                    run, run, invalidation=prep.boundary, trigger=prep.tp50)
                ok, why = t.executable()          # strict vetoes R; relaxed records
                if not ok:
                    prep.structural.append(("r", why))
                else:
                    prep.contract, prep.premium, prep.leverage = c, prem, lev
                    prep.considered, prep.r = n, t.r
                    prep.ready = True
                    t.note(why)

        head = (f"ORB broke {direction} at {prep.boundary:.2f}, run {run:.2f} to "
                f"{price_now:.2f}, 50% TP {prep.tp50:.2f}")
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
    # THE STRATEGY — conditions true -> BUY the plan's contract.
    # ══════════════════════════════════════════════════════════════════════
    def generate_signal(self, *, orb, atr_pct: float, price_now: float,
                        prev_close: float, now_et: str, chain=None,
                        **_ignored) -> Optional[Signal]:
        prep = self.prepare(orb=orb, atr_pct=atr_pct, price_now=price_now,
                            prev_close=prev_close, now_et=now_et, chain=chain)
        if not prep.ready or prep.unmet or prep.structural or prep.starved:
            return prep.tick.already()
        price_now = safe_float(price_now)
        c = prep.contract
        sig = Signal(
            strategy_name=self.name,
            setup_type="runaway_continuation",
            direction=prep.direction,
            option_side=prep.side,
            underlying_entry=price_now,
            underlying_stop=prep.boundary,
            underlying_target=(price_now + prep.run if prep.direction == "long"
                               else price_now - prep.run),
            orb_range_high=getattr(orb, "orb_high", 0.0),
            orb_range_low=getattr(orb, "orb_low", 0.0),
            strike=c.strike,
            expiry=getattr(c, "expiry", ""),
            entry_premium=c.mark,
            contract=c,
        )
        sig.gamma_leverage = prep.leverage
        sig.run_at_entry = prep.run
        sig.atr_pct_at_entry = atr_pct
        sig.disarms_retest = True
        relaxed.tag(sig)
        logger.info("[runaway] FIRE %s — %s  (retest DISARMED - price never came back for it)",
                    prep.direction, prep.trade_line())
        return prep.tick.take(sig)
