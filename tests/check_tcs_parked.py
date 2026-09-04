#!/usr/bin/env python3
"""
tests/check_tcs_parked.py  v1.0
v1.0  2026-09-04  r237 — TCS IS PARKED AT ITS FIRST GATE. Operator, 2026-09-04:
      *"Set the impossible variable and comment it in the changelog. We're
      doing a rewrite tomorrow anyways."*

⚠️ EXECUTED, NOT READ (§21). P1 drives the real `prepare()` and asserts the
verdict and the named reason, because a config constant proves nothing about
what the strategy does with it.

⚠️ AND IT PINS THE BLAST RADIUS. The reason this constant was chosen over a
quality bar is that it is TCS-ONLY: `TCS_START_ET` is pinned equal to
`CREDIT_ENTRY_START_ET` by `check_entry_windows`, and `R_FLOOR_STOP` is shared
with the sweep. P3/P4 pin that neither moved, so a future "just disable it"
cannot reach for the shared ones.
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name)


def main():
    import config as C
    from strategy.trend_credit_spread import TrendCreditSpread
    from utils.time_utils import ET

    # ══ P1 — DORMANT AT EVERY MINUTE OF EVERY SESSION ═════════════════════
    # Driven through the real prepare(), with None for everything downstream:
    # if the park gate did NOT fire first, this would crash on a missing chain
    # rather than return — so a pass here is proof it returned at gate one.
    # ⚠️ A FRESH STRATEGY PER TIME. `dormant()` DEDUPLICATES — it writes one
    # row on the transition and goes quiet on identical ticks (r-note in
    # plan.py: ~900 of UNH's 1,300 morning rows were a transcript of a clock).
    # Reusing one instance would leave every tick after the first blank and
    # this check would read the dedup as a failure to park. Each iteration is
    # therefore a fresh box arriving at that minute.
    verdicts = []
    for h, m in ((9, 31), (11, 42), (13, 59), (15, 45)):
        now = datetime(2026, 9, 4, h, m, tzinfo=ET)
        s = TrendCreditSpread()
        try:
            prep = s.prepare(None, None, None, None, 100.0, now_et=now)
            # `_close("DORMANT", f"{gate}: {why}")` lands on plan._last —
            # (n, verdict, reason). Read the real record, not a guess at a
            # field name.
            last = getattr(prep.tick.plan, "_last", None) or ("", "?", "")
            verdicts.append((f"{h:02d}:{m:02d}", str(last[1]), str(last[2])))
        except Exception as exc:                                # noqa: BLE001
            verdicts.append((f"{h:02d}:{m:02d}", f"RAISED {type(exc).__name__}",
                             str(exc)[:60]))
    dormant = [v for v in verdicts if str(v[1]).upper().startswith("DORMANT")]
    check("P1 TCS is DORMANT at every minute of the session",
          len(dormant) == len(verdicts), str(verdicts[:2]))

    # ══ P2 — AND THE REASON NAMES THE PARK, NOT A CLOCK ═══════════════════
    # 🔴 The generic message would read "past 00:00 — dormant until tomorrow",
    # which describes the wrong thing: tomorrow never arrives. A panel line
    # nobody can act on is worse than no line.
    parked = [v for v in verdicts if "PARKED" in str(v[2]).upper()]
    check("P2 the reason says PARKED, not 'past 00:00 until tomorrow'",
          len(parked) == len(verdicts),
          str(verdicts[0][2])[:80] if verdicts else "")

    # ══ P3 — THE SHARED CONSTANTS DID NOT MOVE ════════════════════════════
    # 🔴 `TCS_START_ET` is pinned equal to `CREDIT_ENTRY_START_ET`; moving it
    # to park TCS would have moved the SWEEP's window with it.
    check("P3 TCS_START_ET is untouched and still equals CREDIT_ENTRY_START_ET",
          C.TCS_START_ET == C.CREDIT_ENTRY_START_ET == (11, 31),
          f"tcs={C.TCS_START_ET} credit={C.CREDIT_ENTRY_START_ET}")
    from strategy.criteria import R_FLOOR, R_FLOOR_STOP
    check("P4 the shared R floors are untouched (the sweep still trades)",
          R_FLOOR == 1.00 and R_FLOOR_STOP == 1.00,
          f"{R_FLOOR}/{R_FLOOR_STOP}")

    # ══ P5 — THE PARK IS THE WINDOW, AND ONLY TCS READS IT ════════════════
    check("P5 TCS_ENTRY_END_ET is out of reach", C.TCS_ENTRY_END_ET == (0, 0),
          str(C.TCS_ENTRY_END_ET))
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    readers = []
    for dirpath, _dn, files in os.walk(root):
        if "/tests" in dirpath or "/." in dirpath:
            continue
        for fn in files:
            if not fn.endswith(".py"):
                continue
            p = os.path.join(dirpath, fn)
            body = "\n".join(l for l in open(p, encoding="utf-8").read().split("\n")
                             if not l.strip().startswith("#"))
            if "TCS_ENTRY_END_ET" in body and fn not in ("config.py",):
                readers.append(fn)
    check("P5b only trend_credit_spread reads it",
          set(readers) <= {"trend_credit_spread.py"}, str(sorted(set(readers))))

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — 6 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
