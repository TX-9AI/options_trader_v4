"""
strategy/iron_condor_strategy.py  v4.8
v4.8  2026-08-27  r160 — THE CONDOR SELECTS NOTHING; IT AUTHORIZES, THEN MANAGES.
      Operator, 2026-08-27: *"If there is already an active vertical spread of
      type (call/put) then only a complementary vertical (call/put) SWEEP
      trade is authorized to fire. Everything else is gated off. The condor
      doesn't select anything, but it starts managing once leg 2 is born.
      And that management is per-tick on executing a roll if threatened, and
      the inverted hedge butterfly if breached, in order of escalation and
      closed entirely if uneconomical to save it."*
      DELETED (r147/r158/r159 level-selection, 230 lines): `plan_second_leg`,
      `_leg2_candidates`, `_leg2_load_finished`, `leg2_fired`, the armed
      level, the finished-level set — all of it was the condor choosing a
      level for the sweep. The sweep chooses its own level under its spec.
      NEW `authorize(open_sides)` -> (side, why): exactly one credit vertical
      open -> the complementary side, and ONLY a sweep; none or both -> "".
      NEW `manage(...)`: the per-tick management row for a FORMED condor —
      which rung it is on (1 ROLL / 2b TENT / 3 CLOSE per TRADES.md), what
      the next rung would cost RIGHT NOW (roll credit, close cost, cumulative
      vs tested width; hedge debit vs the -15% floor) and whether it clears.
      Execution stays in condor_roll (check_and_execute_roll / _tent) — this
      narrates the ladder, it does not pull it. 🔴 FOUND IN SOURCE, NAMED ON
      EVERY SUCH TICK: rung 1 executes ONLY a risk-free roll and the tent
      arms ONLY after a roll, so a formed condor with no risk-free roll
      available is on NO RUNG while price walks through a short. The
      operator's ladder says never "do nothing" on a tested structure; the
      row now says "NO RUNG" so the gap is visible, not silent.
v4.7  2026-08-27  r158 (RECORDED RETROACTIVELY in r159 — r158 changed this file
      by 435 lines and neither bumped the title nor wrote this entry; the
      header still read v4.6/r147, the drift class the operator's standing
      rule forbids). What r158 did: deleted `decide()`, `check_leg_triggers()`
      and `_build_leg_signal()` (366 lines); the condor is no longer
      dispatched as an entry strategy in main.py; `plan_second_leg` returns a
      `Permission` (side, level, source, plan_id, why — no contracts, strikes
      or premium) and main.py hands it to the sweep, which constructs under
      its own rules. Operator, 2026-08-27: *"the iron condor is not a
      strategy. It is a management function"*, *"The condor does not
      construct anything."*
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
from analysis.session_map import CEILING, FLOOR

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

    def __init__(self):
        self._plan: Optional[CondorPlan] = None
        self._plan_id: Optional[str] = None
        self._last_reset_date: Optional[str] = None
        self.planner = Plan(self.name, self.PLAN_CHECKS, self_ledgers=True)

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



    # ═══ AUTHORIZATION — one vertical open, only its complement may fire ═══

    @staticmethod
    def authorize(open_sides) -> tuple:
        """(side, why). Exactly ONE credit vertical open -> the COMPLEMENTARY
        side is authorized, and only as a SWEEP (the caller passes it to the
        sweep's plan as `required_side`). None open -> no authorization is
        needed. Both open -> nothing more may fire. The condor selects no
        level and no strike — ever."""
        sides = set(open_sides or ())
        if len(sides) == 1:
            have = next(iter(sides))
            need = "put" if have == "call" else "call"
            return need, (f"{have} vertical open — only a complementary {need}-side "
                          f"SWEEP is authorized; everything else is gated off")
        if len(sides) >= 2:
            return "", "both sides open — the condor is formed; nothing more may fire"
        return "", ""

    # ═══ MANAGEMENT — per tick, once leg two is born ═══════════════════════

    MGMT_CHECKS = ("legs", "tested", "rolled", "breached", "roll_credit", "close_cost",
                   "credit_after", "tested_width", "risk_free", "hedge_debit",
                   "floor", "rung")

    def manage(self, pos_mgr, chain, current_price: float, df_1m=None) -> Optional[str]:
        """The management plan's row: which rung, what the next rung costs
        right now, does it clear. Returns the rung name or None (no formed
        condor). Executes NOTHING — condor_roll does, and is called by main
        right after this, so the row is the account of the decision it will
        make on the same numbers."""
        from strategy.condor_roll import classify_tested, find_risk_free_roll, _tent_breached
        from config import TENT_FLOOR_PCT
        if not hasattr(self, "_mgmt_planner"):
            self._mgmt_planner = Plan("CondorManagement", self.MGMT_CHECKS, self_ledgers=True)
        t = self._mgmt_planner.tick(current_price)
        legs = [r for r in pos_mgr.get_open_records() if r.get("is_condor_leg")]
        t.check("legs", len(legs), len(legs) == 2)
        if len(legs) < 2:
            if len(legs) == 1:
                t.hold(f"lone {legs[0].get('option_side', '?')} vertical — managed as a "
                       f"standalone on its 15% stop; not a condor")
                return "LONE"
            t.hold("no credit verticals open — nothing to manage")
            return None
        if chain is None:
            t.starved("chain")
            return None
        rolled = any(r.get("is_broken_wing") for r in legs)
        t.check("rolled", 1.0 if rolled else 0.0, None)
        tested, untested = classify_tested(legs, current_price)
        t.check("tested", 1.0 if tested else 0.0, None)
        banked = sum(float(l.get("credit_received", l.get("entry_premium", 0.0))) for l in legs)
        head = (" + ".join(f"{l.get('option_side','?')} {l.get('short_strike',0):g}/"
                           f"{l.get('long_strike',0):g}" for l in legs)
                + f"  banked {banked:.2f}")

        # ── rung 2b: the tent, only on an already-rolled structure ─────────
        breach = None
        try:
            breach = _tent_breached(df_1m, legs) if df_1m is not None else None
        except Exception:                                      # noqa: BLE001
            breach = None
        t.check("breached", 1.0 if breach else 0.0, None)
        if rolled and breach:
            floor = banked * TENT_FLOOR_PCT
            t.check("floor", floor, None)
            t.check("rung", 2.5, True)
            t.hold(f"{head}: RUNG 2b TENT — 1m close beyond the "
                   f"{breach.get('option_side', '?')} short {breach.get('short_strike', 0):g}"
                   f" on a rolled structure; take the profitable side off, buy the "
                   f"opposite-type long equidistant from the survivor; the hedge is "
                   f"bought only if its debit keeps the structure above "
                   f"-{TENT_FLOOR_PCT:.0%} of cumulative credit ({floor:.2f}), else CLOSE",
                   verdict="ROLL")
            return "TENT"

        if tested is None:
            t.hold(f"{head}: formed, neither short tested — no rung, holding")
            return "HOLD"

        # ── rung 1: roll the UNTESTED side toward price to risk-free ──────
        plan = find_risk_free_roll(tested, untested, chain, current_price, banked)
        if plan is None:
            t.check("rung", 3.0, False)
            t.hold(f"{head}: {tested['option_side']} short {tested.get('short_strike', 0):g} "
                   f"TESTED and no roll is available — the untested vertical has no "
                   f"mark, or no liquid strike between it and price pays a credit; "
                   f"RUNG 3 (close and page) is the only rung left", verdict="CLOSE")
            return "CLOSE"
        t.check("roll_credit", plan.roll_credit, plan.roll_credit > 0)
        t.check("close_cost", plan.close_cost, None)
        t.check("credit_after", plan.total_credit_after, None)
        t.check("tested_width", plan.tested_width, None)
        t.check("risk_free", 1.0 if plan.risk_free else 0.0, plan.risk_free)
        cost_line = (f"roll {untested['option_side']} to {plan.new_short_strike:g}/"
                     f"{plan.new_long_strike:g}: +{plan.roll_credit:.2f} credit, "
                     f"-{plan.close_cost:.2f} to close the old, cumulative "
                     f"{plan.total_credit_after:.2f} vs tested width {plan.tested_width:.2f}")
        if plan.risk_free:
            t.check("rung", 1.0, True)
            t.hold(f"{head}: {tested['option_side']} short TESTED — RUNG 1 ROLL clears: "
                   f"{cost_line} — tested side becomes RISK-FREE", verdict="ROLL")
            return "ROLL"
        # ── no risk-free roll: the gap the ladder forbids ─────────────────
        t.check("rung", 0.0, False)
        t.hold(f"{head}: {tested['option_side']} short TESTED — RUNG 1 does NOT clear "
               f"({cost_line}); best roll leaves the tested side {plan.tested_width - plan.total_credit_after:.2f} "
               f"short of risk-free; the tent arms only AFTER a roll, so this structure "
               f"is on NO RUNG — the ladder says never do nothing on a tested structure",
               verdict="DECLINE")
        return "NO_RUNG"

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
