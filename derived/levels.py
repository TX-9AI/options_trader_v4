"""
derived/levels.py  v4.2
Owns `level_ledger`. Tier 3 — stateful; the object has a biography.

v4.2  2026-09-12  r376 — LVL.6: THE 1h TINES COME FROM THE OBSERVER, WHICH
      IS THE RULING FINALLY REACHING THE CODE. r367 ruled that of the two
      live 1h pitchfork builders the OBSERVER informs and `ForkEngine`
      goes LOG-ONLY — and its code half changed only the observer's
      journal fields. This engine went on binding `ForkEngine` and
      `tines_now()` went on reading its `last_forks["1h"]`, so THE BOARD
      WAS INFORMED BY THE BUILDER RULED OUT OF THE DECISION PATH for nine
      revisions. It cost nothing only because nothing decides on the
      board yet — the RULED-but-not-BUILT gap, the same shape as LVL.4's
      row reading DONE while the fleet ran the old code.
      🔑 THE RAILS ARE STASHED IN `derive()`, not looked up in
      `tines_now()`: `rails_for` needs `ctx` and `tines_now(price)` has
      none, and the registry already runs derive() before anything reads
      the board. A failed or absent read stashes None and never a stale
      value, so "no fork" stays one of the four distinct answers.
      ⚠️ ForkEngine's 1h IS NOT REMOVED — still computing, still writing
      `fork_series`. That is the log-only half and the other side of the
      month-long comparison r367 started; deleting it would end the study.
      ⚠️ PF.4 — the `tines_now` docstring claimed `pitchfork_lifecycle`
      invalidates a broken rail. That module is imported by NOTHING; the
      line was written in r364 and named a guarantee no running code
      provides. What actually clears a dead fork is the builder returning
      nothing on the next read, measured at 37% of 1h samples — the
      behaviour was real and the mechanism was misattributed.

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
        self._forks = forks            # r364 — ForkEngine; 1d only since r376
        # r376 / LVL.6 — the OBSERVER's 1h rails, restashed every derive().
        # None until the first tick, and None again the moment the fork dies.
        self._obs_rails = None

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

        # ── 🔴 r376 / LVL.6 — THE 1h TINES COME FROM THE OBSERVER NOW ────────
        # OPERATOR'S RULING, r367: of the two live 1h pitchfork builders, the
        # OBSERVER informs and ForkEngine's 1h goes LOG-ONLY. That was recorded
        # and the code never moved — this engine went on taking its tines from
        # `ForkEngine.last_forks["1h"]`, so the board was informed by the
        # builder ruled out of the decision path. Nothing decided on it, which
        # is the only reason it cost nothing.
        # 🔑 STASHED HERE BECAUSE `rails_for` NEEDS ctx AND `tines_now` HAS NO
        # ctx. The registry runs derive() every tick before anything reads the
        # board, which is the same ordering that already guarantees the board
        # prices its tines from THIS tick's fork and never the previous one.
        # ⚠️ ForkEngine's 1h IS NOT REMOVED — it keeps computing and keeps
        # writing `fork_series`, which is the log-only half of the ruling and
        # the other side of the month-long comparison r367 started. Its 1d and
        # the condor's 1d are untouched.
        # ⚠️ A FAILED OR ABSENT READ STASHES None, NOT A STALE VALUE. "No fork"
        # is one of the board's four distinct answers and must stay reachable:
        # out of sight, out of mind.
        self._obs_rails = None
        try:
            from analysis.pitchfork_observer import rails_for
            self._obs_rails = rails_for(ctx, sym, "1h")
        except Exception as exc:                                # noqa: BLE001
            logger.debug("levels: observer 1h rails unavailable: %s", exc)

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
        a stored level: a rail is `origin_price + slope * (idx - origin_idx)`, a
        FUNCTION, and the map is computed at read time. A dead fork yields
        nothing on the next read — no row to go stale, no encounter to
        de-conflict.

        🔴 r376 / LVL.6 — THE SOURCE IS THE OBSERVER, WHICH IS THE RULING
        FINALLY REACHING THE CODE. Two builders ran the same algorithm on the
        same 1h frame: `ForkEngine` (20-bar high-minus-low ATR) fed this board,
        and `pitchfork_observer` (14-bar true-range ATR) fed the condor AND the
        sweep. The ATR is not cosmetic — it scales the containment tolerance
        that SELECTS the window, so the two can hold structurally different
        forks from identical bars. r367 ruled the observer informs and
        ForkEngine's 1h goes log-only; the row was written and the binding was
        not changed, so until now the board read the builder ruled out of the
        decision path. It cost nothing only because nothing decides on the
        board yet.
        ⚠️ ForkEngine KEEPS ITS 1h — still computing, still writing
        `fork_series`. That is the log-only half, and it is the other side of
        the comparison r367 started; deleting it would end the study.

        ⚠️ A TINE HAS A RATE, A LEVEL HAS A PRICE. `bars_to_contact` is the
        convergence at a STANDING price — the tine closing on us, not a
        forecast of price — and it is None when the two diverge.

        ⚠️ THE ROLES ARE GEOMETRIC AND NOT NEGOTIABLE (operator, 2026-09-12:
        *"the pitchfork tines have geometric restrictions on S/R — a top tine
        can NEVER be support"*). Upper is a ceiling, lower is a floor,
        regardless of where price sits; only the MEDIAN takes its role from the
        side price is on. And a tine's authority is DEFINITIONAL — it carries
        no touch count, because unlike a horizontal level it does not earn
        standing by being defended.

        ⚠️ NO LIFECYCLE MODULE STANDS BEHIND THIS, AND THE PREVIOUS VERSION OF
        THIS DOCSTRING SAID OTHERWISE (PF.4, §0 correction). It read *"the
        projection is valid while the fork is — `pitchfork_lifecycle`
        invalidates a broken rail"*. `analysis/pitchfork_lifecycle.py` is
        imported by NOTHING; `ForkTracker` is never instantiated in the live
        path, and the repo's own generated map lists the module as an orphan. I
        wrote that line in r364 and it named a guarantee no running code
        provides. What actually clears a dead fork is this function returning
        nothing when the builder has none — measured at 37% of 1h samples — so
        the behaviour is real and the mechanism was misattributed.
        """
        r = self._obs_rails
        if not r:
            return []
        slope = _f(r.get("slope")) or 0.0
        out = []
        for name, key in (("fork1h/upper", "upper"),
                          ("fork1h/median", "median"),
                          ("fork1h/lower", "lower")):
            p = _f(r.get(key))
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
