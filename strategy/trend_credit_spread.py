"""
strategy/trend_credit_spread.py  v4.5
v4.5  2026-08-27  r164 — THE PLAN PREPARES, THE STRATEGY EXECUTES WITH THE
      PLAN'S VARIABLES (the sweep's v4.6 shape). `prepare()` is the plan: in
      the slot, every tick, it evaluates each declared CONDITION with its
      reading (active, window, no condor plan, directional vote, ADX, price
      still outside the range), SELECTS the short at the first strike inside
      the opening range, the wing searched to R_FLOOR, the bid/ask credit,
      POP, EV and the nickel floor, and writes DORMANT / NO PLAN / DECLINE
      (structural) / HOLD "PREPARED — <trade>. Waiting on: <conditions>" /
      TAKE. `generate_signal()` executes the prepared spread and touches no
      chain. The muteable `t.executable()` R hurdle is gone — R is a
      construction target inside search_wing (r157) and wing_r_best refuses
      structurally; calling both let relaxed re-decide a structural fact.
v4.4  2026-08-27  r153/r157 (RECORDED RETROACTIVELY in r164 — changed with no
      title bump and no entry): out-of-window ticks go DORMANT (r153); the
      wing is searched to R_FLOOR via credit_vertical.search_wing (r157).
v4.3  2026-08-26  r146 — THE PLAN IS WIRED. This strategy had ZERO `_gate()`
      call sites and fourteen `return None`s, each with a good log line that
      never left the log. Every one now goes through `self.planner`
      (strategy/plan.py) and writes a DECLINE row naming the gate; the
      what-if is priced off the REAL spread this spec selects (short at the
      first-inside strike, wing at TCS_WING_WIDTH, credit from bid-ask):
      R = credit / (width - credit), real width, never an assumed $5. The R
      hurdle is consulted: STRICT refuses below the floor, RELAXED records
      and proceeds. The trigger/invalidation the plan records are the ORB
      bound this file already fixes; the plan moves nothing.
v4.2  2026-08-24  r100 — REMOVED `ms=""` from the OptionsSignal constructor. Not
      a field; TC.6 raised TypeError on every fire and has never produced a
      signal since r65.

v4.1  2026-08-21  r60: reads TCS_ENTRY_END_ET (inert while parked) - the
      global cutoff it used to read is deleted.
ORB-bounded credit spread. TRIGGER REBUILT IN PHASE 2.

v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

strategy/trend_credit_spread.py — options_trader_v3 — (TC.6)
NAMING CODIFIED, AND THE CONDOR RULES DIS-INHERITED.
        **TREND CONTINUATION** = the LONG (DEBIT) contract placed on an ORB
        runaway handoff. Blocked after 11:00 by AFD.1.
        **TREND PARTICIPATION** (this file) = a CREDIT SPREAD at the floor of a
        move, BOUNDED BY THE ORB HIGH for a long / ORB LOW for a short, and
        INVALIDATED BY A BREACH of that level. Nothing else closes it before the
        session hard close.
        THE OPERATOR'S CORRECTION THAT MATTERS: *"those levels are fixtures."*
        The ORB **ENGINE** must not gate an afternoon trade — no runaway flag,
        no slot arbitration, no `invalidation_reason`, and nothing a restart can
        erase. The ORB **LEVEL** is a price on a chart and is recomputed from
        the TAPE (`main._opening_range`). v2.0 over-corrected by removing both.
        DIS-INHERITED FROM THE CONDOR:
          · **the 0.80 x EM minimum distance.** The condor needs it because it
            sells around a PIN with no structural level; TC.6 HAS one. Since a
            strike must clear BOTH constraints, an EM floor beyond the ORB high
            would push the strike past the specified level — a FITTED
            percentage silently overriding a STRUCTURAL one.
          · **the nickel close.** A profit exit caps a position whose measured
            EV was HELD TO EXPIRY, UNMANAGED.
        ADDED: **price must be OUTSIDE the range at entry.** The exit calls a
        close back through the bound INVALIDATION, so entering while price is
        already inside means the trade is BORN IN THE STATE ITS OWN EXIT CALLS
        DEAD — the CNT.1 failure shape, which made every breakout continuation
        a one-tick artefact for a week.
        REMOVED: **the 30-minute cooldown.** It was an emergency brake during
        the rapid-fire incident and the wrong instrument for the right worry —
        the loop came from a $0.06 credit sitting one cent from a nickel close
        and one cent from a mis-set stop, all now fixed at the source. Operator:
        *"It's gated enough. The cooldown is excessive."*
        RETAINED from the condor, deliberately: quote width (liquidity is
        universal), POP >= 0.70 (the operator's own 70-80%% band, stated about
        exactly this trade), the not-exceeded session extreme, and deferral to
        an active condor plan (real deconfliction, not conflation).
AFTERNOON TREND PARTICIPATION BY SELLING PREMIUM BENEATH THE MOVE.
⚠️ v2.0 — **THE ORB LINK IS SEVERED.** Operator, 2026-08-14, after TC.6 went
silent for an entire afternoon: *"Trend participation should have nothing to do
with orb range after the 11AM cutoff... If they are linked in any way after
11AM, then it's wrong."*
WHY THE ORB ANCHOR WAS WRONG, and it was wrong from the start:
  · **IT WAS THE WRONG LEVEL.** v1.x anchored on the broken ORB boundary, which
    was imported from a measurement of MORNING runaway trades where price was
    still near the opening range. By 13:00 that range is four hours stale and
    price may be nowhere near it.
  · **IT MADE AN AFTERNOON STRATEGY DEPEND ON MORNING STATE.** `orb_state.json`
    is WRITE-ONLY — there is no load path anywhere in the repo — so the ORB
    engine lives entirely in memory. The 2026-08-14 10:37 restart wiped
    `invalidation_reason` on all 15 boxes, and because ORB cannot re-arm past
    its 11:00 cutoff, **the runaway flag was gone permanently for the session.**
    TC.6's hard gate became unsatisfiable no matter what the tape did. A whole
    afternoon of zero fires, from a silent gate.
  · **AND THE GATE WAS SILENT**, which is how the afternoon was spent guessing.
THE ANCHOR IS NOW THE SESSION EXTREME — the operator's own original framing,
*"a vertical spread at the floor of the Move."* Session LOW for a bull trend,
session HIGH for a bear. It updates continuously, exists on every box every day,
survives restarts, and needs nothing from the morning.
MEASURED (`spread_counterfactual --anchor floor`, 18 sessions, PDL + session
low): TRENDING_BEAR +0.39 / +0.48 / +0.46 and TRENDING_BULL +0.60 / +0.66 /
+0.78 at 0.00%% / 0.25%% / 0.50%% beyond the floor.
⚠️ **BOTH ARMS POSITIVE, so this is a GENERAL credit edge rather than a
FAILED. Stated plainly rather than dressed up.
⚠️ AND THE RUNAWAY GATE WAS A CATEGORY ERROR. Operator: *"The reason it
requires a runaway before 11am is because ORB OWNS THAT SLOT. So a runaway is
the only exception a different trade can execute."* The runaway is a
SLOT-ARBITRATION rule, never an anchoring rule — ORB owns 09:35-11:00, and a
runaway is the one condition where ORB is definitively out (INVALIDATED, never
re-arms) so the slot frees. The correct occupants of that freed slot ALREADY
EXIST and are unchanged by this file: `trend_continuation_handoff` (via
`_is_runaway`) and `SweepReversal` (gates on `invalidation_reason in ("runaway",
"timeout")`).
**AFTER 11:00 ORB HAS STOPPED ENTIRELY — there is no slot to arbitrate**, so
requiring the arbitration condition was asking permission from a strategy that
is not running. TC.6 owns afternoon trend participation outright.
DIRECTION COMES FROM THE TREND VOTE (`overall_direction` + ADX), the same source
CNT.1's breakout branch already uses — no new machinery, and no dependence on
any morning artefact.
EXIT: BREACH OR NICKEL. Breach is a CLOSED BAR through the floor recorded AT
ENTRY. Fixed, not ratcheting: a floor that follows price would tighten the
invalidation on a winning trade, which is the opposite of letting it run — and
the short strike it was sold against does not move either.
⚠️ **THE MEASURED EV WAS HELD TO EXPIRY, UNMANAGED.** No premium stop, no
ratchet. `is_trend_credit` keeps `exit_engine` out of the condor ladder.
STRIKE SELECTION HAS ONE OWNER, AND IT IS NEITHER STRATEGY.
`strategy/credit_vertical.py` implements rail -> min-distance -> not-exceeded ->
quote-width -> POP, and both this file and the condor import it. TC.6 used to
instantiate `IronCondorStrategy` to borrow five of its methods and six of its
`CONDOR_*` knobs — so a condor tuning change silently retuned this trade, and
its identity had to survive as a flag on a record built by the condor's own
execution path. That is the coupling that produced 108 bad trades on
2026-08-14.
"""

import logging
from datetime import datetime
from typing import Optional

import pytz

from config import (
    TCS_MIN_POP, TCS_MAX_QUOTE_WIDTH, TCS_POP_BAR_MIN, TCS_NICKEL_REF,
    TCS_WING_WIDTH_SPX, TCS_WING_WIDTH_QQQ,
    TREND_CREDIT_ACTIVE, TCS_START_ET, TCS_MIN_CREDIT_NICKEL_MULT,
    TCS_LOSS_GIVEN_BREACH, CONT_BREAKOUT_MIN_ADX,
    TCS_ENTRY_END_ET, INSTRUMENT, HARD_CLOSE_ET,
)
# ⚠️ NOT `from strategy.iron_condor_strategy import IronCondorStrategy`.
# TC.6 previously instantiated the condor to borrow five of its methods. The
# shared math now lives in a module OWNED BY NEITHER, so neither strategy can
# retune the other by accident — and TC.6 no longer needs the condor to exist.
from strategy import credit_vertical as cv
# r157 — the R floor is read DIRECTLY; r_hurdle() returns None under relaxed.
from strategy.criteria import R_FLOOR
from strategy.plan import Plan, _n

logger = logging.getLogger(__name__)

# ── GATE CATEGORIES AS DATA (WA §36) ───────────────────────────────────────
# ⚠️ NOT SPECCED, DELIBERATELY, AND NOT DISPATCHED. TC.6 is absent from v4's
# dispatch chain and has no v4 trigger. The record: **21 trades, 28.6%
# direction accuracy.**
# The reasoning, from docs/TRADES.md: the sweep credit spread sells a boundary
# that PROVED ITSELF - price went there, failed, came back. **The ORB edge has
# proven nothing except that the first fifteen minutes had a high and a low.**
# It is also redundant against the runaway: one trades the ORB *breaking and
# holding*, the other the ORB *holding*. Between them they cover every outcome,
# **which is not coverage.**
# An empty declaration is the honest one - there are no gates because there is
# no trigger. If ORB-boundary credit is worth having, the sweep
# discriminator's method measures it first and the spec comes after.
GATES = {}
ET = pytz.timezone("US/Eastern")


class _TCSPreparation:
    """What the plan hands the strategy each tick of the slot — never executable."""
    __slots__ = ("tick", "side", "direction", "bound", "short", "long", "credit",
                 "width", "pop", "r", "bars", "conditions", "unmet", "structural",
                 "starved", "ready")

    def __init__(self, tick):
        self.tick = tick
        self.side = self.direction = ""
        self.bound = None
        self.short = self.long = None
        self.credit = self.width = self.pop = self.r = None
        self.bars = 0.0
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
        return (f"sell {self.short.strike:g}{self.side[0].upper()} / buy "
                f"{self.long.strike:g}{self.side[0].upper()}  credit {self.credit:.2f} "
                f"(bid/ask)  width {self.width:g}  POP {self.pop:.2f}  R {self.r:.2f} "
                f"(min {R_FLOOR:.2f})  exit BREACH of {self.bound:.2f} or nickel")


class TrendCreditSpread:
    """Sell a defined-risk vertical beyond the session extreme — the floor of
    the current move. Afternoon only; owns the slot outright once ORB stops."""

    name = "TrendCreditSpread"

    def __init__(self):
        self.planner = Plan(self.name, self.PLAN_CHECKS)

    @staticmethod
    def _wing_width() -> float:
        return (TCS_WING_WIDTH_SPX if INSTRUMENT in ("SPX", "SPXW")
                else TCS_WING_WIDTH_QQQ)

    # ── THE DECLARED CONDITIONS — what must be true for this spec to fire ──
    CONDITIONS = {
        "active":        "TREND_CREDIT_ACTIVE is on",
        "entry_window":  "inside TCS_START_ET-TCS_ENTRY_END_ET",
        "condor_active": "no condor plan holds this symbol",
        "trend_vote":    "the trend engine's overall_direction is BULLISH or BEARISH",
        "adx":           f"primary ADX >= {CONT_BREAKOUT_MIN_ADX:.1f}",
        "outside_range": "price is still OUTSIDE the opening range on the trend side",
    }
    STRUCTURAL = ("strike_inside_range", "contract", "pop", "wing", "wing_r_best",
                  "ev", "nickel_floor")
    PLAN_CHECKS = tuple(CONDITIONS) + STRUCTURAL + ("bound", "credit", "width",
                                                    "risk", "r")

    # ══════════════════════════════════════════════════════════════════════
    # THE PLAN — evaluates the declared conditions, SELECTS the spread.
    # ══════════════════════════════════════════════════════════════════════
    def prepare(self, ms, vol_state, chain, macro, current_price: float, trend=None,
                orb_high=None, orb_low=None, session_high=None, session_low=None,
                condor_active: bool = False, now_et=None):
        t = self.planner.tick(current_price)
        prep = _TCSPreparation(t)
        try:
            now = now_et or datetime.now(ET)
            if (now.hour, now.minute) >= TCS_ENTRY_END_ET:
                t.dormant("entry_window", f"past TCS_ENTRY_END_ET "
                                          f"{TCS_ENTRY_END_ET[0]:02d}:{TCS_ENTRY_END_ET[1]:02d}"
                                          f" — dormant until tomorrow")
                return prep
            if (now.hour, now.minute) < TCS_START_ET:
                t.dormant("entry_window", f"before TCS_START_ET "
                                          f"{TCS_START_ET[0]:02d}:{TCS_START_ET[1]:02d}"
                                          f" — dormant, not looking at the chart")
                return prep
            prep.cond("entry_window", None, self.CONDITIONS["entry_window"], True)
            prep.cond("active", 1.0 if TREND_CREDIT_ACTIVE else 0.0,
                      self.CONDITIONS["active"], TREND_CREDIT_ACTIVE)
            prep.cond("condor_active", 1.0 if condor_active else 0.0,
                      self.CONDITIONS["condor_active"], not condor_active)
            _dir = str(getattr(trend, "overall_direction", "NEUTRAL") or "NEUTRAL").upper()
            _adx = float(getattr(trend, "primary_adx", 0.0) or 0.0)
            directional = _dir in ("BULLISH", "BEARISH")
            prep.cond("trend_vote", (1.0 if _dir == "BULLISH" else -1.0) if directional else 0.0,
                      f"BULLISH or BEARISH (now {_dir})", directional)
            prep.cond("adx", _adx, self.CONDITIONS["adx"], _adx >= CONT_BREAKOUT_MIN_ADX)
            if not directional:
                # no side to prepare: the vote decides which bound is the level
                t.hold(f"trend vote {_dir}, ADX {_adx:.1f}: no side to prepare — "
                       f"waiting on a directional vote")
                return prep
            if _dir == "BULLISH":
                side, bound, direction = "put", orb_high, "long"
            else:
                side, bound, direction = "call", orb_low, "short"
            prep.side, prep.direction, prep.bound = side, direction, bound
            t.direction = direction
            if not bound or bound <= 0:
                prep.starved.append("bound")
                t.starved("bound")
                return prep
            t.anchor(trigger=bound, invalidation=bound)
            t.check("bound", bound, True)
            _outside = (current_price > bound if side == "put" else current_price < bound)
            prep.cond("outside_range", current_price - bound, self.CONDITIONS["outside_range"],
                      _outside)

            # ── SELECTION — the spread, if the conditions hold next tick ──
            if chain is None:
                prep.starved.append("chain")
                t.starved("chain")
                return prep
            sigma = float(getattr(vol_state, "atr_current", 0.0) or 0.0)
            bars = cv.bars_left(now, TCS_POP_BAR_MIN, HARD_CLOSE_ET)
            prep.bars = bars
            contracts = chain.puts if side == "put" else chain.calls
            _lo, _hi = (orb_low, orb_high)
            _inside = sorted({float(c.strike) for c in contracts
                              if _lo is not None and _hi is not None
                              and _lo <= float(c.strike) <= _hi})
            if not _inside:
                prep.structural.append(("strike_inside_range",
                    f"no strike inside the opening range {_n(_lo)}–{_n(_hi)} "
                    f"(increments too wide)"))
            else:
                target = _inside[0] if side == "call" else _inside[-1]
                t.check("strike_inside_range", target, True)
                short = cv.find_contract_at_strike(contracts, target)
                if short is None:
                    prep.structural.append(("contract", f"first-inside strike {target:.2f} has no contract"))
                else:
                    t.check("contract", short.strike, True)
                    pop = cv.pop(abs(short.strike - current_price), sigma, bars)
                    t.check("pop", pop, pop >= TCS_MIN_POP)
                    if pop <= 0.0:
                        prep.structural.append(("pop",
                            f"POP unresolvable (sigma {sigma:.4f}, bars {bars:.1f}) — a "
                            f"missing input is not a safe trade"))
                    elif pop < TCS_MIN_POP:
                        prep.structural.append(("pop",
                            f"POP {pop:.2f} < {TCS_MIN_POP:.2f} at {bars:.1f} bars for "
                            f"strike {short.strike:.2f}"))
                    else:
                        _best_r, long_c, credit, _bw = cv.search_wing(contracts, short, side, R_FLOOR)
                        if long_c is None:
                            prep.structural.append(("wing",
                                f"no priceable wing beyond {short.strike:.2f} (undefined risk "
                                f"is never sold)"))
                        else:
                            t.check("wing", long_c.strike, True)
                            t.check("wing_r_best", _best_r, _best_r >= R_FLOOR)
                            if _best_r < R_FLOOR:
                                prep.structural.append(("wing_r_best",
                                    f"no wing clears R {R_FLOOR:.2f} — best is {_best_r:.2f} at "
                                    f"{long_c.strike:.2f} ({_bw:g} wide, credit ${credit:.2f}); "
                                    f"structure, not selection — relaxed does not waive it"))
                            else:
                                t.credit_spread(short.strike, long_c.strike, credit,
                                                invalidation=bound, trigger=bound)
                                width = _bw
                                req = TCS_LOSS_GIVEN_BREACH * (1.0 - pop) / pop
                                t.check("ev", credit / width - req, credit / width > req)
                                floor_n = TCS_MIN_CREDIT_NICKEL_MULT * TCS_NICKEL_REF
                                t.check("nickel_floor", credit - floor_n, credit >= floor_n)
                                if credit / width <= req:
                                    prep.structural.append(("ev",
                                        f"negative EV — credit {credit:.2f} = "
                                        f"{100.0 * credit / width:.1f}% of width {width:.0f}, "
                                        f"needs > {100.0 * req:.1f}% at POP {pop:.2f}"))
                                elif credit < floor_n:
                                    prep.structural.append(("nickel_floor",
                                        f"credit {credit:.2f} below {TCS_MIN_CREDIT_NICKEL_MULT:.1f}x "
                                        f"nickel ({floor_n:.2f}) — no room to profit"))
                                else:
                                    prep.short, prep.long, prep.credit = short, long_c, credit
                                    prep.width, prep.pop, prep.r = width, pop, t.r
                                    prep.ready = True

            head = (f"{'BULLISH' if side == 'put' else 'BEARISH'} vote ADX {_adx:.1f}, "
                    f"{side} spread off the ORB {'high' if side == 'put' else 'low'} "
                    f"{bound:.2f}")
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
        except Exception as exc:                               # noqa: BLE001
            logger.warning("[tcs] prepare failed: %s", exc)
            if not t.closed:
                t.refuse("raised", f"{type(exc).__name__}: {exc}", verdict="NO PLAN")
            prep.starved.append("raised")
            return prep

    # ══════════════════════════════════════════════════════════════════════
    # THE STRATEGY — conditions true -> execute the plan's spread.
    # ══════════════════════════════════════════════════════════════════════
    def generate_signal(self, ms, vol_state, chain, macro,
                        current_price: float, trend=None,
                        orb_high: Optional[float] = None,
                        orb_low: Optional[float] = None,
                        session_high: Optional[float] = None,
                        session_low: Optional[float] = None,
                        condor_active: bool = False,
                        now_et: Optional[datetime] = None):
        """Returns a condor-leg-shaped OptionsSignal, or None.

        ⚠️ NO `orb` PARAMETER. v1.x took one and gated on
        `invalidation_reason == "runaway"`; both are gone. After 11:00 ORB has
        stopped and owns nothing, so there is no slot to arbitrate and no
        morning level worth anchoring to.
        """
        prep = self.prepare(ms, vol_state, chain, macro, current_price, trend=trend,
                            orb_high=orb_high, orb_low=orb_low, session_high=session_high,
                            session_low=session_low, condor_active=condor_active,
                            now_et=now_et)
        if not prep.ready or prep.unmet or prep.structural or prep.starved:
            return prep.tick.already()
        return prep.tick.take(self._build_signal(prep.side, prep.short, prep.long,
                                                 prep.direction, prep.bound,
                                                 current_price, ms, prep.bars))

    def _build_signal(self, side, short, long_c, direction, boundary,
                      current_price, ms, bars):
        """Condor-leg shape, so `_execute_condor_leg` runs it unchanged.

        `is_trend_credit` is the flag `exit_engine` keys on. WITHOUT IT this leg
        inherits the condor's 25%% premium stop and ratchet — and the measured
        EV was HELD TO EXPIRY, UNMANAGED. A stop bolted on afterwards is a
        different trade with a different expectancy.
        """
        from strategy.base_strategy import OptionsSignal
        sig = OptionsSignal(
            strategy_name=self.name,
            setup_type=f"trend_credit_{direction}",
            direction="neutral",              # a credit spread has no side to be on
            option_side=side,
            underlying_entry=current_price,
            # THE INVALIDATION LEVEL, and the exit. A close beyond the broken
            # boundary is thesis death — the same event orb_structure_stop names.
            underlying_stop=boundary,
            # 🔴 r100 — `ms=""` REMOVED. OptionsSignal HAS NO SUCH FIELD, so this
            # constructor raised TypeError on EVERY fire and `_safe_strategy`
            # logged it as a strategy failure: "[tcs] generate_signal failed:
            # OptionsSignal.__init__() got an unexpected keyword argument 'ms'",
            # 160 times on NFLX on 2026-08-24 alone. TC.6 HAS NEVER PRODUCED A
            # SIGNAL since r65 renamed the retired label kwarg here without
            # checking that the field it renamed to exists. Same class as
            # main.py's `manage_open_position(ms=None)` (r99). Pinned repo-wide
            # by tests/check_signal_kwargs.py, which checks every dataclass
            # construction against its real fields.
        )
        sig.is_credit_vertical = True         # credit-spread math, not debit
        sig.is_trend_credit = True            # exit_engine: breach-or-nickel ONLY
        sig.net_credit = max(0.0, (short.bid or 0.0) - (long_c.ask or 0.0))
        if side == "call":
            sig.short_call_contract, sig.long_call_contract = short, long_c
        else:
            sig.short_put_contract, sig.long_put_contract = short, long_c
        sig.contract = short
        sig.conviction = 1.0
        logger.info(
            "[tcs] %s spread: short %.2f / long %.2f, credit %.2f, boundary "
            "%.2f, %.1f bars left — exit is BREACH or NICKEL, no premium stop",
            side, short.strike, long_c.strike, sig.net_credit, boundary, bars)
        return sig
