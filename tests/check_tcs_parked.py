#!/usr/bin/env python3
"""
tests/check_tcs_parked.py  v1.1
v1.1  2026-09-04  r238 — RE-DERIVED. It asserted (0,0); the window is now
      the operator's spec and the park is held only by `OT_TCS_ACTIVE=0` on the
      boxes. Asserts the SPEC, both window ends, and that management reads no
      entry-window constant.
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

    # 🔴 RE-DERIVED AT r238. This file asserted TCS was parked in CONFIG at
    # (0,0). The operator has now SPEC'D the window — "no new positions after
    # 1400, but condor management is allowed until the flatten" — so config is
    # a real window again and the park is held ONLY by `OT_TCS_ACTIVE=0` in the
    # systemd drop-in on the boxes. Asserting (0,0) here would fail on a
    # correct tree; asserting the SPEC is what survives.
    check("P0 the window is the operator's spec, 11:31 -> 14:00",
          C.TCS_START_ET == (11, 31) and C.TCS_ENTRY_END_ET == (14, 0),
          f"{C.TCS_START_ET} -> {C.TCS_ENTRY_END_ET}")
    # ⚠️ MANAGEMENT IS NOT GATED BY THE ENTRY CLOCK, and that is checked rather
    # than assumed: `condor_roll` and `management.py` reference no window
    # constant at all, so a roll runs to the 15:45 flatten.
    _mgmt = ""
    for _f in ("condor_roll.py", "management.py"):
        _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "strategy", _f)
        if os.path.exists(_p):
            _mgmt += open(_p, encoding="utf-8").read()
    check("P0b management reads no entry-window constant",
          "TCS_ENTRY_END_ET" not in _mgmt and "CREDIT_ENTRY_START_ET" not in _mgmt)

    # ══ P1 — WINDOW BOUNDS ARE ENFORCED AT BOTH ENDS ══════════════════════
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
    for h, m in ((9, 31), (14, 0), (15, 45)):        # r238: OUTSIDE the window
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
    check("P1 TCS is DORMANT outside 11:31-14:00, at BOTH ends",
          len(dormant) == len(verdicts), str(verdicts))

    # ══ P2 — AND THE REASON NAMES THE PARK, NOT A CLOCK ═══════════════════
    # 🔴 The generic message would read "past 00:00 — dormant until tomorrow",
    # which describes the wrong thing: tomorrow never arrives. A panel line
    # nobody can act on is worse than no line.
    # ⚠️ 14:00 IS THE FIRST MINUTE REFUSED, not the last accepted — `>=`.
    named = [v for v in verdicts if "entry_window" in str(v[2])]
    check("P2 each refusal names entry_window", len(named) == len(verdicts),
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
    check("P5 the 14:00 bound is TCS-only (the sweep is untouched)",
          C.TCS_ENTRY_END_ET == (14, 0), str(C.TCS_ENTRY_END_ET))
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
