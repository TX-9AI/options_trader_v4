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
PLAN_R_FLOOR      = 1.00    # operator's stated minimum reward:risk
PIN_CONC_MIN      = 3.00    # pin must hold 3x its neighbours' gamma
PIN_SHARE_MIN     = 0.15    # ...and 15% of all near-money gamma
PIN_REACH_MAX     = 1.00    # pin within one remaining expected move
PIN_REACH_MIN     = 0.15    # already there = nothing left to capture
EM_SESSION_PCT    = 0.020   # session expected move as a fraction of spot
NEAR_MONEY_PCT    = 0.15    # strikes beyond this do not participate in gamma


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

    # ── gamma surface ───────────────────────────────────────────────────
    @staticmethod
    def _gamma_by_strike(chain, spot: float):
        """Signed dealer gamma per strike, near the money only.

        ⚠️ ⟨ASSUMPTION⟩ dealers long calls / short puts. NOT verified against
        this fleet's own GEX code. The pin's LOCATION barely moves under it
        (360 in 72/74 TSLA snapshots on 2026-08-25 either way) but the
        PULL/PUSH verdict FLIPS, so this is the most load-bearing assumption
        in the file and it is stamped on every plan as `gex_sign_convention`.
        """
        per = defaultdict(float)
        for c in (getattr(chain, "calls", []) or []):
            g = float(getattr(c, "gamma", 0) or 0)
            oi = float(getattr(c, "oi", 0) or 0)
            k = float(getattr(c, "strike", 0) or 0)
            if g > 0 and oi > 0 and spot and abs(k-spot)/spot <= NEAR_MONEY_PCT:
                per[k] += g * oi
        for p in (getattr(chain, "puts", []) or []):
            g = float(getattr(p, "gamma", 0) or 0)
            oi = float(getattr(p, "oi", 0) or 0)
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
        if chain is None or spot <= 0:
            return None
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
        if r is not None and r < PLAN_R_FLOOR:
            ok = False
            why.append(f"R {r:.2f} below {PLAN_R_FLOOR:.2f}")
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
            "r":          ((r, "PASS" if r >= PLAN_R_FLOOR else "FAIL")
                           if r is not None else None),
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
                   (f"pin {conc:.1f}x neighbours, reachable at {reach:.2f} EM, "
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
        if chain is None or spot <= 0 or not orb_hi or not orb_lo:
            return None
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
        except Exception:                                       # noqa: BLE001
            return None
        risk = round(5.0 - credit, 2)
        r = round(credit / risk, 2) if risk > 0 else None
        ok = r is not None and r >= PLAN_R_FLOOR
        why = ("" if ok else
               f"R {r if r is not None else 0:.2f} below {PLAN_R_FLOOR:.2f} — "
               f"TARGET {sk:.2f} (short strike expiring worthless) pays "
               f"${credit:.2f}; STOP {orb_hi:.2f} (a close back through the ORB "
               f"high) risks ${risk:.2f}")
        checks = {
            "r":       ((r, "PASS" if (r or 0) >= PLAN_R_FLOOR else "FAIL")
                        if r is not None else None),
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
            "why": why or f"R {r:.2f} clears the floor",
            "credit": credit, "risk": risk, "r": r,
        }

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
                    PRIMARY KEY (ts_epoch, symbol, strategy)
                );""")
            self._store.conn.execute("""
                CREATE TABLE IF NOT EXISTS plan_check (
                    ts_epoch  REAL NOT NULL,
                    symbol    TEXT NOT NULL,
                    strategy  TEXT NOT NULL,
                    check_name TEXT NOT NULL,
                    value     REAL,
                    verdict   TEXT,                  -- PASS / FAIL / n/a
                    PRIMARY KEY (ts_epoch, symbol, strategy, check_name)
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
                    " underlying, dist_to_trigger, r_now)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (now, self.symbol, p.get("strategy"), p.get("verdict"),
                     p.get("why"), trig, p.get("invalidation"), spot,
                     (spot - trig) if trig else None, p.get("r")))
                n += 1
            except Exception as exc:                            # noqa: BLE001
                logger.debug("plan_tick write: %s", exc)
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
                        " strategy, check_name, value, verdict)"
                        " VALUES (?,?,?,?,?,?)",
                        (now, self.symbol, p.get("strategy"), name, val, verdict))
                except Exception:                               # noqa: BLE001
                    pass
        try:
            self._store.commit()
        except Exception:                                       # noqa: BLE001
            pass
        return n

    # ── the board ───────────────────────────────────────────────────────
    def derive(self, ctx: dict) -> int:
        plans = []
        for fn in (self._butterfly, self._participation):
            try:
                p = fn(ctx)
            except Exception as exc:                            # noqa: BLE001
                logger.debug("[plans] %s failed: %s", fn.__name__, exc)
                p = None
            if p:
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
                key = f"{p['strategy']}:{p.get('trigger_price')}"
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
