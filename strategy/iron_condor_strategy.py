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
# r157 — the R floor is read DIRECTLY; r_hurdle() returns None under relaxed.
from strategy.criteria import R_FLOOR
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
                   "wing", "wing_r_best",
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


    # ── TRIGGER: check live tine position against current price ───────────



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
        # ── ✅ PERMITTED. THE PLAN STOPS HERE. ───────────────────────────────
        # 🔴 OPERATOR, 2026-08-27: *"The condor doesn't construct anything. The
        # condor plan should just simply define whether a vertical spread is
        # open and active and what's permitted afterwards."* And: *"nothing in
        # the plan is executable. It's an information layer to feed the
        # strategy and the strategy will execute."*
        #
        # ⚠️ WHAT WAS HERE, AND WHY IT IS GONE: 54 lines that picked the short
        # strike, applied a fixed `wing_pts`, looked up both contracts, priced
        # the credit on MARK, gated on `t.executable()` (MUTED under relaxed)
        # and assembled an OptionsSignal. That is a vertical spread being
        # rebuilt inside a management function — *"I don't need two strategies
        # for every strategy"* — and it had already drifted from the real one:
        # mark instead of bid/ask, a fixed wing instead of a search, no
        # `stop_survivable`, and an R gate relaxed could waive.
        #
        # ⚠️ THE SWEEP OWNS CONSTRUCTION AND IS NOW STRICTER THAN THIS EVER WAS
        # — R as a construction target that relaxed cannot mute (r156/r157), a
        # SEARCHED wing rather than a fixed dollar width, `stop_survivable`
        # (r154) and the risk-anchored stop (r155). Leg two inherits all of it
        # by DELETION rather than by re-implementing four gates here.
        #
        # ⚠️ CONSEQUENCE, STATED: leg two will fire LESS. A rejected level whose
        # chain offers no wing clearing the R floor produces no second leg and
        # the condor stays a lone vertical. That is correct, and it compounds
        # with relaxed already producing fewer trades.
        return t.permit(
            side=need_side,
            level=L["price"],
            source=L["source"],
            plan_id=L.get("plan_id"),
            why=f"{head} REJECTED — {d.get('why', '')}; a {need_side} "
                f"complementary vertical is PERMITTED at {L['price']:g}. "
                f"Construction belongs to the sweep.")


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
