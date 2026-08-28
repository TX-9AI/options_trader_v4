"""
strategy/management.py  v1.0
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
        "hard_stop":      "premium <= stop_premium (immutable floor set at entry)",
        "structure_stop": "a 1m close through underlying_stop (the ORB boundary)",
        "trail":          "premium <= trail_stop, once the trail has armed",
        "target":         "premium >= target_premium",
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
               "mae_pct", "ticks_held")


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
