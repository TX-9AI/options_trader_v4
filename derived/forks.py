"""
derived/forks.py  v4.0
Owns `fork_series`. Tier 2 — regressive, and dies on restart today.

v4.0  2026-08-22  See docs/DERIVED_STORES.md.

The pitchfork reaches back 60-80 bars to find its anchors and currently lives
in a **process-resident cache** (`pitchfork_observer._cache`). Three costs, all
of which the r59 investigation ran straight into:

  · It dies on every deploy. The 10:39 restart on 2026-08-21 is the same class
    of loss that wiped confirmed ORB setups on four boxes.
  · Nobody can see what it decided. When the condor said "rails=absent" all day
    there was no way to ask what fork it had at 10:15 — the diagnosis had to be
    reconstructed synthetically in a sandbox, which is why it was WRONG TWICE.
  · Rejections are computed and thrown away.

🔴 THE REJECTION REASONS ARE THE POINT. `pitchfork.py` names six —
FRAME_TOO_SHORT, NOT_ANCHOR_TF, NO_ATR, NO_CONTAINED_WINDOW, RECENCY,
SEPARATION — and **not one reaches storage or a log.** "No usable daily
pitchfork (rails=absent)" was a single undifferentiated message covering six
different problems, printed on every box on every tick of a zero-trade session.

⚠️ A REJECTION IS A ROW, NOT A SKIPPED WRITE. `built=0` with the reason and the
scan depth. A table that only records successes cannot answer "why not", which
is the question actually being asked when the condor stands down.

⚠️ CONDOR ANCHOR IS 1h — operator ruling 2026-08-22. The daily fork demands an
excursion between anchors that a single session rarely meets, so gating on it
produces a permanent no-trade rather than a guardrail. Both frames are recorded
here regardless; the ruling decides what the CONDOR reads, not what we keep.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from derived.base import DerivedEngine

logger = logging.getLogger(__name__)

# Both anchor frames are recorded. Keeping the one the condor does not read
# costs almost nothing and means a later ruling change has history behind it.
FRAMES = ("1h", "1d")


def _f(v) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


class ForkEngine(DerivedEngine):
    name = "forks"
    table = "fork_series"
    # The scan is the expensive part of this file; 60s is far finer than the
    # rate at which a 1h fork's geometry can meaningfully change.
    min_interval_s = 60.0

    def __init__(self, store=None, symbol: str = ""):
        super().__init__(store)
        self.symbol = symbol

    def derive(self, ctx: dict) -> int:
        store = self._store
        if store is None:
            return 0
        sym = self.symbol or ctx.get("symbol") or ""
        data = ctx.get("data") or {}
        if not sym or not data:
            return 0

        from analysis import pitchfork as pf

        now = time.time()
        rows = []
        for tf in FRAMES:
            df = data.get(tf)
            if df is None or getattr(df, "empty", True):
                # ⚠️ RECORDED, NOT SKIPPED. "the frame was not there" is a
                # DIFFERENT failure from "the geometry did not qualify", and
                # on 2026-08-21 the 1d frame was absent from the warehouse
                # entirely — a fact that took hours to establish because
                # nothing wrote it down.
                rows.append((sym, tf, now, 0, "NO_FRAME", 0, None,
                             None, None, None, None, None, None, None, None,
                             None, None, None, None, None, None))
                continue
            try:
                atr = float((df["high"] - df["low"]).tail(20).mean())
            except Exception:                                   # noqa: BLE001
                atr = 0.0
            fork = None
            try:
                fork = pf.build_fork_contained(sym, df, tf, atr)
            except Exception as exc:                            # noqa: BLE001
                logger.debug("fork build raised for %s %s: %s", sym, tf, exc)
            reason = None
            try:
                reason = pf.last_reject_reason()
                depth = pf.last_scan_depth()
            except Exception:                                   # noqa: BLE001
                depth = 0

            if fork is None:
                rows.append((sym, tf, now, 0, reason or "UNKNOWN", depth,
                             None, None, None, None, None, None, None,
                             None, None, None, None, None, None, None, None))
                continue

            # Built. Record the anchors so the fork can be REDRAWN later from
            # the row alone — a fork you cannot reconstruct is a number, not a
            # measurement.
            # ⚠️ FIELD NAMES READ FROM THE DATACLASS, NOT ASSUMED. Fork carries
            # p0/p1/p2 as named Pivots (idx, price, kind, k, timeframe) and has
            # NO containment/span/upper/median/lower attributes — the first
            # draft of this file invented all five. Containment and span live
            # inside `filters_passed` as tags like ("CONTAINMENT_0.96",
            # "SPAN_71"), so they are parsed out rather than read.
            def pv(pt, attr):
                try:
                    return _f(getattr(pt, attr))
                except Exception:                               # noqa: BLE001
                    return None
            contain, span = None, None
            for tag in (getattr(fork, "filters_passed", None) or ()):
                t = str(tag)
                if t.startswith("CONTAINMENT_"):
                    contain = _f(t.split("_", 1)[1])
                elif t.startswith("SPAN_"):
                    try:
                        span = int(t.split("_", 1)[1])
                    except (TypeError, ValueError):
                        span = None
            rows.append((
                sym, tf, now, 1, None, depth,
                getattr(fork, "direction", None),
                pv(getattr(fork, "p0", None), "idx"),
                pv(getattr(fork, "p0", None), "price"),
                pv(getattr(fork, "p1", None), "idx"),
                pv(getattr(fork, "p1", None), "price"),
                pv(getattr(fork, "p2", None), "idx"),
                pv(getattr(fork, "p2", None), "price"),
                _f(getattr(fork, "origin_idx", None)),
                _f(getattr(fork, "origin_price", None)),
                _f(getattr(fork, "slope", None)),
                contain, span,
                # The rails themselves are a projection at a given bar index,
                # not stored state — left NULL here and computed on read from
                # origin + slope, which the row fully determines.
                None, None, None,
            ))
        return store.append_forks(rows)
