"""
derived/levels.py  v4.1
Owns `level_ledger`. Tier 3 — stateful; the object has a biography.

v4.1  2026-09-12  r364 — ONE VOCABULARY, AND NOTHING INSIDE THE OPENING RANGE.
      (1) A POOL NOW ENTERS BY SIDE. `level_ledger.kind` is declared
      `support / resistance`; the session extremes honoured that and pools
      transcribed the DETECTOR's word, `high`/`low`. Measured 2026-09-11 on the
      warehouse: of 786 rows across four symbols, every `PDH*`, `PDL*` and
      `* High|Low (R*)` carried `high`/`low` — so the entire R1/R2/R3 ladder was
      invisible to any kind-filtered reader, which is exactly what OTV4TEST's
      `live_levels` is. The side is the fact a consumer needs; the biography
      still decides when it stops being true.
      (2) TRAVERSED — once the opening range exists, a level inside it is spent
      and retires, because price has already been through it. Inert before the
      range exists: an absent bound must never retire anything.
      (3) `board()` and `tines_now()` — the one map a plan reads: three held
      levels beyond each range edge by geometry, plus the 1h fork's rails
      computed AT READ TIME with slope and bars-to-contact. A tine is never
      stored, so a dead fork leaves no stale rail behind.
      Gated by tests/check_level_vocabulary.py and tests/check_level_board.py.

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

    def __init__(self, store=None, symbol: str = "", forks=None):
        super().__init__(store)
        self.symbol = symbol
        self._live: dict = {}          # level_id -> mutable state
        self._forks = forks            # r364 — ForkEngine, for tine prices

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
            # 🔴 r364 — A POOL ENTERS IN THE CATALOGUE'S OWN VOCABULARY.
            # `level_ledger.kind` is declared `support / resistance`
            # (data/derived_store.py:130) and the session extremes above already
            # honour it — pools transcribed the DETECTOR's word instead, `high`
            # / `low`, so PDH, PDL and the whole R1/R2/R3 ladder entered the
            # store speaking a language no kind-filtered reader asks for.
            # 📊 MEASURED 2026-09-11 on the warehouse: of 786 level rows across
            # four symbols, EVERY `PDH*`, `PDL*` and `* High|Low (R*)` row
            # carried `high` or `low`. OTV4TEST's `live_levels` filters
            # `kind IN ('support','resistance')` and therefore sees none of the
            # ladder its own strategy is specified to hunt.
            # ⚠️ THE SIDE IS THE FACT A CONSUMER NEEDS, not the formation: a
            # pool made by a high is resistance while price sits below it. The
            # biography still decides when that stops being true —
            # ACCEPTED_THROUGH on two closes, TRAVERSED inside the opening range.
            # ⚠️ NO PRICE, NO GUESS, AND NEVER A DROPPED LEVEL: without a live
            # price the formation is the only evidence there is, so high ->
            # resistance and low -> support.
            _px_now = _f(ctx.get("price"))
            for pool in (getattr(liq, "pools", None) or []):
                p = _f(getattr(pool, "price", None))
                if p and p > 0:
                    _formed = str(getattr(pool, "kind", "") or "")
                    if _px_now and _px_now > 0:
                        _side = "resistance" if p > _px_now else "support"
                    else:
                        _side = "resistance" if _formed == "high" else "support"
                    out.append((str(getattr(pool, "name", None) or "pool"), p,
                                _side,
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
        # 🔴 r364 — NO LEVEL INSIDE THE OPENING RANGE (ported from OTV4TEST
        # v4.2, the operator's rule). Once the 09:30 five-minute bar has
        # printed, price has ALREADY been through everything between orb_low
        # and orb_high, so those levels are spent: they retire TRAVERSED and
        # leave every consumer at once rather than sitting in the board as
        # obstacles price demonstrably walked past.
        # ⚠️ BEFORE THE RANGE EXISTS THIS IS INERT — `orb` carries no bounds
        # until the opening bar closes, and a missing bound must never retire
        # a level (an absent range is not a range containing everything).
        _orb = ctx.get("orb")
        _rng_lo = _f(getattr(_orb, "orb_low", None)) if _orb is not None else None
        _rng_hi = _f(getattr(_orb, "orb_high", None)) if _orb is not None else None
        _have_range = bool(_rng_lo and _rng_hi and _rng_hi > _rng_lo)
        for prov, lvl_price, kind, tf, live in self._sources(ctx):
            lid = _level_id(sym, prov, lvl_price)
            st = self._live.get(lid)
            if st is None:
                st = {"created": now, "touches": 0, "beyond": 0,
                      "last_touch": None, "retired": None, "reason": None}
                self._live[lid] = st
            if st["retired"]:
                continue                       # finished — operator's ruling

            # r364 — TRAVERSED. VWAP (`dynamic`) is exempt: it is crossed, not
            # broken, and it is not a level a trade contends with.
            if (_have_range and kind in ("support", "resistance")
                    and _rng_lo <= lvl_price <= _rng_hi):
                st["retired"] = now
                st["reason"] = "TRAVERSED"
                logger.info("[level] %s %s %.2f (%s) retired TRAVERSED — inside "
                            "the opening range %.2f-%.2f",
                            sym, kind, lvl_price, prov, _rng_lo, _rng_hi)
                store.upsert_level((lid, sym, lvl_price, kind, prov, tf,
                                    st["created"], st["touches"], st["last_touch"],
                                    st["beyond"], st["retired"], st["reason"],
                                    int(live)))
                written += 1
                continue

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

    def tines_now(self, price: float):
        """The 1h fork's rails AS A LINE — price now, slope, bars to contact.

        🔴 r364, THE OPERATOR'S RULE: *"as long as there's a fork present, there
        should be a map of its points. And if the fork stops emitting, then the
        map has to go with it... out of sight, out of mind."* So a tine is NEVER
        a stored level: `median_at(idx) = origin_price + slope * (idx -
        origin_idx)` is a function, and the map is computed at read time from
        the fork the ForkEngine holds RIGHT NOW. A dead fork yields nothing on
        the next read — there is no row to go stale and no encounter to
        de-conflict.
        ⚠️ A TINE HAS A RATE, A LEVEL HAS A PRICE. `bars_to_contact` is the
        convergence at a STANDING price — the tine closing on us, not a
        forecast of price — and it is None when the two diverge.
        ⚠️ THE PROJECTION IS VALID WHILE THE FORK IS. `pitchfork_lifecycle`
        invalidates a broken rail; this reports what the structure says today.
        """
        fe = self._forks
        fork = (getattr(fe, "last_forks", {}) or {}).get("1h") if fe is not None else None
        if fork is None:
            return []
        idx = _f((getattr(fe, "last_idx", {}) or {}).get("1h")) or 0.0
        slope = _f(getattr(fork, "slope", None)) or 0.0
        out = []
        for name, fn in (("fork1h/upper", "upper_at"),
                         ("fork1h/median", "median_at"),
                         ("fork1h/lower", "lower_at")):
            try:
                p = _f(getattr(fork, fn)(idx))
            except Exception:                                   # noqa: BLE001
                continue
            if not p or p <= 0:
                continue
            gap = p - (price or 0.0)
            bars = None
            if slope and price:
                b = -gap / slope
                bars = round(b, 2) if b > 0 else None
            out.append({"provenance": name, "price": p,
                        # the tine rule: a top rail can only be a ceiling
                        "kind": "resistance" if name.endswith("upper") else
                                ("support" if name.endswith("lower") else
                                 ("resistance" if price and price < p else "support")),
                        "slope_per_bar": slope, "bars_to_contact": bars,
                        "dist_pct": (abs(gap) / price * 100.0) if price else None})
        return out

    def board(self, price: float, orb_high=None, orb_low=None, limit: int = 3):
        """THE ONE LEVEL MAP A PLAN READS. Held levels outside the opening
        range, by geometry, plus the fork's rails when it exists.

        🔴 r364 — the operator's specification, 2026-09-12: *"3 previously held
        levels above, three previously held levels below and the one hour fork
        tines, if present... invalidating any level that sits within the opening
        range."* The ORB range is the reference, not spot: a level price has
        already traversed is spent (the recorder retires it TRAVERSED), and what
        matters is what stands BEYOND the range in each direction.
        ⚠️ THE LADDER IS MONOTONE BY CONSTRUCTION: ordering by distance from the
        range edge means each rung out is further out than the last, which is
        the operator's *"the next one has to be higher than that one."*
        ⚠️ FEWER THAN THREE IS AN ANSWER, NOT A FAILURE. Near all-time highs
        there may be one above, or none, and `count` says so rather than padding.
        ⚠️ `dynamic` (VWAP) IS NOT A LEVEL A TRADE CONTENDS WITH — it is crossed,
        not broken, and it sits on top of price by construction; a board that
        returned it would answer "the nearest level is 3bp away" every tick.
        ⚠️ FOUR DISTINCT ANSWERS, NEVER MERGED: no store, no range yet, no fork,
        and no level on that side. Silence must never read as clearance.
        """
        out = {"state": "ok", "above": [], "below": [], "tines": [],
               "fork": "absent", "as_of": time.time()}
        if self._store is None or not price:
            out["state"] = "no_store"
            return out
        if not (orb_high and orb_low and orb_high > orb_low):
            out["state"] = "no_range"        # before the opening bar closes
            return out
        try:
            rows = self._store.conn.execute(
                "SELECT price, kind, provenance, touch_count, is_live_session"
                " FROM level_ledger WHERE symbol=? AND retired_ts IS NULL"
                " AND kind IN ('support','resistance')",
                (self.symbol,)).fetchall()
        except Exception:                                       # noqa: BLE001
            out["state"] = "no_store"
            return out
        above = sorted([r for r in rows if r[0] > orb_high], key=lambda r: r[0] - orb_high)
        below = sorted([r for r in rows if r[0] < orb_low], key=lambda r: orb_low - r[0])
        def fmt(r, edge):
            return {"price": r[0], "kind": r[1], "provenance": r[2],
                    "touches": r[3], "live": bool(r[4]),
                    "dist_pct": abs(r[0] - edge) / edge * 100.0}
        out["above"] = [fmt(r, orb_high) for r in above[:limit]]
        out["below"] = [fmt(r, orb_low) for r in below[:limit]]
        out["tines"] = self.tines_now(price)
        out["fork"] = "built" if out["tines"] else "absent"
        out["count"] = {"above": len(out["above"]), "below": len(out["below"]),
                        "tines": len(out["tines"])}
        return out

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
