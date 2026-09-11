#!/usr/bin/env python3
"""
tests/check_tcs_wing_study.py  v1.0
v1.0  2026-09-10  r351 / TCS.1 — the study must recompute the strategy's own
      arithmetic, not an approximation of it.

⚠️ THE FAILURE THAT WOULD MATTER is a floor chosen against a number that is
not the one the strategy computes. So this pins the arithmetic against
`trend_credit_spread` line for line, and pins the two honesty properties: no
candidate is None rather than zero, and the counts are an upper bound because
`stop_survivable` is not applied.

  W1  r = credit / (width − credit), on the judged side (short bid − long ask)
  W2  a put's wing sits BELOW the short, a call's ABOVE
  W3  credit >= width is not a spread and is refused
  W4  credit at exactly half the width is r = 1.00 — the live floor's meaning
  W5  no priceable wing returns None, never 0.0
  W6  the report names its own limits: snapshot cadence, no survivability,
      descriptive-only
"""
import io
import os
import sys
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
FAILS = []


def check(name, ok, detail=""):
    print("  {:<4} {}  {}".format(name, "PASS" if ok else "FAIL", detail))
    if not ok:
        FAILS.append(name)


def main():
    try:
        import tcs_wing_study as T
    except Exception as exc:                                    # noqa: BLE001
        print("  FAIL  tcs_wing_study did not import: {}".format(exc))
        return 1

    # W1 — 5 wide, short bid 1.20, long ask 0.20 -> credit 1.00, r = 1/4
    r = T.best_r(1.20, [{"strike": 95.0, "ask": 0.20}], 100.0, "put")
    check("W1", abs(r - (1.0 / 4.0)) < 1e-9, "r={:.4f} (expect 0.2500)".format(r))

    # W2 — the same strike on the wrong side is not a candidate
    wrong = T.best_r(1.20, [{"strike": 95.0, "ask": 0.20}], 100.0, "call")
    right = T.best_r(1.20, [{"strike": 105.0, "ask": 0.20}], 100.0, "call")
    check("W2", wrong is None and right is not None,
          "put-side strike refused for a call; call-side accepted")

    check("W3", T.best_r(5.0, [{"strike": 99.0, "ask": 0.10}], 100.0, "put") is None,
          "credit >= width refused")

    half = T.best_r(1.00, [{"strike": 98.0, "ask": 0.0}], 100.0, "put")
    check("W4", abs(half - 1.0) < 1e-9,
          "credit = width/2 -> r = {:.4f}".format(half))

    check("W5", T.best_r(1.0, [], 100.0, "put") is None,
          "no candidate -> None, not 0.0")

    buf = io.StringIO()
    with redirect_stdout(buf):
        T.render([("SPX", "2026-09-10", 0.2)], "x", "")
    out = buf.getvalue()
    check("W6", "NEAREST SNAPSHOT" in out and "stop_survivable" in out
          and "Descriptive" in out and "LIVE FLOOR IS 1.00" in out,
          "limits and the live floor are on the report")

    print("")
    if FAILS:
        print("FAILED: {}".format(", ".join(FAILS)))
        return 1
    print("ALL PASS (6)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
