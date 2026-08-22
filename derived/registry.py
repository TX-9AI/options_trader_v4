"""
derived/registry.py  v4.0
Builds the engine set for one box. The single place main.py touches.

v4.0  2026-08-22  See docs/DERIVED_STORES.md.

⚠️ ONE ASSEMBLY POINT, DELIBERATELY. `ctx["chain"]` and `ctx["gex"]` are
written at main.py:2746 INSIDE the dispatch path, so their availability
depends on where in the tick you stand — the same input present for one
consumer and absent for another. Every derived port is built HERE so that
cannot happen to any of them.

⚠️ RETURNS AN EMPTY LIST IF THE STORE WILL NOT OPEN. Derivers are contributors,
never gates: a box with no derived store trades exactly as it does today.
"""

from __future__ import annotations

import logging
from typing import List

logger = logging.getLogger(__name__)


def build_engines(symbol: str) -> List:
    """Every derived engine for this box, or [] if the store is unavailable."""
    try:
        from data.derived_store import get_derived_store
        store = get_derived_store()
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("derived registry: store import failed: %s", exc)
        return []
    if store is None:
        logger.warning("derived registry: no store — derived values will not "
                       "be recorded this session; trading is unaffected")
        return []
    try:
        from derived.indicators import IndicatorEngine
        from derived.forks import ForkEngine
        from derived.levels import LevelEngine
        from derived.surface import SurfaceEngine
        from derived.snapshot import SnapshotEngine
        from derived.counterfactual import CounterfactualExitEngine
        from derived.notes import NotesEngine
        from derived.plan_ledger import PlanLedger
        from derived.character_engine import CharacterEngine
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("derived registry: engine import failed: %s", exc)
        return []

    levels = LevelEngine(store, symbol)
    return [
        IndicatorEngine(store, symbol),
        ForkEngine(store, symbol),
        levels,
        SurfaceEngine(store, symbol),
        SnapshotEngine(store, symbol, levels=levels),
        # ⚠️ RECORDS ONLY — evaluates a flow exit on every open
        # position and writes when it WOULD have fired. The
        # mechanical stop is untouched. See the module docstring
        # for why the burden of proof here is high (bos_exit).
        CounterfactualExitEngine(store, symbol),
        # ⚠️ EVENT-DRIVEN, not per-tick: one row per STRATEGY
        # EVALUATION — fired AND declined — written from main's
        # dispatch hook after the decision is already made.
        NotesEngine(store, symbol),
        # ⚠️ CHARACTER IS A STATE WITH DURATION — it records
        # TRANSITIONS, not per-tick samples, and gates nothing.
        CharacterEngine(store, symbol),
    ]


def snapshot_engine(engines):
    """The SnapshotEngine out of a built set, or None."""
    for e in engines or []:
        if getattr(e, "name", "") == "snapshot":
            return e
    return None


def plan_ledger(symbol: str):
    """The plan ledger for this box, or None.

    ⚠️ NOT AN ENGINE — it is EVENT-DRIVEN (a plan opens when a strategy
    decides, transitions when a leg fills). Modelling it as a tick engine
    would either miss transitions or invent them.
    """
    try:
        from data.derived_store import get_derived_store
        from derived.plan_ledger import PlanLedger
        from derived.character_engine import CharacterEngine
        store = get_derived_store()
        return PlanLedger(store, symbol) if store is not None else None
    except Exception:                                           # noqa: BLE001
        return None
