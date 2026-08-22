"""
derived/levels.py  v4.0
Owns `level_ledger`. Tier 3 — stateful; the object has a biography.

v4.0  2026-08-22  See docs/DERIVED_STORES.md.

🔴 THE OPERATOR'S RULING, 2026-08-22:
    "In a live session a touch count is a HELD level, and when it doesn't
     hold, that level is FINISHED."

A touch is a HOLD. `touch_count` is the length of a run that TERMINATES at the
break — not a score that accumulates forever.

⚠️ THE EXISTING CODE DOES NOT MODEL THIS. `LiquidityPool` carries `touch_count`
and `swept` as separate fields, so a pool can read five-touch AND swept at the
same time — the count survives its own invalidation. Here the break is a
RECORDED EVENT: `retired_ts` + `retired_reason`, after which the level is
history and stops competing for attention.

🔴 BODIES DECIDE, WICKS TEST — universal convention, operator 2026-08-22, taken
from the sweep rules whose own doctrine says it plainly:
    `closes_beyond >= ACCEPT_CLOSES` is no longer a sweep — it is a BREAKOUT.
A wick through a level is a TEST. A close through is ACCEPTANCE.
⚠️ MEASURED, NOT INVENTED: closes_beyond >= 2 blocked 64.5% of named-pool
sweeps (2026-08-15). And it already fixed this exact defect once — the old
`rejection_pct` measured wick-to-last-close and STAMPED A BREAKOUT AS A
CONFIRMED SWEEP, which is precisely the error a wick-based rule produces.

🔴 NY IS THE DANGEROUS SESSION and the operator has been bitten by it. It is
the only session that is LIVE while being traded; Asia and London are closed
and final by the time an RTH box reads them. So "store once at session close"
is WRONG for NY. The resolution is the operator's own framing: **do not read
session fields at all.** Walk outward from price and report the first level
each way WITH ITS PROVENANCE — the session becomes a LABEL ON THE ANSWER, not
the query. A still-forming NY high that is nearest above genuinely IS the level
that matters, because that is where the stops are. `is_live_session` marks it
as still forming so nothing mistakes it for settled.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from derived.base import DerivedEngine

logger = logging.getLogger(__name__)

# A close beyond by less than this is inside the noise of the level itself.
TOUCH_TOL_PCT = 0.0015
# Closes through required before the level is retired. Inherited from the
# sweep rules, where it was MEASURED rather than chosen.
ACCEPT_CLOSES = 2


def _f(v) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def _level_id(symbol: str, provenance: str, price: float) -> str:
    """Stable identity so touches land on the SAME row across ticks.

    ⚠️ ROUNDED INTO THE ID ON PURPOSE. A level is a zone, not a float; without
    rounding, a price that wobbles in the fifth decimal creates a NEW level
    every tick and every one of them has touch_count=1 — which would silently
    destroy the entire premise of scoring by touches.
    """
    return f"{symbol}:{provenance}:{price:.2f}"


class LevelEngine(DerivedEngine):
    name = "levels"
    table = "level_ledger"
    min_interval_s = 0.0

    def __init__(self, store=None, symbol: str = ""):
        super().__init__(store)
        self.symbol = symbol
        self._live: dict = {}          # level_id -> mutable state

    def _sources(self, ctx: dict):
        """(provenance, price, kind, timeframe, is_live) for every known level.

        ⚠️ PROVENANCE TRAVELS WITH THE LEVEL. "Resistance at 218.40, from Asia"
        is a different trade from "resistance at 218.40, from yesterday's
        close", and today the map exposes a bare price with the origin lost.
        """
        liq = ctx.get("liq_map")
        vol = ctx.get("vol")
        out = []
        if liq is not None:
            for attr, prov, kind, live in (
                ("prev_day_high", "prev_day", "resistance", 0),
                ("prev_day_low", "prev_day", "support", 0),
                ("asia_session_high", "asia", "resistance", 0),
                ("asia_session_low", "asia", "support", 0),
                ("london_session_high", "london", "resistance", 0),
                ("london_session_low", "london", "support", 0),
                # NY is LIVE — flagged, never treated as settled.
                ("ny_session_high", "ny", "resistance", 1),
                ("ny_session_low", "ny", "support", 1),
            ):
                p = _f(getattr(liq, attr, None))
                if p and p > 0:
                    out.append((prov, p, kind, "1d" if "prev" in prov else "session", live))
            for pool in (getattr(liq, "pools", None) or []):
                p = _f(getattr(pool, "price", None))
                if p and p > 0:
                    out.append((str(getattr(pool, "name", None) or "pool"), p,
                                str(getattr(pool, "kind", "") or ""),
                                str(getattr(pool, "timeframe", "") or ""), 0))
        # VWAP is a level too and belongs in the same walk — operator.
        if vol is not None:
            p = _f(getattr(vol, "vwap", None))
            if p and p > 0:
                out.append(("vwap", p, "dynamic", "session", 1))
        return out

    def derive(self, ctx: dict) -> int:
        store = self._store
        if store is None:
            return 0
        sym = self.symbol or ctx.get("symbol") or ""
        price = _f(ctx.get("price"))
        if not sym or not price:
            return 0

        # ⚠️ THE LAST CLOSED BAR DECIDES, NOT THE LIVE PRICE. Bodies decide,
        # wicks test — so acceptance is judged on a CLOSE. Using `price`
        # mid-bar would retire levels on wicks, which is the failure the
        # convention exists to prevent.
        close = price
        df = ctx.get("df_5m")
        try:
            if df is not None and not getattr(df, "empty", True):
                close = _f(df["close"].iloc[-1]) or price
        except Exception:                                       # noqa: BLE001
            pass

        now = time.time()
        written = 0
        for prov, lvl_price, kind, tf, live in self._sources(ctx):
            lid = _level_id(sym, prov, lvl_price)
            st = self._live.get(lid)
            if st is None:
                st = {"created": now, "touches": 0, "beyond": 0,
                      "last_touch": None, "retired": None, "reason": None}
                self._live[lid] = st
            if st["retired"]:
                continue                       # finished — operator's ruling

            tol = lvl_price * TOUCH_TOL_PCT
            if kind == "resistance":
                accepted = close > lvl_price + tol
            elif kind == "support":
                accepted = close < lvl_price - tol
            else:
                accepted = False               # VWAP is crossed, not broken

            if accepted:
                st["beyond"] += 1
                if st["beyond"] >= ACCEPT_CLOSES:
                    st["retired"] = now
                    st["reason"] = "ACCEPTED_THROUGH"
            elif abs(close - lvl_price) <= tol:
                # Held at the level — that is a TOUCH.
                st["touches"] += 1
                st["last_touch"] = now
                st["beyond"] = 0               # the run of acceptance is broken

            store.upsert_level((lid, sym, lvl_price, kind, prov, tf,
                                st["created"], st["touches"], st["last_touch"],
                                st["beyond"], st["retired"], st["reason"],
                                int(live)))
            written += 1
        return written

    def walk(self, price: float, limit: int = 3):
        """Levels ordered by DISTANCE from price, nearest first, with grade.

        🔴 THE OPERATOR'S OWN FRAMING: walk up from where price is until you
        hit the last session high — which could be overnight, previous day or
        previous session — and the same going down. **The session is a label on
        the answer, not the query.** That is what makes the live NY high safe
        to use: if it is nearest above, it IS the level that matters.

        ⚠️ DISTANCE ORDERS, TOUCH COUNT SCORES. The nearest level may be a
        one-touch artifact while the one 0.4% beyond has held five times — that
        is the whole distinction between trading into something and trading
        into noise.
        """
        if self._store is None or not price:
            return {"above": [], "below": []}
        try:
            cur = self._store.conn.execute(
                "SELECT price, kind, provenance, touch_count, is_live_session"
                " FROM level_ledger WHERE symbol=? AND retired_ts IS NULL",
                (self.symbol,))
            rows = cur.fetchall()
        except Exception:                                       # noqa: BLE001
            return {"above": [], "below": []}
        above = sorted([r for r in rows if r[0] > price], key=lambda r: r[0] - price)
        below = sorted([r for r in rows if r[0] < price], key=lambda r: price - r[0])
        def fmt(r):
            return {"price": r[0], "kind": r[1], "provenance": r[2],
                    "touches": r[3], "live": bool(r[4]),
                    "dist_pct": abs(r[0] - price) / price * 100.0}
        return {"above": [fmt(r) for r in above[:limit]],
                "below": [fmt(r) for r in below[:limit]]}
