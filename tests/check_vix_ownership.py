#!/usr/bin/env python3
"""
tests/check_vix_ownership.py  v1.0
v1.0  2026-09-10  r350 / S3.28 — SPX owns the VIX family, strictly.

🔴 THE HOLE. The operator ruled weeks ago that SPX owns VIX and no other box
pushes it. The test was `str(sym).upper() in ("VIX", "^VIX")` — two literals —
and `VIX_EXT` matched neither. So all fifteen boxes pushed the extended-hours
series into ONE shared `sym=VIX_EXT` prefix.

⚠️ MEASURED 2026-09-10: every box's reconcile rewrote the SAME rows to the
SAME targets — `VIX_EXT/interval=1m 8 -> 37`, `15m 4 -> 12`, `1h 1 -> 3` on
AMD, MU and NFLX alike — because each counter holds only its own PUTs while
S3 holds the union of fifteen. `n > expected` there permanently, and the
reconcile then makes a box CLAIM 37 objects it never sent.

🔑 AND THE EXTENDED-HOURS SERIES IS THE ONE THAT MATTERS: SPX is the only box
that stops quoting after hours, so the other fourteen are awake, collecting,
and writing over each other.

  X1  a non-SPX box skips VIX, ^VIX and VIX_EXT alike
  X2  SPX pushes all of them — ownership means it still does the work
  X3  a non-VIX symbol is never skipped on any box (VIXY is a different
      instrument, not a VIX variant)
  X4  the predicate matches by ROOT, so a future VIX_W / VIX_9D cannot slip
      the same way this one did
"""
import ast
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "warehouse", "s3_push.py")
FAILS = []


def check(name, ok, detail=""):
    print("  {:<4} {}  {}".format(name, "PASS" if ok else "FAIL", detail))
    if not ok:
        FAILS.append(name)


def main():
    src = open(SRC, encoding="utf-8").read()
    # the ownership test, lifted from push_candles by AST — not grepped, so
    # the comment block explaining the bug cannot satisfy it.
    fn = None
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.FunctionDef) and node.name == "push_candles":
            fn = node
    if fn is None:
        print("  FAIL  push_candles not found")
        return 1
    test = None
    for node in ast.walk(fn):
        if (isinstance(node, ast.If) and isinstance(node.test, ast.BoolOp)
                and "SPX" in (ast.get_source_segment(src, node.test) or "")):
            test = ast.get_source_segment(src, node.test)
    if test is None:
        print("  FAIL  no SPX ownership test inside push_candles")
        return 1

    def skips(sym, me):
        return bool(eval(test, {"str": str}, {"sym": sym, "me": me}))

    fam = ["VIX", "^VIX", "VIX_EXT", "vix_ext"]
    check("X1", all(skips(s, "NVDA") for s in fam),
          "NVDA skips {}".format(fam))
    check("X2", not any(skips(s, "SPX") for s in fam),
          "SPX pushes every VIX variant")
    check("X3", not skips("VIXY", "NVDA") and not skips("NVDA", "NVDA")
          and not skips("SPX", "NVDA"),
          "VIXY / NVDA / SPX all unaffected on a non-SPX box")
    check("X4", skips("VIX_W", "NVDA") and skips("VIX_9D", "NVDA"),
          "future VIX_* variants are covered by the root match")

    print("")
    if FAILS:
        print("FAILED: {}".format(", ".join(FAILS)))
        return 1
    print("ALL PASS (4)   predicate: {}".format(test))
    return 0


if __name__ == "__main__":
    sys.exit(main())
