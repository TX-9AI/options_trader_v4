#!/usr/bin/env python3
"""
tests/check_wargame.py  v1.0
v1.0  2026-09-19  r391 / FU.5 — THE HARNESS IS GATED BEFORE IT IS TRUSTED, NOT
      AFTER IT PRODUCES A NUMBER SOMEONE LIKES.

🔴 THIS FILE EXISTS BECAUSE OF [[CHK.8]] AND [[RPL.1]]. Measured 2026-09-19:
168 files in tests/, 132 swept, and 22 analysis tools with NO gate naming them
— because the sweep globs `check_*.py` and anything that ANALYSES rather than
ASSERTS is invisible to it by construction. `exit_replay` was in that set and
spent its whole life returning nothing and blaming the tape. A new instrument
that ships ungated is that story queued up again, so the gate lands in the
SAME revision as the instrument.

WHAT IT PINS — the properties a replay harness is worthless without:
  W1  the lookahead guard RAISES rather than returning rows
  W2  point-in-time slicing withholds the future
  W3  `closed_at` admits ONLY bars that had finished
  W4  the clock freeze reaches a BOUND name in a real engine module
  W5  the freeze is restored afterwards
  W6  a mid-bar tick is NOT counted as agreement
  W7  the report REFUSES to bless an unreconciled control
"""
import datetime
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import pandas as pd

import wargame as w

FAILS = []
RAN = []


def ck(name, ok, msg):
    RAN.append(name)
    print(f"  {name:<4} {'PASS' if ok else 'FAIL'}  {msg}")
    if not ok:
        FAILS.append(name)


# a synthetic session: one bar a minute from 09:30
idx = pd.date_range("2026-09-18 09:30:00", periods=60, freq="1min", tz=w.ET)
df = pd.DataFrame({"open": 100.0, "high": 101.0, "low": 99.0,
                   "close": 100.5, "volume": 1000.0}, index=idx)
tape = w.Tape(df, "TEST", "2026-09-18")
mid = w.ET.localize(datetime.datetime(2026, 9, 18, 10, 0, 0))

# ------------------------------------------------------------------ W1
try:
    tape.future_of(mid)
    ck("W1", False, "future_of() returned instead of raising")
except w.LookaheadError:
    ck("W1", True, "future_of() RAISES — a decision path cannot see forward")

# ------------------------------------------------------------------ W2
pit = tape.at(mid)
ck("W2", len(pit) < len(tape.df) and pit.index[-1] <= mid,
   f"at() withholds the future: {len(pit)} of {len(tape.df)} bars, "
   f"last {pit.index[-1]:%H:%M}")

# ------------------------------------------------------------------ W3
# 🔑 THE ONE THAT CAUGHT A REAL DEFECT. `at()` returns the bar STAMPED 10:00,
# which does not close until 10:01 — so its close is from the future. This is
# the lookahead the `future_of` guard does NOT catch, because it arrives
# inside a legitimate-looking slice. Found by the control disagreeing with the
# tape, never by reading the code.
closed = tape.closed_at(mid)
ck("W3", closed.index[-1] < mid and (mid - closed.index[-1]).total_seconds() >= 60,
   f"closed_at() admits only FINISHED bars: last {closed.index[-1]:%H:%M} "
   f"vs at()'s {pit.index[-1]:%H:%M} — the forming bar is excluded")

ck("W3b", len(closed) == len(pit) - 1,
   f"exactly one bar separates them ({len(pit)} vs {len(closed)}) — the "
   f"forming one, not an off-by-many")

# ------------------------------------------------------------------ W4
# ⚠️ BOUND NAMES, NOT THE DEFINITION. 47 modules do
# `from utils.time_utils import now_et`, which resolves at import; patching
# utils.time_utils alone would leave every one of them on the real clock and
# a replay would silently report the hour it RAN. That is CHK.7 exactly.
import analysis.orb_engine as oe                                  # noqa: E402
real = oe.now_et()
target = w.ET.localize(datetime.datetime(2026, 9, 18, 10, 15))
with w.FrozenClock(target) as fc:
    inside = oe.now_et()
    ck("W4", inside == target and fc.patched >= 1,
       f"freeze reaches orb_engine's BOUND now_et: {inside:%m-%d %H:%M} "
       f"({fc.patched} binding(s) patched)")
after = oe.now_et()
ck("W5", after != target and after >= real,
   f"clock restored afterwards: {after:%m-%d %H:%M}")

# ------------------------------------------------------------------ W6
ck("W6", w.Tape.bar_aligned(target) and
   not w.Tape.bar_aligned(target + datetime.timedelta(seconds=15)),
   "a mid-bar instant is NOT bar-aligned, so reconcile_orb counts it "
   "NOT RECONCILABLE by name instead of as agreement (RPL.2's ruling)")

# ------------------------------------------------------------------ W7
# 🔴 THE REFUSAL IS THE PRODUCT. A harness that cannot reproduce what happened
# must not be allowed to score what would have happened — RPL.1 shipped a
# "POSITIVE CONTROL: 0" that was true and meaningless.
import io                                                          # noqa: E402
import contextlib                                                  # noqa: E402
_saved = w.reconcile_orb
try:
    w.reconcile_orb = lambda date, tol=0.011: {
        "agree": {"x": 1}, "disagree": {"y": 1}, "unreconcilable": 0,
        "unreconcilable_by_symbol": {}, "examples": [], "ticks": 1}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = w.report("2026-09-18")
    out = buf.getvalue()
    ck("W7", rc == 1 and "may NOT be used to score" in out,
       "an unreconciled control REFUSES the harness (rc=1) and says why")

    w.reconcile_orb = lambda date, tol=0.011: {
        "agree": {}, "disagree": {}, "unreconcilable": 9,
        "unreconcilable_by_symbol": {"Z": 9}, "examples": [], "ticks": 9}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc0 = w.report("2026-09-18")
    ck("W7b", rc0 == 1,
       "ZERO agreements out of zero comparisons is REFUSED too — '0 disagreed' "
       "on an empty set is the most convincing possible zero and means nothing")
finally:
    w.reconcile_orb = _saved

print()
if FAILS:
    print(f"FAILED: {', '.join(FAILS)}")
    sys.exit(1)
print(f"ALL PASS ({len(RAN)})")
