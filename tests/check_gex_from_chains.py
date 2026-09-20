#!/usr/bin/env python3
"""
tests/check_gex_from_chains.py  v1.0
v1.0  2026-09-19  r391 / GEX.1 — THE INSTRUMENT THE GAMMA HYPOTHESIS WOULD
      HAVE LEANED ON WAS RETURNING CONFIDENT NOTHING.

🔴 BORN FROM A MEASUREMENT, NOT A WORRY. `gex_from_chains` v1.0 globbed
`/home/claude/cc` — a path from ANOTHER MACHINE — got zero files, and printed
"NO GAMMA FLIP FOUND IN ANY SNAPSHOT ... that is a REAL answer, not a missing
one" with exit code 0. It asserted its own absence was the tape's answer,
which is r39 exactly inverted, and it is the third ungated analysis tool found
doing this in one day ([[CHK.8]], [[RPL.1]]).

G1  an absent/empty load REFUSES BY NAME and exits NON-ZERO
G2  the refusal reaches for the WAREHOUSE, not a local directory
G3  a real load produces a real profile (gamma x OI, signed)
G4  the conclusion block is UNREACHABLE on an empty set
G5  "no pin" carries the n it rests on
G6  the unverified dealer-sign ASSUMPTION is still declared to the reader
"""
import io
import contextlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import gex_from_chains as g

FAILS, RAN = [], []


def ck(n, ok, msg):
    RAN.append(n)
    print(f"  {n:<4} {'PASS' if ok else 'FAIL'}  {msg}")
    if not ok:
        FAILS.append(n)


# ---------------------------------------------------------------- G1 / G4 / G2
_saved = g.snapshots
try:
    g.snapshots = lambda d, s: (None, "no chain_snapshots for X on Y — this is "
                                      "the TOOL's gap, not the tape's (r39)")
    # ⚠️ A CRASH IS NOT A CLEAN RED AND MUST NOT BE REPORTED AS ONE. Removing
    # the refusal makes `run()` reach `len(None)` and raise, which killed this
    # checker outright and printed no verdict at all — a gate that dies tells
    # you less than one that fails. The exception is caught and NAMED instead.
    buf = io.StringIO()
    rc, exc = None, None
    try:
        with contextlib.redirect_stdout(buf):
            rc = g.run("2026-01-01", "NOPE")
    except Exception as e:                                       # noqa: BLE001
        exc = f"{type(e).__name__}: {e}"
    out = buf.getvalue()
    ck("G1", exc is None and rc == 1 and "REFUSED" in out,
       f"an empty load REFUSES and exits non-zero (rc={rc}"
       + (f", RAISED {exc}" if exc else "") + ")")
    ck("G4", "REAL answer" not in out and "NO GAMMA FLIP" not in out,
       "the conclusion block is UNREACHABLE on an empty set — v1.0 fell "
       "straight through it and declared the nothing a result")
    ck("G1b", "not the tape's" in out or "absence" in out,
       "the refusal NAMES whose gap it is (r39)")
finally:
    g.snapshots = _saved

# ⚠️ BEHAVIOUR, NOT SOURCE TEXT (§21). The first cut of this check grepped the
# file for "/home/claude/cc" and FAILED — because the v2.0 changelog documents
# that path as the defect. A gate satisfied or broken by PROSE is asserting
# about the comment, not the code; the same shape defeated two NEG assertions
# in r390's own land.spec hours earlier.
import inspect
_sig = list(inspect.signature(g.snapshots).parameters)
ck("G2", _sig[:2] == ["date", "symbol"],
   f"snapshots() is keyed on (date, symbol) — a warehouse lookup, not a "
   f"machine-local glob: {_sig}")

_res = g.snapshots("1970-01-01", "NOSUCHSYM")
ck("G2b", isinstance(_res, tuple) and _res[0] is None and _res[1],
   f"an absent symbol-session returns (None, reason) and NEVER a bare [] — "
   f"'nothing was there' and 'nothing came back' cannot be the same value: "
   f"{str(_res)[:70]}")

# ------------------------------------------------------------------------- G3
# Synthetic chain: gamma x OI, calls +, puts -. A flip must exist between them.
snap = {"event": "chain_snapshot", "ts_et": "2026-09-18T10:00:00-04:00",
        "expiry": "2026-09-18", "symbol": "T", "underlying": "100.0",
        "contracts": [
            {"type": "C", "strike": 95.0, "gamma": 0.05, "oi": 1000},
            {"type": "C", "strike": 100.0, "gamma": 0.08, "oi": 2000},
            {"type": "P", "strike": 105.0, "gamma": 0.09, "oi": 9000},
            {"type": "P", "strike": 110.0, "gamma": 0.07, "oi": 5000}]}
spot, per = g.gex_profile(snap)
ck("G3", spot == 100.0 and len(per) == 4 and per[95.0] > 0 and per[105.0] < 0,
   f"profile signs by type: call {per.get(95.0, 0):+,.0f} / "
   f"put {per.get(105.0, 0):+,.0f}")

pin, _ = g.pin_from(per, spot)
ck("G3b", pin is not None,
   f"a chain whose cumulative gamma changes sign HAS a flip: pin={pin}")

# a chain with no sign change must return None, never the nearest strike
allcalls = {k: abs(v) for k, v in per.items()}
ck("G3c", g.pin_from(allcalls, spot)[0] is None,
   "a chain that never flips returns None, NOT the nearest strike — "
   "'no pin' and 'a pin somewhere' must not be the same answer")

# ---------------------------------------------------------------- G5 / G6
_saved = g.snapshots
try:
    nofl = dict(snap)
    nofl["contracts"] = [{"type": "C", "strike": 95.0, "gamma": 0.05, "oi": 1000}]
    g.snapshots = lambda d, s: ([nofl], "")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = g.run("2026-09-18", "T")
    out = buf.getvalue()
    ck("G5", "NO GAMMA FLIP IN ANY OF 1 LOADED SNAPSHOT" in out,
       "'no pin' is printed WITH the n it rests on, so it can never again be "
       "read as a verdict on a tape that was never loaded")
    ck("G6", "ASSUMPTION" in out and "not verified" in out.lower(),
       "the unverified dealer-sign convention is declared to the reader")
finally:
    g.snapshots = _saved

print()
if FAILS:
    print(f"FAILED: {', '.join(FAILS)}")
    sys.exit(1)
print(f"ALL PASS ({len(RAN)})")
