"""
strategy/orb_strategy.py  v4.2
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
from analysis.liquidity_mapper import LiquidityMap, LiquidityPool
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
                         liq_map: LiquidityMap,
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

        direction   = orb.break_direction
        option_side = "call" if direction == "long" else "put"
        break_level = orb.orb_high if direction == "long" else orb.orb_low
        t.direction = direction
        t.anchor(trigger=break_level, invalidation=orb.stop_level)

        liq_result = self._analyze_liquidity(
            orb, liq_map, current_price, direction, break_level
        )

        # v-nopause 2026-07-28: a named pool in the target path DOWNGRADES the
        # entry (setup_scorer: grade A -> B, smaller size). It does NOT veto and it
        # does NOT pause. The veto here was never part of the design and produced
        # behaviour nobody asked for: on 2026-07-28 it held the AVGO ORB short for
        # SIX ticks (90s) from the moment the retest confirmed, then let it fill
        # 1.4pt lower at the exhaustion low of the move (-$135.50). Waiting for the
        # obstacle to fall behind price is the worst of the three possible
        # responses. The pool is still detected, named, and journalled — it just
        # feeds the grade instead of blocking the trade.
        if liq_result["block"]:
            logger.info(
                f"ORB pool in path (DOWNGRADE, not a block): "
                f"{liq_result['block_reason']}"
            )

        target_100 = liq_result.get("adjusted_target", orb.target_100pct)
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

        if liq_result["break_is_named_level"]:
            pool_name = liq_result["break_level_name"]
            self._add_confluence(
                signal,
                f"ORB break through named level {pool_name} — sweep catalyst"
            )
            signal.conviction += 0.15

        if direction == "long" and vol_state.price_vs_vwap == "ABOVE":
            self._add_confluence(signal, "Above VWAP — bullish bias")
        elif direction == "short" and vol_state.price_vs_vwap == "BELOW":
            self._add_confluence(signal, "Below VWAP — bearish bias")

        # UNKNOWN so it could never fire - and a dead branch reads as a live
        # one to anyone auditing this file.

        if liq_result["path_clear"]:
            self._add_confluence(signal, "Liquidity path clear to target")
        if liq_result["unnamed_in_path"] > 0:
            # metric only — equal-H/L clusters are logged, NOT penalized (low quality).
            signal.notes += (
                f" | {liq_result['unnamed_in_path']} unnamed liq cluster(s) in path"
                f" (logged, no grade impact)"
            )

        if liq_result.get("target_adjusted"):
            signal.notes += (
                f" | Target adjusted to {target_100:.2f} "
                f"(named level {liq_result['target_adj_reason']} just beyond TP)"
            )

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
        target_strike = orb.target_strike
        if liq_result.get("target_adjusted"):
            from utils.math_utils import round_to_strike
            from config import STRIKE_INCREMENT
            target_strike = round_to_strike(target_100, STRIKE_INCREMENT)

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
            f"break_is_named={liq_result['break_is_named_level']} "
            f"path_clear={liq_result['path_clear']} "
            f"target_adjusted={liq_result.get('target_adjusted', False)} "
            f"fed_day={macro.is_fed_day} "
            f"confluence={signal.confluence_factors}"
        )
        return t.take(signal)

    # ─── Liquidity Analysis ───────────────────────────────────────────────────

    def _analyze_liquidity(self, orb, liq_map, current_price,
                            direction, break_level) -> dict:
        result = {
            "break_is_named_level": False,
            "break_level_name":     "",
            "block":                False,
            "block_reason":         "",
            "path_clear":           True,
            "named_in_path":        0,
            "unnamed_in_path":      0,
            # v-namelevels 2026-07-28: identities, not just counts. "1 named
            # level(s)" told us NOTHING when this gate held an AVGO ORB entry for
            # 6 straight ticks (90s) and the trade filled 1.4pt late at the low.
            "named_in_path_detail":   [],   # [(name, price), ...] in the fakeout zone
            "unnamed_in_path_detail": [],   # [price, ...] equal-H/L clusters (metric only)
            "target_adjusted":      False,
            "adjusted_target":      orb.target_100pct,
            "target_adj_reason":    "",
        }

        orb_width  = orb.orb_width
        target_100 = orb.target_100pct
        target_50  = orb.target_50pct

        for pool in liq_map.pools:
            if pool.swept:
                continue

            pool_price = pool.price
            is_named   = pool.is_named
            pool_name  = pool.name or "unnamed"

            prox = abs(pool_price - break_level) / max(break_level, 1)
            if is_named and prox <= BREAK_LEVEL_PROXIMITY_PCT:
                result["break_is_named_level"] = True
                result["break_level_name"]     = pool_name
                continue

            is_obstacle_kind = (
                (direction == "long"  and pool.kind == "high") or
                (direction == "short" and pool.kind == "low")
            )
            if not is_obstacle_kind:
                continue

            in_danger_zone = (
                (direction == "long"  and current_price < pool_price < target_50) or
                (direction == "short" and target_50 < pool_price < current_price)
            )
            if in_danger_zone and is_named:
                result["named_in_path"] += 1
                result["named_in_path_detail"].append((pool_name, float(pool_price)))
                result["path_clear"]     = False

            in_full_path = (
                (direction == "long"  and current_price < pool_price < target_100) or
                (direction == "short" and target_100 < pool_price < current_price)
            )
            if in_full_path and not is_named:
                # v-obs: equal-H/L (unnamed) clusters are LOW QUALITY and no longer
                # penalize the ORB — they do NOT flip path_clear. We still COUNT them
                # (metric only) so we can later study whether they matter at scale.
                # Only NAMED pools (PDH/PDL/session) affect path_clear / grade.
                result["unnamed_in_path"] += 1
                result["unnamed_in_path_detail"].append(float(pool_price))

            adj_zone_long  = (direction == "long"  and
                              target_100 < pool_price < target_100 + orb_width * BEYOND_TP_ADJUSTMENT_WIDTHS)
            adj_zone_short = (direction == "short" and
                              target_100 - orb_width * BEYOND_TP_ADJUSTMENT_WIDTHS < pool_price < target_100)

            if is_named and (adj_zone_long or adj_zone_short) and not result["target_adjusted"]:
                result["target_adjusted"]   = True
                result["adjusted_target"]   = pool_price
                result["target_adj_reason"] = pool_name

        if result["named_in_path"] > 0 and not result["break_is_named_level"]:
            result["block"]        = True
            _named = ", ".join(f"{n}@{px:.2f}" for n, px in result["named_in_path_detail"]) \
                     or "(unidentified)"
            result["block_reason"] = (
                f"Named pool in fakeout zone (entry→50%TP): "
                f"{result['named_in_path']} named level(s): {_named} "
                f"[entry={current_price:.2f} 50%TP={target_50:.2f} dir={direction}]"
            )

        return result
