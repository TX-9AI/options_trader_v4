"""
strategy/iron_condor_strategy.py  v4.6
v4.6  2026-08-26  r147 — LEG TWO IS A ONE-LEVEL PLAN, AND IT NEEDS A REJECTION.
      Operator, 2026-08-26: *"the condor's formation is permissive/
      opportunistic, not required. If the complementary vertical spread
      becomes available on mapper, the plan should account for it and confirm
      a rejection of the level before deploying the second leg. Acceptance of
      the level invalidates it and the plan should start looking at the next
      available level in the mapper … the condor should only 'plan' based on
      available levels and price action at that level for leg #2 — it cannot
      'pre-select strikes' beyond the next available one until it's
      invalidated by acceptance … We would not sell a complementary spread on
      a level that's getting breached."*
      NEW `plan_second_leg()`, called by main.py ONLY while exactly one credit
      side is open. Each tick: take the NEXT available level of the
      complementary role from the shared session map (fork tines of both
      timeframes + the mapper's named pools, geometry-valid, not finished
      this session, permitted by the Rule 4 pairing table) — ONE level, no
      list; price the what-if for that level only (short strike first beyond
      it, wing at the condor width, credit off the live chain, R at real
      width, re-priced each tick because the tine slopes); read the tape AT
      the level via analysis/level_test.py — UNTESTED hold, BREACHED hold
      ("no complementary spread on a level being breached"), REJECTED fire
      (R hurdle: strict vetoes, relaxed records), ACCEPTED finish the level
      for the session and move to the next. Finished levels persist in
      plan_ledger (strategy CondorLeg2) so a restart cannot re-arm on a level
      the tape already broke. Leg ONE is unchanged. The second-leg window in
      main.py routes through this alone; a sweep or TC.6 no longer fires a
      second leg directly (their levels are candidates here, with the
      rejection the operator requires of them).
v4.5  2026-08-26  r146 — THE PLAN IS WIRED, in both entry points. `decide()`
      (window, fork present, VIX, expected move, strike clears the anchor,
      guardrail) and `check_leg_triggers()` (cutoff, fork invalidated, tine
      not yet hit, contracts, credit) go through `self.planner`
      (strategy/plan.py) and write a row naming the gate; `_gate_report()`
      is kept as an alias. NEW: at plan-build the 1h rails are checked
      against the SHARED SESSION MAP (analysis/session_map.py) — an upper
      tine below the 5-minute opening range, or a lower tine above it, is
      INVALIDATED BY GEOMETRY (operator, 2026-08-25) and that side is not
      priced; both invalid = no plan. Reads ctx["orb_high"/"orb_low"], the
      one assembly point. The leg's what-if is priced off the REAL spread
      this file already selects: R = credit / (width - credit). The R
      hurdle is consulted at LEG time: STRICT refuses, RELAXED records.
      ⚠️ NOTED, NOT CHANGED: strikes are selected ONCE at plan-build and do
      not follow the sloped tine to the trigger. The operator's fork thesis
      ("that's the level, but sloped") would select at trigger time. That
      alters what gets traded and is his call, not this revision's.
      Self-ledgers: this file opens its own plan_ledger rows, so take()
      does not open a second.
v4.4  2026-08-24  r100 — `is_iron_condor=True` in the constructor is not a field
      (it is a property alias); the 1h fork leg raised TypeError on every fire.
      Now sets is_credit_vertical.
v4.3  2026-08-24  CONDOR REMODEL. The plan-and-pair state machine is removed.
      Each vertical spread is INDEPENDENT — it fires when its fork tine is hit,
      manages as a standalone, and if a complementary spread happens to fire later
      the pair becomes a condor (managed by condor_roll). Nothing in this strategy
      "expects" or "waits for" a second leg.

      What this changes:
        · CondorState, call_filled/put_filled, leg1_side/leg2_side, notify_leg_filled,
          pending_side, leg1_credit/leg2_credit, leg1_filled_at  — ALL REMOVED.
          The pairing expectation lived entirely in those fields.
        · CondorPlan is now a SESSION-SCOPED FORK CACHE: strikes computed when the
          fork is fresh, approach telemetry, plan ledger entry. No state machine.
        · check_leg_triggers() reads the CURRENT trigger level from the trigger map
          (ctx["condor_triggers"]) rather than the stale plan-time level. A 1h fork
          with slope $1/bar shifts its trigger $6 over 6 bars; using the cached
          level was selling premium not near the rail.
        · Each leg signal carries condor_trigger_source="1h_fork" for grading.
        · _execute_condor_leg in main.py no longer calls notify_leg_filled.

      What is preserved:
        · Strike selection (select_beyond_rail, dual floor, POP gate, session extreme).
        · Fork as the required guardrail — no fork → no plan → no signal.
        · The approach telemetry (max/min price seen, abandon log) — still the
          single most useful diagnostic for a condor day with no fills.
        · Plan ledger open/expire (but no COMPLETE/LEG1_FILLED transitions).
        · The VIX gate, the entry window, and the EM guardrail.

      INHERITED DOCTRINE — WORKING_AGREEMENT 32 requires reading before editing.
      Not repeated here; unchanged from v4.2. Read the git history or the v4.2 doc.

v4.2  2026-08-23  AUDIT F6: plan ledger transitions.
v4.1  2026-08-25  r65 EXORCISM.
v4.0  2026-08-19  OTV4 split.
"""

import logging
from dataclasses import dataclass, field
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
    CONDOR_PROXIMITY_STRIKES,
    CONDOR_TRIGGER_APPROACH,
    CONDOR_NICKEL_CLOSE, CONDOR_STOP_LOSS_PCT,
    CONDOR_ENTRY_START_ET, CONDOR_ENTRY_CUTOFF_ET,
    HARD_CLOSE_ET,
    CONDOR_PITCHFORK_ANCHOR, CONDOR_REQUIRE_FORK,
    CONDOR_PF_FLAT_SLOPE, CONDOR_MIN_POP, CONDOR_POP_BAR_MIN,
    CONDOR_PF_TIMEFRAME, CONDOR_MAX_QUOTE_WIDTH,
    STRIKE_INCREMENT, INSTRUMENT, VIX_BUTTERFLY_DISABLE
)

from strategy.plan import Plan, _n
from analysis.session_map import CEILING, FLOOR, build_session_map
from analysis.level_test import (level_state, UNTESTED, BREACHED, REJECTED,
                                 ACCEPTED)

logger = logging.getLogger(__name__)

GATES = {
    "CONDOR_TRIGGER_APPROACH": "SELECTION",
    "CONDOR_WING_WIDTH_SPX":   "SELECTION",
    "CONDOR_WING_WIDTH_QQQ":   "SELECTION",
    "CONDOR_EM_FLOOR_FRAC":    "FEASIBILITY",
    "CONDOR_EXPECTED_MOVE_GUARDRAIL_MULT": "FEASIBILITY",
    # FOUNDATIONAL — fork required, strikes outside rails, not exceeded
}
ET = ZoneInfo("US/Eastern")


@dataclass
class CondorPlan:
    """Session-scoped fork cache. Strikes and approach telemetry only.

    v4.3: NO PAIRING STATE. call_filled/put_filled/leg1_side/leg2_side and the
    entire state machine are gone. The plan answers "what strikes would I use
    if the tine is hit this session" — nothing more. Whether a second leg ever
    fires is not this plan's concern.
    """
    # Strike selections — computed once per fork-build, used at trigger time
    short_call_strike:      float = 0.0
    long_call_strike:       float = 0.0
    short_put_strike:       float = 0.0
    long_put_strike:        float = 0.0

    # VIX at plan time — STR.1: plan-time, not fill-time
    vix_at_plan:            float = 0.0
    expected_move:          float = 0.0
    underlying_at_decision: float = 0.0

    # Approach telemetry — the diagnostic that turns an empty day into a number
    max_price_seen:         float = 0.0
    min_price_seen:         float = 0.0
    decided_at:             str   = ""

    # Rails at plan time (for logging; triggers re-read from the live map)
    call_rail_at_decision:  float = 0.0
    put_rail_at_decision:   float = 0.0


class IronCondorStrategy(BaseOptionsStrategy):
    """
    1h-fork credit vertical. Each leg is an independent trade.
    Second leg is allowed, never expected.
    """

    PLAN_CHECKS = ("entry_window", "fork", "vix", "expected_move", "geometry",
                   "strike_clears_anchor", "guardrail", "fork_invalidated",
                   "trigger", "contract", "credit", "width", "risk", "r")

    LEG2_CHECKS = ("open_side", "candidates", "level", "level_state", "pierce",
                   "closes_beyond", "short_anchor", "contract", "wing", "credit",
                   "width", "risk", "r")

    def __init__(self):
        self._plan: Optional[CondorPlan] = None
        self._plan_id: Optional[str] = None
        self._last_reset_date: Optional[str] = None
        self.planner = Plan(self.name, self.PLAN_CHECKS, self_ledgers=True)
        # ── leg two (v4.6): ONE armed level, and the levels finished today ──
        self.leg2_planner = Plan("CondorLeg2", self.LEG2_CHECKS, self_ledgers=True)
        self._leg2: Optional[dict] = None        # the armed level
        self._leg2_finished: set = set()         # (role, round(price,2)) accepted today
        self._leg2_loaded_date: Optional[str] = None

    # ── ledger plumbing (unchanged from v4.2) ──────────────────────────────

    def _gate_report(self, name: str, reason: str) -> None:
        try:
            from analysis.gate_report import get_gate_reporter
            r = get_gate_reporter(INSTRUMENT)
            if r is not None:
                r.blocked("IronCondorStrategy", name, reason)
        except Exception:
            pass

    def _ledger(self):
        try:
            from derived.registry import plan_ledger
            return plan_ledger(INSTRUMENT)
        except Exception:
            return None

    def _ledger_open(self, plan, ctx=None):
        try:
            led = self._ledger()
            if led is None:
                return
            self._plan_id = led.open_plan(
                "IronCondorStrategy", "ACTIVE", ctx or {},
                short_strike=plan.short_call_strike,
                long_strike=plan.long_call_strike,
                short_put_strike=plan.short_put_strike,
                long_put_strike=plan.long_put_strike,
                underlying_at_decision=plan.underlying_at_decision,
                expected_move=plan.expected_move)
        except Exception:
            pass

    def _ledger_expire(self, reason: str) -> None:
        try:
            led = self._ledger()
            if led and self._plan_id:
                led.transition(self._plan_id, "EXPIRED", reason,
                               max_price=getattr(self._plan, "max_price_seen", None),
                               min_price=getattr(self._plan, "min_price_seen", None))
                self._plan_id = None
        except Exception:
            pass

    @property
    def name(self) -> str:
        return "IronCondorStrategy"

    def _reset_if_new_day(self):
        today = datetime.now(ET).strftime("%Y-%m-%d")
        if self._last_reset_date != today:
            self._ledger_expire("new_day")
            self._plan = None
            self._last_reset_date = today

    @property
    def has_active_plan(self) -> bool:
        """True when a fork-validated plan exists for this session."""
        return self._plan is not None

    @property
    def plan(self) -> Optional[CondorPlan]:
        return self._plan

    def _wing_width(self) -> int:
        return (CONDOR_WING_WIDTH_SPX if INSTRUMENT == "SPX"
                else CONDOR_WING_WIDTH_QQQ) // STRIKE_INCREMENT

    def _expected_move_from_straddle(self, chain: OptionsChain,
                                      underlying: float) -> float:
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

    @staticmethod
    def _liquidity_rank(c):  return cv.liquidity_rank(c)
    @staticmethod
    def _pop(d, s, n):       return cv.pop(d, s, n)
    @staticmethod
    def _bars_left(now_et_dt, bar_minutes):
        return cv.bars_left(now_et_dt, bar_minutes, HARD_CLOSE_ET)
    @staticmethod
    def _quote_ok(c, w):     return cv.quote_ok(c, w)
    @staticmethod
    def _leg_order_from_slope(slope, flat_eps):
        return cv.leg_order_from_slope(slope, flat_eps)

    def _select_beyond_rail(self, contracts, side, rail, min_distance_level,
                            session_extreme, spot=0.0, sigma=0.0,
                            bars_left=0.0, min_pop=0.0, max_width_pct=0.0):
        return cv.select_beyond_rail(
            contracts, side, rail, min_distance_level, session_extreme,
            spot=spot, sigma=sigma, bars=bars_left, min_pop=min_pop,
            max_width_pct=max_width_pct)

    def _find_contract_at_strike(self, contracts, target_strike):
        exact = [c for c in contracts if c.strike == target_strike and c.mark > 0]
        if exact:
            return exact[0]
        liquid = [c for c in contracts if c.mark > 0]
        return min(liquid, key=lambda c: abs(c.strike - target_strike)) if liquid else None

    # ── PLAN: fork validation + strike pre-selection ───────────────────────

    def decide(self, ms: MarketState, vol_state: VolatilityState,
               chain: OptionsChain, macro: MacroSnapshot,
               current_price: float,
               rails: Optional[dict] = None,
               session_high: Optional[float] = None,
               session_low:  Optional[float] = None,
               ctx: Optional[dict] = None) -> Optional[CondorPlan]:
        """
        Build the session plan: validate the 1h fork and pre-select strikes.
        No orders, no pairing expectation. Returns the plan if the fork is
        valid; None means no credit spreads from this strategy today.
        """
        self._reset_if_new_day()
        now_et = datetime.now(ET)
        hm = (now_et.hour, now_et.minute)
        t = self.planner.tick(current_price)

        # 🔴 DORMANT, TIME-INVARIANT REASON (r153) — see strategy/plan.py.
        if hm < CONDOR_ENTRY_START_ET or hm >= CONDOR_ENTRY_CUTOFF_ET:
            return t.dormant("entry_window",
                             f"outside the credit window "
                             f"{CONDOR_ENTRY_START_ET[0]:02d}:"
                             f"{CONDOR_ENTRY_START_ET[1]:02d}-"
                             f"{CONDOR_ENTRY_CUTOFF_ET[0]:02d}:"
                             f"{CONDOR_ENTRY_CUTOFF_ET[1]:02d} — dormant, "
                             f"not looking at the chart")
        t.check("entry_window", None, True)
        if self._plan is not None:
            t.hold("plan already built this session — legs watched by "
                   "check_leg_triggers")
            return self._plan  # plan already built this session

        # ── Fork gate ──────────────────────────────────────────────────────
        use_rails = bool(CONDOR_PITCHFORK_ANCHOR and rails)
        if CONDOR_REQUIRE_FORK and not use_rails:
            _why = "absent"
            try:
                from analysis.pitchfork import last_reject_reason
                rr = last_reject_reason()
                if rr and not rails:
                    _why = f"absent ({rr})"
            except Exception:
                pass
            logger.debug("Condor: NO PLAN — no %s fork (rails=%s)",
                         CONDOR_PF_TIMEFRAME, _why)
            return t.refuse("fork", f"no usable {CONDOR_PF_TIMEFRAME} pitchfork "
                                    f"(rails={_why})")
        t.check("fork", 1.0 if use_rails else 0.0, True)

        t.check("vix", macro.vix, macro.vix < VIX_BUTTERFLY_DISABLE)
        if macro.vix >= VIX_BUTTERFLY_DISABLE:
            logger.info("Condor blocked: VIX=%.1f", macro.vix)
            return t.refuse("vix", f"VIX {macro.vix:.1f} >= {VIX_BUTTERFLY_DISABLE}")

        em = self._expected_move_from_straddle(chain, current_price)
        t.check("expected_move", em or None, None if em <= 0 else True)
        if em <= 0:
            return t.starved("expected_move")

        # ── Strike selection at PLAN TIME (chain available here) ───────────
        bb_upper = vol_state.bb_upper if vol_state.bb_upper > 0 else current_price + em
        bb_lower = vol_state.bb_lower if vol_state.bb_lower > 0 else current_price - em
        em_floor   = em * CONDOR_EM_FLOOR_FRAC
        _em_call   = current_price + em_floor
        _em_put    = current_price - em_floor
        _sigma     = float(getattr(vol_state, "atr_current", 0.0) or 0.0)
        _bars      = self._bars_left(now_et, CONDOR_POP_BAR_MIN)

        # ── GEOMETRY: THE SHARED SESSION MAP (v4.5) ──────────────────────
        # An upper tine is a CEILING for the session and a lower tine a FLOOR;
        # a ceiling below the opening range (or a floor above it) is
        # invalidated, never re-cast. Unmeasured (no ORB yet) records n/a and
        # the spec proceeds.
        _oh = (ctx or {}).get("orb_high")
        _ol = (ctx or {}).get("orb_low")
        _call_ok = _put_ok = None
        if use_rails:
            _call_ok = t.level(float(rails["upper"]), CEILING,
                               f"{CONDOR_PF_TIMEFRAME} upper tine", _oh, _ol)
            _call_why = t.last_why
            _put_ok = t.level(float(rails["lower"]), FLOOR,
                              f"{CONDOR_PF_TIMEFRAME} lower tine", _oh, _ol)
            _put_why = t.last_why
            if _call_ok is False and _put_ok is False:
                return t.refuse("geometry", f"{_call_why}; {_put_why}")
            if _call_ok is False:
                logger.info("Condor: call side eliminated by geometry — %s", _call_why)
            if _put_ok is False:
                logger.info("Condor: put side eliminated by geometry — %s", _put_why)

        if use_rails:
            call_anchor = max(float(rails["upper"]), _em_call)
            put_anchor  = min(float(rails["lower"]), _em_put)
            call_rail_saved = float(rails["upper"])
            put_rail_saved  = float(rails["lower"])
        else:
            call_anchor = max(current_price + em_floor, bb_upper)
            put_anchor  = min(current_price - em_floor, bb_lower)
            call_rail_saved = call_anchor
            put_rail_saved  = put_anchor

        if session_high is None or session_low is None:
            logger.warning("Condor: session extremes missing — not-exceeded filter inert")

        short_call = self._select_beyond_rail(
            chain.calls, "call", call_anchor, _em_call, session_high,
            spot=current_price, sigma=_sigma, bars_left=_bars,
            min_pop=CONDOR_MIN_POP, max_width_pct=CONDOR_MAX_QUOTE_WIDTH)
        short_put = self._select_beyond_rail(
            chain.puts, "put", put_anchor, _em_put, session_low,
            spot=current_price, sigma=_sigma, bars_left=_bars,
            min_pop=CONDOR_MIN_POP, max_width_pct=CONDOR_MAX_QUOTE_WIDTH)

        # A side eliminated by geometry is not priced — its strike is None
        # and it can never trigger. Both sides are still stored so the leg
        # check reads a plan of the same shape.
        if _call_ok is False:
            short_call = None
        if _put_ok is False:
            short_put = None
        t.check("strike_clears_anchor",
                (1 if short_call else 0) + (1 if short_put else 0),
                bool(short_call or short_put))
        if short_call is None and short_put is None:
            logger.info("Condor: no strike clears anchor on either side")
            return t.refuse("strike_clears_anchor",
                            "no strike clears the anchor on either side")
        if short_call is None or short_put is None:
            logger.info("Condor: one-sided plan (call=%s put=%s)",
                        "ok" if short_call else "none",
                        "ok" if short_put else "none")

        guardrail = em * CONDOR_EXPECTED_MOVE_GUARDRAIL_MULT
        _reach = max((short_call.strike - current_price) if short_call else 0.0,
                     (current_price - short_put.strike) if short_put else 0.0)
        t.check("guardrail", _reach - guardrail, _reach <= guardrail)
        if _reach > guardrail:
            logger.info("Condor: strikes exceed %.1f-pt guardrail", guardrail)
            return t.refuse("guardrail", f"strike distance {_reach:.2f} exceeds "
                                         f"the {guardrail:.1f}-pt guardrail "
                                         f"({CONDOR_EXPECTED_MOVE_GUARDRAIL_MULT}x EM)")

        wing = self._wing_width()
        plan = CondorPlan(
            vix_at_plan            = float(getattr(macro, "vix", 0.0) or 0.0),
            short_call_strike      = short_call.strike if short_call else 0.0,
            long_call_strike       = (short_call.strike + wing * STRIKE_INCREMENT
                                      if short_call else 0.0),
            short_put_strike       = short_put.strike if short_put else 0.0,
            long_put_strike        = (short_put.strike - wing * STRIKE_INCREMENT
                                      if short_put else 0.0),
            expected_move          = em,
            underlying_at_decision = current_price,
            decided_at             = now_et.strftime("%H:%M ET"),
            call_rail_at_decision  = call_rail_saved,
            put_rail_at_decision   = put_rail_saved,
        )
        self._plan = plan
        self._ledger_open(plan, ctx)

        logger.info(
            "🦅 CONDOR PLAN: call_spread=%g/%g  put_spread=%g/%g  "
            "EM=$%.2f  VIX=%.1f  rail_U=%.2f/L=%.2f",
            plan.short_call_strike, plan.long_call_strike,
            plan.long_put_strike, plan.short_put_strike,
            em, macro.vix, call_rail_saved, put_rail_saved)
        t.hold(f"plan built: call {plan.short_call_strike:g}/{plan.long_call_strike:g} "
               f"put {plan.short_put_strike:g}/{plan.long_put_strike:g} — "
               f"waiting on a tine", verdict="HOLD")
        return plan

    # ── TRIGGER: check live tine position against current price ───────────

    def check_leg_triggers(self, ms: MarketState,
                            chain: OptionsChain,
                            current_price: float,
                            ctx: Optional[dict] = None) -> Optional[OptionsSignal]:
        """
        Called every tick. Returns a signal for ONE side if its tine is hit.
        Uses the LIVE trigger level from ctx["condor_triggers"] (the moving-
        target map) rather than the plan-time value. If the map is absent,
        falls back to recomputing from the plan's saved rails.

        ⚠️ DOES NOT CHECK _can_open_credit_spread — that is main.py's job.
           This method answers "is a trigger active?" not "should we fire?"
        """
        plan = self._plan
        t = self.planner.tick(current_price)
        if plan is None:
            return t.refuse("plan", "no session plan built (decide() has not "
                                    "produced one)")

        # Approach telemetry — cheap, runs every tick
        if plan.max_price_seen <= 0:
            plan.max_price_seen = plan.min_price_seen = current_price
        plan.max_price_seen = max(plan.max_price_seen, current_price)
        plan.min_price_seen = min(plan.min_price_seen, current_price)

        now_et = datetime.now(ET)
        hm = (now_et.hour, now_et.minute)
        if hm >= CONDOR_ENTRY_CUTOFF_ET:
            self._abandon_past_cutoff(plan, chain, current_price)
            return t.refuse("entry_window", f"{hm[0]:02d}:{hm[1]:02d} ET is past "
                                            f"the cutoff — plan abandoned")

        # ── Fork invalidation ──────────────────────────────────────────────
        # A filled leg is never cancelled — but there is no "filled leg" to
        # track here any more. If the fork dies the plan expires; any already-
        # executed vertical manages itself via its own stop/nickel rules.
        if getattr(ms, "fork_invalidated", False):
            logger.info("Condor: fork invalidated — plan expires (any open verticals manage standalone)")
            self._ledger_expire("fork_invalidated")
            self._plan = None
            return t.refuse("fork_invalidated", "fork invalidated — plan expires")
        t.check("fork_invalidated", 0.0, True)

        # ── Live trigger level ─────────────────────────────────────────────
        # Read from the per-tick map if available; fall back to recomputing
        # from the plan's saved rail (which is approximately correct for
        # the current tick on a slowly-sloping fork).
        call_trigger = put_trigger = None
        try:
            ctm = (ctx or {}).get("condor_triggers")
            if ctm is not None:
                for ft in ctm.triggers:
                    if ft.tf == "1h" and ft.side == "call":
                        call_trigger = ft.trigger
                    elif ft.tf == "1h" and ft.side == "put":
                        put_trigger = ft.trigger
        except Exception:
            pass

        if call_trigger is None:
            mid_ref = (plan.call_rail_at_decision + plan.put_rail_at_decision) / 2
            call_trigger = mid_ref + CONDOR_TRIGGER_APPROACH * (plan.call_rail_at_decision - mid_ref)
        if put_trigger is None:
            mid_ref = (plan.call_rail_at_decision + plan.put_rail_at_decision) / 2
            put_trigger  = mid_ref - CONDOR_TRIGGER_APPROACH * (mid_ref - plan.put_rail_at_decision)

        # a side with no strike (geometry-eliminated, v4.5) can never trigger
        call_hit = current_price >= call_trigger and plan.short_call_strike > 0
        put_hit  = current_price <= put_trigger and plan.short_put_strike > 0

        if call_hit and put_hit:
            # Both active this tick — take the side price has exceeded further
            side = ("call" if (current_price - call_trigger) >= (put_trigger - current_price)
                    else "put")
        elif call_hit:
            side = "call"
        elif put_hit:
            side = "put"
        else:
            # the nearer tine is the trigger this plan is waiting on
            _dc, _dp = call_trigger - current_price, current_price - put_trigger
            if plan.short_call_strike > 0 and (plan.short_put_strike <= 0 or _dc <= _dp):
                t.anchor(trigger=call_trigger, invalidation=plan.short_call_strike)
                t.direction = "call"
            else:
                t.anchor(trigger=put_trigger, invalidation=plan.short_put_strike)
                t.direction = "put"
            t.check("trigger", None, False)
            return t.hold(f"neither tine hit — call trigger {call_trigger:.2f} / "
                          f"put trigger {put_trigger:.2f}, price {current_price:.2f}")

        t.direction = side
        t.anchor(trigger=call_trigger if side == "call" else put_trigger)
        t.check("trigger", 1.0, True)
        return self._build_leg_signal(plan, side, chain, t)

    def _build_leg_signal(self, plan: CondorPlan, side: str,
                           chain: OptionsChain, t=None) -> Optional[OptionsSignal]:
        """Build a fully-specified credit-spread OptionsSignal for one side."""
        if t is None:
            t = self.planner.tick(plan.underlying_at_decision, side)
        if side == "call":
            contracts    = chain.calls
            short_strike = plan.short_call_strike
            long_strike  = plan.long_call_strike
        else:
            contracts    = chain.puts
            short_strike = plan.short_put_strike
            long_strike  = plan.long_put_strike

        short_contract = self._find_contract_at_strike(contracts, short_strike)
        long_contract  = self._find_contract_at_strike(contracts, long_strike)

        if short_contract is None or long_contract is None:
            logger.warning("Condor: could not find %s spread contracts %g/%g",
                           side, short_strike, long_strike)
            return t.refuse("contract", f"could not find {side} spread contracts "
                                        f"{short_strike:g}/{long_strike:g}")
        t.check("contract", short_strike, True)

        net_credit = short_contract.mark - long_contract.mark
        # ── THE WHAT-IF, off the spread this plan chose ───────────────────
        t.credit_spread(short_strike, long_strike, net_credit,
                        invalidation=short_strike)
        if net_credit <= 0:
            logger.info("Condor: %s credit <= 0 (%.2f) — skip", side, net_credit)
            return t.refuse("credit", f"{side} credit {net_credit:.2f} <= 0")
        # ── THE R HURDLE — strict refuses, relaxed records ────────────────
        _ok, _why = t.executable()
        if not _ok:
            logger.info("Condor: %s leg R %s refused: %s", side, _n(t.r), _why)
            return t.refuse("r", _why)
        t.note(_why)

        wing_width = abs(long_strike - short_strike)
        signal = OptionsSignal(
            vix_at_signal          = float(plan.vix_at_plan or 0.0),
            strategy_name          = self.name,
            setup_type             = f"1h_fork_{side}_credit_spread",
            direction              = "neutral",
            option_side            = side,
            # 🔴 r100 — WAS `is_iron_condor=True`, WHICH IS NOT A FIELD. It is a
            # read/write PROPERTY on OptionsSignal, so the dataclass __init__
            # rejected it and this leg builder raised TypeError on EVERY fire —
            # the 1h fork credit spread could never produce a signal. The alias
            # exists so a caller setting EITHER name gets identical behaviour;
            # that only holds for ATTRIBUTE assignment, never in the constructor.
            is_credit_vertical         = True,
            short_call_contract    = short_contract if side == "call" else None,
            long_call_contract     = long_contract  if side == "call" else None,
            short_put_contract     = short_contract if side == "put"  else None,
            long_put_contract      = long_contract  if side == "put"  else None,
            net_credit             = net_credit,
            max_loss_condor        = wing_width - net_credit,
            underlying_entry       = plan.underlying_at_decision,
            stop_loss_pct          = CONDOR_STOP_LOSS_PCT,
            tp_pct                 = 0.0,
            condor_trigger_source  = "1h_fork",
            notes                  = (
                f"1h-fork {side} spread | EM=${plan.expected_move:.2f} | "
                f"rail_U={plan.call_rail_at_decision:.2f} "
                f"rail_L={plan.put_rail_at_decision:.2f} | "
                f"standalone unless complement fires"
            ),
        )
        self._add_confluence(signal, "1h pitchfork tine — premium rich at the rail")
        logger.info(
            "🦅 1H FORK SIGNAL (%s): sell=%g buy=%g credit=$%.2f "
            "stop=$%.2f nickel=$%.2f",
            side.upper(), short_strike, long_strike,
            net_credit, net_credit * (1 + CONDOR_STOP_LOSS_PCT), CONDOR_NICKEL_CLOSE)
        return t.take(signal)

    # ═══ LEG TWO — the one-level plan (v4.6) ═══════════════════════════════

    def _leg2_load_finished(self, ledger) -> None:
        """Rebuild today's finished-level set from plan_ledger after a restart."""
        today = datetime.now(ET).strftime("%Y-%m-%d")
        if self._leg2_loaded_date == today:
            return
        self._leg2_loaded_date = today
        self._leg2_finished = set()
        try:
            store = getattr(ledger, "_store", None)
            if store is None:
                return
            day0 = datetime.now(ET).replace(hour=0, minute=0, second=0,
                                            microsecond=0).timestamp()
            for px, direction, reason in store.conn.execute(
                    "SELECT trigger_price, direction, terminal_reason FROM plan_ledger "
                    "WHERE symbol=? AND strategy='CondorLeg2' AND created_ts>=? "
                    "AND state='EXPIRED'", (INSTRUMENT, day0)):
                if px is not None and (reason or "").startswith("accepted"):
                    self._leg2_finished.add((direction or "", round(float(px), 2)))
        except Exception as exc:                                # noqa: BLE001
            logger.debug("CondorLeg2: finished-level reload skipped: %s", exc)

    def _leg2_candidates(self, ctx: dict, role: str, allowed: set) -> list:
        """Levels of `role` on the shared session map, nearest to price first,
        geometry-valid, not finished, and of a source the pairing table
        permits ('fork' -> tines, 'sweep' -> the mapper's named pools)."""
        oh, ol = ctx.get("orb_high"), ctx.get("orb_low")
        lm = ctx.get("liq_map")

        class _Shim:            # build_session_map reads `.levels` w/ kind/price/name
            levels = [p for p in (getattr(lm, "pools", None) or [])
                      if getattr(p, "is_named", False) and not getattr(p, "swept", False)]
        ceilings, floors, _inv = build_session_map(oh, ol, ledger=_Shim(),
                                                   ctm=ctx.get("condor_triggers"))
        pool = ceilings if role == CEILING else floors
        out = []
        for lv in pool:
            cls = "fork" if lv.source == "fork" else "sweep"
            if cls not in allowed:
                continue
            if (role, round(lv.price, 2)) in self._leg2_finished:
                continue
            out.append(lv)
        px = float(ctx.get("price") or 0.0)
        out.sort(key=lambda lv: abs(lv.price - px))
        return out

    def plan_second_leg(self, ctx: dict, chain: OptionsChain, current_price: float,
                        open_side: str, allowed_classes=("fork", "sweep")
                        ) -> Optional[OptionsSignal]:
        """The complementary vertical, ONE level at a time, on a confirmed
        rejection. Returns a signal to hand to the pairing gate, or None.

        ⚠️ CALLED ONLY WHILE EXACTLY ONE CREDIT SIDE IS OPEN. Leg one fires from
        its own trigger and never consults this.
        """
        t = self.leg2_planner.tick(current_price)
        need_role = FLOOR if open_side == "call" else CEILING       # complement
        need_side = "put" if open_side == "call" else "call"
        t.direction = need_side
        t.check("open_side", 1.0 if open_side == "call" else -1.0, True)
        led = self._ledger()
        self._leg2_load_finished(led)
        allowed = set(allowed_classes or ())

        # ── the level: keep the armed one unless it is finished ──────────
        if self._leg2 is not None and (
                self._leg2["role"] != need_role
                or (need_role, round(self._leg2["price"], 2)) in self._leg2_finished):
            self._leg2 = None
        if self._leg2 is None:
            cands = self._leg2_candidates(ctx, need_role, allowed)
            t.check("candidates", len(cands), bool(cands))
            if not cands:
                return t.hold(f"no {need_role} available on the map for a {need_side} "
                              f"spread (finished today: {len(self._leg2_finished)}, "
                              f"allowed classes: {', '.join(sorted(allowed)) or 'none'}) "
                              f"— leg two is off the table")
            lv = cands[0]
            pid = None
            try:
                if led is not None:
                    pid = led.open_plan("CondorLeg2", "ARMED", ctx, direction=need_role,
                                        trigger_price=lv.price,
                                        underlying_at_decision=current_price)
            except Exception:                                   # noqa: BLE001
                pid = None
            self._leg2 = {"price": float(lv.price), "role": need_role, "name": lv.name,
                          "source": lv.source, "tf": lv.tf,
                          "armed_ts": datetime.now(ET).timestamp(), "plan_id": pid}
            logger.info("CondorLeg2: ARMED on %s %s at %.2f (%s) — waiting for the "
                        "tape to reject it", lv.name, need_role, lv.price, lv.source)
        L = self._leg2
        t.check("level", L["price"], True)
        t.anchor(trigger=L["price"], invalidation=L["price"])

        # ── the tape at the level ─────────────────────────────────────────
        state, d = level_state(ctx.get("df_1m"), L["price"], L["role"], L["armed_ts"])
        t.check("level_state", {UNTESTED: 0, BREACHED: 1, REJECTED: 2, ACCEPTED: 3}[state],
                state == REJECTED)
        t.check("pierce", d.get("pierce"), None)
        t.check("closes_beyond", d.get("closes_beyond"), None)
        head = f"{L['name']} ({L['role']}) at {L['price']:.2f}"
        if state == ACCEPTED:
            self._leg2_finished.add((L["role"], round(L["price"], 2)))
            try:
                if led is not None and L.get("plan_id"):
                    led.transition(L["plan_id"], "EXPIRED",
                                   terminal_reason=f"accepted: {d.get('why', '')}")
            except Exception:                                   # noqa: BLE001
                pass
            logger.info("CondorLeg2: %s ACCEPTED — finished for the session; "
                        "looking at the next level", head)
            self._leg2 = None
            return t.hold(f"{head} ACCEPTED — {d.get('why', '')}; level finished, "
                          f"next level next tick")
        if state == UNTESTED:
            return t.hold(f"{head} untested since arming ({d.get('bars', 0)} bars) — "
                          f"waiting for a test and a rejection")
        if state == BREACHED:
            return t.hold(f"{head} is BEING BREACHED — {d.get('why', '')}. No "
                          f"complementary spread is sold on a level under test")

        # ── REJECTED: price the leg for THIS level only ──────────────────
        contracts = chain.calls if need_side == "call" else chain.puts
        wing_pts = self._wing_width() * STRIKE_INCREMENT
        try:
            ks = sorted({float(c.strike) for c in contracts
                         if float(getattr(c, "mark", 0) or 0) > 0})
        except Exception:                                       # noqa: BLE001
            ks = []
        beyond = ([k for k in ks if k > L["price"]] if need_side == "call"
                  else [k for k in reversed(ks) if k < L["price"]])
        if not beyond:
            t.check("short_anchor", None, False)
            return t.refuse("short_anchor", f"{head} rejected but the {need_side} "
                                            f"chain has no priced strike beyond it")
        short_k = beyond[0]
        long_k = short_k + wing_pts if need_side == "call" else short_k - wing_pts
        t.check("short_anchor", short_k, True)
        short_c = self._find_contract_at_strike(contracts, short_k)
        long_c = self._find_contract_at_strike(contracts, long_k)
        if short_c is None or long_c is None:
            return t.refuse("contract", f"no contracts at {short_k:g}/{long_k:g} "
                                        f"for the {need_side} spread beyond {head}")
        t.check("contract", short_k, True)
        t.check("wing", long_k, True)
        credit = float(short_c.mark) - float(long_c.mark)
        t.credit_spread(short_k, long_k, credit, invalidation=L["price"],
                        trigger=L["price"])
        if credit <= 0:
            return t.refuse("credit", f"{need_side} {short_k:g}/{long_k:g} credit "
                                      f"{credit:.2f} <= 0")
        ok, why = t.executable()
        if not ok:
            logger.info("CondorLeg2: %s rejected but R %s refused: %s", head, _n(t.r), why)
            return t.refuse("r", why)
        t.note(f"{head} REJECTED — {d.get('why', '')}")
        t.note(why)

        src = ("1h_fork" if L["tf"] == "1h" else "1d_fork") if L["source"] == "fork"             else "sweep_reversal"
        signal = OptionsSignal(
            strategy_name          = self.name,
            setup_type             = f"leg2_{L['source']}_{need_side}_credit_spread",
            direction              = "neutral",
            option_side            = need_side,
            is_credit_vertical     = True,
            short_call_contract    = short_c if need_side == "call" else None,
            long_call_contract     = long_c  if need_side == "call" else None,
            short_put_contract     = short_c if need_side == "put"  else None,
            long_put_contract      = long_c  if need_side == "put"  else None,
            net_credit             = credit,
            max_loss_condor        = abs(long_k - short_k) - credit,
            underlying_entry       = current_price,
            underlying_stop        = L["price"],
            stop_loss_pct          = CONDOR_STOP_LOSS_PCT,
            tp_pct                 = 0.0,
            condor_trigger_source  = src,
            notes                  = (f"leg2 on {head} REJECTED | pierce "
                                      f"{_n(d.get('pierce'))} | complement of open "
                                      f"{open_side} spread"),
        )
        signal.contract = short_c
        signal.strike = short_k
        signal.expiry = getattr(short_c, "expiry", "")
        signal.entry_premium = credit
        signal.leg2_level = L["price"]
        signal.leg2_plan_id = L.get("plan_id")
        logger.info("🦅 LEG2 SIGNAL (%s): %s REJECTED -> sell %g buy %g credit $%.2f R %s",
                    need_side.upper(), head, short_k, long_k, credit, _n(t.r))
        return t.take(signal)

    def leg2_fired(self) -> None:
        """main.py: the leg-2 signal was executed. Close the armed level."""
        try:
            led = self._ledger()
            if led is not None and self._leg2 and self._leg2.get("plan_id"):
                led.transition(self._leg2["plan_id"], "FIRED", terminal_reason="leg2 executed")
        except Exception:                                       # noqa: BLE001
            pass
        self._leg2 = None

    # ── approach telemetry (unchanged) ─────────────────────────────────────

    @staticmethod
    def _approach(plan, current_price) -> dict:
        s0  = plan.underlying_at_decision or current_price
        cr  = plan.call_rail_at_decision
        pr  = plan.put_rail_at_decision
        mid = (cr + pr) / 2 if (cr and pr) else s0
        cd  = CONDOR_TRIGGER_APPROACH * (cr - mid) if (cr and mid) else 0
        pd  = CONDOR_TRIGGER_APPROACH * (mid - pr) if (pr and mid) else 0
        return {
            "spot_at_plan": round(s0, 2),
            "call_approach": round((plan.max_price_seen - s0) / cd, 4) if cd > 0 else None,
            "put_approach":  round((s0 - plan.min_price_seen) / pd, 4) if pd > 0 else None,
            "max_seen":  round(plan.max_price_seen, 2),
            "min_seen":  round(plan.min_price_seen, 2),
            "call_rail": round(cr, 2),
            "put_rail":  round(pr, 2),
            "em_at_plan": round(plan.expected_move or 0.0, 2),
            "decided_at": plan.decided_at,
        }

    @staticmethod
    def _approach_text(a: dict) -> str:
        def _p(v): return "n/a" if v is None else f"{v:.0%}"
        return (f"call_approach={_p(a['call_approach'])} (max={a['max_seen']}) "
                f"put_approach={_p(a['put_approach'])} (min={a['min_seen']}) "
                f"rails={a['call_rail']}/{a['put_rail']}")

    @staticmethod
    def _journal_abandon(plan, a: dict, cause: str) -> None:
        try:
            from analysis.signal_journal import journal
            journal("condor_abandon", cause=cause, approach=a)
        except Exception as exc:
            logger.debug("condor_abandon journal failed (%s: %s)", type(exc).__name__, exc)

    def _abandon_past_cutoff(self, plan, chain, current_price):
        a = self._approach(plan, current_price)
        logger.info("Condor: past cutoff, no fill | %s", self._approach_text(a))
        self._journal_abandon(plan, a, "cutoff")
        self._ledger_expire("past_cutoff")
        self._plan = None

    def reset_plan(self):
        """Clear the session plan (end of session)."""
        self._ledger_expire("session_end")
        self._plan = None

    # ABC stub
    def generate_signal(self, *args, **kwargs) -> Optional[OptionsSignal]:
        return None
