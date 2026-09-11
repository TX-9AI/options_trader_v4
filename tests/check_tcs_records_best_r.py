#!/usr/bin/env python3
"""
tests/check_tcs_records_best_r.py  v1.0
v1.0  2026-09-10  r351 / TCS.1 — the wing floor must say BY HOW MUCH it refused.

🔴 WHY. `wing_r_best` is the single most common last refusal in the book. Over
2026-09-05..09-10 it was the ONLY failing rung on 8,381 TCS ticks — 52% of
every "exactly one gate short" — and TCS cleared every gate 7 times in 34,686.
The operator saw trending signals all day with no trend trades: the trend
rungs pass, the wing pricing refuses.

⚠️ AND THE NUMBER THAT WOULD SETTLE THE LEVEL WAS NEVER RECORDED. The failing
branch appended a WHY STRING and no value, so `PLAN GATES` printed a BLANK
fail range for this rung while `pin_concentration` beside it has p10..p90.
The floor could be argued and never fitted.

  T1  a refusing tick records `r_expiry` as a FAILED check with the BEST R the
      chain offered — not the last one examined, not nothing
  T2  it records the width that best R sat at, as context (no verdict)
  T3  a tick with NO priceable wing at all records nothing — absence of a
      candidate is not an R of zero
  T4  BEHAVIOUR IS UNCHANGED: the floor still refuses the same ticks, and the
      structural key is still wing_r_best
"""
import ast
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "strategy", "trend_credit_spread.py")
FAILS = []


def check(name, ok, detail=""):
    print("  {:<4} {}  {}".format(name, "PASS" if ok else "FAIL", detail))
    if not ok:
        FAILS.append(name)


def main():
    src = open(SRC, encoding="utf-8").read()
    tree = ast.parse(src)

    # the block under `if best is None:` inside the wing search
    blk = None
    for node in ast.walk(tree):
        if (isinstance(node, ast.If)
                and (ast.get_source_segment(src, node.test) or "") == "best is None"):
            blk = ast.get_source_segment(src, node) or ""
    if not blk:
        print("  FAIL  no `if best is None:` branch found")
        return 1
    code = "\n".join(l for l in blk.splitlines()
                     if not l.lstrip().startswith("#"))

    check("T1", 't.check("r_expiry"' in code and "_best_r" in code
          and "False)" in code,
          "records r_expiry as a failed check from _best_r")
    check("T2", "wing_width_at_best_r" in code,
          "records the width the best R sat at")
    check("T3", "if _best_r is not None:" in code,
          "no candidate -> nothing recorded (absence is not zero)")

    # T4 — the gate itself must be untouched.
    floor_intact = "if r_expiry < TCS_R_FLOOR_EXPIRY:" in src
    key_intact = '"wing_r_best" if "1:1" in _why else "stop_vs_spread"' in src
    # and the tracker must NOT sit inside the floor's body, or a refused wing
    # would never be remembered.
    body = src.split("if r_expiry < TCS_R_FLOOR_EXPIRY:", 1)[0]
    tracked_before = "_best_r = r_expiry" in body
    check("T4", floor_intact and key_intact and tracked_before,
          "floor={} key={} tracked-before-the-gate={}".format(
              floor_intact, key_intact, tracked_before))

    print("")
    if FAILS:
        print("FAILED: {}".format(", ".join(FAILS)))
        return 1
    print("ALL PASS (4)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
