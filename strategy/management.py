"""
strategy/management.py  v2.1
v2.1  2026-08-27  r168: the runaway declares NO structure stop — its floor is
      the 20% premium loss on the record; the breach check cannot fire for it
      because the signal carries no underlying_stop.
v2.0  2026-08-27  r167 — THE PLAN DECIDES; THE EXIT ENGINE CALCULATES AND
      EXECUTES. Operator, 2026-08-27: *"I'm ready for the managed exits
      build, if on the next tick is this, cut it loose, or roll, or whatever
      the management is."* With the rulings: *"Everything tied to the orb
      stays. Even the trailing stop armed at 50% and the tightening after
      100% on the peak. The other variables for the other strategies were
      all good except for the BOS"* and *"We still have the 15% floor & the
      'breach' stops."*
      NEW `decide(record, premium, df_1m, open_records)` -> Intent for the
      records this plan COVERS: RunawayContinuation, GEXPinButterfly, and a
      SweepCreditSpread / TrendCreditSpread vertical while it stands alone
      (a formed condor, a tent, ORB and ADOPTED are NOT covered — the ladder
      and ORB's own path decide those, untouched). Order, and it matters:
        1. THE DECLARED SPEC CONDITIONS, read straight off the record — the
           15% floor / hard stop (`stop_premium`), the BREACH stops (a 1m
           close through `underlying_stop`: the ORB boundary, the bound,
           the pool), the target, the nickel. These are never outranked.
        2. THE CALCULATORS — the exit engine's evaluate() for the 50% trail,
           the tightening after 100% on the peak, theta bleed, velocity
           stall. Its ExitDecision is adopted as the plan's own. BOS is gone
           (exit_engine v4.7).
      Every intent is a ROW before it is an act (CLOSE / TRAIL / HOLD with
      the condition that fired and the numbers). position_manager v4.6 asks
      this plan first and executes its intent through the same
      _execute_exit; the engine's evaluate() runs directly only for records
      the plan does not cover.
v1.0  2026-08-27  r166 — THE MANAGEMENT PLAN: ONE WATCHER PER OPEN POSITION.
      Operator, 2026-08-27, on where stops live: *"The plan seems like the
      right place for them … I like the thought of it watching & thinking if
      it does 'this' or 'this' we're out!"* And on the r66 vectors: *"if there
      is a way to incorporate those vectors back into the management (and
      stop functions) I think that is the logical next step."*

THE SAME SPLIT AS ENTRIES, ONE POSITION AT A TIME.
  · The STRATEGY declares its exit conditions as data (`EXIT_CONDITIONS`
    below, keyed by strategy name) — what "we're out" means for that spec.
  · The MANAGEMENT PLAN reads, every tick for every open record, the current
    value of each of those conditions off what the exit engine already
    tracks (premium now, stop premium, trail stop, target, underlying stop,
    MFE/MAE, ticks held) and writes ONE row: HOLD "if premium <= 0.66 -> out
    (hard stop); if 1m close < 101.00 -> out (structure); trail 1.12 armed;
    MFE +41%". It also records the r66 DERIVED VECTOR for that strategy
    (aggression at the level, tape, VRP, charm …) into strategy_note with
    phase "manage", so a stop can later be FITTED against what the tape was
    doing while the position lived, not just at entry.
  · The EXIT ENGINE executes, exactly as today. This file changes no exit.

⚠️ WRITTEN AFTER manage_open_position, deliberately: the exit engine has just
priced the record and updated trail/MFE. The row says what would take the
position out on the NEXT tick — anticipatory, like the entry plans.

⚠️ NEVER RAISES, NEVER GATES. A bookkeeping failure here cannot reach an exit.

⚠️ CONDITIONS ARE READ, NOT RE-DERIVED. Every threshold below is the record's
own field (set at entry from the strategy's spec) or the exit engine's own
state. When this file and the exit engine disagree, the exit engine is
right and this file has a bug — pinned by tests/check_management_plan.py.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from strategy.plan import Plan, _n

logger = logging.getLogger(__name__)

# ── WA §36 GATE CATEGORIES ──────────────────────────────────────────────
# This file OWNS NO THRESHOLD. Every number it writes is the record's own
# field (set at entry from the strategy's spec) or the exit engine's state;
# tests/check_management_plan.py M9 refuses a literal compared to a premium.
GATES = {}

# ── THE DECLARED EXIT CONDITIONS — the strategy's spec, as data ─────────────
# name -> what "true" means. Read from the record; nothing computed here.
EXIT_CONDITIONS: Dict[str, Dict[str, str]] = {
    "RunawayContinuation": {
        # r168 — NO price stop. Operator: a 20% premium loss, decay or adverse
        # move; "the runaway needs room to breathe. A few pullbacks in an
        # uptrend are ok." The ORB structure stop is ORB's alone.
        "hard_stop":      "premium <= stop_premium (the 20% floor set at entry)",
        "trail":          "premium <= trail_stop, once the trail has armed at +50%",
        "target":         "premium >= target_premium, then the tightening off the peak",
    },
    "ORBStrategy": {
        "hard_stop":      "premium <= stop_premium",
        "structure_stop": "a 1m close through underlying_stop (the impulsive-candle extreme)",
        "trail":          "premium <= trail_stop, once the trail has armed",
        "target":         "premium >= target_premium",
    },
    "SweepCreditSpread": {
        "premium_stop":   "spread value >= stop_premium (credit x (1 + max_loss_pct))",
        "acceptance":     "a 1m close through the swept pool (the level failed)",
        "nickel":         "spread value <= the nickel — let it go",
    },
    "TrendCreditSpread": {
        "breach":         "a 1m close through the ORB bound (underlying_stop) — no premium stop",
        "nickel":         "spread value <= the nickel",
    },
    "IronCondorStrategy": {
        "ladder":         "CondorManagement decides: ROLL / TENT / CLOSE (TRADES.md)",
        "premium_stop":   "spread value >= credit x (1 + 25%) while a lone vertical",
    },
    "GEXPinButterfly": {
        "stop":           "fly value <= entry x (1 - stop_loss_pct)",
        "target":         "fly value >= the profit take",
    },
}

MGMT_CHECKS = ("premium", "entry_premium", "pnl_pct", "stop_premium", "trail_stop",
               "target_premium", "underlying_stop", "dist_to_stop", "mfe_pct",
               "mae_pct", "ticks_held", "fired")

COVERED = ("RunawayContinuation", "GEXPinButterfly", "SweepCreditSpread",
           "TrendCreditSpread")
NICKEL = 0.05


class Intent:
    """What the plan decided for the NEXT tick. Executed by position_manager."""
    __slots__ = ("action", "reason", "condition", "trail", "pnl_pct")

    def __init__(self, action: str, reason: str = "", condition: str = "",
                 trail: Optional[float] = None, pnl_pct: float = 0.0):
        self.action = action            # HOLD / CLOSE / TRAIL
        self.reason = reason
        self.condition = condition
        self.trail = trail
        self.pnl_pct = pnl_pct

    def to_exit_decision(self):
        from execution.exit_engine import ExitDecision
        d = ExitDecision()
        d.should_exit = self.action == "CLOSE"
        d.exit_reason = self.reason if d.should_exit else ""
        d.new_trail_stop = self.trail
        d.current_pnl_pct = self.pnl_pct
        return d


def covers(record, open_records=None) -> bool:
    """Which records THIS plan decides for. ORB, ADOPTED, tents and formed
    condors are decided elsewhere and are only narrated here."""
    strategy = str(record.get("strategy", "") or "")
    if strategy not in COVERED:
        return False
    if record.get("is_tent") or record.get("is_broken_wing"):
        return False
    if record.get("is_condor_leg") or record.get("is_credit_vertical"):
        legs = [r for r in (open_records or []) if r.get("is_condor_leg")
                and not r.get("is_tent")]
        if len(legs) >= 2:
            return False                # formed: the ladder decides
    return True


def _f(v) -> Optional[float]:
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


class ManagementPlan:
    """One `Plan` per strategy, rows written under "<Strategy>/manage"."""

    def __init__(self):
        self._plans: Dict[str, Plan] = {}
        self._writer = None          # the r66 NoteWriter, resolved lazily

    def _plan(self, strategy: str) -> Plan:
        key = f"{strategy}/manage"
        if key not in self._plans:
            self._plans[key] = Plan(key, MGMT_CHECKS, self_ledgers=True)
        return self._plans[key]

    def _notes(self, ctx: dict):
        if self._writer is not None:
            return self._writer
        try:
            for e in (ctx.get("derived_engines") or []):
                if getattr(e, "name", "") == "notes":
                    self._writer = e.writer
                    break
        except Exception:                                      # noqa: BLE001
            self._writer = None
        return self._writer

    # ══════════════════════════════════════════════════════════════════════
    # THE DECISION — for the records this plan covers
    # ══════════════════════════════════════════════════════════════════════
    def decide(self, record, current_premium: float, df_1m=None, open_records=None,
               current_price: Optional[float] = None, ctx: Optional[dict] = None,
               exit_engine=None, now_minutes_held: Optional[float] = None
               ) -> Optional[Intent]:
        """The intent for the NEXT tick, or None if this plan does not cover
        the record (caller falls back to the engine's own evaluate()).
        Writes the row. Never raises — a raise here returns None, and the
        engine decides as it always did."""
        try:
            if not covers(record, open_records):
                return None
            strategy = str(record.get("strategy", "") or "")
            prem = _f(current_premium)
            entry = _f(record.get("entry_premium")) or 0.0
            credit = bool(record.get("is_credit_vertical")) or strategy in (
                "SweepCreditSpread", "TrendCreditSpread")
            pnl = 0.0
            if prem is not None and entry > 0:
                pnl = (entry - prem) / entry if credit else (prem - entry) / entry
            stop_p = _f(record.get("stop_premium"))
            target = _f(record.get("target_premium"))
            ustop = _f(record.get("underlying_stop"))
            price = _f(current_price) if current_price is not None else _f(record.get("current_price"))
            last_close = None
            try:
                if df_1m is not None and len(df_1m):
                    last_close = float(df_1m["close"].iloc[-1])
            except Exception:                                  # noqa: BLE001
                last_close = None
            if price is None:
                price = last_close
            plan = self._plan(strategy)
            t = plan.tick(price, str(record.get("option_side", "") or ""))
            self._readings(t, record, price)

            # ── 1. THE DECLARED SPEC CONDITIONS — never outranked ──────────
            intent = None
            if prem is not None and stop_p and strategy != "TrendCreditSpread":
                hit = (prem >= stop_p) if credit else (prem <= stop_p)
                if hit:
                    name = "premium_stop" if credit else ("stop" if strategy == "GEXPinButterfly" else "hard_stop")
                    floor_pct = (abs(stop_p - entry) / entry) if entry else 0.0
                    intent = Intent("CLOSE", f"{name}_{floor_pct:.0%} pnl={pnl:.1%}", name, pnl_pct=pnl)
            if intent is None and ustop and last_close is not None:
                side = str(record.get("option_side", "") or "")
                if not credit and record.get("direction") in ("long", "short"):
                    breached = last_close < ustop if record.get("direction") == "long" else last_close > ustop
                else:
                    breached = last_close < ustop if side == "put" else last_close > ustop
                if breached:
                    name = ("structure_stop" if not credit else
                            ("breach" if strategy == "TrendCreditSpread" else "acceptance"))
                    intent = Intent("CLOSE", f"{name}: 1m close {last_close:.2f} through "
                                             f"{ustop:.2f} pnl={pnl:.1%}", name, pnl_pct=pnl)
            if intent is None and prem is not None and target and not credit and prem >= target:
                intent = Intent("CLOSE", f"target_hit pnl={pnl:.1%}", "target", pnl_pct=pnl)
            if intent is None and credit and prem is not None and prem <= NICKEL:
                intent = Intent("CLOSE", f"nickel_close pnl={pnl:.1%}", "nickel", pnl_pct=pnl)

            # ── 2. THE CALCULATORS — the engine's trail / tightening / theta /
            # velocity, adopted as the plan's own decision ────────────────────
            if intent is None and exit_engine is not None and prem is not None:
                try:
                    d = exit_engine.evaluate(record, prem, df_1m=df_1m,
                                             df_5m=(ctx or {}).get("df_5m"),
                                             vol_state=(ctx or {}).get("vol"),
                                             trend=(ctx or {}).get("trend"))
                    if d.should_exit:
                        cond = str(d.exit_reason or "").split(" ")[0].split(":")[0]
                        intent = Intent("CLOSE", d.exit_reason, cond, pnl_pct=pnl)
                    elif d.new_trail_stop is not None:
                        intent = Intent("TRAIL", f"trail -> {d.new_trail_stop:.2f}", "trail",
                                        trail=d.new_trail_stop, pnl_pct=pnl)
                except Exception as exc:                        # noqa: BLE001
                    logger.warning("[manage] calculator raised for %s: %s — holding this tick",
                                   str(record.get("trade_id", ""))[:8], exc)
            if intent is None:
                intent = Intent("HOLD", "", "", pnl_pct=pnl)

            # ── the row: what fired, or what would fire next tick ──────────
            head = (f"{strategy} {record.get('option_side', '')} "
                    f"{'credit ' if credit else ''}{_n(entry)} -> now {_n(prem)} ({pnl:+.0%})")
            t.check("fired", 1.0 if intent.action == "CLOSE" else 0.0, None)
            if intent.action == "CLOSE":
                t.hold(f"{head}: CUT — {intent.reason}", verdict="CLOSE")
            elif intent.action == "TRAIL":
                t.hold(f"{head}: {intent.reason}; " + self._next_tick_line(record, credit, stop_p, ustop,
                                                                          intent.trail, target),
                       verdict="TRAIL")
            else:
                t.hold(f"{head}: holding — " + self._next_tick_line(
                    record, credit, stop_p, ustop, _f(record.get("trail_stop")), target))
            if ctx is not None:
                self._vector(ctx, strategy, record)
            return intent
        except Exception as exc:                                # noqa: BLE001
            logger.warning("[manage] decide() raised for %s: %s — the engine decides",
                           str(record.get("trade_id", ""))[:8], exc)
            return None

    @staticmethod
    def _next_tick_line(record, credit, stop_p, ustop, trail, target) -> str:
        outs = []
        if stop_p and str(record.get("strategy", "")) != "TrendCreditSpread":
            outs.append(f"premium {'>=' if credit else '<='} {stop_p:.2f} -> out (floor)")
        if ustop:
            side = str(record.get("option_side", "") or "")
            if not credit and record.get("direction") in ("long", "short"):
                thru = "<" if record.get("direction") == "long" else ">"
            else:
                thru = "<" if side == "put" else ">"
            outs.append(f"1m close {thru} {ustop:.2f} -> out (breach)")
        if trail:
            outs.append(f"premium <= {trail:.2f} -> out (trail)")
        if target and not credit:
            outs.append(f"premium >= {target:.2f} -> out (target)")
        if credit:
            outs.append("value <= nickel -> out")
        return "; ".join(outs) if outs else "no exit condition readable"

    def _readings(self, t, rec, price) -> None:
        entry = _f(rec.get("entry_premium")) or 0.0
        prem = _f(rec.get("current_premium"))
        t.check("premium", prem, None)
        t.check("entry_premium", entry or None, None)
        t.check("stop_premium", _f(rec.get("stop_premium")), None)
        t.check("trail_stop", _f(rec.get("trail_stop")), None)
        t.check("target_premium", _f(rec.get("target_premium")), None)
        ustop = _f(rec.get("underlying_stop"))
        t.check("underlying_stop", ustop, None)
        t.check("ticks_held", int(rec.get("excursion_ticks") or 0), None)
        if ustop and price:
            t.check("dist_to_stop", round(float(price) - ustop, 4), None)
            t.anchor(invalidation=ustop)
        mfe, mae = _f(rec.get("mfe_premium")), _f(rec.get("mae_premium"))
        if mfe is not None and entry > 0:
            t.check("mfe_pct", (mfe - entry) / entry, None)
        if mae is not None and entry > 0:
            t.check("mae_pct", (mae - entry) / entry, None)

    # ══════════════════════════════════════════════════════════════════════
    def tick(self, ctx: dict, records, current_price: float) -> int:
        """One row per open record. Returns rows written. Never raises."""
        n = 0
        for rec in (records or []):
            try:
                if self._one(ctx, rec, current_price):
                    n += 1
            except Exception as exc:                            # noqa: BLE001
                logger.debug("[manage] row skipped for %s: %s",
                             str(rec.get("trade_id", ""))[:8], exc)
        return n

    def _one(self, ctx: dict, rec, price: float) -> bool:
        strategy = str(rec.get("strategy", "") or "")
        if not strategy or strategy == "ADOPTED":
            return False
        if covers(rec, ctx.get("_open_records")):
            return False                # decide() wrote this record's row
        conds = EXIT_CONDITIONS.get(strategy)
        plan = self._plan(strategy)
        t = plan.tick(price, str(rec.get("option_side", "") or ""))

        # ── the readings — the record's own fields, the exit engine's state ─
        entry = _f(rec.get("entry_premium")) or 0.0
        prem = _f(rec.get("current_premium"))
        stop_p = _f(rec.get("stop_premium"))
        trail = _f(rec.get("trail_stop"))
        target = _f(rec.get("target_premium"))
        ustop = _f(rec.get("underlying_stop"))
        mfe = _f(rec.get("mfe_premium"))
        mae = _f(rec.get("mae_premium"))
        ticks = int(rec.get("excursion_ticks") or 0)
        credit = bool(rec.get("is_credit_vertical")) or strategy in (
            "SweepCreditSpread", "TrendCreditSpread", "IronCondorStrategy")
        pnl = None
        if prem is not None and entry > 0:
            pnl = (entry - prem) / entry if credit else (prem - entry) / entry
        t.check("premium", prem, None)
        t.check("entry_premium", entry or None, None)
        t.check("pnl_pct", pnl, None)
        t.check("stop_premium", stop_p, None)
        t.check("trail_stop", trail, None)
        t.check("target_premium", target, None)
        t.check("underlying_stop", ustop, None)
        t.check("ticks_held", ticks, None)
        if ustop and price:
            t.check("dist_to_stop", round(float(price) - ustop, 4), None)
            t.anchor(invalidation=ustop)
        if mfe is not None and entry > 0:
            t.check("mfe_pct", (mfe - entry) / entry if not credit else (entry - mfe) / entry, None)
        if mae is not None and entry > 0:
            t.check("mae_pct", (mae - entry) / entry if not credit else (entry - mae) / entry, None)

        if conds is None:
            t.hold(f"{strategy}: no declared exit conditions — the exit engine's "
                   f"default route applies; premium {_n(prem)} vs entry {_n(entry)}")
            self._vector(ctx, strategy, rec)
            return True

        # ── "if this or this -> out", from the declared conditions ─────────
        outs = []
        for name in conds:
            if name in ("hard_stop", "premium_stop", "stop") and stop_p:
                outs.append(f"premium {'>=' if credit else '<='} {stop_p:.2f} -> out ({name})")
            elif name in ("structure_stop", "breach", "acceptance") and ustop:
                # the side price must CLOSE ON to hurt this structure: a long
                # debit or a put credit spread is hurt below the level; a
                # short debit or a call credit spread above it
                side = str(rec.get("option_side", "") or "")
                if not credit and rec.get("direction") in ("long", "short"):
                    thru = "<" if rec.get("direction") == "long" else ">"
                else:
                    thru = "<" if side == "put" else ">"
                outs.append(f"1m close {thru} {ustop:.2f} -> out ({name})")
            elif name == "trail":
                outs.append(f"premium <= {trail:.2f} -> out (trail armed)" if trail
                            else "trail not armed yet")
            elif name == "target" and target:
                outs.append(f"premium >= {target:.2f} -> out (target)")
            elif name == "nickel":
                outs.append("value at the nickel -> out (nickel)")
            elif name == "ladder":
                outs.append("see CondorManagement (roll / tent / close)")
        head = (f"{strategy} {rec.get('option_side', '')} "
                f"{'credit ' if credit else ''}{_n(entry)} -> now {_n(prem)}"
                + (f" ({pnl:+.0%})" if pnl is not None else "")
                + (f", MFE {_n(mfe)}" if mfe is not None else "")
                + f", {ticks} ticks")
        t.hold(f"{head}: " + "; ".join(outs) if outs else f"{head}: holding")
        self._vector(ctx, strategy, rec)
        return True

    def _vector(self, ctx: dict, strategy: str, rec) -> None:
        """The r66 derived vector, recorded for the OPEN position — phase
        'manage' in strategy_note's outcome column, trade_id attached."""
        w = self._notes(ctx)
        if w is None:
            return
        try:
            w.write(strategy, ctx, fired=False, outcome="manage",
                    trade_id=str(rec.get("trade_id", "") or ""))
        except Exception:                                      # noqa: BLE001
            pass


_PLAN: Optional[ManagementPlan] = None


def get_management_plan() -> ManagementPlan:
    global _PLAN
    if _PLAN is None:
        _PLAN = ManagementPlan()
    return _PLAN
