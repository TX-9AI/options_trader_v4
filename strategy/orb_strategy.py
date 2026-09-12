"""
strategy/orb_strategy.py  v4.6
v4.6  2026-09-12  r365 — THE ORB NO LONGER KNOWS ABOUT LEVELS, AT ALL.
      Operator, 2026-09-12: *"the orb trade does not need to know about any
      levels… I used to give it awareness of the levels to avoid fake outs, but
      even that knowledge didn't prevent them."* The whole liquidity read goes:
      the map parameter, the analysis helper, the confluence line and its
      conviction bump, the path notes, and the strike branch.
      🔴 IT WAS NOT ALL RECORD-ONLY, AND THE BACKLOG SAID IT WAS. ORB.4 records
      the pool as recorded-not-applied since r193 — true of the target, whose
      pull was removed then, and FALSE of the strike: a pool just beyond the TP
      re-derived it through `round_to_strike` rather than the engine's own
      `orb_strike_selection`, on the global increment BFLY.3 measured wrong for
      every non-$1 ladder. 📊 THAT BRANCH FIRED ON 10 OF 115 ORB TRADES over
      2026-09-01..09-11 (8.7%), so this changes which contract is bought and
      landed on a weekend per WORKING_AGREEMENT §38.8.
      ⚠️ WHAT IS LOST IS NOTES, NOT EVIDENCE: the recorded fields were read ONLY
      inside this file — no plan row, no journal, no report — and the same
      question is answerable by joining `level_ledger` to the trades, which is
      how the 2026-09-11 liquidity study ran.
      Gated by check_orb_window W5/W6 (rewritten WITH the ruling, anchored on
      code shape per §20) and check_orb_sequence S4.
v4.5  2026-09-04  r235 — 🔴 THE GATE ASKS "HAS THIS CONFIRMATION
      FIRED", NOT "HAS ANY". `confirmation_spent()` is EXTRACTED to module
      level so the checker drives it rather than a copy (C.23). `>=` not `==`,
      so an out-of-order restore fails SHUT; and the `_c > 0` guard means the
      latch does not depend on the state gate for its correctness.
v4.4  2026-09-01  r207 — ONE CONFIRMATION, ONE ORDER, AND THE GEOMETRY COMES
      FROM THE ENGINE. This file gated on `orb.state` ALONE, so anything
      holding an OPEN_* object fired every tick it was asked. On 2026-09-01
      QQQ took two ORB shorts off one confirmation because main.py held a
      stale ORBData across the manage→entry seam and this gate had nothing
      else to say no with. It now refuses a confirmation whose
      `order_placed` latch is set, which is true in paper and live alike.
      The signal also carries `orb_stop_distance_px` — the boundary-to-wick
      distance frozen at the break — so the sizer stops recomputing it from
      the live price at the entry seam.
v4.3  2026-08-30  r193 — POOL IN PATH IS RECORD-ONLY. A named pool within
      BEYOND_TP_ADJUSTMENT_WIDTHS past the 100% target used to PULL the
      target to that pool. Operator's ruling: record it, do not let it move
      the trade. Detection, the counted clusters and the notes all stay, so
      the effect can be studied later; the target is now the pure measured
      move. ⚠️ The pull was a grading-era survivor that CHANGED WHAT THE
      TRADE DOES while reading like an annotation.
v4.2  2026-08-26  r146 — RECORDED THROUGH THE PLAN, ZERO HURDLES. Operator,
      2026-08-26: *"Include orb in that, zero hurdles."* The three refusals
      this file makes AFTER the engine confirms (no contract, zero premium,
      ATR below the reachable floor) and the fire itself now write a
      plan_tick row through `self.planner` (strategy/plan.py, `record_only`).
      ⚠️ NOTHING GATES. `executable()` is never called on this plan; no R
      hurdle, no geometry, no window is applied to ORB. The 2026-08-25 ruling
      — *"leave orb alone. That one can't get encumbered with extra hurdles"*
      — stands; this is narration of decisions the file already made, so
      "why did ORB not fire this morning" has an answer in the table. The
      engine-state-not-confirmed case is recorded by main.py, which is the
      only place that knows the engine was not asked.
v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).


v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

strategy/orb_strategy.py — ORB break-and-retest signal generation.
v3.0 — original release
populate orb_range_high/low on signal so exit_engine
        can apply strategy-aware ORB stop logic
update state check for orb_engine v1.1 rename:
        CONFIRMED_LONG/SHORT -> OPEN_LONG/SHORT
repo-wide v3.0 bump: Yahoo-Finance purge & data stream
        mapping optimization (all market data now flows from the single
        shared TastyTrade candle feed — see data/candle_feed.py). No logic
        change in this file.
Liquidity-aware ORB logic:
RULE 1 — Named level IS the break level (catalyst, not obstacle):
  If the ORB high/low sits within 0.15% of a named pool (PDH, PDL, session H/L),
  and the break direction is THROUGH that level, this is a high-quality setup.
  The sweep of that level IS the ORB catalyst. Add confluence, don't penalize.
RULE 2 — Named level in path between entry and 50% TP (hard reduce):
  A named pool sitting between entry and the trail-activation level is a known
  reversal zone. Require at least one extra confluence factor, OR block.
RULE 3 — Named level just beyond 100% TP (adjust target, don't block):
  If a named pool sits within 0.5 ORB-widths past the 100% TP, move the target
  to that pool price rather than projecting past it.
v-namelevels (2026-07-28) — the liquidity gate NAMES the levels it blocks on.
        Was: "Named pool in fakeout zone (entry->50%TP): 1 named level(s)." — a bare
        count, unauditable. On 2026-07-28 this gate held the AVGO ORB short for SIX
        consecutive ticks (13:42:15 -> 13:43:30, 90s) starting the same tick the
        retest confirmed; the trade finally filled at 372.11 — 1.4pt below the
        confirmation and 0.5pt off the absolute low — then reversed and stopped out
        (-$135.50). The block never said WHAT it blocked on. Now logs name@price for
        every pool in the fakeout zone plus entry/50%TP/direction, and carries
        named_in_path_detail / unnamed_in_path_detail on the result for callers.
        NOTE: this is OBSERVABILITY ONLY — the gate behaviour is unchanged. What the
        block SHOULD do (skip / trade-to-pool / enter reduced) is still open.
"""

import logging
import config
from typing import Optional, List, Tuple

from strategy.base_strategy import BaseOptionsStrategy, OptionsSignal
# ⚠️ `_n` renders an absent value as "n/a" and never raises — the ORB sequence
# below prints levels that can legitimately be None before the range forms.
from strategy.plan import Plan, _n
from analysis.orb_engine import ORBData, ORBState
from analysis.market_state import MarketState
from analysis.volatility_engine import VolatilityState
from data.options_chain import OptionsChain
from data.options_chain import get_chain_fetcher
from data.macro_data import MacroSnapshot
from config import FED_DAY_ORB_BOOST, INSTRUMENT, MAX_LOSS_PCT

logger = logging.getLogger(__name__)

# ⚠️ FEASIBILITY FLOOR. Below this ATR the target is unreachable - measured, not
# chosen. Config-overridable because it was measured on 28 sessions in ONE
ORB_ATR_FLOOR_PCT = getattr(config, "ORB_ATR_FLOOR_PCT", 0.05)

# ── GATE CATEGORIES AS DATA (WA §36) ───────────────────────────────────────
# ⚠️ ORB HAS NO SELECTION GATES AND THEREFORE NOTHING TO RELAX. Every condition
# is either the setup itself or a veto. That is why it does not import
# `relaxed` - and why the relaxed toggle cannot loosen the one strategy with a
# positive record. **The break and retest are the trade; there is no worse
# version of them to fire on.**
GATES = {
    "ORB_ATR_FLOOR_PCT": "FEASIBILITY",
    # FOUNDATIONAL, all tested inline with no knob:
    #   the ORB engine armed (a break AND a retest: wick back inside the range,
    #     body still outside - `low < orb_high and body_low >= orb_high`)
    #   direction from the ORB state
    #   the liquidity path to target not blocked by a named level
}

BREAK_LEVEL_PROXIMITY_PCT   = 0.0015
NAMED_IN_PATH_ORB_WIDTHS    = 1.5
BEYOND_TP_ADJUSTMENT_WIDTHS = 0.5


def confirmation_spent(orb) -> bool:
    """Has THIS confirmation already produced an order?

    🔴 r235 — EXTRACTED SO THE CHECKER DRIVES IT AND NOT A COPY (C.23). As
    an inline comparison it was untestable, and a test that re-implements the
    arithmetic it pins tests itself — the r181 sizing checker stayed green for
    two days doing exactly that.
    ⚠️ `>=`, NOT `==`. If a seq were ever restored out of order from a
    persisted snapshot, `==` would fail OPEN and re-fire; `>=` fails shut.
    ⚠️ AND `_c > 0` MATTERS: before any confirmation both are 0, and 0 >= 0
    would refuse a setup that has never fired. The state gate already blocks
    that case, but a latch that depends on ANOTHER gate for its correctness is
    one refactor away from being wrong.
    """
    _c = int(getattr(orb, "confirmation_seq", 0) or 0)
    _o = int(getattr(orb, "order_placed_seq", 0) or 0)
    return _c > 0 and _o >= _c


def _confirmed_epoch(orb) -> float:
    """`confirmed_at` as an epoch, or 0.0. Never raises: this feeds an
    observation, and an observation must not break an entry."""
    raw = str(getattr(orb, "confirmed_at", "") or "").strip()
    if not raw:
        return 0.0
    try:
        from datetime import datetime as _dt
        return _dt.fromisoformat(raw).timestamp()
    except Exception:                                          # noqa: BLE001
        return 0.0


class ORBStrategy(BaseOptionsStrategy):
    """
    Opening Range Breakout strategy.
    Liquidity-aware: distinguishes catalyst sweeps from obstacle sweeps.
    """

    # RECORD ONLY. ORB opens its own plan_ledger rows (main.py's open_plan
    # calls stand), so `self_ledgers=True`; `record_only=True` documents that
    # its verdict is never consulted.
    # 🔴 THE WHOLE ORB SEQUENCE IS RECORDED, NOT JUST THE STATE LABEL (r153).
    # Operator, 2026-08-27: *"I want the entire ORB sequence writing to the per
    # tick log."*
    # ⚠️ WHAT WAS WRONG: the plan wrote one line — "ORB engine is
    # WAITING_FOR_BREAK/ARMED_SHORT/EXPIRED" — and nothing about the GEOMETRY
    # that produced it. UNH on 2026-08-27 logged 70 ticks ARMED_SHORT and one
    # TAKE, with no record of where the break was, how deep the retest went, or
    # what the engine was waiting for. When the operator sees a qualifying
    # break+retest on the chart and the bot does not take it, the table could
    # not say why. Every field below already exists on ORBData and was simply
    # never read.
    PLAN_CHECKS = ("engine_state", "orb_high", "orb_low", "orb_width",
                   "break_direction", "break_close", "bars_since_break",
                   "retest_depth_px", "attempt_number", "stop_level",
                   "target_50pct", "target_100pct",
                   # r207 — both declared so the row can say WHY a confirmed
                   # setup did not produce an order. `stop_distance_px` is the
                   # number the size ramps on and is recorded whether or not
                   # the trade fires.
                   "stop_distance_px", "order_already_placed",
                   "contract", "premium", "atr_pct")

    def __init__(self):
        self.planner = Plan("ORBStrategy", self.PLAN_CHECKS,
                         record_only=True, self_ledgers=True)

    @property
    def name(self) -> str:
        return "ORBStrategy"

    def generate_signal(self,
                         orb: ORBData,
                         ms: MarketState,
                         vol_state: VolatilityState,
                         chain: OptionsChain,
                         macro: MacroSnapshot,
                         current_price: float) -> Optional[OptionsSignal]:
        t = self.planner.tick(current_price)

        # ── 🔴 NARRATE THE SEQUENCE FIRST, EVERY TICK, WHATEVER THE STATE ────
        # These are recorded BEFORE the gate so a refusal carries the geometry
        # with it. A row that says only "ARMED_SHORT" cannot be argued with;
        # one that says "armed short at 396.01, broke to 395.40, 3 bars since,
        # retest 0.22 deep, attempt 2" can be checked against the chart.
        _bd = getattr(orb, "break_direction", "") or ""
        t.check("orb_high", getattr(orb, "orb_high", None))
        t.check("orb_low", getattr(orb, "orb_low", None))
        t.check("orb_width", getattr(orb, "orb_width", None))
        t.check("break_direction", 1.0 if _bd == "long"
                else -1.0 if _bd == "short" else None)
        t.check("break_close", getattr(orb, "break_candle_close", None))
        t.check("bars_since_break", getattr(orb, "bars_since_break", None))
        t.check("retest_depth_px", getattr(orb, "retest_depth_px", None))
        t.check("attempt_number", getattr(orb, "attempt_number", None))
        t.check("stop_level", getattr(orb, "stop_level", None))
        t.check("stop_distance_px", getattr(orb, "stop_distance_px", None))
        t.check("target_50pct", getattr(orb, "target_50pct", None))
        t.check("target_100pct", getattr(orb, "target_100pct", None))

        if orb.state not in (ORBState.OPEN_LONG, ORBState.OPEN_SHORT):
            # ⚠️ THE REASON NAMES WHAT IT IS WAITING FOR, not just where it is.
            _lvl = (getattr(orb, "orb_high", None) if _bd == "long"
                    else getattr(orb, "orb_low", None))
            _st = str(orb.state)
            if "WAITING" in _st:
                _await = (f"no break yet of {_n(getattr(orb,'orb_high',None))}/"
                          f"{_n(getattr(orb,'orb_low',None))}")
            elif "ARMED" in _st:
                _await = (f"broke {_bd or '?'} at {_n(_lvl)}, close "
                          f"{_n(getattr(orb,'break_candle_close',None))}, "
                          f"{getattr(orb,'bars_since_break',0)} bars since — "
                          f"AWAITING RETEST (wick into the range, body outside)")
            elif "INVALIDATED" in _st:
                _await = (f"invalidated: "
                          f"{getattr(orb,'invalidation_reason','') or 'unknown'}"
                          f" (attempt {getattr(orb,'attempt_number','?')})")
            elif "EXPIRED" in _st:
                _await = "past the 11:00 ET cutoff — no further ORB entries"
            else:
                _await = "state carries no further detail"
            return t.refuse("engine_state",
                            f"ORB {_st} — {_await}")
        t.check("engine_state", None, True)

        # ── 🔴 r207 — ONE CONFIRMATION, ONE ORDER ────────────────────────────
        # Checked AFTER the state gate so the refusal is distinguishable from
        # "not confirmed", and BEFORE anything is priced so a spent setup never
        # reaches the chain. r195 made `_orb_offer_working()` the duplicate
        # suppressor; that reads a table paper never writes, so paper had no
        # suppressor at all. This latch is a property of the CONFIRMATION, so
        # it is mode-independent — and `_rearm()` replaces ORBData wholesale,
        # so a genuine next attempt is unaffected by construction.
        # 🔴 r235 — KEYED TO THE CONFIRMATION, NOT TO THE SESSION. The bare
        # boolean could only say "an order happened at some point", so the
        # armed path had to clear it globally (r227) for the setup to fire
        # again — and a global clear is indistinguishable from never having
        # been set. Comparing sequences answers the real question: has THIS
        # retest already produced an order? A fresh retest bumps
        # `confirmation_seq` and re-opens the gate by construction; a resolved
        # trade with no new retest leaves them equal and stays shut.
        _cseq = int(getattr(orb, "confirmation_seq", 0) or 0)
        if confirmation_spent(orb):
            return t.refuse(
                "order_already_placed",
                f"attempt #{getattr(orb, 'attempt_number', '?')}, confirmation "
                f"#{_cseq} has already produced an order — THIS confirmation is "
                f"SPENT. The next order needs a fresh qualifying retest (wick "
                f"into {_n(getattr(orb, 'orb_low', None))}-"
                f"{_n(getattr(orb, 'orb_high', None))}, close back outside); a "
                f"CLOSE inside the range ends the thesis and waits for a new "
                f"break.")
        t.check("order_already_placed", None, True)

        direction   = orb.break_direction
        option_side = "call" if direction == "long" else "put"
        break_level = orb.orb_high if direction == "long" else orb.orb_low
        t.direction = direction
        t.anchor(trigger=break_level, invalidation=orb.stop_level)

        # 🔴 r193 — POOL IS RECORD-ONLY. Operator, 2026-08-29: pool presence is
        # "recorded but not influence the entry or target location. We can
        # evaluate its effects later on." The target is the pure measured
        # move; `adjusted_target` is still COMPUTED and still written to the
        # notes and the plan row, so the study is possible later, but it no
        # longer moves where the trade aims. A grading-era survivor that
        # changed what the trade DOES while looking like an annotation.
        target_100 = orb.target_100pct
        target_50  = orb.orb_high + (target_100 - orb.orb_high) * 0.5 \
                     if direction == "long" \
                     else orb.orb_low - (orb.orb_low - target_100) * 0.5

        signal = OptionsSignal(
            strategy_name     = self.name,
            setup_type        = f"ORB {direction.title()}",
            direction         = direction,
            option_side       = option_side,
            underlying_entry  = current_price,
            underlying_stop   = orb.stop_level,
            underlying_target = target_100,
            underlying_tp50   = target_50,
            # ── ORB range boundaries for strategy-aware exit ──────────────────
            orb_range_high    = orb.orb_high,
            orb_range_low     = orb.orb_low,
            # r207 — FROZEN AT THE BREAK, not recomputed at the fill. The
            # sizer reads this; see analysis/orb_engine.py v4.6.
            orb_stop_distance_px = float(getattr(orb, "stop_distance_px", 0.0) or 0.0),
            # r120 — carried from the engine's own counter, not recomputed.
            # r120 — the tape window opens at the CONFIRMED BREAK, so the
            # measurement spans the fight over the level rather than the fire
            # instant. `confirmed_at` is an ET string; parsed to epoch here
            # because the consumer needs a number and this is where the
            # timezone context lives.
            orb_break_ts      = _confirmed_epoch(orb),
            atr_at_signal     = float(getattr(vol_state, "atr", 0.0) or 0.0),
            # - which is exactly why it kept working while every gated strategy
            # degraded, and why it is the one v3 strategy with a positive
            # record (orb_trail_stop 96% / 85 trades / +$30,696, worst -$16).
            # The label is no longer stamped: writing one the engine did not
            # compute puts a fabricated field on the trade record where a
            # reader will take it for an observation.
            vix_at_signal     = macro.vix,
            is_fed_day        = macro.is_fed_day,
            stop_loss_pct     = MAX_LOSS_PCT,
            tp_pct            = 1.0,
        )

        # ── Base confluence ───────────────────────────────────────────────────
        self._add_confluence(signal, f"ORB break confirmed ({direction})")
        self._add_confluence(signal, "Break+retest pattern (1m body/wick rules)")

        if direction == "long" and vol_state.price_vs_vwap == "ABOVE":
            self._add_confluence(signal, "Above VWAP — bullish bias")
        elif direction == "short" and vol_state.price_vs_vwap == "BELOW":
            self._add_confluence(signal, "Below VWAP — bearish bias")

        # UNKNOWN so it could never fire - and a dead branch reads as a live
        # one to anyone auditing this file.

        if macro.is_fed_day:
            self._add_confluence(
                signal, f"Fed day: {macro.fed_event_name} (+confluence)"
            )
            signal.conviction += FED_DAY_ORB_BOOST

        # confirmatory by construction - a leaky integrator over argmax
        # agreement is only confident once winning has already persisted - and
        # it is permanently 0.0 in v4, so this line added nothing while looking
        # like it added something.
        # ⚠️ THE REMAINING `signal.conviction` ADDITIONS ARE STRUCTURAL FACTS
        # describe the setup; they do not authorise it.
        signal.adx_at_signal = ms.adx
        signal.flat_angle_deg = getattr(ms, 'flat_angle_deg', 0.0) or 0.0

        # ⚠️ v4.0: THE CONFLUENCE GATE IS GONE, AND IT COULD NEVER FAIL.
        # Two factors were required; two are added UNCONDITIONALLY above ("ORB
        # break confirmed" and "Break+retest pattern"), so the bar was met
        # before any optional factor was considered. **A gate that cannot
        # refuse is a gate in name only** - it reads as a safeguard to anyone
        # auditing the file and provides none.
        # Confluence was also the scoring model v4 abandoned: conditions are
        # structural now, and they either hold or they do not.

        # ── Strike selection ──────────────────────────────────────────────────
        # 🔴 r365 — THE STRIKE COMES FROM THE ENGINE, ALWAYS. Until now a pool
        # sitting just beyond the TP re-derived it as
        # `round_to_strike(target_100, STRIKE_INCREMENT)` instead, which is a
        # DIFFERENT function from `orb_strike_selection(...)` and leaned on the
        # global increment BFLY.3 measured wrong for every non-$1 ladder.
        # 📊 IT FIRED ON 10 OF 115 ORB TRADES over 2026-09-01..09-11 (8.7%), so
        # this is the one part of removing ORB's level awareness that changes
        # which contract is bought — which is why it landed on a weekend (§38.8).
        target_strike = orb.target_strike

        contract = get_chain_fetcher().select_orb_strike(
            chain, direction, target_strike
        )
        if contract is None:
            logger.warning("ORB: no valid option contract found")
            return t.refuse("contract", f"no valid {option_side} contract near "
                                        f"target strike {target_strike}")
        t.check("contract", contract.strike, True)

        signal.strike        = contract.strike
        signal.expiry        = contract.expiry
        signal.entry_premium = contract.mark
        signal.contract      = contract

        # ── v4.0: REACHABILITY, NOT `premium > 0` ───────────────────────────
        # A zero-premium check only catches a contract with no quote. The real
        # question is whether the TAPE CAN REACH THE TARGET, which is what the
        # ATR map answers for RunawayContinuation and which ORB had no
        # equivalent of.
        # `tests/magnitude_estimator.py`, 52,949 bars over 28 dates: below
        # **0.05% ATR the required move was reached on 0% of 5,517 bars** - not
        # rarely, not once. `tests/chain_feasibility.py`, 110,162 contract
        # observations, sets what "required" means: a 0.20-0.35 delta 0DTE
        # contract needs ~0.75% including the round-trip spread.
        # ⚠️ FEASIBILITY, NOT SELECTION - it says the trade CANNOT PAY, however
        # clean the break and retest were.
        if signal.entry_premium <= 0:
            logger.warning("ORB: option has zero premium - skipping")
            return t.refuse("premium", f"{option_side} {contract.strike} has zero premium")
        t.check("premium", signal.entry_premium, True)
        # 🔴 r96 — READ THE PERCENT FIELD, NOT THE FRACTION. This line read
        # `atr_normalized` (atr/price, a FRACTION) and compared it against
        # ORB_ATR_FLOOR_PCT, which is 0.05 meaning 0.05 PERCENT. The gate
        # therefore demanded a 5% intraday ATR and REFUSED EVERY ORB THE FLEET
        # EVER CONFIRMED. NFLX 2026-08-24: clean break+retest at 09:58 ET, strike
        # priced, then "ATR 0.004% below the reachable floor" every tick to the
        # cutoff — true ATR 0.4%, eight times ABOVE the floor.
        # ⚠️ FALLBACK IS ×100 OF THE FRACTION, NOT 0.0. A box part-way through a
        # bake has the old VolatilityState without `atr_pct`; defaulting to 0.0
        # would make `_atr_pct` falsy, skip the gate entirely, and let a trade
        # through on an UNMEASURED ATR — turning a feasibility veto into a
        # silent pass. The conversion is exact, so the fallback is the same
        # number by another route.
        _atr_pct = float(getattr(vol_state, "atr_pct", None)
                         or (float(getattr(vol_state, "atr_normalized", 0.0) or 0.0)
                             * 100.0))
        t.check("atr_pct", _atr_pct or None,
                None if not _atr_pct else _atr_pct >= ORB_ATR_FLOOR_PCT)
        if _atr_pct and _atr_pct < ORB_ATR_FLOOR_PCT:
            logger.info(
                "ORB: NO TRADE - ATR %.3f%% is below the reachable floor "
                "(%.2f%%). Measured: below 0.05%% no strike was reached on any "
                "of 5,517 bars, so the target cannot pay regardless of setup "
                "quality.", _atr_pct, ORB_ATR_FLOOR_PCT)
            return t.refuse("atr_pct", f"ATR {_atr_pct:.3f}% below the reachable "
                                       f"floor {ORB_ATR_FLOOR_PCT:.2f}% — the "
                                       f"target cannot pay")

        logger.info(
            f"🎯 ORB SIGNAL {direction.upper()}: "
            f"underlying={current_price:.2f} "
            f"orb={orb.orb_low:.2f}–{orb.orb_high:.2f} "
            f"width={orb.orb_width:.2f} "
            f"option={option_side.upper()} {contract.strike} "
            f"mark=${contract.mark:.2f} delta={contract.delta:.3f} "
            f"stop={orb.stop_level:.2f} target={target_100:.2f} "
            f"fed_day={macro.is_fed_day} "
            f"confluence={signal.confluence_factors}"
        )
        return t.take(signal)

    # ─── Liquidity Analysis ───────────────────────────────────────────────────
