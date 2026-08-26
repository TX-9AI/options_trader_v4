"""
derived/plans.py  v1.0  (2026-08-25)

FORWARD PLANS — declared, priced, and RECORDED. Gates nothing.

🔴 OPERATOR, 2026-08-25: *"I want to see better communication from the bots
tomorrow about what they're seeing."*

This engine answers, every tick, the question the fleet could not answer today:

    WHAT DOES EACH PLAN LOOK LIKE RIGHT NOW — what would I trade, what does it
    cost, what does it pay, and what would stop it?

════════════════════════════════════════════════════════════════════════════
⚠️ OBSERVE-ONLY. THIS ENGINE CANNOT CAUSE OR PREVENT A TRADE.
════════════════════════════════════════════════════════════════════════════
It is a DerivedEngine, and this project's rule for those is absolute:
contributors inform, they never authorise. Nothing in `main.py` reads its
output; entry and exit behave EXACTLY as they did before it existed. That is
deliberate for tonight — the plan architecture is a large build (docs/PLAN_SPEC.md)
and the operator's stated need right now is VISIBILITY, not new behaviour.
Landing observation first means tomorrow's session produces the evidence the
build needs, at zero risk to what trades.

════════════════════════════════════════════════════════════════════════════
WHY THIS EXISTS — 2026-08-25, verified
════════════════════════════════════════════════════════════════════════════
TSLA ran 351.4 -> 356.9 between 11:35 and 13:00. Verified from strategy_note:
`TrendCreditSpread` evaluated 182 times in that window and signalled once;
`TrendCS2nd` signalled on 207 of 218 looks and traded nothing. Verified from
main.py: ONLY `ORBStrategy` ever calls `open_plan`, so the PLANS panel showed
six ORB rows, newest 10:38, and NOTHING about the largest move of the day.
Operator: *"it's looking like nothing was watching it & that's where my
aggravation lies."*

`strategy_note` records that a strategy was ASKED. It cannot record what was
AVAILABLE, or what any of it would have cost. This engine records both.

════════════════════════════════════════════════════════════════════════════
WHAT IS FROZEN, WHAT IS LIVE
════════════════════════════════════════════════════════════════════════════
  FROZEN at declaration      LIVE every tick
  ────────────────────       ───────────────
  trigger price              mark of the named contracts
  invalidation price         credit / debit available now
  the contracts by strike    R offered now
  the reason declared        distance to trigger

⚠️ RE-PRICING A NAMED CONTRACT IS NOT THE CIRCULAR LOOP. The loop was a SCORE
recomputed from data containing the move and then used to FIRE. Here the
trigger never moves; only the cost of a FIXED instrument changes, which is a
fact about the market rather than a signal derived from it.

════════════════════════════════════════════════════════════════════════════
THE R FLOOR, AND WHAT IT MEASURED TODAY
════════════════════════════════════════════════════════════════════════════
Operator: *"can it decline on r-value alone if it determines that we can't get
at least a 1:1 and state that as the reason while naming the target level &
stop level?"* Yes — `PLAN_R_FLOOR`, and the decline names its levels.

⚠️ STOP DISTANCE IS THE PLAN'S OWN INVALIDATION AND NOTHING ELSE — no trail,
no ratchet. Operator's constraint and it is the right one: a trail is a
MANAGEMENT decision taken after entry, so folding it into the entry's R
flatters every setup by counting a rescue that has not happened.

MEASURED on TSLA 2026-08-25 from raw/chain_snapshots, at 11:31/12:00/12:30/
13:00/13:30/14:00 — trend participation offered **R 0.18 to 0.34, never once
near 1:1**, while the butterfly on the same chain in the same minutes offered
**3.81 to 5.10**. Nothing in the system compared them because nothing computed
either number before firing.
"""
from __future__ import annotations

import logging
import math
import time
from collections import defaultdict
from typing import Optional, List, Dict, Any

from derived.base import DerivedEngine

logger = logging.getLogger(__name__)

# ⟨PRIOR⟩ every threshold here. Stated, not fitted — they exist so a plan can
# render a verdict at all, and the fit replaces them. See docs/PLAN_SPEC.md.
# 🔴 r128 — THE R HURDLE MOVED TO strategy/criteria.py. It is the ONE thing
# the relaxed flag changes, and it now lives in one file with every other
# mode-dependent criterion rather than being re-decided per plan.
# ⚠️ `r_hurdle()` returns None when MUTED — never 0.0. A floor of zero would
# still reject a negative-R plan and would look like a decision nobody made.
from strategy.criteria import r_verdict, r_hurdle, mode as criteria_mode
PIN_CONC_MIN      = 3.00    # pin must hold 3x its neighbours' gamma
PIN_SHARE_MIN     = 0.15    # ...and 15% of all near-money gamma
PIN_REACH_MAX     = 1.00    # pin within one remaining expected move
PIN_REACH_MIN     = 0.15    # already there = nothing left to capture
EM_SESSION_PCT    = 0.020   # session expected move as a fraction of spot
NEAR_MONEY_PCT    = 0.15    # strikes beyond this do not participate in gamma



# ═══ THE SHARED SESSION MAP ═══════════════════════════════════════════
# 🔴 THE CENTER IS THE 5-MINUTE ORB RANGE, NOT THE OPENING PRICE. Operator,
# 2026-08-25: *"Why don't we use the five minute ORB range as the marker?
# Levels have to be above the ORB or below to count and they have to be the
# right kind."* This SUPERSEDES the "opening price" wording of the ruling
# quoted below — a ZONE rather than a POINT.
# ⚠️ WHY IT IS BETTER, and it is not just tidier: a level sitting a few cents
# from the open is not meaningfully above or below anything, and the first
# five minutes routinely straddle it. A level outside the OPENING RANGE has
# actually been left behind by the session's first move. Levels INSIDE the
# range are neither ceiling nor floor and are eliminated as such.
# ⚠️ CONSEQUENCE: THE MAP CANNOT EXIST BEFORE 09:35 ET. Until today's opening
# range closes there is no marker, so there are no candidates — not an empty
# map, NO map. Recorded rather than worked around.
# SOURCE: `main.py::_opening_range()` — ORB_WINDOW_MINUTES=5, recomputed from
# the tape (df_5m primary), restart-proof and available all session. TCS.3
# proved the 1m-only version went off the left edge of a rolling window by
# ~10:35, so the 5m path is the one to read.
#
# 🔴 THE ORIGINAL RULING, 2026-08-25. Verbatim: *"The mapper for our session
# highs and lows, which are liquidity zones, and the forks have to SHARE A MAP.
# Center of the map is gonna be where price currently sits at the open. There
# are gonna be some levels above the price that are identified by either
# session levels or fork tines. And the same will be below it. The levels below
# are the only ones that can be the FLOOR and the levels above are the only
# ones that can be the CEILING. No other combination will work."*
#
# ⚠️ AND THE CLARIFICATION THAT FOLLOWED, WHICH I HAD WRONG. My first reading
# was "position governs, the label is only provenance" — so an upper tine that
# drifted below the open would become a FLOOR candidate. He corrected it:
# *"an upper tine below the current open is UNUSABLE as a candidate. It would
# have to go to the lower tine to qualify for the put credit spread. Upper
# tines can only be call credit spreads, but would be INVALIDATED BY GEOMETRY
# if they are below the open."*
#
# ⇒ SO THE TWO FACTS MUST AGREE, AND DISAGREEMENT ELIMINATES:
#     ROLE comes from the SOURCE and never changes — an upper tine and a
#     session HIGH are CEILINGS (call credit spreads) for the whole session; a
#     lower tine and a session LOW are FLOORS (put credit spreads).
#     POSITION is measured against the OPENING PRICE, frozen at the open.
#     A ceiling at or below the open is INVALID. A floor at or above it is
#     INVALID. Neither is re-cast as the other side — the displaced upper tine
#     does not become the floor; the LOWER tine is the floor, or there is none.
#
# ⚠️ THIS IS WHY IT IS STRUCTURAL RATHER THAN A GATE. An inverted condor (PCS
# above, CCS below) cannot be CONSTRUCTED from this map, so nothing downstream
# has to detect one. It also removes a defect I reproduced tonight in the fork
# plan and which credit_edge had already recorded weeks ago: pricing a short
# call beyond an "upper" tine that had drifted below spot — an ITM short call,
# something nobody would sell.

def _n(v, spec: str = ".2f") -> str:
    """Format a value that may be None. None renders as 'n/a', never raises.

    🔴 THE 2026-08-26 CRASH. Every plan's `why` string formatted `r`, `credit`
    and the strikes with `{x:.2f}`. Under RELAXED entries `r_verdict(None)`
    returns MUTED — NOT FAIL — so nothing is appended to `why`, `ok` stays
    True, and execution falls straight into the f-string with r=None:
    `TypeError: unsupported format string passed to NoneType.__format__`.
    IronCondor raised it on all 15 boxes every tick and produced no rows for a
    whole session; the fork hit it wherever strikes were unpriceable.
    ⚠️ THIS IS THE MUTED_NO_R CASE, which we identified the night before and
    handled in the VERDICT while leaving it live in the MESSAGE. A value that
    can be absent must be absent-safe EVERYWHERE it is read, not only where it
    is judged.
    """
    if v is None:
        return "n/a"
    try:
        return format(v, spec)
    except Exception:                                          # noqa: BLE001
        return str(v)


CEILING, FLOOR = "ceiling", "floor"


class MapLevel:
    """One candidate on the shared session map.

    `role` is what the SOURCE says it is and is immutable. `valid` is whether
    the geometry agrees. A level that fails geometry is KEPT with valid=False
    and a reason, never silently dropped — the elimination is the record.
    """
    __slots__ = ("price", "role", "name", "source", "tf", "valid", "why")

    def __init__(self, price, role, name, source, tf=""):
        self.price = round(float(price), 4)
        self.role = role
        self.name = name
        self.source = source          # "ledger" | "fork"
        self.tf = tf                  # "1h" / "1d" for forks, "" otherwise
        self.valid = True
        self.why = ""

    @property
    def option_side(self):
        """A CEILING is sold as a CALL spread. A FLOOR as a PUT spread. Always."""
        return "call" if self.role == CEILING else "put"

    def check_geometry(self, orb_high, orb_low):
        """A CEILING must sit ABOVE the opening range; a FLOOR must sit BELOW
        it. Inside the range is neither."""
        inside = orb_low <= self.price <= orb_high
        if inside:
            self.valid = False
            self.why = (f"{self.name} at {self.price:.2f} sits INSIDE the "
                        f"opening range {orb_low:.2f}-{orb_high:.2f} — neither "
                        f"above nor below it, so it is neither a ceiling nor a "
                        f"floor this session")
        elif self.role == CEILING and self.price < orb_low:
            self.valid = False
            self.why = (f"{self.name} is a CEILING at {self.price:.2f} but sits "
                        f"BELOW the opening range low {orb_low:.2f} — "
                        f"invalidated by geometry. A ceiling can only be sold "
                        f"as a call credit spread, and this one is beneath the "
                        f"session's first move; the opposite side's level is "
                        f"the candidate, not this one re-cast")
        elif self.role == FLOOR and self.price > orb_high:
            self.valid = False
            self.why = (f"{self.name} is a FLOOR at {self.price:.2f} but sits "
                        f"ABOVE the opening range high {orb_high:.2f} — "
                        f"invalidated by geometry; a floor can only be sold as "
                        f"a put credit spread")
        return self.valid


def build_session_map(orb_high, orb_low, ledger=None, ctm=None):
    """Every credit-spread candidate this session, on ONE map, centered on the
    5-MINUTE OPENING RANGE. Returns (ceilings, floors, invalid) — all three,
    because the eliminated ones are evidence too.

    ⚠️ NO OPENING RANGE ⇒ NO MAP. Before 09:35 ET there is no marker, and a
    map centered on nothing would classify every level by accident. Returning
    empty lists here is the CORRECT answer, not a degraded one.
    """
    if (not orb_high or not orb_low or orb_high <= 0 or orb_low <= 0
            or orb_high < orb_low):
        return [], [], []
    cands = []
    try:
        for lv in (getattr(ledger, "levels", None) or []):
            k = getattr(lv, "kind", "")
            if k not in ("high", "low"):
                continue
            cands.append(MapLevel(
                lv.price, CEILING if k == "high" else FLOOR,
                getattr(lv, "name", "") or f"{k} {lv.price:.2f}", "ledger"))
    except Exception:                                           # noqa: BLE001
        pass
    try:
        for t in (ctm.all_rails() if ctm is not None else []):
            # ⚠️ THE FORK'S OWN `side` IS THE ROLE. "call" == upper tine ==
            # CEILING. It is NOT re-derived from position — that is the whole
            # point of the ruling.
            role = CEILING if getattr(t, "side", "") == "call" else FLOOR
            tf = getattr(t, "tf", "")
            cands.append(MapLevel(float(getattr(t, "rail", 0) or 0), role,
                                  f"{tf} {'upper' if role == CEILING else 'lower'} tine",
                                  "fork", tf))
    except Exception:                                           # noqa: BLE001
        pass

    ceilings, floors, invalid = [], [], []
    for c in cands:
        if c.price <= 0:
            continue
        if not c.check_geometry(orb_high, orb_low):
            invalid.append(c)
        elif c.role == CEILING:
            ceilings.append(c)
        else:
            floors.append(c)
    ceilings.sort(key=lambda c: c.price)     # nearest the opening range first
    floors.sort(key=lambda c: -c.price)
    return ceilings, floors, invalid


class PlanEngine(DerivedEngine):
    """Declares, prices and records forward plans. Writes only."""

    name = "plans"
    table = "plan_ledger"
    min_interval_s = 30.0     # a plan is not a tick-level object

    def __init__(self, store=None, symbol: str = "", ledger=None):
        super().__init__(store)
        self.symbol = symbol
        self._ledger = ledger
        self._declared: Dict[str, str] = {}     # key -> plan_id
        self._made = False
        # 🔴 r133 — CREATE THE TABLES AT INIT, NOT ON FIRST WRITE.
        # ⚠️ `_ensure()` used to be called only from `_write_tick`, which is
        # only reached when there IS at least one plan. So a session that
        # produced nothing left NO TABLES AT ALL, and "the engine is not
        # registered", "the engine crashed on import" and "the engine ran fine
        # and found nothing" were INDISTINGUISHABLE from outside. On the
        # morning of 2026-08-26 that ambiguity cost three rounds of fleet
        # queries before the real cause (no ctx["chain"], see main.py r133)
        # was isolated.
        # AN EMPTY TABLE IS A MEASUREMENT. A missing table is a mystery.
        self._ensure()


    # 🔴 EVERY BUILDER SPEAKS WHEN STARVED (r134).
    # ⚠️ A builder that returns None writes NO ROW, so "this plan could not be
    # evaluated" and "this plan does not exist" look identical in plan_tick.
    # That is the same ambiguity that cost three rounds of fleet queries this
    # morning at the TABLE level, sitting one layer down inside each builder —
    # and it hid the real defect for a full session: ForkCreditSpread and
    # IronCondor were ABSENT from the table while five other plans wrote 80-95
    # rows each, and nothing in the data said why.
    @staticmethod
    def _starved(name: str, ctx: dict, needs: dict, spot: float = 0.0):
        """A NO PLAN row naming the absent inputs, or None when all present."""
        missing = [k for k, v in needs.items()
                   if v is None or (k == "price" and not v)]
        if not missing:
            return None
        return [{"strategy": name, "verdict": "NO PLAN", "checks": {},
                 "underlying_at_decision": spot or None,
                 "why": (f"input(s) absent from ctx: {', '.join(missing)} — "
                         f"this plan could not be evaluated this tick")}]

    # ── gamma surface ───────────────────────────────────────────────────
    @staticmethod
    def _gamma_by_strike(chain, spot: float):
        """Signed dealer gamma per strike, near the money only.

        🔴 THE FIELD IS `open_interest`, NOT `oi` (r139). I read `getattr(c,
        "oi", 0)`, which returns the DEFAULT 0 on every contract, so
        `oi > 0` was never true, the gamma map was always empty, and all 15
        boxes reported "no gamma flip near the money — there is no pin" every
        tick of every session. The butterfly has never once been evaluated.
        ⚠️ THIRD INSTANCE OF THE SAME ERROR IN ONE DAY — ctm.all() vs
        all_rails(), bars_since_reclaim vs bars_ago, now oi vs open_interest.
        Every one was a field name I ASSUMED instead of reading, and every one
        failed SILENTLY because getattr with a default cannot raise.

        ⚠️ ⟨ASSUMPTION⟩ dealers long calls / short puts. NOT verified against
        this fleet's own GEX code. The pin's LOCATION barely moves under it
        (360 in 72/74 TSLA snapshots on 2026-08-25 either way) but the
        PULL/PUSH verdict FLIPS, so this is the most load-bearing assumption
        in the file and it is stamped on every plan as `gex_sign_convention`.
        """
        per = defaultdict(float)
        for c in (getattr(chain, "calls", []) or []):
            g = float(getattr(c, "gamma", 0) or 0)
            oi = float(getattr(c, "open_interest", 0) or 0)
            k = float(getattr(c, "strike", 0) or 0)
            if g > 0 and oi > 0 and spot and abs(k-spot)/spot <= NEAR_MONEY_PCT:
                per[k] += g * oi
        for p in (getattr(chain, "puts", []) or []):
            g = float(getattr(p, "gamma", 0) or 0)
            oi = float(getattr(p, "open_interest", 0) or 0)
            k = float(getattr(p, "strike", 0) or 0)
            if g > 0 and oi > 0 and spot and abs(k-spot)/spot <= NEAR_MONEY_PCT:
                per[k] -= g * oi
        return dict(per)

    @staticmethod
    def _pin(per: dict) -> Optional[float]:
        """Gamma flip nearest the money; largest |gamma×OI| when several exist.

        🔴 A NAIVE FIRST-CROSSING SEARCH RETURNS GARBAGE. Walking strikes from
        the low end and taking the first sign change returned 230 on TSLA's
        11:35 chain instead of 360 — a spurious crossing among deep strikes
        with stale marks — and the plan built on it priced at NEGATIVE R.
        Caught only by rendering EVERY tick; a sampled check had shown
        "pin 360 in 70/74" and hid the outliers.
        """
        if not per:
            return None
        cum, prev, flips = 0.0, None, []
        for k in sorted(per):
            cum += per[k]
            if prev is not None and (prev < 0 <= cum or prev > 0 >= cum):
                flips.append((abs(per[k]), k))
            prev = cum
        return max(flips)[1] if flips else None

    @staticmethod
    def _concentration(per: dict, pin: float):
        """(ratio to neighbours, share of near-money gamma) — PIN STRENGTH.

        🔴 THIS REPLACED CHARM AS THE STRENGTH GATE, and it was measured, not
        argued. On TSLA 2026-08-25 concentration ran 5.94-6.90 on EVERY
        snapshot and rose monotonically into the close (pin share 26.9% ->
        32.6%), while charm FLIPPED SIGN on three of six readings over the same
        tape. Concentration is a LEVEL not a RATE — one snapshot, no
        derivative, nothing to confound — and it is closer to the mechanism:
        dealers long gamma at K must sell rallies and buy dips near K, so the
        force IS gamma×OI at K relative to its neighbours. The rise into the
        close carries the time signal charm was being asked for, without the
        derivative.
        ⚠️ CAVEAT, stated before anyone builds on it: concentration is stable
        partly BECAUSE it is dominated by OI at one strike, which barely moves
        intraday, so WITHIN a session it may discriminate weakly. Its likely
        power is ACROSS symbols and days. One pin in one session cannot prove
        that.
        """
        if not per or pin not in per:
            return None, None
        at = abs(per[pin])
        near = sorted(per, key=lambda k: abs(k - pin))[1:9]
        m = sum(abs(per[k]) for k in near) / len(near) if near else 0.0
        tot = sum(abs(v) for v in per.values())
        return (at/m if m else None), (at/tot if tot else None)

    # ── plan construction ───────────────────────────────────────────────
    def _butterfly(self, ctx: dict) -> Optional[dict]:
        chain = ctx.get("chain")
        spot = float(ctx.get("price") or 0)
        _s = self._starved("GEXPinButterfly", ctx, {"chain": chain, "price": spot}, spot)
        if _s:
            return _s
        per = self._gamma_by_strike(chain, spot)
        pin = self._pin(per)
        if pin is None:
            return {"strategy": "GEXPinButterfly", "verdict": "NO PLAN",
                    "checks": {},
                    "why": "no gamma flip near the money — there is no pin"}
        net = sum(per.values())
        conc, share = self._concentration(per, pin)

        frac = float(ctx.get("session_fraction_remaining") or 0.0)
        em_rem = spot * EM_SESSION_PCT * math.sqrt(frac) if frac > 0 else 0.0
        reach = abs(pin - spot) / em_rem if em_rem > 0 else None

        calls = {float(getattr(c, "strike", 0)): c
                 for c in (getattr(chain, "calls", []) or [])}
        body, w1, w2 = calls.get(pin), calls.get(pin-5), calls.get(pin+5)
        debit = r = None
        if body is not None and w1 is not None and w2 is not None:
            try:
                debit = round(float(w1.ask) - 2*float(body.bid) + float(w2.ask), 2)
                r = round((5.0 - debit) / debit, 2) if debit > 0 else None
            except Exception:                                   # noqa: BLE001
                debit = r = None

        why = []
        ok = True
        if net <= 0:
            ok = False
            why.append(f"net gamma NEGATIVE ({net:.0f}) — the pin PUSHES")
        if conc is None or conc < PIN_CONC_MIN or (share or 0) < PIN_SHARE_MIN:
            ok = False
            why.append(f"pin DIFFUSE ({(conc or 0):.1f}x neighbours, "
                       f"{(share or 0)*100:.0f}% of gamma)")
        if reach is None or reach > PIN_REACH_MAX:
            ok = False
            why.append(f"pin {(reach or 99):.2f} EM away — not reachable "
                       f"({abs(pin-spot):.2f} to travel)")
        elif reach < PIN_REACH_MIN:
            ok = False
            why.append(f"already at the pin ({reach:.2f} EM)")
        _rv, _rr = r_verdict(r)
        if _rv == "FAIL":
            ok = False
            why.append(_rr)
        # ⚠️ EACH CHECK CARRIES ITS OWN (value, verdict). That is what makes an
        # elimination a QUERYABLE ROW rather than a sentence — "which check
        # failed, at what reading" becomes one GROUP BY instead of a log grep.
        checks = {
            "net_gamma":  (net,  "PASS" if net > 0 else "FAIL"),
            "pin_conc":   ((conc, "PASS" if (conc or 0) >= PIN_CONC_MIN else "FAIL")
                           if conc is not None else None),
            "pin_share":  ((share, "PASS" if (share or 0) >= PIN_SHARE_MIN else "FAIL")
                           if share is not None else None),
            "reach_em":   ((reach, "PASS" if PIN_REACH_MIN <= reach <= PIN_REACH_MAX
                            else "FAIL") if reach is not None else None),
            "r":          ((r, r_verdict(r)[0]) if r is not None else None),
            # RECORDED ONLY — these gate nothing. Carried so the fit can decide
            # whether charm deserves authority; concentration replaced it as
            # the strength gate on measured grounds (see the docstring).
            "charm_raw":       ((ctx.get("charm"), "n/a")
                                if ctx.get("charm") is not None else None),
            "charm_corrected": None,
        }
        return {
            "strategy": "GEXPinButterfly",
            "direction": "pin",
            "checks": checks,
            "invalidation": round(pin - 12.0, 2),
            "trigger_price": round(pin - 5.0, 2),
            "short_strike": pin,
            "long_strike": pin + 5.0,
            "short_put_strike": pin - 5.0,
            "underlying_at_decision": spot,
            "verdict": "TAKE" if ok else "DECLINE",
            "why": "; ".join(why) if why else
                   (f"pin {_n(conc, '.1f')}x neighbours, reachable at {reach:.2f} EM, "
                    f"dealers holding — R {r if r is not None else float('nan'):.2f}"),
            "pin": pin, "net_gamma": net, "conc": conc, "share": share,
            "reach": reach, "debit": debit, "r": r,
        }

    def _participation(self, ctx: dict) -> Optional[dict]:
        """The credit floor under a move, bounded by the ORB high/low."""
        chain = ctx.get("chain")
        spot = float(ctx.get("price") or 0)
        orb_hi = ctx.get("orb_high")
        orb_lo = ctx.get("orb_low")
        _s = self._starved("TrendParticipation", ctx, {"chain": chain, "price": spot, "orb_high": orb_hi, "orb_low": orb_lo}, spot)
        if _s:
            return _s
        puts = {float(getattr(p, "strike", 0)): p
                for p in (getattr(chain, "puts", []) or [])}
        inside = sorted(k for k in puts if orb_lo <= k <= orb_hi)
        if not inside:
            return {"strategy": "TrendParticipation", "verdict": "NO PLAN",
                    "checks": {"strike_inside_range": None},
                    "why": f"no strike inside the range {orb_lo:.2f}-{orb_hi:.2f} "
                           f"— the grid is wider than the range"}
        sk = inside[-1]
        sp, lp = puts.get(sk), puts.get(sk - 5)
        if sp is None or lp is None:
            return None
        try:
            credit = round(float(sp.bid) - float(lp.ask), 2)
        except Exception as exc:                                # noqa: BLE001
            # ⚠️ NEVER VANISH ON AN EXCEPTION — a builder that returns None
            # writes no row, and an exception caught HERE never reaches
            # derive()'s handler, so nothing is logged either.
            return [{"strategy": "TrendParticipation", "verdict": "NO PLAN", "checks": {},
                     "why": f"builder raised: {type(exc).__name__}: {exc}"}]
        risk = round(5.0 - credit, 2)
        r = round(credit / risk, 2) if risk > 0 else None
        _rv, _rr = r_verdict(r)
        ok = _rv in ("PASS", "MUTED")
        why = ("" if ok else
               f"{_rr} — TARGET {_n(sk, '.2f')} (short strike expiring worthless) "
               f"pays ${_n(credit, '.2f')}; STOP {orb_hi:.2f} (a close back through "
               f"the ORB high) risks ${_n(risk, '.2f')}")
        checks = {
            "r":       ((r, r_verdict(r)[0]) if r is not None else None),
            "credit":  (credit, "n/a"),
            "risk":    (risk, "n/a"),
            "strike_inside_range": (float(sk), "PASS"),
        }
        return {
            "strategy": "TrendParticipation",
            "direction": "credit_floor",
            "checks": checks,
            "invalidation": float(orb_hi),
            "credit": credit, "risk": risk,
            "trigger_price": float(orb_hi),
            "short_put_strike": sk, "long_put_strike": sk - 5,
            "underlying_at_decision": spot,
            "verdict": "TAKE" if ok else "DECLINE",
            # 🔴 SAY WHAT ACTUALLY HAPPENED, NOT WHAT THE HAPPY PATH ASSUMES.
            # ⚠️ THIS SENTENCE WAS FALSE ON LIVE DATA: PLTR wrote "R 0.10
            # clears the floor" against a floor of 1.00. Under RELAXED the
            # hurdle is MUTED, so `why` stays empty and this fallback asserted
            # a comparison that never ran. The VERDICT was defensible; the
            # REASON was a lie, in the one table we intend to fit against.
            # A row that misstates WHY it was taken is worse than one that
            # says nothing, because the fit cannot tell the two apart.
            "why": why or (f"R {_n(r)} — {r_verdict(r)[1]}"),
            "credit": credit, "risk": risk, "r": r,
        }

    def _sweep(self, ctx: dict) -> Optional[dict]:
        """The credit spread sold beyond a swept-and-RECLAIMED named level.

        🔴 THIS PLAN EXISTS BECAUSE OF CVX, 2026-08-25. The strategy sold the
        SAME 200/195 put spread at least a dozen times — entry, stop, re-entry
        inside the same MINUTE at 13:30, 13:31, 13:32 — for about -$400 on one
        symbol. Every foundational gate passed on every tick because they are
        properties of the SWEEP EVENT, and the event does not change.

        ⚠️ THE ROOT CAUSE IS A CATEGORY ERROR, and the operator named it:
        *"a wick can be a pierce. But it takes a CLOSE to log a rejection."*
        The strategy reads `sweep.reclaimed`, a LATCHED FLAG on a persisted
        object that stays true for as long as the sweep lives. His thesis is a
        BAR EVENT, true exactly once. Three reclaim candles cannot exist in
        three consecutive minutes for one level — so those were one reclaim,
        counted every tick for hours. The same failure was recorded on
        2026-08-11 about the predecessor: "`liq_map.recent_sweep` PERSISTS once
        set". It is also why AGE has always been the only binding damper:
        nothing else ever goes false.

        ⇒ **THE PLAN'S IDENTITY IS (pool_price, reclaim_bar).** One plan per
        reclaim bar. Once that plan produces a position the event is SPENT, and
        re-firing requires a NEW closing bar on the rejected side. The
        one-attempt rule falls out of the definition rather than being bolted
        on as a cooldown — operator: *"It doesn't need a cooldown it needs that
        level taken out. You tried once you lost it should be gone now."*

        ⚠️ AND HE RAISED THE COUNTER-ARGUMENT HIMSELF, WHICH IS NOT SETTLED:
        *"if it went right back to it minutes or hours later… that only
        strengthens the level then because it defended many times."* Genuinely
        open. `level_hold_rate` is what will answer it: a level that is truly
        defended shows holds/touches near 1.0 (TSLA's London LOW ran 70/71 =
        98.6%), while one that is merely being tested repeatedly decays
        (London HIGH ran 188 holds / 135 breaches = 58%). Recording both is how
        the fit decides rather than either of us.
        """
        liq = ctx.get("liq_map")
        spot = float(ctx.get("price") or 0)
        chain = ctx.get("chain")
        _s = self._starved("SweepCreditSpread", ctx,
                           {"liq_map": liq, "chain": chain,
                            "price": spot}, spot)
        if _s:
            return _s
        sweep = getattr(liq, "recent_sweep", None)
        if sweep is None:
            return {"strategy": "SweepCreditSpread", "verdict": "NO PLAN",
                    "checks": {}, "why": "no sweep on the map"}
        name = getattr(sweep, "swept_named_level", "") or ""
        if not name:
            return {"strategy": "SweepCreditSpread", "verdict": "NO PLAN",
                    "checks": {}, "why": "sweep is not on a NAMED level"}

        pool = float(getattr(sweep, "pool_price", 0) or 0)
        extreme = float(getattr(sweep, "sweep_price", 0) or 0)
        kind = str(getattr(sweep, "kind", ""))
        is_low = "low" in kind
        age = int(getattr(liq, "sweep_age_bars", 999) or 999)
        invalid = bool(getattr(liq, "sweep_invalidated", False))
        # ⚠️ DEPTH AS A FRACTION OF THE LEVEL, not dollars — comparable across
        # symbols, which a dollar figure is not.
        depth = (abs(extreme - pool) / pool * 100.0) if pool else None

        # ── the hold rate, from the level book the bot itself writes ──────
        hold = holds = touches = None
        try:
            from analysis.liquidity_ledger import get_ledger
            led = get_ledger(self.symbol)
            for lv in (getattr(led, "levels", []) or []):
                if abs(float(lv.price) - pool) < 0.01:
                    touches = int(getattr(lv, "touches", 0) or 0)
                    holds = int(getattr(lv, "holds", 0) or 0)
                    hold = (holds / touches) if touches else None
                    break
        except Exception as exc:                                # noqa: BLE001
            logger.debug("[plans] level book unreachable: %s", exc)

        # ── the structure: sell beyond the pool ──────────────────────────
        side = "P" if is_low else "C"
        contracts = (getattr(chain, "puts", []) if is_low
                     else getattr(chain, "calls", [])) or []
        strikes = sorted({float(getattr(c, "strike", 0) or 0) for c in contracts})
        if is_low:
            cands = [k for k in strikes if k <= pool]
            sk = cands[-1] if cands else None
        else:
            cands = [k for k in strikes if k >= pool]
            sk = cands[0] if cands else None
        if sk is None:
            return {"strategy": "SweepCreditSpread", "verdict": "NO PLAN",
                    "checks": {}, "why": f"no strike beyond the pool {pool:.2f}"}
        by_k = {float(getattr(c, "strike", 0) or 0): c for c in contracts}
        lk = sk - 5 if is_low else sk + 5
        sp, lp = by_k.get(sk), by_k.get(lk)
        credit = risk = r = None
        if sp is not None and lp is not None:
            try:
                credit = round(float(sp.bid) - float(lp.ask), 2)
                risk = round(5.0 - credit, 2)
                r = round(credit / risk, 2) if risk > 0 else None
            except Exception:                                   # noqa: BLE001
                credit = risk = r = None

        # ── EVENT IDENTITY. This is the whole fix. ───────────────────────
        reclaim_bar = getattr(sweep, "reclaim_bar_ts", None) or age
        key = f"SweepCreditSpread:{pool:.2f}:{reclaim_bar}"
        spent = key in self._declared

        why, ok = [], True
        if spent:
            ok = False
            why.append(f"event SPENT — {name} @{pool:.2f} reclaim already "
                       f"produced a plan; a new attempt needs a NEW closing bar")
        if invalid:
            ok = False
            why.append(f"ACCEPTED through {pool:.2f} — that is a breakout, "
                       f"not a sweep")
        if hold is not None and hold < 0.75:
            ok = False
            why.append(f"{name} hold rate {hold*100:.0f}% on {touches} touches "
                       f"— the level is being GIVEN UP, not defended")
        if age > 8:
            ok = False
            why.append(f"reclaim is {age} bars old (max 8)")
        _rv, _rr = r_verdict(r)
        if _rv == "FAIL":
            ok = False
            why.append(f"{_rr} — TARGET {_n(sk, '.2f')} "
                       f"(short strike expiring worthless) pays ${_n(credit, '.2f')}; "
                       f"STOP {extreme:.2f} (a close beyond the sweep extreme) "
                       f"risks ${_n(risk, '.2f')}")
        checks = {
            "level_hold_rate": ((hold, "PASS" if hold >= 0.75 else "FAIL")
                                if hold is not None else None),
            "acceptance":      (1.0 if invalid else 0.0,
                                "FAIL" if invalid else "PASS"),
            "reclaim_age":     (float(age), "PASS" if age <= 8 else "FAIL"),
            "r":               ((r, r_verdict(r)[0]) if r is not None else None),
            "event_spent":     (1.0 if spent else 0.0,
                                "FAIL" if spent else "PASS"),
            # RECORDED ONLY — gates nothing until the fit says what depth means
            "pierce_depth":    ((depth, "n/a") if depth is not None else None),
        }
        return {
            "strategy": "SweepCreditSpread",
            "direction": "low_sweep" if is_low else "high_sweep",
            "checks": checks,
            "trigger_price": pool,
            "invalidation": extreme,
            "short_put_strike": sk if is_low else None,
            "long_put_strike": lk if is_low else None,
            "short_strike": None if is_low else sk,
            "long_strike": None if is_low else lk,
            "underlying_at_decision": spot,
            "credit": credit, "risk": risk, "r": r,
            "identity": key,
            "verdict": "TAKE" if ok else "DECLINE",
            "why": "; ".join(why) if why else
                   (f"{name} @{pool:.2f} swept to {extreme:.2f} and reclaimed, "
                    f"hold {(hold or 0)*100:.0f}%, {age} bars old, "
                    f"R {_n(r)}"),
        }

    def _runaway(self, ctx: dict) -> Optional[dict]:
        """The DEBIT continuation on an ORB that ran without retesting.

        ════════════════════════════════════════════════════════════════════
        THE DEBIT R PROBLEM, AND HOW THIS SOLVES IT
        ════════════════════════════════════════════════════════════════════
        A credit spread's risk is DEFINED — width minus credit, known at
        declaration. A debit's stop is a SPOT level, so R needs an estimate of
        what the contract is worth when spot reaches it.

        🔴 OPERATOR'S RULING, 2026-08-25: *"the stop distance has to dictate
        the target... we can use some of our available indicators to inform us
        if a 1-r target passes the sanity check (and address theta separately).
        We can add a theta burn layer during fitting later, but calculate this
        one in dollars at entry."*

        So: **STOP DISTANCE IN SPOT SETS THE TARGET IN SPOT.** The stop is the
        ORB boundary (structural, not chosen); the target is the same distance
        the other way.

        ⚠️ **AND HERE IS THE TRAP THAT MAKES THE NAIVE VERSION USELESS.**
        A first-order delta estimate gives

            prem_at_target ≈ prem + delta·d
            prem_at_stop   ≈ prem − delta·d
            R = (delta·d) / (delta·d) = **1.00, EXACTLY, ALWAYS.**

        A symmetric spot target under a linear delta produces R = 1.00 for
        EVERY debit trade on every tape. The gate would be decorative — it
        would pass everything at precisely the floor and measure nothing.

        **THE ASYMMETRY IS GAMMA, AND IT IS THE WHOLE EDGE OF A DEBIT.** A long
        option GAINS delta moving toward the target and LOSES it moving toward
        the stop, so the same spot distance is worth more up than down:

            prem_at_target ≈ prem + delta·d + ½·gamma·d²
            prem_at_stop   ≈ prem − delta·d + ½·gamma·d²   (gamma cushions BOTH)

        Gamma is positive for a long option in both directions — it lifts the
        gain and softens the loss — so R > 1 by construction, and HOW MUCH is
        a real property of the contract rather than an artefact of the
        arithmetic. That is what makes the number worth gating on.

        ⚠️ SECOND ORDER IS STILL AN APPROXIMATION. It degrades on a large move
        and it assumes IV holds. `gamma_lift` is recorded separately so the fit
        can see how much of R came from convexity rather than direction.

        ⚠️ THETA IS IN DOLLARS AND NEVER NETTED INTO R. Operator's
        instruction. A debit fights decay the whole way to the target, but
        folding an estimated burn into the entry R would bury a fitted guess
        inside a structural number. Recorded, visible, gates nothing.
        """
        orb = ctx.get("orb")
        chain = ctx.get("chain")
        spot = float(ctx.get("price") or 0)
        orb_hi = ctx.get("orb_high")
        orb_lo = ctx.get("orb_low")
        _s = self._starved("RunawayContinuation", ctx, {"chain": chain, "price": spot, "orb_high": orb_hi, "orb_low": orb_lo}, spot)
        if _s:
            return _s
        state = str(getattr(orb, "state", "") or "")
        reason = str(getattr(orb, "invalidation_reason", "") or "")
        if "runaway" not in reason.lower():
            return {"strategy": "RunawayContinuation", "verdict": "NO PLAN",
                    "checks": {},
                    "why": f"ORB has not run away (state={state or 'unknown'}, "
                           f"reason={reason or 'none'}) — no handoff to take"}

        is_long = spot > float(orb_hi)
        stop_spot = float(orb_hi) if is_long else float(orb_lo)
        risk_spot = abs(spot - stop_spot)
        if risk_spot <= 0:
            return {"strategy": "RunawayContinuation", "verdict": "NO PLAN",
                    "checks": {}, "why": "price is AT the boundary — no risk "
                                         "distance, so no target either"}
        # ⚠️ THE TARGET IS THE STOP DISTANCE MIRRORED. Not a fitted multiple,
        # not a level someone liked — the structure sets both ends.
        target_spot = spot + risk_spot if is_long else spot - risk_spot

        # ── the contract ────────────────────────────────────────────────
        pool = (getattr(chain, "calls", []) if is_long
                else getattr(chain, "puts", [])) or []
        if not pool:
            return None
        # nearest strike to spot, the staged pick's shape
        c = min(pool, key=lambda x: abs(float(getattr(x, "strike", 0) or 0) - spot))
        try:
            prem = float(c.ask)
            delta = abs(float(getattr(c, "delta", 0) or 0))
            gamma = float(getattr(c, "gamma", 0) or 0)
            theta = abs(float(getattr(c, "theta", 0) or 0))
        except Exception as exc:                                # noqa: BLE001
            # ⚠️ NEVER VANISH ON AN EXCEPTION — a builder that returns None
            # writes no row, and an exception caught HERE never reaches
            # derive()'s handler, so nothing is logged either.
            return [{"strategy": "RunawayContinuation", "verdict": "NO PLAN", "checks": {},
                     "why": f"builder raised: {type(exc).__name__}: {exc}"}]
        if prem <= 0 or delta <= 0:
            return {"strategy": "RunawayContinuation", "verdict": "NO PLAN",
                    "checks": {}, "why": "contract has no premium or no delta"}

        d = risk_spot
        lift = 0.5 * gamma * d * d
        gain = delta * d + lift
        loss = max(0.01, delta * d - lift)      # gamma cushions the loss too
        r = round(gain / loss, 2)

        # ⚠️ THETA IN DOLLARS AT ENTRY. Per contract, for the hours remaining.
        frac = float(ctx.get("session_fraction_remaining") or 0.0)
        hours_left = 6.5 * frac
        theta_dollars = round(theta * (hours_left / 24.0) * 100.0, 2)

        # ── THE SANITY CHECK: can the tape actually cover the distance? ──
        # 🔴 ATR LIVES ON ctx["vol"], NOT AS A TOP-LEVEL KEY (r138).
        # ⚠️ `ctx.get("atr")` is set NOWHERE in main.py. It returned 0 on every
        # tick of every box, so every ATR-derived value was None and the gates
        # that depend on them NEVER FIRED — the condor's "range narrower than
        # 1 ATR is too tight" check and the runaway's travel_atr sanity check,
        # both silently inert. Measured 2026-08-26: 100% of condor rows on all
        # 15 boxes read "n/a-ATR range".
        # ⚠️ SAME FAMILY AS ctm.all() AND bars_since_reclaim — a name I assumed
        # instead of reading. But `ctx.get()` with a default NEVER RAISES, so
        # this one threw no error at all: just a gate that quietly never
        # applied. The quietest of the three, and the hardest to notice.
        # Every other consumer in main.py uses this form:
        atr = float(getattr(ctx.get("vol"), "atr_current", None) or 0)
        travel = (risk_spot / atr) if atr > 0 else None

        why, ok = [], True
        _rv, _rr = r_verdict(r)
        if _rv == "FAIL":
            ok = False
            why.append(f"{_rr} — TARGET {target_spot:.2f} (the stop distance "
                       f"mirrored), STOP {stop_spot:.2f} (the ORB boundary)")
        if travel is None:
            ok = False
            why.append("ATR unavailable — cannot say whether the target is "
                       "reachable, and an unmeasurable input is not a pass")
        elif travel > 1.5:
            ok = False
            why.append(f"target is {travel:.2f} ATR away ({risk_spot:.2f} on "
                       f"ATR {atr:.2f}) — the tape does not move that far that "
                       f"often; a 1R target that cannot be reached is not 1R")
        checks = {
            "travel_atr":    ((travel, "PASS" if travel <= 1.5 else "FAIL")
                              if travel is not None else None),
            "r":             (r, r_verdict(r)[0]),
            "delta":         (delta, "n/a"),
            # RECORDED, NEVER NETTED INTO R — the operator's instruction.
            "theta_dollars": (theta_dollars, "n/a"),
            # How much of R came from CONVEXITY rather than direction. Without
            # this term R would be exactly 1.00 on every debit, always.
            "gamma_lift":    (round(lift, 4), "n/a"),
        }
        return {
            "strategy": "RunawayContinuation",
            "direction": "long" if is_long else "short",
            "checks": checks,
            "trigger_price": round(spot, 2),
            "invalidation": round(stop_spot, 2),
            "short_strike": float(getattr(c, "strike", 0) or 0),
            "underlying_at_decision": spot,
            "debit": round(prem, 2),
            "risk": round(loss, 2),
            "r": r,
            "verdict": "TAKE" if ok else "DECLINE",
            "why": "; ".join(why) if why else
                   (f"stop {stop_spot:.2f} is {risk_spot:.2f} away; target "
                    f"{target_spot:.2f} mirrors it at {travel:.2f} ATR; "
                    f"R {_n(r)} (gamma lift {_n(lift, '.3f')}); theta "
                    f"${theta_dollars:.2f}/contract to the close"),
        }

    def _condor(self, ctx: dict) -> Optional[dict]:
        """The iron condor — ONE PLAN, TWO TRIGGERS, and both sides priced.

        🔴 WHY THIS IS ONE PLAN AND NOT TWO. On 2026-08-25 CRM opened a PUT
        credit spread at 12:08 ET and then signalled a second leg on **406
        consecutive ticks** without trading, leaving NOTHING in any log. The
        cause: `_can_open_credit_spread` refused every one of them — the open
        leg was a PUT and the second-leg signal was also a PUT, so Rule 3
        (never two of a side) returned False silently. It took five queries to
        establish that, and the answer was visible nowhere.

        ⇒ A CONDOR IS A STRUCTURE, SO THE PLAN IS THE STRUCTURE. It declares
        BOTH sides, prices BOTH, and carries `leg2_pending` — which side is
        still open to be filled. "Half a condor waiting for its complement" is
        a real state that lasts hours, and under a two-plan model it is
        expressible only as the absence of a second plan, which is exactly how
        406 refusals produced silence.

        ⚠️ R IS THE COMBINED STRUCTURE, NOT A SIDE. Both spreads collect; only
        ONE can lose at expiry (price cannot finish beyond both shorts), so
        risk is width minus the TOTAL credit, not per-leg. Scoring one leg
        alone systematically understates the trade — a 0.30 side and a 0.30
        side are not a 0.30 condor.
        """
        chain = ctx.get("chain")
        spot = float(ctx.get("price") or 0)
        _s = self._starved("IronCondor", ctx, {"chain": chain, "price": spot}, spot)
        if _s:
            return _s
        # 🔴 ATR LIVES ON ctx["vol"], NOT AS A TOP-LEVEL KEY (r138).
        # ⚠️ `ctx.get("atr")` is set NOWHERE in main.py. It returned 0 on every
        # tick of every box, so every ATR-derived value was None and the gates
        # that depend on them NEVER FIRED — the condor's "range narrower than
        # 1 ATR is too tight" check and the runaway's travel_atr sanity check,
        # both silently inert. Measured 2026-08-26: 100% of condor rows on all
        # 15 boxes read "n/a-ATR range".
        # ⚠️ SAME FAMILY AS ctm.all() AND bars_since_reclaim — a name I assumed
        # instead of reading. But `ctx.get()` with a default NEVER RAISES, so
        # this one threw no error at all: just a gate that quietly never
        # applied. The quietest of the three, and the hardest to notice.
        # Every other consumer in main.py uses this form:
        atr = float(getattr(ctx.get("vol"), "atr_current", None) or 0)
        hi = ctx.get("session_high") or ctx.get("orb_high")
        lo = ctx.get("session_low") or ctx.get("orb_low")
        if not hi or not lo:
            return {"strategy": "IronCondor", "verdict": "NO PLAN",
                    "checks": {}, "why": "no range — both boundaries must be "
                                         "known before a condor can be planned"}
        hi, lo = float(hi), float(lo)

        calls = {float(getattr(c, "strike", 0) or 0): c
                 for c in (getattr(chain, "calls", []) or [])}
        puts = {float(getattr(p, "strike", 0) or 0): p
                for p in (getattr(chain, "puts", []) or [])}
        # ⚠️ ⟨PRIOR⟩ half an ATR beyond each boundary. Structural in shape —
        # the boundary sets it — but the 0.5 is stated, not fitted.
        up_target = hi + 0.5 * atr
        dn_target = lo - 0.5 * atr
        ck = min((k for k in sorted(calls) if k >= up_target), default=None)
        pk = max((k for k in sorted(puts) if k <= dn_target), default=None)

        c_credit = p_credit = None
        if ck is not None and (ck + 5) in calls:
            try:
                c_credit = round(float(calls[ck].bid) - float(calls[ck+5].ask), 2)
            except Exception:                                   # noqa: BLE001
                c_credit = None
        if pk is not None and (pk - 5) in puts:
            try:
                p_credit = round(float(puts[pk].bid) - float(puts[pk-5].ask), 2)
            except Exception:                                   # noqa: BLE001
                p_credit = None

        # which side is already on the book
        open_sides = set()
        for t in (ctx.get("open_trades") or []):
            if t.get("is_condor_leg"):
                open_sides.add(str(t.get("option_side", "")))
        pending = None
        if open_sides and len(open_sides) < 2:
            pending = "call" if "put" in open_sides else "put"

        # ⚠️ R ON THE COMBINED STRUCTURE. Only one side can lose at expiry.
        total = sum(x for x in (c_credit, p_credit) if x is not None)
        r = None
        if c_credit is not None and p_credit is not None:
            risk = round(5.0 - total, 2)
            r = round(total / risk, 2) if risk > 0 else None
        elif total:
            # one side priceable — R on that side alone, and SAY SO
            risk = round(5.0 - total, 2)
            r = round(total / risk, 2) if risk > 0 else None

        width_atr = ((hi - lo) / atr) if atr > 0 else None
        why, ok = [], True
        if ck is None or pk is None:
            ok = False
            why.append(f"no strike beyond one boundary "
                       f"(call>={_n(up_target)}, put<={_n(dn_target)})")
        if width_atr is not None and width_atr < 1.0:
            ok = False
            why.append(f"range is only {_n(width_atr, '.2f')} ATR wide — too tight to "
                       f"sell both sides of")
        _rv, _rr = r_verdict(r)
        if _rv == "FAIL":
            ok = False
            why.append(f"{_rr} — combined credit ${_n(total, '.2f')} against "
                       f"${(5.0-total):.2f} of risk")
        checks = {
            "r":               ((r, r_verdict(r)[0]) if r is not None else None),
            "call_side_ready": ((float(ck), "PASS") if ck is not None else None),
            "put_side_ready":  ((float(pk), "PASS") if pk is not None else None),
            # ⚠️ 1.0 = a leg is OPEN and its complement is still wanted. This
            # is the CRM state that produced 406 silent refusals.
            "leg2_pending":    ((1.0 if pending else 0.0, "n/a")),
            "range_width_atr": ((width_atr, "PASS" if width_atr >= 1.0 else "FAIL")
                                if width_atr is not None else None),
        }
        return {
            "strategy": "IronCondor",
            "direction": "range",
            "checks": checks,
            # the CALL trigger is the spine's trigger_price; the put side's
            # is carried on the plan and shown in `why`.
            "trigger_price": round(up_target, 2),
            "invalidation": round(float(ck) if ck else up_target, 2),
            "short_strike": float(ck) if ck is not None else None,
            "long_strike": float(ck) + 5 if ck is not None else None,
            "short_put_strike": float(pk) if pk is not None else None,
            "long_put_strike": float(pk) - 5 if pk is not None else None,
            "underlying_at_decision": spot,
            "credit": round(total, 2) if total else None,
            "risk": round(5.0 - total, 2) if total else None,
            "r": r,
            "verdict": "TAKE" if ok else "DECLINE",
            "why": "; ".join(why) if why else
                   (f"CCS {_n(ck, '.0f')}/{_n(ck + 5 if ck is not None else None, '.0f')} "
                    f"+ PCS {_n(pk, '.0f')}/{_n(pk - 5 if pk is not None else None, '.0f')}, "
                    f"combined ${_n(total)} on a {_n(width_atr)}-ATR range, "
                    f"R {_n(r)}"
                    + (f" · LEG 2 PENDING: the {pending} side is still open"
                       if pending else "")),
        }

    def _roll(self, ctx: dict) -> Optional[dict]:
        """THE ESCALATION LADDER, made visible: ROLL → TENT → CLOSE.

        🔴 THIS PLAN DESCRIBES CODE THAT ALREADY EXISTS. `strategy/condor_roll.py`
        v4.5 (r106, 2026-08-24) implements the ladder; NOTHING here changes it.
        What did not exist is the per-tick answer to "which rung am I on, what
        would the next rung cost RIGHT NOW, and does it still clear the floor?"
        — and that is the same gap as everywhere else tonight.

        ⚠️ I NEARLY DESIGNED A DIFFERENT MECHANISM FROM MEMORY. My first draft
        priced a textbook roll — BUY BACK the tested short, sell a farther one —
        which the operator caught immediately: *"why would we be buying the
        tested side???"* Buying back a tested short is the most expensive leg on
        the board, which is exactly why that roll costs more than closing. The
        real ladder never does it. Read the file, not the recollection.

        ════════════════════════════════════════════════════════════════════
        THE THREE RUNGS, FROM condor_roll.py
        ════════════════════════════════════════════════════════════════════
        **RUNG 1 — ROLL.** Available while the condor is UNROLLED. It closes the
        old UNTESTED vertical and opens a farther one, COLLECTING credit. The
        code says it plainly: the tent "is the rung BELOW the roll, not an
        alternative to it: an unrolled condor still has the roll available and
        the roll is strictly better (it collects credit rather than paying a
        debit)."

        **RUNG 2 — THE TENT.** Only ONCE ROLLED (`is_broken_wing`), and only on
        a 1-min CLOSE beyond a short strike. Take the PROFITABLE side off —
        which side is winning is computed from marks, never assumed — and buy a
        long of the **OPPOSITE TYPE**, equidistant from the remaining short as
        its wing: `hedge_k = short_k − width` for a call side, `+ width` for a
        put. That leaves price under the tent.

        **RUNG 3 — CLOSE.** When the tent cannot be built OR cannot be afforded.

        ════════════════════════════════════════════════════════════════════
        THE ECONOMIC TEST, VERBATIM FROM THE CODE
        ════════════════════════════════════════════════════════════════════
            cum_credit  = credit(keep) + credit(breached)
            net_after   = cum_credit − winner_take − hedge_ask
            REFUSE if   net_after <= cum_credit × (1 − TENT_FLOOR_PCT)

        ⚠️ **PRICED BEFORE IT IS PAID.** If the hedge's debit ALONE puts the
        structure past the floor, the tent is not built and the position closes.
        That ordering is the whole discipline — the alternative is discovering
        the cost after wearing it.

        ⚠️ **THE FLOOR MEASURES THE WHOLE ADJUSTED POSITION.** The survivor is
        re-booked as `Structure.TENT` carrying CUMULATIVE credit, so the 15%
        floor applies to everything collected across the roll and the tent, not
        to one leg's original credit. Measuring a rung against its own credit
        alone would let a structure bleed indefinitely one adjustment at a time.
        """
        chain = ctx.get("chain")
        spot = float(ctx.get("price") or 0)
        _s = self._starved("CreditRoll", ctx, {"chain": chain, "price": spot}, spot)
        if _s:
            return _s
        legs = [t for t in (ctx.get("open_trades") or [])
                if t.get("is_condor_leg") and str(t.get("status")) == "open"]
        if len(legs) != 2:
            return {"strategy": "CreditRoll", "verdict": "NO PLAN",
                    "checks": {},
                    "why": f"{len(legs)} condor leg(s) open — the ladder needs "
                           f"a two-legged structure"}
        rolled = any(t.get("is_broken_wing") for t in legs)
        _no_roll_reason = ""      # set when rung 1 exists but has no room

        def _mark(t):
            """What it costs to buy this vertical back. None when unmarkable."""
            pool = {float(getattr(c, "strike", 0) or 0): c
                    for c in ((getattr(chain, "calls", []) if
                               t.get("option_side") == "call"
                               else getattr(chain, "puts", [])) or [])}
            sh, lo = pool.get(float(t.get("short_strike") or 0)), \
                     pool.get(float(t.get("long_strike") or 0))
            if sh is None or lo is None:
                return None
            try:
                return round(float(sh.ask) - float(lo.bid), 2)
            except Exception:                                   # noqa: BLE001
                return None

        cum_credit = sum(float(t.get("credit_received")
                               or t.get("entry_premium") or 0) for t in legs)
        floor_pct = float(ctx.get("tent_floor_pct") or 0.15)

        # ── which leg is TESTED — proximity, not penetration ─────────────
        # 🔴 MIRRORS `classify_tested`: "A side is 'tested' when price is
        # within proximity_strikes of that side's short strike (OR BEYOND
        # IT)" — `current_price >= short − prox`, prox = one strike increment.
        # ⚠️ MY FIRST VERSION REQUIRED PENETRATION (`spot >= short`) and the
        # operator's own scenario caught it: price touching 204.6 against a
        # 205 short is TESTED by the source and was NOT by mine. That is the
        # whole point of the rung — you act while price is AT the strike, not
        # after it has gone through, because through is where the roll stops
        # being affordable.
        _PROX = 5.0                      # STRIKE_INCREMENT, as in the source
        breached = None
        for t in legs:
            k = float(t.get("short_strike") or 0)
            if ((spot >= k - _PROX) if t.get("option_side") == "call"
                    else (spot <= k + _PROX)):
                breached = t
                break

        if breached is None:
            return {"strategy": "CreditRoll", "verdict": "HOLD",
                    "checks": {"rung": (1.0 if not rolled else 2.0, "n/a"),
                               "cum_credit_after_pct": (100.0, "PASS"),
                               "floor_pct": (floor_pct * 100, "n/a")},
                    "trigger_price": None, "underlying_at_decision": spot,
                    "why": (f"neither short is tested — the ladder is armed at "
                            f"rung {'2 (rolled)' if rolled else '1 (roll)'} and "
                            f"waiting")}

        # ── RUNG 1: the RISK-FREE ROLL, mirroring find_risk_free_roll ────
        #
        # 🔴 **THE TESTED SIDE NEVER MOVES.** Operator, 2026-08-25, and he was
        # right to demand it in writing before landing: *"confirm to me that
        # we're rolling the untested side I repeat the tested side stays on the
        # board."* Verified in condor_roll.py: `untested_side` is "the side we
        # roll toward price"; `tested_side` is "the threatened side (goes
        # risk-free)"; step 1 closes the "old UNTESTED vertical".
        #
        # THE MECHANISM: roll the CHEAP far-OTM untested vertical TOWARD price,
        # collecting credit. When cumulative credit covers the tested side's
        # WIDTH, the tested side can no longer lose money —
        #
        #     banked_credit + roll_credit − close_cost  >=  tested_width
        #
        # — and the structure is a broken-wing butterfly. The threatened short
        # is protected by credit taken from the other side, never by buying it
        # back. Buying back a tested short is the most expensive leg on the
        # board; that is why the textbook roll costs more than closing, and why
        # this ladder does not do it.
        #
        # ⚠️ SMALLEST ROLL THAT REACHES RISK-FREE, not the largest credit. The
        # source returns the FIRST risk-free candidate marching toward price —
        # least new risk on the rolled side. Taking the richest instead would
        # drag the untested short closer to price for credit nobody needed.
        if not rolled:
            u = keep_side = next((t for t in legs if t is not breached), None)
            if u is None:
                return None
            u_side = u.get("option_side")
            u_pool = {float(getattr(c, "strike", 0) or 0): c
                      for c in ((getattr(chain, "puts", []) if u_side == "put"
                                 else getattr(chain, "calls", [])) or [])}
            u_sh = u_pool.get(float(u.get("short_strike") or 0))
            u_lo = u_pool.get(float(u.get("long_strike") or 0))
            t_width = abs(float(breached.get("short_strike") or 0)
                          - float(breached.get("long_strike") or 0))
            wing = abs(float(u.get("short_strike") or 0)
                       - float(u.get("long_strike") or 0))
            if u_sh is None or u_lo is None:
                return {"strategy": "CreditRoll", "verdict": "HOLD",
                        "checks": {"rung": (1.0, "n/a")},
                        "trigger_price": float(breached.get("short_strike") or 0),
                        "underlying_at_decision": spot,
                        "why": (f"no mark for the untested {u_side} vertical — "
                                f"declining this pass, position left as-is "
                                f"(the roll's silent-refusal lesson)")}
            close_cost = max(round(float(u_sh.ask) - float(u_lo.bid), 2), 0.0)
            inc = 5.0
            cands, k = [], float(u.get("short_strike") or 0)
            if u_side == "put":
                k += inc
                while k <= spot:
                    cands.append(k); k += inc
            else:
                k -= inc
                while k >= spot:
                    cands.append(k); k -= inc
            best = None
            for ns_k in cands:
                nl_k = ns_k - wing if u_side == "put" else ns_k + wing
                ns, nl = u_pool.get(ns_k), u_pool.get(nl_k)
                if ns is None or nl is None:
                    continue
                try:
                    rc = round((float(ns.bid) + float(ns.ask)) / 2
                               - (float(nl.bid) + float(nl.ask)) / 2, 2)
                except Exception:                               # noqa: BLE001
                    continue
                if rc <= 0:
                    continue
                after = round(cum_credit + rc - close_cost, 2)
                cand = (ns_k, nl_k, rc, after, after >= t_width)
                if best is None or after > best[3]:
                    best = cand
                if cand[4]:            # first risk-free wins — smallest roll
                    best = cand
                    break
            # 🔴 NO ROLL AVAILABLE ⇒ FALL THROUGH TO THE TENT, NOT TO CLOSE.
            # Operator, 2026-08-25: *"If the first roll is off the table, try
            # inverted with the hedge, if that's off the table (economic or
            # cutoff entry times), then close it."*
            # ⚠️ MY FIRST VERSION RETURNED CLOSE HERE and skipped rung 2
            # entirely. That is the worse error of the two available: it exits
            # a position that still had a cheaper protective option, and it
            # does so precisely when price has run far enough that the untested
            # short has no room left — which is exactly when the hedge matters
            # most.
            # 🔴 TWO WAYS RUNG 1 CAN BE OFF THE TABLE, AND BOTH FALL THROUGH.
            # Operator, 2026-08-25: *"I thought if no roll exists, go inverted
            # with the hedge. Not 'do nothing' — I don't think any of my specs
            # ever advise do nothing."*
            # ⚠️ HIS SPEC HAS THREE STATES: roll, else hedge, else close. I
            # introduced a fourth (HOLD) and it was mine, not his.
            # ⚠️ AND "SHORT OF RISK-FREE" IS NOT A ROLL. The roll's ENTIRE
            # PURPOSE is making the tested side risk-free — the source refuses
            # to execute one that does not (`if plan is None or not
            # plan.risk_free: return False`). So a roll that falls short is not
            # a smaller version of the trade; it is a DIFFERENT and worse one,
            # and it belongs in the same bucket as no roll at all.
            if best is None or not best[4]:
                _no_roll_reason = (
                    (f"the untested {u_side} short has no room left toward "
                     f"{spot:.2f}")
                    if best is None else
                    (f"the best roll of the untested {u_side} side reaches "
                     f"${best[3]:.2f} against a tested width of ${t_width:.2f} "
                     f"— ${t_width - best[3]:.2f} SHORT of risk-free, and a "
                     f"roll that does not make the tested side risk-free is "
                     f"not the trade"))
                rolled = True          # fall through to the tent below
            else:
                ns_k, nl_k, rc, after, rf = best
                checks = {
                    "rung": (1.0, "n/a"),
                    "roll_credit": (rc, "PASS" if rc > 0 else "FAIL"),
                    "close_cost": (close_cost, "n/a"),
                    "credit_after": (after, "n/a"),
                    "tested_width": (t_width, "n/a"),
                    # ⚠️ RISK-FREE means the tested side CANNOT LOSE, not that the
                    # trade is guaranteed to win. Cumulative credit covers that
                    # side's width; the rolled side carries the new risk.
                    "risk_free": (1.0 if rf else 0.0, "PASS" if rf else "FAIL"),
                }
                return {
                    "strategy": "CreditRoll", "direction": u_side, "checks": checks,
                    "trigger_price": float(breached.get("short_strike") or 0),
                    "invalidation": float(breached.get("short_strike") or 0),
                    "short_strike": ns_k if u_side == "call" else None,
                    "short_put_strike": ns_k if u_side == "put" else None,
                    "underlying_at_decision": spot, "credit": rc,
                    "verdict": "ROLL",
                    "why": (f"the {breached.get('option_side')} short "
                        f"{float(breached.get('short_strike') or 0):.2f} is TESTED "
                        f"and STAYS ON THE BOARD; roll the UNTESTED {u_side} "
                        f"{float(u.get('short_strike') or 0):.0f}/"
                        f"{float(u.get('long_strike') or 0):.0f} → "
                        f"{ns_k:.0f}/{nl_k:.0f} toward price for ${rc:.2f} "
                        f"(closing the old costs ${close_cost:.2f}); cumulative "
                        f"${cum_credit:.2f} → ${after:.2f} against a tested "
                        f"width of ${t_width:.2f}"
                        + " — TESTED SIDE GOES RISK-FREE"),
                }

        # ── RUNG 2: rolled already ⇒ price the TENT before paying for it ──
        keep = next(t for t in legs if t is not breached)
        v_keep, v_breach = _mark(keep), _mark(breached)
        if v_keep is None or v_breach is None:
            return {"strategy": "CreditRoll", "verdict": "HOLD",
                    "checks": {"rung": (2.0, "n/a"),
                               "floor_pct": (floor_pct * 100, "n/a")},
                    "trigger_price": float(breached.get("short_strike") or 0),
                    "underlying_at_decision": spot,
                    "why": "a leg has no mark — declining this pass and leaving "
                           "the position as-is (the roll's silent-refusal lesson)"}

        c_keep = float(keep.get("credit_received") or keep.get("entry_premium") or 0)
        c_br = float(breached.get("credit_received")
                     or breached.get("entry_premium") or 0)
        p_keep, p_br = c_keep - v_keep, c_br - v_breach
        winner, loser = ((keep, breached) if p_keep >= p_br else (breached, keep))
        winner_take = _mark(winner) or 0.0

        side = loser.get("option_side")
        short_k = float(loser.get("short_strike") or 0)
        width = abs(short_k - float(loser.get("long_strike") or 0))
        hedge_k = short_k - width if side == "call" else short_k + width
        # ⚠️ OPPOSITE TYPE. A long PUT hedges a call side, a long CALL hedges a
        # put side — the operator's own construction, and the code's.
        hpool = {float(getattr(c, "strike", 0) or 0): c
                 for c in ((getattr(chain, "puts", []) if side == "call"
                            else getattr(chain, "calls", [])) or [])}
        hedge = hpool.get(hedge_k)
        hedge_ask = float(getattr(hedge, "ask", 0) or 0) if hedge else 0.0
        net_after = round(cum_credit - winner_take - hedge_ask, 2)
        pct = (net_after / cum_credit * 100.0) if cum_credit else 0.0
        affordable = hedge_ask > 0 and net_after > cum_credit * (1 - floor_pct)

        # ⚠️ THE CUTOFF IS THE CREDIT FLATTEN, NOT A NUMBER I CHOSE.
        # Operator: the tent is off the table on "economic OR CUTOFF ENTRY
        # TIMES". My first version invented a 20-minute prior — and he
        # corrected the premise it rested on: *"We have a 1545 credit
        # flatten."* `VERTICAL_HOLD_TO_ET = (15, 45)` and exit_engine closes
        # credit verticals there.
        # 🔴 SO AN INVENTED CUTOFF WAS WORSE THAN REDUNDANT — IT WAS A SECOND
        # TIME AUTHORITY. At 15:30 it would have returned CLOSE while the exit
        # engine intended to hold to 15:45, so the plan would advertise a close
        # the system was not going to perform. Two clocks disagreeing about the
        # same position is the failure class that costs a session to diagnose.
        # The tent's deadline is DERIVED from the flatten: buying a hedge with
        # minutes left before the position is closed anyway is paying a debit
        # for cover that expires with it.
        from config import VERTICAL_HOLD_TO_ET
        _flat_min = VERTICAL_HOLD_TO_ET[0] * 60 + VERTICAL_HOLD_TO_ET[1]
        _now = ctx.get("now_et_minutes")
        mins = (float(_flat_min - _now) if _now is not None
                else float(ctx.get("minutes_to_flatten") or 999))
        # ⟨PRIOR⟩ the hedge needs SOME life to be worth its debit; 15 min is
        # stated, not fitted, and it is measured against the FLATTEN.
        _TENT_MIN_MINUTES = 15.0
        in_window = mins >= _TENT_MIN_MINUTES
        checks = {
            "rung": (2.0, "n/a"),
            "roll_room": (0.0 if _no_roll_reason else 1.0,
                          "FAIL" if _no_roll_reason else "PASS"),
            "tent_hedge_cost": ((hedge_ask, "PASS" if hedge_ask > 0 else "FAIL")
                                if hedge is not None else None),
            "cum_credit_after_pct": (round(pct, 1),
                                     "PASS" if affordable else "FAIL"),
            "floor_pct": (floor_pct * 100, "n/a"),
            "winner_side_profit": (round(max(p_keep, p_br), 2), "n/a"),
            # minutes to the 15:45 CREDIT FLATTEN, not to the bell
            "minutes_to_close": (mins, "PASS" if in_window else "FAIL"),
        }
        if not in_window:
            return {
                "strategy": "CreditRoll", "direction": side, "checks": checks,
                "trigger_price": short_k, "underlying_at_decision": spot,
                "verdict": "CLOSE",
                "why": (f"only {mins:.0f} min to the 15:45 CREDIT FLATTEN — "
                        f"inside the tent's ⟨PRIOR⟩ {_TENT_MIN_MINUTES:.0f}-min "
                        f"deadline. A hedge is a DEBIT bought for cover that "
                        f"expires with a position the exit engine is about to "
                        f"flatten anyway"
                        + (f". {_no_roll_reason}" if _no_roll_reason else "")),
            }
        if not affordable:
            return {
                "strategy": "CreditRoll", "direction": side, "checks": checks,
                "trigger_price": short_k, "underlying_at_decision": spot,
                "verdict": "CLOSE",
                "why": ((f"no priced {'put' if side == 'call' else 'call'} hedge "
                         f"at {hedge_k:.2f} — a tent that cannot be built is a "
                         f"close") if hedge is None or hedge_ask <= 0 else
                        (f"the hedge at {hedge_k:.2f} costs ${hedge_ask:.2f}; "
                         f"that ALONE puts the structure at {pct:.1f}% of "
                         f"cumulative credit ${cum_credit:.2f}, past the "
                         f"{floor_pct*100:.0f}% floor. NOT BUYING IT — closing")
                        + (f". {_no_roll_reason}" if _no_roll_reason else "")),
            }
        return {
            "strategy": "CreditRoll", "direction": side, "checks": checks,
            "trigger_price": short_k, "underlying_at_decision": spot,
            "short_strike": hedge_k,
            "verdict": "TENT",
            "why": (f"keep the {side} {short_k:.0f}/{float(loser.get('long_strike') or 0):.0f}, "
                    f"take the {winner.get('option_side')} side off at "
                    f"${winner_take:.2f}, hedge LONG "
                    f"{'put' if side == 'call' else 'call'} {hedge_k:.2f} at "
                    f"${hedge_ask:.2f} — cumulative credit ${cum_credit:.2f} → "
                    f"${net_after:.2f} ({pct:.1f}%), clears the "
                    f"{floor_pct*100:.0f}% floor"
                    + (f" — reached because {_no_roll_reason}"
                       if _no_roll_reason else "")),
        }

    def _fork(self, ctx: dict) -> Optional[list]:
        """Sell just beyond a pitchfork TINE. One plan per available timeframe.

        🔴 OPERATOR'S CORRECTION, 2026-08-25, and it removed a whole gate I was
        about to build: *"The tines are what's of value, not the channel. That
        is the distinction. Tapping a tine is the trigger for selecting a short
        strike just outside the channel. That's the level, but sloped."*

        ⚠️ **A TINE IS A LEVEL. THE CHANNEL IS NOT A DISTANCE TO BE CROSSED.**
        I had started building a `span_vs_session` check — refuse the daily
        fork because a 0DTE cannot traverse a daily channel. That is the
        CONDOR's logic (price must stay between two shorts) applied to a trade
        that does not work that way. Selling beyond a tine no more requires
        price to reach the opposite rail than selling beyond London High
        requires it to reach London Low. The gate was deleted before it shipped.

        ⚠️ AND I HAD THE 08-22 RULING'S REASON WRONG TOO. I read
        `daily_fork_credit_spread.py`'s docstring, which leads with a
        DATA-AVAILABILITY note, and repeated that as the reason 1h was chosen.
        `main.py:2340` carries the operator's actual words: *"A DAILY fork
        demands an excursion from one anchor to the next that a single session
        rarely meets"* — about the fork BUILDING, not about the tine's worth.
        **Strategy docstrings carry historical and secondary framing; the
        ruling comments in main.py carry the operative decision.** Third time
        tonight that distinction mattered.

        ⇒ BOTH TIMEFRAMES ARE VALID and this emits a plan for each available
        one, tagged `fork_tf`. A DAILY tine is a multi-session structural
        boundary — a STRONGER level than an hourly one, not a disqualified one.

        ⚠️ THE RAIL IS FROZEN AT DECLARATION. `condor_trigger_map` recomputes
        tine positions every tick — its own comment: "a plan from 11am reads
        the 11am rail; by 2pm the tine has drifted by slope×bars." A plan that
        re-read the rail would chase its own anchor, which is the circular
        loop in miniature. `tine_slope` is RECORDED so the fit can see how far
        an hourly tine drifted while a plan stood; a daily tine barely moves
        intraday, which is why freezing matters more for 1h than 1d.
        """
        ctm = ctx.get("condor_triggers")
        chain = ctx.get("chain")
        spot = float(ctx.get("price") or 0)
        # 🔴 A MISSING INPUT IS A MEASUREMENT, NOT A REASON TO VANISH.
        # ⚠️ Returning None here wrote NO ROW, so "the fork was never
        # evaluated" was indistinguishable from "the fork engine does not
        # exist" — the same ambiguity that cost three rounds of fleet queries
        # this morning at the table level, repeated one layer down inside the
        # builder. On 2026-08-26 ForkCreditSpread and IronCondor were simply
        # ABSENT from plan_tick while five other plans wrote 80-95 rows each,
        # and nothing in the data said why.
        _missing = [n for n, v in (("condor_triggers", ctm), ("chain", chain))
                    if v is None] + (["price"] if spot <= 0 else [])
        if _missing:
            return [{"strategy": "ForkCreditSpread", "verdict": "NO PLAN",
                     "checks": {}, "underlying_at_decision": spot or None,
                     "why": (f"input(s) absent from ctx: {', '.join(_missing)} "
                             f"— the fork could not be evaluated this tick")}]
        # 🔴 `all_rails()`, NOT `all()`. I wrote this against a FIXTURE I had
        # invented — my test double exposed `.all()`, the real CondorTriggerMap
        # exposes `all_rails()`. So on every live tick this raised
        # AttributeError, the bare `except` below swallowed it, and the fork
        # returned None: NO ROW, no starved row, no "[plans] failed" line
        # (the exception never reached derive()'s handler because it was caught
        # in here). The plan was invisible in exactly the way r134 was built to
        # prevent, one level deeper than r134 reached.
        # ⚠️ A GREEN TEST AGAINST A FIXTURE I AUTHORED PROVES ONLY THAT I AM
        # CONSISTENT WITH MYSELF. The fixture must be checked against the real
        # interface, which is what check_fixture_fidelity now does.
        try:
            trigs = list(ctm.all_rails())
        except Exception as exc:                                # noqa: BLE001
            # ⚠️ AND NEVER VANISH ON AN EXCEPTION EITHER — say what broke.
            return [{"strategy": "ForkCreditSpread", "verdict": "NO PLAN",
                     "checks": {}, "underlying_at_decision": spot,
                     "why": (f"could not read the fork trigger map: "
                             f"{type(exc).__name__}: {exc}")}]
        if not trigs:
            return [{"strategy": "ForkCreditSpread", "verdict": "NO PLAN",
                     "checks": {}, "why": "no fork tines this tick"}]

        # 🔴 THE SHARED SESSION MAP DECIDES WHICH TINES ARE EVEN CANDIDATES.
        # ⚠️ I BUILT build_session_map AND THEN NEVER CALLED IT — it sat as
        # dead code, so the whole ceiling/floor geometry the operator specified
        # was never applied. A tine's own `side` was trusted outright, which is
        # exactly the defect credit_edge recorded weeks ago: an "upper" tine
        # that has drifted BELOW price still priced a short call — an ITM short
        # call, something nobody would sell.
        # Operator: *"an upper tine below the current open is UNUSABLE as a
        # candidate ... upper tines can only be call credit spreads, but would
        # be INVALIDATED BY GEOMETRY if they are below the open."*
        orb_hi = ctx.get("orb_high")
        orb_lo = ctx.get("orb_low")
        _valid_rails, _killed = None, {}
        if orb_hi and orb_lo:
            _ce, _fl, _inv = build_session_map(float(orb_hi), float(orb_lo),
                                               ledger=None, ctm=ctm)
            _valid_rails = {round(c.price, 4) for c in (_ce + _fl)}
            _killed = {round(c.price, 4): c.why for c in _inv}

        out = []
        for t in trigs:
            tf = getattr(t, "tf", "")
            side = getattr(t, "side", "")
            rail = float(getattr(t, "rail", 0) or 0)
            # ⚠️ NO OPENING RANGE ⇒ NO MAP ⇒ NO PLAN. Before 09:35 there is no
            # marker to measure against, and classifying without one would be
            # an accident dressed as a decision.
            if _valid_rails is None:
                out.append({
                    "strategy": "ForkCreditSpread", "direction": f"{tf}_{side}",
                    "verdict": "NO PLAN",
                    "checks": {"fork_tf": (1.0 if tf == "1h" else 2.0, "n/a")},
                    "why": ("no opening range yet — the session map cannot "
                            "exist before 09:35, so no tine is a candidate"),
                })
                continue
            if round(rail, 4) not in _valid_rails:
                out.append({
                    "strategy": "ForkCreditSpread", "direction": f"{tf}_{side}",
                    "verdict": "DECLINE",
                    "checks": {"fork_tf": (1.0 if tf == "1h" else 2.0, "n/a"),
                               "geometry": (0.0, "FAIL")},
                    "trigger_price": rail, "underlying_at_decision": spot,
                    "why": _killed.get(round(rail, 4),
                                       f"the {tf} {side} tine at {_n(rail, '.2f')} is "
                                       f"not a valid candidate on the session "
                                       f"map"),
                })
                continue
            slope = float(getattr(t, "slope", 0) or 0)
            trigger = float(getattr(t, "trigger", 0) or 0)
            if rail <= 0:
                continue
            is_call = side == "call"
            pool = {float(getattr(c, "strike", 0) or 0): c
                    for c in ((getattr(chain, "calls", []) if is_call
                               else getattr(chain, "puts", [])) or [])}
            # ⚠️ JUST OUTSIDE THE TINE — the operator's words. First strike
            # beyond the rail, not a fitted offset from it.
            if is_call:
                sk = min((k for k in sorted(pool) if k >= rail), default=None)
                lk = sk + 5 if sk is not None else None
            else:
                sk = max((k for k in sorted(pool) if k <= rail), default=None)
                lk = sk - 5 if sk is not None else None
            credit = risk = r = None
            if sk is not None and lk in pool:
                try:
                    credit = round(float(pool[sk].bid) - float(pool[lk].ask), 2)
                    risk = round(5.0 - credit, 2)
                    r = round(credit / risk, 2) if risk > 0 else None
                except Exception:                               # noqa: BLE001
                    credit = risk = r = None
            dist_pct = abs(rail - spot) / spot * 100.0
            why, ok = [], True
            if sk is None:
                ok = False
                why.append(f"no strike beyond the {tf} {side} tine {_n(rail, '.2f')}")
            _rv, _rr = r_verdict(r)
            if _rv == "FAIL":
                ok = False
                why.append(f"{_rr} — TARGET {_n(sk, '.2f')} (short strike expiring "
                           f"worthless), STOP a close beyond the tine "
                           f"{_n(rail, '.2f')}")
            out.append({
                "strategy": "ForkCreditSpread", "direction": f"{tf}_{side}",
                "checks": {
                    # ⚠️ NEVER DROP THE CHECK WHEN R IS UNMEASURABLE — write
                    # the verdict with a NULL value. A missing ROW and a NULL
                    # VALUE mean different things to the fit.
                    "r": (r, r_verdict(r)[0]),
                    "tine_distance_pct": (round(dist_pct, 3), "n/a"),
                    "strike_beyond_tine": ((float(sk), "PASS")
                                           if sk is not None else None),
                    # 1.0 = 1h, 2.0 = 1d — numeric so the column stays REAL
                    "fork_tf": (1.0 if tf == "1h" else 2.0, "n/a"),
                    # the tine survived the session map's ceiling/floor test
                    "geometry": (1.0, "PASS"),
                    # RECORDED: how fast this tine drifts. The reason freezing
                    # the rail matters more for 1h than 1d.
                    "tine_slope": (round(slope, 5), "n/a"),
                    "credit": ((credit, "n/a") if credit is not None else None),
                },
                "trigger_price": trigger or rail,
                "invalidation": rail,
                "short_strike": float(sk) if (sk is not None and is_call) else None,
                "long_strike": float(lk) if (lk is not None and is_call) else None,
                "short_put_strike": None if is_call else (float(sk) if sk else None),
                "long_put_strike": None if is_call else (float(lk) if lk else None),
                "underlying_at_decision": spot, "credit": credit, "risk": risk,
                "r": r,
                "verdict": "TAKE" if ok else "DECLINE",
                "why": "; ".join(why) if why else
                       (f"{tf} {side} tine at {_n(rail)} ({_n(dist_pct)}% from "
                        f"spot, slope {_n(slope, '+.4f')}/bar); sell "
                        f"{_n(sk, '.0f')}/{_n(lk, '.0f')} just beyond it for "
                        f"${_n(credit)}, R {_n(r)}"),
            })
        return out

    # ── the tables ──────────────────────────────────────────────────────
    # 🔴 r126b — TWO TABLES, AND THE SPLIT IS THE WHOLE DESIGN.
    #
    # Operator: *"You would have to identify what elements belong in the table
    # for each plan so that every plan can live in the table and only the
    # columns that it needs are going to record for that plan."*
    #
    # He is naming the schema problem exactly. A single WIDE table needs a
    # column for every variable of every plan — sweep's pierce depth, the
    # condor's second side, the butterfly's pin concentration — so every row
    # is mostly NULL, and every NEW plan is a schema migration on 15 boxes.
    # That is how a table stops being written to.
    #
    #   `plan_tick`   THE SPINE. Only what EVERY plan has: what fires it, what
    #                 kills it, what it pays, and the verdict. These MUST be
    #                 shared columns, because comparing R ACROSS plans at one
    #                 instant is the entire point — on 2026-08-25 participation
    #                 offered 0.18-0.34 while the butterfly offered 3.81-5.10
    #                 on the same chain in the same minutes, and nothing in the
    #                 system could see both numbers at once.
    #
    #   `plan_check`  LONG FORMAT — one row per VARIABLE per plan per tick,
    #                 which is the operator's own picture: ticks across, the
    #                 variables being checked down. A plan writes ONLY the
    #                 checks it owns. No NULLs, no migration when a plan is
    #                 added, and each check carries its own PASS/FAIL so the
    #                 elimination reason is a queryable row rather than a
    #                 sentence.
    #
    # ⚠️ DECLINES ARE THE POINT, NOT THE EXHAUST. Both tables record TAKE and
    # DECLINE alike. A plan that never fired is the counterfactual arm the fit
    # needs most — and it is precisely what `strategy_note` cannot express,
    # since that table records only that a strategy was ASKED.

    # Which checks each plan owns. Declared here so the table is
    # self-describing and a reader can tell "not applicable" from "not run".
    CHECKS = {
        "GEXPinButterfly":    ("net_gamma", "pin_conc", "pin_share",
                               "reach_em", "r", "charm_raw", "charm_corrected"),
        "TrendParticipation": ("r", "credit", "risk", "strike_inside_range"),
        # 🔴 r127 — SWEEP. Six kill variables, and `level_hold_rate` is the
        # only validator in the system so far that MOVES MEANINGFULLY WITHIN A
        # SESSION: TSLA's London High read 93.3% at 11:31 and 58% by the close
        # (measured from raw/liquidity_ledger, 75 snapshots). Everything else
        # we have is near-constant intraday. `pierce_depth` is RECORDED ONLY —
        # operator, 2026-08-25: "the depth of the pierce is what's going to
        # discriminate on what constitutes a pierce" — fitted later, gating
        # nothing now.
        "SweepCreditSpread":  ("level_hold_rate", "acceptance", "reclaim_age",
                               "r", "event_spent", "pierce_depth"),
        # 🔴 r129 — RUNAWAY CONTINUATION, the first DEBIT plan. `travel_atr`
        # is the sanity check the operator asked for: a 1R target is only real
        # if the tape can actually cover that distance in the time left.
        # `theta_dollars` is RECORDED IN DOLLARS AT ENTRY and NEVER netted
        # into R — his instruction, and the right one; a theta-burn layer is
        # a fitting-phase question, not an entry gate.
        "RunawayContinuation": ("travel_atr", "r", "delta", "theta_dollars",
                                "gamma_lift"),
        # 🔴 r130 — IRON CONDOR. ONE PLAN, TWO TRIGGERS. `leg2_pending` is the
        # column that makes a half-built structure legible: on 2026-08-25 CRM
        # signalled a second leg on 406 CONSECUTIVE TICKS with a put already
        # open and NOTHING in any log, because `_can_open_credit_spread`
        # returned False for both Rule 1 and Rule 3 without a word. A condor
        # that is half on is a real state and it now has a row.
        "IronCondor":         ("r", "call_side_ready", "put_side_ready",
                               "leg2_pending", "range_width_atr"),
        # 🔴 r131 — THE ROLL. Operator: "we are already trying to find the
        # farthest strike that satisfies the economical question & that is
        # worthy of a tick by tick plan." Its verdict is THREE-WAY —
        # ROLL / CLOSE / HOLD — because "get out" is an answer, not a refusal.
        # 🔴 r132 — THE FORK PLAN, 1h AND 1d, ONE BUILDER. Operator, 2026-08-25:
        # *"The tines are what's of value, not the channel... Tapping a tine is
        # the trigger for selecting a short strike just outside the channel.
        # That's the level, but sloped."* And: *"the hourly is valid too. Same
        # rationale."* `fork_tf` separates them for the fit.
        "ForkCreditSpread":   ("r", "tine_distance_pct", "strike_beyond_tine",
                               "fork_tf", "tine_slope", "credit"),
        "CreditRoll":         ("rung", "roll_room", "roll_credit", "close_cost",
                               "credit_after", "tested_width", "risk_free",
                               "tent_hedge_cost", "cum_credit_after_pct",
                               "floor_pct", "winner_side_profit",
                               "minutes_to_close"),
    }

    def _ensure(self):
        if self._made or self._store is None:
            return
        try:
            self._store.conn.execute("""
                CREATE TABLE IF NOT EXISTS plan_tick (
                    ts_epoch     REAL NOT NULL,
                    symbol       TEXT NOT NULL,
                    strategy     TEXT NOT NULL,
                    verdict      TEXT NOT NULL,      -- TAKE / DECLINE / NO PLAN
                    reason       TEXT,
                    trigger_price   REAL,            -- FROZEN at declaration
                    invalidation    REAL,            -- FROZEN at declaration
                    underlying      REAL,            -- LIVE
                    dist_to_trigger REAL,            -- LIVE
                    r_now           REAL,            -- LIVE, comparable ACROSS plans
                    -- 🔴 `direction` IS PART OF THE KEY (r133). The original
                    -- key was (ts_epoch, symbol, strategy) — correct in r126,
                    -- when every builder returned exactly ONE plan. The fork
                    -- builder returns FOUR (1h/1d x call/put), so INSERT OR
                    -- REPLACE silently overwrote three of them: 5 plans
                    -- produced, 4 rows stored, no error anywhere.
                    -- ⚠️ FIXED TODAY BECAUSE TODAY IT IS FREE — the ordering
                    -- bug meant these tables were NEVER CREATED on any box, so
                    -- there is nothing to migrate. Tomorrow there would be.
                    direction    TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (ts_epoch, symbol, strategy, direction)
                );""")
            self._store.conn.execute("""
                CREATE TABLE IF NOT EXISTS plan_check (
                    ts_epoch  REAL NOT NULL,
                    symbol    TEXT NOT NULL,
                    strategy  TEXT NOT NULL,
                    check_name TEXT NOT NULL,
                    value     REAL,
                    verdict   TEXT,                  -- PASS / FAIL / n/a
                    -- same collision, same fix: one fork timeframe/side per row
                    direction TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (ts_epoch, symbol, strategy, direction, check_name)
                );""")
            self._store.conn.execute(
                "CREATE INDEX IF NOT EXISTS ix_plan_tick "
                "ON plan_tick(symbol, strategy, ts_epoch)")
            self._store.conn.execute(
                "CREATE INDEX IF NOT EXISTS ix_plan_check "
                "ON plan_check(symbol, strategy, check_name, ts_epoch)")
            self._made = True
        except Exception as exc:                                # noqa: BLE001
            logger.debug("plan tables: %s", exc)

    def _write_tick(self, ctx: dict, plans: list) -> int:
        if self._store is None:
            return 0
        self._ensure()
        now = time.time()
        spot = float(ctx.get("price") or 0)
        n = 0
        for p in plans:
            trig = p.get("trigger_price")
            try:
                self._store.conn.execute(
                    "INSERT OR REPLACE INTO plan_tick (ts_epoch, symbol,"
                    " strategy, verdict, reason, trigger_price, invalidation,"
                    " underlying, dist_to_trigger, r_now, direction)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (now, self.symbol, p.get("strategy"), p.get("verdict"),
                     p.get("why"), trig, p.get("invalidation"), spot,
                     (spot - trig) if trig else None, p.get("r"),
                     p.get("direction") or ""))
                n += 1
            except Exception as exc:                            # noqa: BLE001
                # ⚠️ WARNING — a row that fails to write is data lost, and
                # r133 spent three query rounds on exactly this kind of silence.
                logger.warning("plan_tick write FAILED for %s: %s: %s",
                               p.get("strategy"), type(exc).__name__, exc)
                continue
            # ── the checks THIS plan owns, one row each ──────────────────
            for name in self.CHECKS.get(p.get("strategy"), ()):
                v = p.get("checks", {}).get(name)
                if v is None:
                    # ⚠️ ABSENT, NOT ZERO. A check that could not be computed
                    # is recorded with a NULL value and verdict 'n/a' — never
                    # 0.0/PASS. Conflating "no reading" with "a reading of
                    # zero" is the VW.1 failure and second_order.py already
                    # refuses it for exactly this reason.
                    val, verdict = None, "n/a"
                else:
                    val, verdict = v
                try:
                    self._store.conn.execute(
                        "INSERT OR REPLACE INTO plan_check (ts_epoch, symbol,"
                        " strategy, check_name, value, verdict, direction)"
                        " VALUES (?,?,?,?,?,?,?)",
                        (now, self.symbol, p.get("strategy"), name, val,
                         verdict, p.get("direction") or ""))
                except Exception:                               # noqa: BLE001
                    pass
        try:
            self._store.commit()
        except Exception:                                       # noqa: BLE001
            pass
        return n

    # ── the board ───────────────────────────────────────────────────────
    # Builder -> the strategy name its rows carry, so a RAISED builder still
    # files under the name a reader would look for.
    _PLAN_NAME_BY_FN = {
        "_butterfly": "GEXPinButterfly", "_participation": "TrendParticipation",
        "_sweep": "SweepCreditSpread", "_runaway": "RunawayContinuation",
        "_condor": "IronCondor", "_roll": "CreditRoll",
        "_fork": "ForkCreditSpread",
    }

    def derive(self, ctx: dict) -> int:
        plans = []
        for fn in (self._butterfly, self._participation, self._sweep,
                   self._runaway, self._condor, self._roll, self._fork):
            try:
                p = fn(ctx)
            except Exception as exc:                            # noqa: BLE001
                # 🔴 WARNING, NOT DEBUG, AND IT WRITES A ROW (r136).
                # ⚠️ THIS LINE COST A FULL DAY. IronCondor produced no row AND
                # no INFO line for an entire session — the only shape that fits
                # is a raise here — while this handler whispered at DEBUG into a
                # journal handler set to INFO. So the exception was logged
                # nowhere, the plan was absent from the table, and three
                # separate queries (plan_tick, journalctl, logs/) all came back
                # empty in a way that looked like "the builder does not exist".
                # ⚠️ AND A LOG LINE IS NOT ENOUGH — the TABLE must carry it too,
                # or the failure is invisible to anyone reading the data rather
                # than the journal. Same rule as r134's starved rows.
                logger.warning("[plans] %s RAISED: %s: %s — this plan is "
                               "absent this tick", fn.__name__,
                               type(exc).__name__, exc)
                p = [{"strategy": self._PLAN_NAME_BY_FN.get(fn.__name__, fn.__name__),
                      "verdict": "NO PLAN", "checks": {},
                      "why": (f"builder RAISED {type(exc).__name__}: {exc}")}]
            if isinstance(p, list):
                # ⚠️ ONE BUILDER, MANY PLANS. The fork emits one per available
                # timeframe; flattening here keeps every other builder's
                # single-plan contract unchanged.
                plans.extend(x for x in p if x)
            elif p:
                plans.append(p)
        if not plans:
            return 0

        # ⚠️ ONE LINE PER PLAN AT INFO, EVERY CYCLE. The operator reads
        # bot.log at INFO; a plan logged at DEBUG is a plan nobody sees, and
        # that is exactly how the sweep strategy's eleven refusal paths stayed
        # invisible for weeks (2026-08-11).
        for p in plans:
            if p.get("verdict") == "NO PLAN":
                logger.info("[plan] %-18s NO PLAN — %s", p["strategy"], p["why"])
                continue
            bits = []
            if p.get("r") is not None:
                bits.append(f"R {p['r']:.2f}")
            if p.get("debit") is not None:
                bits.append(f"pay ${p['debit']:.2f}")
            if p.get("credit") is not None:
                bits.append(f"collect ${p['credit']:.2f}")
            if p.get("reach") is not None:
                bits.append(f"reach {p['reach']:.2f}EM")
            if p.get("conc") is not None:
                bits.append(f"conc {p['conc']:.1f}x")
            logger.info("[plan] %-18s %-7s trig %.2f · %s · %s",
                        p["strategy"], p["verdict"], p.get("trigger_price", 0),
                        " · ".join(bits) or "-", p["why"])

        # ⚠️ EVERY plan this tick — TAKE and DECLINE — lands in `plan_tick`.
        rows = self._write_tick(ctx, plans)

        # TAKE plans also open a plan_ledger row so the counterfactual can
        # score them against what price subsequently did.
        if self._ledger is not None:
            for p in plans:
                if p.get("verdict") != "TAKE":
                    continue
                # ⚠️ A PLAN THAT DECLARES ITS OWN IDENTITY OWNS IT. The sweep
                # keys on (pool, reclaim bar) so a NEW reclaim is a NEW plan
                # while the SAME reclaim can never re-declare — that is the
                # CVX fix, and a generic strategy:trigger key would not
                # express it (the pool price is identical across re-fires).
                key = p.get("identity") or f"{p['strategy']}:{p.get('trigger_price')}"
                if key in self._declared:
                    continue        # one plan per trigger — never a re-fire loop
                pid = self._ledger.open_plan(
                    p["strategy"], "DECLARED", ctx,
                    direction=p.get("direction"),
                    short_strike=p.get("short_strike"),
                    long_strike=p.get("long_strike"),
                    short_put_strike=p.get("short_put_strike"),
                    long_put_strike=p.get("long_put_strike"),
                    trigger_price=p.get("trigger_price"),
                    underlying_at_decision=p.get("underlying_at_decision"))
                if pid:
                    self._declared[key] = pid
        return rows
