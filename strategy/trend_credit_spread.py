"""
strategy/trend_credit_spread.py  v4.12
v4.12  2026-09-04  r238 — 🔴 THE CREDIT VERSION OF THE RUNAWAY. Operator's
      spec, 2026-09-04. TRIGGER is `fifty_accepted` — a 1m close beyond
      `target_50pct` HELD at the next tick — reused from the ORB engine rather
      than rebuilt, because it is a dated latched event and this strategy has
      never had one. ANCHOR is the nearest OTM strike from CURRENT PRICE on the
      floor side: *"the ORB boundary is incorrect as an anchor."* The 50 is the
      trigger, spot is the anchor, and `holds_fifty` keeps a sticky latch from
      selling into a level price has retaken.
      🔑 THE WING IS THE WIDEST CLEARING 1:1 ON THE EXPIRY BASIS, not the
      best-R one — so it does NOT call `search_wing`, which maximises R and
      drives the wing narrow. Wider means more credit and more absolute stop
      room. 1:1 must be the expiry basis because with the stop at 15% OF CREDIT
      `credit/stop` is 1/0.15 for every wing — a constant, with nothing to
      solve for.
      ⚠️ `adx`, `trend_vote`, `outside_range`, `pop` and `drift_bar` are GONE.
      All were inherited for a continuation trade this is not.
      ⚠️ THREE FAULTS CAUGHT BY THE SUITE ON THE FIRST RUN, all mine: a ghost
      `chain.contracts` (OptionsChain has `.calls`/`.puts`), `safe_float` used
      six times and never imported, and an invented `cv.fill_credit`.
v4.11  2026-09-04  r237 — 🔴 PARKED. `TCS_ENTRY_END_ET` is (0,0), so
      the window gate fires at every tick and TCS goes DORMANT before a chain
      is read. Operator, 2026-09-04: *"I don't know how TCS has cleared the bar
      to fire. It looks like I do need it disabled."*
      🔑 WHY IT CLEARED: r234 moved R to the stop basis and TCS passed HONESTLY
      — UNH sold 398/402 for $0.84, credit/width 21.0% against a 13.04% bar,
      r_stop 1.77. My "TCS still fails" note was measured on SPX and QQQ at
      0.04–0.09 and I let it stand for the fleet.
      🔴 AND IT CHURNED: 11:40, 11:42, 11:42 on identical strikes for -$2.00,
      -$2.00, -$0.00. TCS has NO re-entry latch of any kind — the shape r235
      fixed for the ORB, which this never had — and `exit=breach@397.07` is the
      ORB LOW, the same bound it anchors its short strike to, so price sitting
      ON the boundary makes it enter and exit on alternating ticks.
      ⚠️ THE DORMANT MESSAGE NAMES THE PARK. The generic text would read "past
      00:00 — dormant until tomorrow", a refusal describing the wrong thing:
      tomorrow never arrives. A panel line nobody can act on is the
      plausible-silence class this repo keeps paying for.
v4.10  2026-09-04  r237 — 🔴 PARKED. `TCS_ENTRY_END_ET` is (0,0), so
      the FIRST gate is dormant at every tick of every session — before a
      chain is read or a strike is chosen. The dormant message NAMES THE PARK
      rather than printing "past 00:00 — dormant until tomorrow", which would
      describe the wrong thing: tomorrow never arrives, and a panel line
      nobody can act on is worse than none.
      ⚠️ WHY IT FIRED AT ALL: r234 moved R to the stop basis and TCS cleared it
      HONESTLY — UNH sold 398/402 for $0.84, credit/width 21.0% against a
      13.04% bar, r_stop 1.77. My "TCS still fails" note was measured on SPX
      and QQQ at 0.04–0.09 and I let it stand for the fleet.
      ⚠️ AND IT CHURNED — 11:40, 11:42, 11:42 on identical strikes closing at
      −$2.00, −$2.00, −$0.00. TCS has NO re-entry latch of any kind, the shape
      r235 fixed for the ORB and TCS never had; and `exit=breach@397.07` is the
      ORB LOW, the same bound it anchors its short strike to, so price sitting
      ON the boundary makes it enter and exit on alternating ticks.
      🔑 Rewrite spec is TCS.7. Re-enable needs BOTH a real window here AND
      clearing `OT_TCS_ACTIVE=0` from the boxes.
v4.9  2026-09-03  r234 — GATED ON THE STOP BASIS. TCS stops
      through the same lone stop at 15% of risk, so it is judged the same way.
      Reads `WingResult` BY NAME. `r_expiry` recorded.
v4.8  2026-09-02  r220 — 🔴 r219 FIXED THE PREPARE LAYER AND THIS FILE UNDID IT
      AT THE SIGNAL LAYER. `_build_signal` had no credit in scope, so it
      recomputed `short.bid - long.ask` three hundred lines below the fix —
      and `main.py:2220` hands `sig.net_credit` to `paper_fill_credit`, whose
      parameter is named `mark`. TCS kept booking the bid/ask credit while
      position_manager marked it at mid: BOTH HALF-SPREADS charged as a loss
      at fill, on every trade, exactly as the sweep did. `prep.credit` is
      passed through now and `entry_premium` is set explicitly.
      ⚠️ A FIX APPLIED AT ONE LAYER AND REVERSED AT ANOTHER LOOKS COMPLETE
      FROM EITHER END — only walking every strategy's fill path found it,
      which is what the operator asked for. check_fill_basis F5 is that walk,
      kept as a check.
v4.7  2026-09-02  r219 — 🔴 THE ENTRY AND THE MARK WERE ON DIFFERENT SIDES OF THE QUOTE.
      `search_wing` priced the credit as short.BID - long.ASK and that number
      became `sig.entry_premium` — the position's entry of record — while
      `position_manager._fetch_current_premium` marks a credit vertical at
      short.MARK - long.MARK. The gap is BOTH HALF-SPREADS, present the
      instant the position opens, and for a credit vertical a higher mark is a
      LOSS. Measured on the fleet's shape: judged $0.37, booked $0.97, gap
      $0.60 — against a lone stop carrying 60.5 cents of room. The position
      was born at its stop.
      🔑 SWEEP FORENSICS 2026-08-25..09-02 SAYS THE UNDERLYING NEVER DID IT:
      38 of 41 stopped, price NEVER reached the short strike on any of 22
      measurable trades, and moved 0.63 points toward it — implying a spread
      delta of 0.96, which a 5-wide cannot carry.
      ⚠️ OPERATOR RULING 2026-09-02: "I have a ladder for live offers, all
      paper needs to fill at mark, period." The MARK is booked. The BID/ASK
      credit is kept for the R hurdle — deciding on the conservative number
      and booking the mark refuses trades that only clear R when priced
      optimistically, so the error runs in the safe direction.
      ⚠️ AND THE OLD BEHAVIOUR HAD A PASSING TEST: check_plan_prepares S2
      asserted net_credit == 1.30, the bid/ask figure, so the suite certified
      the mismatch. Re-derived to 1.33.
v4.6  2026-08-29  r176: mu measured over the last TCS_DRIFT_HORIZON_BARS
      (the same two hours pop_drift projects over), not since the open —
      since-open zeroed on V-shapes/late trends while the vote read ADX 50+
      (MU 2026-08-29: drift +0.18 against a BEARISH vote). The vote and the
      drift now read the same clock.
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
    TCS_R_FLOOR_EXPIRY, TCS_STOP_PCT_OF_CREDIT,
    TCS_DRIFT_HORIZON_BARS,
    TCS_LOSS_GIVEN_BREACH, CONT_BREAKOUT_MIN_ADX,
    TCS_ENTRY_END_ET, INSTRUMENT, HARD_CLOSE_ET,
)
# ⚠️ NOT `from strategy.iron_condor_strategy import IronCondorStrategy`.
# TC.6 previously instantiated the condor to borrow five of its methods. The
# shared math now lives in a module OWNED BY NEITHER, so neither strategy can
# retune the other by accident — and TC.6 no longer needs the condor to exist.
from strategy import credit_vertical as cv
# r157 — the R floor is read DIRECTLY; r_hurdle() returns None under relaxed.
# ⚠️ r238 — `safe_float` was USED SIX TIMES AND NEVER IMPORTED. It parsed,
# imported and would have raised NameError on the first tick past the
# window; `check_singletons` caught it, which is exactly the class it
# exists for: "a global declared but never bound raises only when the line
# RUNS."
from utils.math_utils import safe_float
from strategy.criteria import R_FLOOR, R_FLOOR_STOP, stop_survivable
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
    # 🔴 r238 — REBUILT TO THE OPERATOR'S SPEC, 2026-09-04. The old set gated on
    # `trend_vote`, `adx` and `outside_range` and anchored the short strike to
    # the ORB BOUNDARY, frozen at 09:35. Operator: *"the ORB boundary is
    # incorrect as an anchor. The sale and the stop should be much more
    # aggressive than that"*, and *"if we made it the credit version of the
    # runaway, and anchored to the 50, I think the data would tell a completely
    # different story."* ADX and the trend vote are GONE — both were inherited
    # for a continuation trade this is not.
    CONDITIONS = {
        "active":        "TREND_CREDIT_ACTIVE is on",
        "entry_window":  "inside TCS_START_ET-TCS_ENTRY_END_ET",
        "condor_active": "no condor plan holds this symbol",
        "fifty_accepted": "a 1m close beyond the 50, HELD at the next tick",
        "holds_fifty":   "price is still on the traded side of the 50",
    }
    STRUCTURAL = ("contract", "wing", "wing_r_best", "stop_vs_spread",
                  "nickel_floor")
    PLAN_CHECKS = tuple(CONDITIONS) + STRUCTURAL + (
        "fifty", "credit", "width", "risk", "r", "r_expiry", "stop_dist",
        "dist_from_fifty_pts")

    # ══════════════════════════════════════════════════════════════════════
    # THE PLAN — the credit version of the runaway, anchored to the 50.
    # ══════════════════════════════════════════════════════════════════════
    def prepare(self, ms, vol_state, chain, macro, current_price: float, trend=None,
                orb_high=None, orb_low=None, session_high=None, session_low=None,
                condor_active: bool = False, now_et=None, orb=None):
        t = self.planner.tick(current_price)
        prep = _TCSPreparation(t)
        try:
            now = now_et or datetime.now(ET)
            if (now.hour, now.minute) >= TCS_ENTRY_END_ET:
                t.dormant("entry_window",
                          f"past TCS_ENTRY_END_ET "
                          f"{TCS_ENTRY_END_ET[0]:02d}:{TCS_ENTRY_END_ET[1]:02d}"
                          f" — no NEW positions; management runs to the flatten")
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

            # ── THE TRIGGER: the runaway's own acceptance test ──────────────
            # 🔑 `fifty_accepted` is 1m close beyond `target_50pct` THEN a hold
            # at the next tick, with the pending state discarded if it reverses
            # ("a close that reverses immediately is a wick with extra steps").
            # Reused rather than rebuilt: it is a dated, latched, falsifiable
            # event, which is exactly what this strategy has never had.
            _acc = bool(getattr(orb, "fifty_accepted", False))
            _fifty = safe_float(getattr(orb, "target_50pct", 0.0)) or 0.0
            _bdir = str(getattr(orb, "break_direction", "") or "")
            prep.cond("fifty_accepted", 1.0 if _acc else 0.0,
                      self.CONDITIONS["fifty_accepted"], _acc)
            if not _acc or _fifty <= 0 or _bdir not in ("long", "short"):
                if _acc and (_fifty <= 0 or not _bdir):
                    prep.starved.append("target_50pct")
                    t.starved("target_50pct")
                return prep
            t.check("fifty", round(_fifty, 4), True)

            # ── SIDE: sell the FLOOR side of a long break, the ceiling of a
            # short one. The 50 is the level the move proved by accepting
            # through it, so the credit sits behind it.
            long_side = (_bdir == "long")
            side = "put" if long_side else "call"
            direction = "long" if long_side else "short"
            prep.side, prep.direction, prep.bound = side, direction, _fifty
            t.direction = direction
            t.anchor(trigger=_fifty, invalidation=_fifty)

            # ── THE 50 MUST STILL HOLD ──────────────────────────────────────
            # 🔴 OPERATOR: *"the 50 is still the lowest bar for entry after the
            # clock."* `fifty_accepted` is LATCHED for the session, and the
            # strike is anchored to SPOT — so without this, an acceptance at
            # 947 followed by a collapse to 930 would sell the 925 put into a
            # level price had already retaken. The latch says the move
            # happened; this says it is still true.
            _holds = (current_price > _fifty) if long_side else (current_price < _fifty)
            prep.cond("holds_fifty", round(current_price - _fifty, 4),
                      self.CONDITIONS["holds_fifty"], _holds)
            t.check("dist_from_fifty_pts", round(abs(current_price - _fifty), 4), None)
            if prep.unmet:
                return prep

            # ── THE SHORT: NEAREST OTM FROM CURRENT PRICE ────────────────────
            # 🔴 OPERATOR: *"the short should be the nearest OTM strike from the
            # current price on the floor side."* SPOT, not the 50 — at the
            # moment of acceptance they coincide, but the debit block (r197)
            # can delay entry, and when it lifts the sale must be aggressive
            # relative to where price IS, not where it was.
            # ⚠️ `.calls` / `.puts` — OptionsChain HAS NO `.contracts`, and
            # check_attr_fidelity caught the ghost attribute on the first run.
            if isinstance(chain, (list, tuple)):
                contracts = list(chain)
            else:
                contracts = list(getattr(chain, "puts" if side == "put" else "calls",
                                         None) or [])
            strikes = sorted({safe_float(getattr(c, "strike", 0)) or 0.0
                              for c in contracts} - {0.0})
            _otm = [k for k in strikes if k < current_price] if side == "put" \
                else [k for k in strikes if k > current_price]
            if not _otm:
                prep.structural.append(("contract",
                    f"no OTM {side} strike from {current_price:.2f}"))
                return prep
            target = max(_otm) if side == "put" else min(_otm)
            short = cv.find_contract_at_strike(contracts, target)
            if short is None:
                prep.structural.append(("contract",
                    f"nearest OTM strike {target:.2f} has no contract"))
                return prep
            t.check("contract", short.strike, True)
            prep.short = short

            # ── THE WING: WIDEST THAT STILL CLEARS 1:1 ──────────────────────
            # 🔴 OPERATOR: *"a 1:1R minimum required, so set the protective wing
            # accordingly"*, taking the MOST AGGRESSIVE reading — 1:1 on the
            # EXPIRY basis, `credit / (width - credit) >= 1`, i.e. credit >= 50%
            # of width. NOT r234's stop basis, and that is deliberate: with the
            # stop at 15% OF CREDIT, `credit / stop` is 1/0.15 = 6.67 for every
            # credit and every wing, so R on the stop basis is a CONSTANT and
            # the wing would have nothing to solve for. Only the expiry basis
            # makes "set the wing accordingly" mean anything.
            # 🔑 WIDEST, NOT BEST. `search_wing` maximises R, which drives the
            # wing NARROW. Here a wider wing collects more credit and buys more
            # absolute room, so the best qualifying wing is the WIDEST one that
            # still clears the floor — the opposite search, and the reason this
            # does not call `cv.search_wing`.
            best = None
            _sb = safe_float(getattr(short, "bid", 0.0)) or 0.0
            _sa = safe_float(getattr(short, "ask", 0.0)) or 0.0
            _why = ""
            for c in contracts:
                k = safe_float(getattr(c, "strike", 0)) or 0.0
                if k <= 0 or (k >= target if side == "put" else k <= target):
                    continue
                ask = safe_float(getattr(c, "ask", None))
                if ask is None or ask < 0:
                    continue
                width = abs(target - k)
                credit = _sb - ask                     # judged bid/ask (r219)
                if width <= 0 or credit <= 0 or credit >= width:
                    continue
                r_expiry = credit / (width - credit)
                if r_expiry < TCS_R_FLOOR_EXPIRY:
                    _why = _why or (f"widest wing clearing 1:1 not found — best "
                                    f"R {r_expiry:.2f} at {width:g} wide")
                    continue
                # 🔴 THE STOP IS 15% OF CREDIT, and it must still clear twice
                # the short leg's quote. A stop inside the spread fires on a
                # quote update, not on the trade being wrong — exit_engine
                # calls this exact form "the inverted rule r155 replaced. The
                # trade will stop on noise."
                _sd = credit * TCS_STOP_PCT_OF_CREDIT
                _ok, _svwhy = stop_survivable(_sd, _sb, _sa)
                if not _ok:
                    _why = f"15%-of-credit stop is unsurvivable: {_svwhy}"
                    continue
                if best is None or width > best[0]:
                    best = (width, c, credit, r_expiry, _sd)
            if best is None:
                prep.structural.append(
                    ("wing_r_best" if "1:1" in _why else "stop_vs_spread",
                     _why or f"no wing beyond {target:.2f} prices a credit"))
                return prep
            _bw, long_c, credit, r_expiry, _sd = best
            t.check("wing", long_c.strike, True)
            t.check("width", _bw, True)
            t.check("credit", round(credit, 4), True)
            t.check("r_expiry", round(r_expiry, 4), r_expiry >= TCS_R_FLOOR_EXPIRY)
            t.check("wing_r_best", round(r_expiry, 4), True)
            t.check("stop_vs_spread", round(_sd, 4), True)
            t.check("stop_dist", round(_sd, 4), None)
            t.check("risk", round(_bw - credit, 4), None)
            t.check("r", round(r_expiry, 4), True)

            # ── THE NICKEL FLOOR: a credit worth collecting ─────────────────
            _nick = TCS_NICKEL_REF * TCS_MIN_CREDIT_NICKEL_MULT
            if credit < _nick:
                prep.structural.append(("nickel_floor",
                    f"credit ${credit:.2f} below the nickel floor ${_nick:.2f}"))
                return prep
            t.check("nickel_floor", round(credit, 4), True)

            # 🔑 BOOK THE MARK, JUDGE ON BID/ASK (r219). The economics above are
            # decided on the conservative number; what gets RECORDED is what a
            # mid fill actually pays.
            # ⚠️ `cv.fill_credit` DOES NOT EXIST — the first draft invented it,
            # which is the §0.1 failure this repo names. The mark credit is
            # computed the same way `search_wing` does it, with `safe_float`
            # so a NaN mark is None rather than a number.
            _sm = safe_float(getattr(short, "mark", None))
            _lm = safe_float(getattr(long_c, "mark", None))
            _fill = (round(max(0.0, _sm - _lm), 4)
                     if _sm is not None and _lm is not None else None)
            if _fill is None:
                prep.structural.append(("contract",
                    "a leg has no usable mark — no fill credit to book"))
                return prep
            prep.long, prep.credit, prep.width = long_c, _fill, _bw
            prep.r = round(r_expiry, 4)
            prep.ready = not (prep.unmet or prep.structural or prep.starved)
        except Exception as exc:                                # noqa: BLE001
            logger.error("[tcs] prepare raised: %s", exc, exc_info=True)
            prep.starved.append("exception")
            t.starved("exception")
        return prep

    def generate_signal(self, ms, vol_state, chain, macro,
                        current_price: float, trend=None,
                        orb_high: Optional[float] = None,
                        orb_low: Optional[float] = None,
                        session_high: Optional[float] = None,
                        session_low: Optional[float] = None,
                        condor_active: bool = False,
                        now_et: Optional[datetime] = None,
                        orb=None):
        """Returns a condor-leg-shaped OptionsSignal, or None.

        ⚠️ NO `orb` PARAMETER. v1.x took one and gated on
        `invalidation_reason == "runaway"`; both are gone. After 11:00 ORB has
        stopped and owns nothing, so there is no slot to arbitrate and no
        morning level worth anchoring to.
        """
        prep = self.prepare(ms, vol_state, chain, macro, current_price, trend=trend,
                            orb_high=orb_high, orb_low=orb_low, session_high=session_high,
                            session_low=session_low, condor_active=condor_active,
                            now_et=now_et, orb=orb)
        if not prep.ready or prep.unmet or prep.structural or prep.starved:
            return prep.tick.already()
        # ⚠️ `prep.credit` IS PASSED NOW. `_build_signal` had no credit in scope
        # and so recomputed one from bid/ask — which is how r219's fix at the
        # prepare layer was silently undone at the signal layer.
        return prep.tick.take(self._build_signal(prep.side, prep.short, prep.long,
                                                 prep.direction, prep.bound,
                                                 current_price, ms, prep.bars,
                                                 prep.credit))

    def _build_signal(self, side, short, long_c, direction, boundary,
                      current_price, ms, bars, fill_credit):
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
        # 🔴 r220 — THIS RECOMPUTED THE BID/ASK CREDIT AND BYPASSED r219. r219
        # moved `prep.credit` to the mark, and this line then overwrote the
        # decision three hundred lines later — `main.py:2220` hands
        # `sig.net_credit` to `paper_fill_credit`, whose parameter is named
        # `mark`. So TCS kept booking `short.bid - long.ask` while
        # position_manager marked it at mid: both half-spreads charged as a
        # loss at fill, on every trade, exactly as the sweep did.
        # ⚠️ A FIX APPLIED AT THE PREPARE LAYER AND UNDONE AT THE SIGNAL LAYER
        # LOOKS COMPLETE FROM EITHER END. Only walking every strategy's fill
        # path found it, which is why the operator asked for that walk.
        sig.net_credit = fill_credit
        sig.entry_premium = fill_credit     # what the row records
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
