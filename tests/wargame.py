#!/usr/bin/env python3
"""
tests/wargame.py  v0.2
v0.2  2026-09-20  r393 / FU.5 — REBUILT TO RUN EXCLUSIVELY ON THE TICK-LEVEL
      FEED. The bar-reconstruction path is GONE, and this is the operator's
      ruling rather than a refactor.

🔴 WHY v0.1'S FOUNDATION WAS WRONG. v0.1 rebuilt 1m bars from `raw/ohlc` and
drove the real engines from them. Its own positive control killed it: of the
26 recorded ORB decision ticks on 2026-09-18, **25 were MID-BAR**. The bot
decides on a ~15s tick; the warehouse stores 1m bars; so at 09:37:15 the live
engine held fifteen seconds of a bar this harness could only supply whole.
Reconstructing the input was never going to work, and the fix is the
operator's own framing — **read what the tick RECORDED instead of rebuilding
what the tick SAW.**

📊 THE STREAMS SHARE ONE CLOCK, MEASURED BEFORE ANY OF THIS WAS BUILT
(AMD 2026-09-18): `plan_tick` 1,754 ticks and `indicator_series` 1,758 ticks,
both at a **median 15.0s cadence**, and the nearest indicator row to a given
plan tick is **median 0.00s away, p90 0.10s, max 4.2s**. They are co-emitted
per tick, so joining them on `ts_epoch` is reading one record rather than
correlating two.

🔑 WHAT THE CONTROL IS NOW, AND WHY IT CHANGED. v0.1 had to prove it could
REPRODUCE a decision, because it was rebuilding the inputs. This harness does
not rebuild anything — the inputs ARE the record — so the thing that can go
wrong is the JOIN: an invented tick, a dropped tick, a silent mismatch. The
control is therefore INTEGRITY: every tick accounted for, every unjoined tick
NAMED, and nothing counted as agreement that was never compared. RPL.2's
ruling carried over unchanged.

⚠️ WHAT THIS HARNESS CANNOT DO, STATED SO IT IS NOT DISCOVERED LATER. It
cannot re-run the ORB STATE MACHINE, because the engine's state is not a field
in any stream — it survives only inside `plan_tick.reason` as PROSE, parseable
on ~24% of ticks. So threshold and discriminator questions are fully
answerable here; "would the engine have ARMED" is not, until the per-tick
logging carries state as a FIELD. That is a production change and is not
assumed by this file.
"""
from __future__ import annotations

import bisect
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))          # repo root — RPL.1's lesson

JOIN_TOL_S = 1.0          # measured p90 is 0.10s; 1.0s is ten times the slack


class Tick:
    """One tick, as the bot recorded it. Nothing here is reconstructed."""

    __slots__ = ("ts", "symbol", "strategy", "verdict", "reason",
                 "underlying", "ind", "checks")

    def __init__(self, ts, symbol, strategy, verdict, reason, underlying):
        self.ts = ts
        self.symbol = symbol
        self.strategy = strategy
        self.verdict = verdict
        self.reason = reason
        self.underlying = underlying
        self.ind = {}
        self.checks = {}

    def get(self, name, default=None):
        """A recorded value by name — indicator first, then gate value."""
        if name in self.ind:
            return self.ind[name]
        if name in self.checks:
            return self.checks[name][0]
        return default

    def __repr__(self):
        return (f"<Tick {self.symbol} {self.strategy} {self.ts:.1f} "
                f"{self.verdict} ind={len(self.ind)} checks={len(self.checks)}>")


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


class TickFeed:
    """Every recorded tick for one symbol-session, joined on the tick clock.

    🔑 THE JOIN IS NEAREST-WITHIN-TOLERANCE, NOT EXACT-MATCH, AND THAT IS
    MEASURED RATHER THAN HOPEFUL. The two streams are written by the same loop
    but stamped at slightly different instants; median separation is 0.00s and
    p90 is 0.10s, so a 1.0s window is ten times the observed slack. A tick
    with no partner inside it is NOT quietly dropped — it is counted and
    reported, because an unjoined tick is exactly the kind of silent thinning
    that makes a study of 1,700 ticks secretly a study of 900.
    """

    def __init__(self, date: str, symbol: str, strategy: str = "ORBStrategy",
                 with_checks: bool = True):
        self.date, self.symbol, self.strategy = date, symbol, strategy
        self.ticks: list = []
        self.unjoined = 0
        self.no_indicator: list = []
        self.error = ""
        self._load(with_checks)

    def _load(self, with_checks):
        import warehouse_source as ws
        pt, m1 = ws.load_derived("plan_tick", [self.date])
        if getattr(m1, "error", None):
            self.error = str(m1.error)
            return
        rows = [r for r in pt if r.get("symbol") == self.symbol
                and r.get("strategy") == self.strategy]
        if not rows:
            self.error = (f"no plan_tick rows for {self.symbol}/"
                          f"{self.strategy} on {self.date} — the TOOL's gap "
                          f"or a session the strategy never ran (r39)")
            return

        ind, m2 = ws.load_series("indicator_series", [self.date],
                                 symbols=[self.symbol])
        if getattr(m2, "error", None):
            self.error = str(m2.error)
            return
        by_ts = {}
        for r in ind:
            t = _f(r.get("ts_epoch"))
            if t is not None:
                by_ts[round(t, 3)] = r
        ind_ts = sorted(by_ts)

        checks = defaultdict(dict)
        if with_checks:
            pc, m3 = ws.load_derived("plan_check", [self.date])
            if getattr(m3, "error", None):
                self.error = str(m3.error)
                return
            for r in pc:
                if r.get("symbol") != self.symbol:
                    continue
                t = _f(r.get("ts_epoch"))
                if t is None:
                    continue
                checks[round(t, 3)][r.get("check_name")] = (r.get("value"),
                                                            r.get("verdict"))

        for r in sorted(rows, key=lambda x: _f(x.get("ts_epoch")) or 0.0):
            t = _f(r.get("ts_epoch"))
            if t is None:
                continue
            tk = Tick(t, self.symbol, self.strategy, str(r.get("verdict") or ""),
                      str(r.get("reason") or ""), _f(r.get("underlying")))
            i = bisect.bisect_left(ind_ts, t)
            best, bestd = None, None
            for j in (i - 1, i):
                if 0 <= j < len(ind_ts):
                    d = abs(ind_ts[j] - t)
                    if bestd is None or d < bestd:
                        best, bestd = ind_ts[j], d
            if best is not None and bestd <= JOIN_TOL_S:
                src = by_ts[best]
                tk.ind = {k: _f(v) for k, v in src.items()
                          if k not in ("symbol", "interval") and _f(v) is not None}
            else:
                self.unjoined += 1
                self.no_indicator.append(t)
            tk.checks = dict(checks.get(round(t, 3), {}))
            self.ticks.append(tk)

    def __iter__(self):
        return iter(self.ticks)

    def __len__(self):
        return len(self.ticks)

    def decided(self):
        """Ticks where the strategy actually reached a verdict."""
        return [t for t in self.ticks if t.verdict and t.verdict != "NOT ASKED"]

    def integrity(self) -> dict:
        n = len(self.ticks)
        with_ind = sum(1 for t in self.ticks if t.ind)
        with_chk = sum(1 for t in self.ticks if t.checks)
        ts = [t.ts for t in self.ticks]
        return {"ticks": n, "with_indicator": with_ind,
                "unjoined": self.unjoined, "with_checks": with_chk,
                "monotonic": all(ts[i] <= ts[i + 1] for i in range(len(ts) - 1)),
                "duplicates": n - len(set(ts)), "decided": len(self.decided())}


def report(date: str, symbol: str, strategy: str = "ORBStrategy") -> int:
    f = TickFeed(date, symbol, strategy)
    print("=" * 72)
    print(f"  WARGAME v0.2 — TICK FEED · {symbol} {strategy} {date}")
    print("=" * 72)
    if f.error:
        print(f"  ⚠️ REFUSED: {f.error}")
        return 1
    g = f.integrity()
    print(f"  ticks                 : {g['ticks']}")
    print(f"  joined to an indicator: {g['with_indicator']}")
    print(f"  UNJOINED (named)      : {g['unjoined']}")
    print(f"  carrying gate values  : {g['with_checks']}")
    print(f"  reached a verdict     : {g['decided']}")
    print(f"  monotonic / dupes     : {g['monotonic']} / {g['duplicates']}")
    # 🔴 INTEGRITY IS THE CONTROL. A feed that silently thinned would make a
    # study of 1,700 ticks secretly a study of 900, and nothing downstream
    # could tell.
    bad = (not g["monotonic"]) or g["duplicates"] or g["ticks"] == 0
    if bad:
        print("\n  🔴 FEED INTEGRITY FAILED — no hypothesis may be scored on it.")
        return 1
    if g["unjoined"]:
        pct = g["unjoined"] / max(1, g["ticks"])
        print(f"\n  ⚠️ {g['unjoined']} tick(s) ({pct:.1%}) carry NO indicator row "
              f"within {JOIN_TOL_S:.1f}s. They are counted, not dropped; any "
              f"indicator study must treat them as MISSING and never as zero.")
    print("\n  ✅ feed integrity holds.")
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-09-18")
    ap.add_argument("--symbol", default="AMD")
    ap.add_argument("--strategy", default="ORBStrategy")
    a = ap.parse_args()
    sys.exit(report(a.date, a.symbol, a.strategy))
