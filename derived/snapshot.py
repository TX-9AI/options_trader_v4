"""
derived/snapshot.py  v4.1
v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

Owns `fire_snapshot`. Everything derived at the instant a trade fired.

v4.0  2026-08-22  See docs/DERIVED_STORES.md.

🔴 THE OPERATOR'S PURPOSE, 2026-08-22: if shadow observers are rebuilt on this
repo it is to study **which derived indicators reveal any usable edge** — so
what is wanted is a snapshot of everything available at the moment of the fire.

That makes the study a JOIN:

    fire_snapshot JOIN trades ON trade_id

Derived indicators on one side, outcome and excursion on the other. "Did high
charm at fire predict a larger MFE?" becomes one query. Today it cannot be
asked at all.

⚠️ EXCURSION TELEMETRY IS UNAFFECTED AND LIVES ON A DIFFERENT AXIS.
`mfe_premium` / `mfe_bars` / `mae_premium` / `mae_bars` are properties of the
trade's LIFE and stay on `trades`. This is one frozen instant at entry.
Different clocks, different tables, no collision — and the join is what makes
excursion work BETTER than it does today.

recorded label plus conviction and dropped every term that actually decided the
entry — so the journal had a vocabulary of two for a decision made on twenty.
If the point is DISCOVERING which indicator reveals edge, pre-selecting the
columns defeats the exercise before it starts.

⚠️ ABSENCE IS RECORDED EXPLICITLY. A value that was unavailable at fire time is
written as null — NEVER omitted, NEVER zero. A missing indicator and an
indicator that measured zero are different facts, and the whole VW.1 saga was
that distinction going wrong across five layers.

⚠️ WHY A JSON PAYLOAD RATHER THAN COLUMNS. The indicator set will keep growing
— order of 60-100 fields — and every addition would otherwise be a migration on
a table that already carries 75 columns and an `entry_snapshot` JSON escape
hatch. `trades` stays about the trade; this stays about the world at that
moment. Promote a field to a real column when a study proves it earns one.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Optional

from derived.base import DerivedEngine

logger = logging.getLogger(__name__)


def _f(v) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


class SnapshotEngine(DerivedEngine):
    name = "snapshot"
    table = "fire_snapshot"

    def __init__(self, store=None, symbol: str = "", levels=None):
        super().__init__(store)
        self.symbol = symbol
        self._levels = levels          # LevelEngine, for the provenance walk

    def build_payload(self, ctx: dict) -> dict:
        """Every derived value we can see right now. Keys ALWAYS present.

        ⚠️ EVERY KEY IS EMITTED EVEN WHEN NULL. A caller — or a study three
        months from now — can then tell "measured as absent" from "this field
        did not exist yet in that era", which an omitted key cannot express.
        """
        trend, vol = ctx.get("trend"), ctx.get("vol")
        price = _f(ctx.get("price"))

        payload = {
            "schema": 1,
            "ts": time.time(),
            "price": price,
            # ── tier 1: path-dependent
            "adx": _f(getattr(trend, "primary_adx", None)) if trend else None,
            "atr": _f(getattr(vol, "atr_current", None)) if vol else None,
            "atr_normalized": _f(getattr(vol, "atr_normalized", None)) if vol else None,
            "bb_width_pct": _f(getattr(vol, "bb_width_pct", None)) if vol else None,
            "vwap": _f(getattr(vol, "vwap", None)) if vol else None,
            "price_vs_vwap": _f(getattr(vol, "price_vs_vwap", None)) if vol else None,
            # ── tier 4: second-order + vol measures
            "charm": _f(ctx.get("charm")),
            "vanna": _f(ctx.get("vanna")),
            "gex": _f(ctx.get("gex")),
            "atm_iv": _f(ctx.get("atm_iv")),
            "iv_slope": _f(ctx.get("iv_slope")),
            "realised_vol_cc": _f(ctx.get("realised_vol_cc")),
            "realised_vol_parkinson": _f(ctx.get("realised_vol_parkinson")),
            "variance_risk_premium": _f(ctx.get("variance_risk_premium")),
            "expected_move_iv": _f(ctx.get("expected_move_iv")),
            "expected_move_straddle": _f(ctx.get("expected_move_straddle")),
            "session_fraction_remaining": _f(ctx.get("session_fraction_remaining")),
            # ── context
            "trend_direction": getattr(trend, "overall_direction", None) if trend else None,
            "gap_pct": _f(ctx.get("gap_pct")),
        }

        # The level walk WITH PROVENANCE — nearest levels each way and their
        # touch scores. This is the operator's own framing of what price is
        # trading into, and it has never been recorded at fire time.
        walk = None
        try:
            if self._levels is not None and price:
                walk = self._levels.walk(price, limit=3)
        except Exception as exc:                                # noqa: BLE001
            logger.debug("snapshot: level walk unavailable: %s", exc)
        payload["levels"] = walk           # null if unavailable, never {}

        # Fork state at fire, both frames — including WHY it was absent.
        fork = None
        try:
            fork = ctx.get("fork_state")
        except Exception:                                       # noqa: BLE001
            pass
        payload["fork"] = fork
        return payload

    def capture(self, trade_id: str, ctx: dict) -> int:
        """Write the snapshot for a fired trade. Returns rows written.

        ⚠️ CALLED FROM THE TRADE WRITE PATH so the snapshot and the trade row
        land together. A trade with no snapshot is a hole in the study; a
        snapshot with no trade is an orphan.
        ⚠️ NEVER RAISES — the base class wraps `run`, and this path is wrapped
        too, because a study artifact must never be able to fail a fill.
        """
        store = self._store
        if store is None or not trade_id:
            return 0
        try:
            payload = self.build_payload(ctx)
            return store.write_fire_snapshot(
                trade_id, self.symbol or ctx.get("symbol") or "",
                json.dumps(payload, default=str))
        except Exception as exc:                                # noqa: BLE001
            logger.warning("[derived:snapshot] capture failed for %s: %s — the "
                           "trade is unaffected; this study row is absent",
                           trade_id, exc)
            return 0

    def derive(self, ctx: dict) -> int:
        """Nothing per-tick. This engine is event-driven — see `capture`."""
        return 0
