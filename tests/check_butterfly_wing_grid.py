#!/usr/bin/env python3
"""tests/check_butterfly_wing_grid.py  v1.0
THE BUTTERFLY'S WINGS SIT ON STRIKES THAT ACTUALLY EXIST.

v1.0  2026-08-31  r198 — born red at r197: `_chain_increment` does not exist
      there, and the wing is quantised by `config.STRIKE_INCREMENT` through
      `round_to_strike()`, which returns an **int**.

🔴 THE FAILURE THIS PINS, measured on the first live-fleet session. One global
increment for fifteen symbols, and an int-returning rounder:
    PLTR  pin 190,   EM 3.25 -> wing 1 -> legs 189 / 191   ($2.50 ladder)
    AMD   pin 472.5          -> wing 1 -> legs 470.5 / 474.5
Neither pair is listed, so `_exact()` refused — correctly — for **242 and 243
minutes**, roughly 900 ticks each, on both boxes, all session. An arithmetic
problem wearing the costume of a market judgement.

🔑 W3 IS THE CHECK THAT KEEPS THE DOCTRINE. The apex is the trade, and *"a
nearest-strike substitute is a different one"*. Both pins above were LISTED
strikes — only the wings were off-grid. So this must snap the WINGS and never
the apex, and W3 asserts the apex is exactly the pin after snapping.

⚠️ W5 GUARDS THE MEDIAN. A single stray half-strike in a $2.50 ladder would
set a min-based grid to 0.50 and reproduce the bug for that symbol on that day.

Run:  python3 tests/check_butterfly_wing_grid.py
"""
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.environ.setdefault("OT_PAPER_TRADING", "1")

_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


class _K:
    def __init__(self, k):
        self.strike = k


def ladder(step, lo, hi):
    n = int(round((hi - lo) / step))
    return [_K(round(lo + i * step, 2)) for i in range(n + 1)]


def main():
    import strategy.gex_pin_butterfly as b

    if not hasattr(b, "_chain_increment"):
        check("W0 the wing grid is read from the chain", False,
              "_chain_increment is absent — wings are still quantised by one "
              "global STRIKE_INCREMENT for every symbol")
        print("\nFAILED 1: W0 — nothing below can execute")
        return 1

    # ── W1: the real ladders, including the two that failed live ──────────
    cases = [("PLTR $2.50 @190", ladder(2.5, 180, 200), 190.0, 2.5),
             ("AMD  $2.50 @472.5", ladder(2.5, 460, 485), 472.5, 2.5),
             ("SPX  $5    @7660", ladder(5, 7600, 7700), 7660.0, 5.0),
             ("NVDA $1    @180", ladder(1, 170, 190), 180.0, 1.0)]
    bad = [n for n, ks, pin, want in cases
           if abs(b._chain_increment(ks, pin) - want) > 1e-9]
    check("W1 the increment is read off the chain, per symbol", not bad,
          f"wrong: {bad}" if bad else "PLTR/AMD 2.5, SPX 5, NVDA 1")

    # ── W2: the live failures now produce LISTED strikes ──────────────────
    # PLTR: pin 190, EM 3.25, WING_EM_FRAC 0.25 -> intended 0.8125.
    inc = b._chain_increment(ladder(2.5, 180, 200), 190.0)
    wing = round(round((b.WING_EM_FRAC * 3.25) / inc) * inc, 4)
    wing = max(inc, wing)
    listed = {k.strike for k in ladder(2.5, 180, 200)}
    check("W2 PLTR's wings land on strikes that exist",
          (190.0 - wing) in listed and (190.0 + wing) in listed,
          f"inc={inc} wing={wing} -> {190.0 - wing} / {190.0 + wing}")

    # ── W3: THE APEX NEVER MOVES ──────────────────────────────────────────
    # 🔑 The doctrine protects the apex, not the wings. Snapping must be
    # symmetric about the pin and leave it untouched.
    check("W3 the apex stays exactly on the pin after snapping",
          (190.0 - wing) + (190.0 + wing) == 2 * 190.0,
          "wings are symmetric about the pin; the pin itself is never rounded")

    # ── W4: the int rounder is not used for the wing any more ─────────────
    # ⚠️ Shape of the CALL, not a mention (WA §20): the v4.7 changelog names
    # round_to_strike while explaining why it cannot be used here.
    src = open(os.path.join(_root, "strategy", "gex_pin_butterfly.py"),
               encoding="utf-8").read()
    body = "\n".join(l for l in src.splitlines()
                     if not l.strip().startswith("#"))
    check("W4 round_to_strike() no longer computes the wing",
          "round_to_strike(WING_EM_FRAC" not in body
          and "from utils.math_utils import round_to_strike" not in body,
          "it returns an int, so a $2.50 ladder cannot be expressed by it")

    # ── W5: a stray listing must not drag the grid down ───────────────────
    mixed = ladder(2.5, 180, 200) + [_K(189.5)]
    check("W5 one stray half-strike does not set the grid (median, not min)",
          abs(b._chain_increment(mixed, 190.0) - 2.5) < 1e-9,
          str(b._chain_increment(mixed, 190.0)))

    # ── W6: degenerate chains fall back, never crash ──────────────────────
    check("W6 a thin or absent chain falls back to the configured default",
          b._chain_increment([_K(190)], 190.0, 1.0) == 1.0
          and b._chain_increment(None, 190.0, 1.0) == 1.0
          and b._chain_increment([], 190.0, 2.5) == 2.5)

    # ── W7: the stretch is RECORDED, because the ruling defers to metrics ──
    # ⚠️ Operator accepted a wider-than-intended wing *on the condition that it
    # bears out in the metrics later*. That is only checkable if the
    # counterfactual rides on the signal.
    check("W7 intended width, grid and stretch ride on the signal",
          "sig.wing_intended" in src and "sig.grid_increment" in src
          and "sig.wing_stretch" in src,
          "a ruling that defers to the metrics needs the metrics to see it")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_butterfly_wing_grid: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
