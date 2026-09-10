#!/usr/bin/env python3
"""
tests/check_stop_sweep_renders.py  v1.0
v1.0  2026-09-09  r326 — the land gate for tests/stop_sweep.py's render().

🔴 WHAT IT CATCHES, AND WHY NOTHING DID. `stop_sweep --selftest` has covered
`replay_row` since v1.0 and has NEVER touched `render()` — so the arithmetic
was gated and the only function the operator ever sees was not. `render()`
sorted its `(stop, tp)` keys directly, `TP_GRID` opens with None, and Python 3
refuses `None < float`: the tool died on ANY non-empty surface, every run,
for seventeen days, and printed its header and column rule FIRST so the
traceback read as a formatting fault rather than a function that never worked.

⚠️ IT DRIVES THE REAL FUNCTION over a synthetic book. A grep for the sort key
would pass against any rewrite that reintroduced the same comparison by
another route.
"""
import io
import os
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stop_sweep as ss                                          # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print("  {:<4} {}  {}".format(name, "PASS" if ok else "FAIL", detail))
    if not ok:
        FAILS.append(name)


def main():
    # A winner cut pre-peak, a loser capped — enough of each to clear MIN_N.
    A = dict(pnl_usd=300.0, entry_premium=1.0, mfe_premium=5.0,
             mae_premium=0.88, mfe_bars=20, mae_bars=3, contracts=1,
             is_short_position=0)
    B = dict(pnl_usd=-80.0, entry_premium=1.0, mfe_premium=1.05,
             mae_premium=0.10, mfe_bars=2, mae_bars=15, contracts=1,
             is_short_position=0)
    book = [dict(A) for _ in range(ss.MIN_N + 5)] + \
           [dict(B) for _ in range(ss.MIN_N + 5)]

    buf = io.StringIO()
    err = None
    try:
        with redirect_stdout(buf):
            ss.render(book, "GATE · call")
    except Exception as exc:                                     # noqa: BLE001
        err = exc
    out = buf.getvalue()
    rows = [ln for ln in out.splitlines() if ln.strip().startswith("0.")]

    check("S1", err is None,
          "render() raised {}: {}".format(type(err).__name__, err) if err
          else "completed")
    check("S2", len(rows) > 0, "{} data row(s)".format(len(rows)))
    # None means NO take profit and must sort first, not blow up or trail.
    first = rows[0].split() if rows else []
    check("S3", bool(first) and first[1] == "none",
          "leading tp = {}".format(first[1] if len(first) > 1 else "(none drawn)"))
    # Every tp in the grid reaches the table for the tightest stop.
    tps = {ln.split()[1] for ln in rows if ln.split()[0] == "0.10"}
    check("S4", len(tps) == len(ss.TP_GRID),
          "{} of {} tp levels drawn at stop 0.10".format(len(tps), len(ss.TP_GRID)))
    check("S5", "recorded book:" in out, "book line present")

    print("")
    if FAILS:
        print("FAILED: {}".format(", ".join(FAILS)))
        return 1
    print("ALL PASS (5)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
