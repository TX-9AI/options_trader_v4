#!/usr/bin/env python3
"""
tests/check_tcs_floor.py  v1.0
v1.0  2026-09-10  r353 / TCS.1 — the floor is 0.75, and it is the ONLY thing
      that changed.

🔴 THE EVIDENCE IT RESTS ON. `tcs_wing_study` over 2026-09-01..09-10
reconstructed the best wing R the chain actually offered at 15,456
symbol-snapshots: p10 0.316 · p25 0.462 · MEDIAN 0.587 · p75 0.712 · p90 0.818.
The old floor of 1.00 admitted **1.4%** — it was not strict, it was OUTSIDE
THE DISTRIBUTION. That matches the live record: TCS cleared every gate 7 times
in 34,686 ticks, with `wing_r_best` the only failing rung on 8,381 of them.

⚠️ AND IT WIDENS THE SPREADS, which the admit rate does not show. The search
keeps `width > best[0]` — the WIDEST wing clearing the floor, not the best-R
one — so the floor governs STRUCTURE as well as frequency. F3 pins that
selection rule, because if it ever changed to best-R this floor would mean
something different from what it was chosen to mean.

  F1  the floor is 0.75
  F2  it is still compared with `<` against `r_expiry` — the gate's shape is
      untouched, only its level
  F3  the wing search still takes the WIDEST qualifying wing
  F4  `TCS_STOP_PCT_OF_CREDIT` is unchanged — the stop was never in question
  F5  the sweep's `R_FLOOR_STOP` is untouched; the two bases stay separate
      (§35: one constant with two bases is the rot)
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILS = []


def check(name, ok, detail=""):
    print("  {:<4} {}  {}".format(name, "PASS" if ok else "FAIL", detail))
    if not ok:
        FAILS.append(name)


def main():
    cfg = open(os.path.join(REPO, "config.py"), encoding="utf-8").read()
    tcs = open(os.path.join(REPO, "strategy", "trend_credit_spread.py"),
               encoding="utf-8").read()
    crit = open(os.path.join(REPO, "strategy", "criteria.py"),
                encoding="utf-8").read()

    m = re.search(r'OT_TCS_R_FLOOR_EXPIRY",\s*"([\d.]+)"', cfg)
    check("F1", m is not None and float(m.group(1)) == 0.75,
          "floor = {}".format(m.group(1) if m else "NOT FOUND"))

    check("F2", "if r_expiry < TCS_R_FLOOR_EXPIRY:" in tcs,
          "gate shape unchanged")

    check("F3", "if best is None or width > best[0]:" in tcs,
          "still selects the WIDEST qualifying wing")

    m2 = re.search(r'OT_TCS_STOP_PCT_CREDIT",\s*"([\d.]+)"', cfg)
    check("F4", m2 is not None and float(m2.group(1)) == 0.15,
          "stop pct = {}".format(m2.group(1) if m2 else "NOT FOUND"))

    m3 = re.search(r'OT_PLAN_R_FLOOR_STOP",\s*"([\d.]+)"', crit)
    check("F5", m3 is not None and float(m3.group(1)) == 1.00,
          "sweep R_FLOOR_STOP = {} (separate basis, untouched)".format(
              m3.group(1) if m3 else "NOT FOUND"))

    print("")
    if FAILS:
        print("FAILED: {}".format(", ".join(FAILS)))
        return 1
    print("ALL PASS (5)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
