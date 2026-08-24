"""
strategy/daily_fork_credit_spread.py  v1.1
v1.1  2026-08-24  r100 — `is_iron_condor=True` in the constructor is not a field
      (it is a property alias); the 1d fork leg raised TypeError on every fire.
      Now sets is_credit_vertical.
v1.0  2026-08-24  NEW. The fourth credit-spread trigger: a call or put vertical
      sold when price reaches a DAILY pitchfork tine.

      Same mechanics as IronCondorStrategy but anchored to the 1d frame rather
      than 1h. The daily fork is structurally more stable (each bar is a full
      session; the rails change slowly) but has shallower intraday movement —
      the tines are typically further from current price and less frequently
      hit. When they ARE hit, premium is rich by construction.

      WHY DAILY:
        · The 1h fork was the operator's ruling of 2026-08-22 because 1d rails
          had data-availability gaps on some boxes. That concern is about the
          fork BUILDING — once it's built, its tines are valid anchor points.
        · A daily fork tine represents a multi-session structural boundary.
          Price near it means rich premium with strong confluence. Exactly the
          condition for a credit spread.
        · The daily fork's slope matters: it is per-DAY, so within a 6.5h
          session the tine moves by at most ~slope/bar × 0.27 bars ≈ small.
          Still recomputed live (via the trigger map) for correctness.

      DESIGN:
        · Reads rails from ctx["condor_triggers"] (1d entries) — the trigger
          map already called rails_for("1d") this tick.
        · Strike selection: select_beyond_rail with the daily upper/lower rail
          as the anchor. Same POP gate, same width gate, same session-extreme
          guard as the 1h fork.
        · condor_trigger_source = "1d_fork" for grading.
        · Each signal is INDEPENDENT AND STANDALONE. The condor that may form
          if a complementary spread fires is allowed, never expected.
        · Entry window: same as IronCondorStrategy (CONDOR_ENTRY_START_ET /
          CONDOR_ENTRY_CUTOFF_ET). Override-able by DAILY_FORK_CS_START_ET /
          DAILY_FORK_CS_CUTOFF_ET.

      GATE CATEGORIES (WA §36 — same as IronCondorStrategy):
        FOUNDATIONAL: daily fork must be constructible; strike beyond rail;
                      not exceeded by session extreme.
        FEASIBILITY:  POP >= CONDOR_MIN_POP; quote width <= CONDOR_MAX_QUOTE_WIDTH;
                      EM breathing room (CONDOR_EM_FLOOR_FRAC).
        SELECTION:    entry window; VIX gate; guardrail mult.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from zoneinfo import ZoneInfo

from strategy import credit_vertical as cv
from strategy.base_strategy import BaseOptionsStrategy, OptionsSignal
from analysis.market_state import MarketState
from analysis.volatility_engine import VolatilityState
from data.options_chain import OptionContract, OptionsChain
from data.macro_data import MacroSnapshot
from config import (
    CONDOR_WING_WIDTH_SPX, CONDOR_WING_WIDTH_QQQ,
    CONDOR_EXPECTED_MOVE_GUARDRAIL_MULT,
    CONDOR_EM_FLOOR_FRAC,
    CONDOR_NICKEL_CLOSE, CONDOR_STOP_LOSS_PCT,
    CONDOR_ENTRY_START_ET, CONDOR_ENTRY_CUTOFF_ET,
    HARD_CLOSE_ET,
    CONDOR_MIN_POP, CONDOR_POP_BAR_MIN,
    CONDOR_MAX_QUOTE_WIDTH,
    STRIKE_INCREMENT, INSTRUMENT, VIX_BUTTERFLY_DISABLE,
)
import os

logger = logging.getLogger(__name__)
ET = ZoneInfo("US/Eastern")

# Gate categories (WA §36)
GATES = {
    # FOUNDATIONAL — never relaxed. Relax one and this stops being the trade.
    "CONDOR_REQUIRE_FORK":                 "FOUNDATIONAL",  # daily fork must exist
    "CONDOR_EM_FLOOR_FRAC":                "FEASIBILITY",   # breathing room
    "CONDOR_EXPECTED_MOVE_GUARDRAIL_MULT": "FEASIBILITY",   # absurd-skew reject
    "CONDOR_MIN_POP":                      "FEASIBILITY",   # P(safe) floor
    "CONDOR_MAX_QUOTE_WIDTH":              "FEASIBILITY",   # quote quality
    "CONDOR_WING_WIDTH_SPX":               "SELECTION",     # wing width
    "CONDOR_WING_WIDTH_QQQ":               "SELECTION",
}

# Separate env overrides so the daily fork window can differ from the 1h fork
_DAILY_START  = tuple(int(x) for x in os.environ.get(
    "OT_DAILY_FORK_CS_START",  f"{CONDOR_ENTRY_START_ET[0]}:{CONDOR_ENTRY_START_ET[1]}").split(":"))
_DAILY_CUTOFF = tuple(int(x) for x in os.environ.get(
    "OT_DAILY_FORK_CS_CUTOFF", f"{CONDOR_ENTRY_CUTOFF_ET[0]}:{CONDOR_ENTRY_CUTOFF_ET[1]}").split(":"))


@dataclass
class DailyForkPlan:
    """Session-scoped daily-fork cache. Mirrors CondorPlan (v4.3 shape)."""
    short_call_strike:      float = 0.0
    long_call_strike:       float = 0.0
    short_put_strike:       float = 0.0
    long_put_strike:        float = 0.0
    vix_at_plan:            float = 0.0
    expected_move:          float = 0.0
    underlying_at_decision: float = 0.0
    call_rail_at_decision:  float = 0.0
    put_rail_at_decision:   float = 0.0
    decided_at:             str   = ""
    max_price_seen:         float = 0.0
    min_price_seen:         float = 0.0


class DailyForkCreditSpread(BaseOptionsStrategy):
    """
    Credit vertical anchored to the DAILY pitchfork tine.
    Each leg is independent; second leg is allowed, never expected.
    """

    def __init__(self):
        self._plan: Optional[DailyForkPlan] = None
        self._last_reset_date: Optional[str] = None

    @property
    def name(self) -> str:
        return "DailyForkCreditSpread"

    def _reset_if_new_day(self):
        today = datetime.now(ET).strftime("%Y-%m-%d")
        if self._last_reset_date != today:
            self._plan = None
            self._last_reset_date = today

    @property
    def has_active_plan(self) -> bool:
        return self._plan is not None

    def _wing_width(self) -> int:
        return (CONDOR_WING_WIDTH_SPX if INSTRUMENT == "SPX"
                else CONDOR_WING_WIDTH_QQQ) // STRIKE_INCREMENT

    def _expected_move_from_straddle(self, chain: OptionsChain, underlying: float) -> float:
        try:
            atm_call = min([c for c in chain.calls if c.mark > 0],
                           key=lambda c: abs(c.strike - underlying))
            atm_put  = min([c for c in chain.puts  if c.mark > 0],
                           key=lambda c: abs(c.strike - underlying))
            if atm_call.mark > 0 and atm_put.mark > 0:
                return atm_call.mark + atm_put.mark
        except Exception:
            pass
        return 0.0

    def _find_contract_at_strike(self, contracts, strike):
        exact = [c for c in contracts if c.strike == strike and c.mark > 0]
        if exact:
            return exact[0]
        liquid = [c for c in contracts if c.mark > 0]
        return min(liquid, key=lambda c: abs(c.strike - strike)) if liquid else None

    # ── plan ───────────────────────────────────────────────────────────────

    def decide(self, ms: MarketState, vol_state: VolatilityState,
               chain: OptionsChain, macro: MacroSnapshot,
               current_price: float,
               rails_1d: Optional[dict] = None,
               session_high: Optional[float] = None,
               session_low:  Optional[float] = None,
               ctx: Optional[dict] = None) -> Optional[DailyForkPlan]:
        """
        Validate the daily fork and pre-select strikes for this session.
        Returns the plan if valid; None means no 1d-fork spreads today.
        `rails_1d` should come from rails_for(ctx, INSTRUMENT, "1d") — or from
        ctx["condor_triggers"] if the trigger map is already built.
        """
        self._reset_if_new_day()
        now_et = datetime.now(ET)
        hm = (now_et.hour, now_et.minute)

        if hm < _DAILY_START or hm >= _DAILY_CUTOFF:
            return None
        if self._plan is not None:
            return self._plan

        if not rails_1d:
            logger.debug("DailyFork: no 1d rails available — no plan")
            return None

        if macro.vix >= VIX_BUTTERFLY_DISABLE:
            logger.info("DailyFork: blocked VIX=%.1f", macro.vix)
            return None

        em = self._expected_move_from_straddle(chain, current_price)
        if em <= 0:
            return None

        em_floor = em * CONDOR_EM_FLOOR_FRAC
        _em_call = current_price + em_floor
        _em_put  = current_price - em_floor
        _sigma   = float(getattr(vol_state, "atr_current", 0.0) or 0.0)
        _bars    = cv.bars_left(now_et, CONDOR_POP_BAR_MIN, HARD_CLOSE_ET)

        call_anchor = max(float(rails_1d["upper"]), _em_call)
        put_anchor  = min(float(rails_1d["lower"]), _em_put)

        if session_high is None or session_low is None:
            logger.warning("DailyFork: session extremes missing — not-exceeded filter inert")

        short_call = cv.select_beyond_rail(
            chain.calls, "call", call_anchor, _em_call, session_high,
            spot=current_price, sigma=_sigma, bars=_bars,
            min_pop=CONDOR_MIN_POP, max_width_pct=CONDOR_MAX_QUOTE_WIDTH)
        short_put = cv.select_beyond_rail(
            chain.puts, "put", put_anchor, _em_put, session_low,
            spot=current_price, sigma=_sigma, bars=_bars,
            min_pop=CONDOR_MIN_POP, max_width_pct=CONDOR_MAX_QUOTE_WIDTH)

        if short_call is None or short_put is None:
            logger.info("DailyFork: no strike clears 1d anchor (call=%s put=%s)",
                        "ok" if short_call else "none",
                        "ok" if short_put else "none")
            return None

        guardrail = em * CONDOR_EXPECTED_MOVE_GUARDRAIL_MULT
        if max(short_call.strike - current_price,
               current_price - short_put.strike) > guardrail:
            logger.info("DailyFork: strikes exceed %.1f-pt guardrail", guardrail)
            return None

        wing = self._wing_width()
        plan = DailyForkPlan(
            vix_at_plan            = float(getattr(macro, "vix", 0.0) or 0.0),
            short_call_strike      = short_call.strike,
            long_call_strike       = short_call.strike + wing * STRIKE_INCREMENT,
            short_put_strike       = short_put.strike,
            long_put_strike        = short_put.strike  - wing * STRIKE_INCREMENT,
            expected_move          = em,
            underlying_at_decision = current_price,
            decided_at             = now_et.strftime("%H:%M ET"),
            call_rail_at_decision  = float(rails_1d["upper"]),
            put_rail_at_decision   = float(rails_1d["lower"]),
        )
        self._plan = plan
        logger.info(
            "📅 1D FORK PLAN: call=%g/%g  put=%g/%g  EM=$%.2f  VIX=%.1f  "
            "rail_U=%.2f/L=%.2f",
            short_call.strike, plan.long_call_strike,
            plan.long_put_strike, short_put.strike,
            em, macro.vix, plan.call_rail_at_decision, plan.put_rail_at_decision)
        return plan

    # ── trigger check ───────────────────────────────────────────────────────

    def check_leg_triggers(self, current_price: float,
                            chain: OptionsChain,
                            ctx: Optional[dict] = None) -> Optional[OptionsSignal]:
        """
        Returns a signal for one side if its daily tine is hit this tick.
        Reads the LIVE trigger level from ctx["condor_triggers"] (1d entries).

        ⚠️ Does NOT check _can_open_credit_spread — main.py's responsibility.
           This answers "is a 1d trigger active?" not "should we fire?"
        """
        plan = self._plan
        if plan is None:
            return None

        # Approach telemetry
        if plan.max_price_seen <= 0:
            plan.max_price_seen = plan.min_price_seen = current_price
        plan.max_price_seen = max(plan.max_price_seen, current_price)
        plan.min_price_seen = min(plan.min_price_seen, current_price)

        hm = (datetime.now(ET).hour, datetime.now(ET).minute)
        if hm >= _DAILY_CUTOFF:
            return None

        # Get live trigger levels from the per-tick map
        call_trigger = put_trigger = None
        try:
            ctm = (ctx or {}).get("condor_triggers")
            if ctm is not None:
                for ft in ctm.triggers:
                    if ft.tf == "1d" and ft.side == "call":
                        call_trigger = ft.trigger
                    elif ft.tf == "1d" and ft.side == "put":
                        put_trigger = ft.trigger
        except Exception:
            pass

        # Fallback: recompute from plan-time rail (daily slope is negligible intraday)
        from config import CONDOR_TRIGGER_APPROACH as _APPROACH
        if call_trigger is None:
            mid = (plan.call_rail_at_decision + plan.put_rail_at_decision) / 2
            call_trigger = mid + _APPROACH * (plan.call_rail_at_decision - mid)
        if put_trigger is None:
            mid = (plan.call_rail_at_decision + plan.put_rail_at_decision) / 2
            put_trigger  = mid - _APPROACH * (mid - plan.put_rail_at_decision)

        call_hit = current_price >= call_trigger
        put_hit  = current_price <= put_trigger

        if call_hit and put_hit:
            side = ("call" if (current_price - call_trigger) >= (put_trigger - current_price)
                    else "put")
        elif call_hit:
            side = "call"
        elif put_hit:
            side = "put"
        else:
            return None

        return self._build_signal(plan, side, chain)

    def _build_signal(self, plan: DailyForkPlan, side: str,
                      chain: OptionsChain) -> Optional[OptionsSignal]:
        contracts    = chain.calls if side == "call" else chain.puts
        short_strike = plan.short_call_strike if side == "call" else plan.short_put_strike
        long_strike  = plan.long_call_strike  if side == "call" else plan.long_put_strike

        short_c = self._find_contract_at_strike(contracts, short_strike)
        long_c  = self._find_contract_at_strike(contracts, long_strike)
        if short_c is None or long_c is None:
            logger.warning("DailyFork: could not find %s contracts %g/%g",
                           side, short_strike, long_strike)
            return None

        net_credit = short_c.mark - long_c.mark
        if net_credit <= 0:
            logger.info("DailyFork: %s credit=%.2f — skip", side, net_credit)
            return None

        signal = OptionsSignal(
            vix_at_signal         = float(plan.vix_at_plan or 0.0),
            strategy_name         = self.name,
            setup_type            = f"1d_fork_{side}_credit_spread",
            direction             = "neutral",
            option_side           = side,
            # 🔴 r100 — WAS `is_iron_condor=True`, WHICH IS NOT A FIELD. It is a
            # read/write PROPERTY on OptionsSignal, so the dataclass __init__
            # rejected it and this leg builder raised TypeError on EVERY fire —
            # the 1d fork credit spread could never produce a signal. The alias
            # exists so a caller setting EITHER name gets identical behaviour;
            # that only holds for ATTRIBUTE assignment, never in the constructor.
            is_credit_vertical        = True,
            short_call_contract   = short_c if side == "call" else None,
            long_call_contract    = long_c  if side == "call" else None,
            short_put_contract    = short_c if side == "put"  else None,
            long_put_contract     = long_c  if side == "put"  else None,
            net_credit            = net_credit,
            max_loss_condor       = abs(long_strike - short_strike) - net_credit,
            underlying_entry      = plan.underlying_at_decision,
            stop_loss_pct         = CONDOR_STOP_LOSS_PCT,
            tp_pct                = 0.0,
            condor_trigger_source = "1d_fork",
            notes                 = (
                f"1d-fork {side} spread | EM=${plan.expected_move:.2f} | "
                f"rail_U={plan.call_rail_at_decision:.2f} "
                f"rail_L={plan.put_rail_at_decision:.2f} | "
                f"standalone unless complement fires"
            ),
        )
        self._add_confluence(signal, "1d pitchfork tine — multi-session structural boundary")
        logger.info(
            "📅 1D FORK SIGNAL (%s): sell=%g buy=%g credit=$%.2f "
            "stop=$%.2f nickel=$%.2f",
            side.upper(), short_strike, long_strike,
            net_credit, net_credit * (1 + CONDOR_STOP_LOSS_PCT), CONDOR_NICKEL_CLOSE)
        return signal

    def reset_plan(self):
        self._plan = None

    def generate_signal(self, *args, **kwargs) -> Optional[OptionsSignal]:
        return None
