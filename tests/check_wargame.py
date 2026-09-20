#!/usr/bin/env python3
"""
tests/check_wargame.py  v2.0
v2.0  2026-09-20  r393 / FU.5 — REWRITTEN FOR THE TICK-FEED HARNESS.
      v1.0 gated `Tape` and `FrozenClock`, which v0.2 of the harness DELETED
      when it stopped reconstructing bars. A gate left pointing at removed
      machinery does not fail honestly — it fails on an ImportError and reads
      as breakage rather than as a design change, which is how a dead gate
      starts hiding the next one ([[SHD.5]], [[LAND.9]]).

WHAT IT PINS — the properties a record-replay is worthless without:
  T1  the feed REFUSES a session it has no rows for, by name
  T2  every plan_tick becomes exactly one Tick — no invention, no silent drop
  T3  a tick with no indicator partner is COUNTED, never quietly dropped
  T4  the join is nearest-within-tolerance and respects the tolerance
  T5  integrity failure REFUSES the feed for scoring
  T6  a missing value reads as MISSING, never as zero
"""
import io
import contextlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import wargame as w

FAILS, RAN = [], []


def ck(n, ok, msg):
    RAN.append(n)
    print(f"  {n:<4} {'PASS' if ok else 'FAIL'}  {msg}")
    if not ok:
        FAILS.append(n)


# ── synthetic streams, so nothing here depends on the network ───────────────
class _WS:
    """Stands in for warehouse_source. The fixture is built from the REAL
    column names measured on 2026-09-18, not from invented ones — §0.4: a
    fixture drawn from the author's own assumption cannot fail."""

    class Meta:
        error = ""

    def __init__(self, pt, ind, pc):
        self._pt, self._ind, self._pc = pt, ind, pc

    def load_derived(self, table, dates):
        return ({"plan_tick": self._pt, "plan_check": self._pc}[table],
                _WS.Meta())

    def load_series(self, table, dates, symbols=None):
        return self._ind, _WS.Meta()


def feed(pt, ind, pc=(), **kw):
    import warehouse_source as real
    stub = _WS(list(pt), list(ind), list(pc))
    saved = (real.load_derived, real.load_series, real.Meta)
    real.load_derived, real.load_series = stub.load_derived, stub.load_series
    try:
        return w.TickFeed("2026-09-18", "AMD", "ORBStrategy", **kw)
    finally:
        real.load_derived, real.load_series, real.Meta = saved


def PT(ts, verdict="NOT ASKED", reason="", und=None):
    return {"symbol": "AMD", "strategy": "ORBStrategy", "ts_epoch": ts,
            "verdict": verdict, "reason": reason, "underlying": und}


def IND(ts, adx=30.0):
    return {"symbol": "AMD", "interval": "primary", "ts_epoch": ts,
            "adx": adx, "atr": 1.5, "vwap": 545.0}


# ------------------------------------------------------------------------ T1
f = feed([], [])
ck("T1", f.error and "no plan_tick rows" in f.error,
   f"a session with no rows REFUSES by name: {f.error[:58]}")

# ------------------------------------------------------------------------ T2
pt = [PT(1000.0), PT(1015.0), PT(1030.0)]
f = feed(pt, [IND(1000.0), IND(1015.0), IND(1030.0)])
g = f.integrity()
ck("T2", g["ticks"] == 3 and g["duplicates"] == 0 and g["monotonic"],
   f"3 plan_ticks -> 3 Ticks, no dupes, monotonic: {g['ticks']}/"
   f"{g['duplicates']}/{g['monotonic']}")

# ------------------------------------------------------------------------ T3
# 🔴 THE ONE THAT MATTERS. A silently dropped tick makes a study of 1,700
# secretly a study of 900 and nothing downstream can tell.
f = feed(pt, [IND(1000.0), IND(1030.0)])          # 1015 has no partner
g = f.integrity()
ck("T3", g["ticks"] == 3 and g["unjoined"] == 1 and g["with_indicator"] == 2,
   f"an unpartnered tick is KEPT and COUNTED, not dropped: "
   f"ticks={g['ticks']} unjoined={g['unjoined']} joined={g['with_indicator']}")

# ------------------------------------------------------------------------ T4
f = feed([PT(1000.0)], [IND(1000.4)])             # inside 1.0s
ck("T4", f.integrity()["with_indicator"] == 1,
   "an indicator 0.4s away joins (measured p90 is 0.10s)")

f = feed([PT(1000.0)], [IND(1003.0)])             # outside 1.0s
g = f.integrity()
ck("T4b", g["with_indicator"] == 0 and g["unjoined"] == 1,
   "an indicator 3.0s away does NOT join and is counted unjoined — the "
   "tolerance is enforced, not decorative")

# ------------------------------------------------------------------------ T5
f = feed([PT(1030.0), PT(1000.0)], [IND(1000.0), IND(1030.0)])
# TickFeed sorts, so build the failure directly on the integrity contract
f.ticks = list(reversed(f.ticks))
ck("T5", not f.integrity()["monotonic"],
   "out-of-order ticks are DETECTED by the integrity contract")

_saved = w.TickFeed
try:
    class _Bad:
        error = ""

        def __init__(self, *a, **k):
            pass

        def integrity(self):
            return {"ticks": 2, "with_indicator": 2, "unjoined": 0,
                    "with_checks": 0, "monotonic": False, "duplicates": 1,
                    "decided": 0}
    w.TickFeed = _Bad
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = w.report("2026-09-18", "AMD")
    out = buf.getvalue()
    ck("T5b", rc == 1 and "FEED INTEGRITY FAILED" in out
       and "no hypothesis may be scored" in out,
       "a broken feed REFUSES scoring (rc=1) and says so")
finally:
    w.TickFeed = _saved

# ------------------------------------------------------------------------ T6
# ⚠️ MISSING IS NOT ZERO. `flat_angle_deg` sat at -1 = NOT COMPUTED on 187 of
# 187 ORB trades and would read as a measured null in any scan ([[DISC.1]]).
f = feed([PT(1000.0)], [IND(1000.0)])
t = f.ticks[0]
ck("T6", t.get("adx") == 30.0 and t.get("nonesuch") is None
   and t.get("nonesuch", "MISSING") == "MISSING",
   "a present value returns, an absent one returns None/sentinel — never 0.0")

print()
if FAILS:
    print(f"FAILED: {', '.join(FAILS)}")
    sys.exit(1)
print(f"ALL PASS ({len(RAN)})")
