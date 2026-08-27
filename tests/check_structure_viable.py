#!/usr/bin/env python3
"""check_structure_viable.py — v1.0

🔴 A STRUCTURE THAT CANNOT SURVIVE ITS OWN BID-ASK IS NOT A BAD TRADE.

Operator, 2026-08-27, after CVX entered the SAME 198/192 spread seven times in
seven minutes — each stopped inside a minute, about -$170 total:
*"It's allowed to enter bad trades, but if structurally it can't even survive
for a minute we need to address the structure."*

THE MEASUREMENT, straight off the alerts: credit $0.58, stop $0.67 (15%).
**The stop was NINE CENTS away** on a contract quoted in nickels. One quote
update moves the mark further than the entire stop distance — the trade was
stopped out by its own SPREAD, not by price.

⚠️ THIS IS NOT THE R HURDLE AND MUST NEVER BE MUTED BY RELAXED. R asks whether
a trade PAYS ENOUGH; relaxed exists to collect the population R would refuse.
This asks whether the trade can EXIST — construction, like requiring a
protective wing before selling undefined risk. A trade closed before it opened
teaches the sample nothing except how fast the loop spins.

⚠️ UNIVERSAL BY CONSTRUCTION. It compares two numbers from the same chain, so a
$9 stock and a $7,000 index are judged identically. That matters because
`WING_WIDTH = 5.0` is a FIXED DOLLAR amount — one strike increment on SPX, SIX
on CVX — which is how a 6-wide spread collecting $0.58 looked normal to the
code.
"""
import ast
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


def main():
    from strategy.criteria import stop_survivable, STOP_VS_SPREAD_MIN

    # ── 🔴 V1 — THE EXACT CVX STRUCTURE IS REFUSED ───────────────────────
    ok, why = stop_survivable(0.09, 0.55, 0.61)
    check("V1 the CVX 2026-08-27 structure is refused (9c stop, 6c spread)",
          not ok, why[:72])

    # ── V2 — a healthy structure passes ──────────────────────────────────
    ok2, why2 = stop_survivable(0.45, 2.90, 2.95)
    check("V2 a wide stop over a tight quote passes", ok2, why2[:60])

    # ── V3 — UNMEASURABLE IS NOT PASSING ─────────────────────────────────
    # ⚠️ The whole failure class this week was a gate that silently never
    # applied. A viability check that cannot see the spread must REFUSE.
    check("V3 a missing quote refuses rather than assuming",
          not stop_survivable(0.45, 0.0, 0.0)[0])
    check("V4 a zero stop refuses", not stop_survivable(0.0, 1.0, 1.05)[0])

    # ── 🔴 V5 — IT IS NOT MODE-DEPENDENT ─────────────────────────────────
    # The same inputs must give the same answer in strict and relaxed. If this
    # ever reads `relaxed_active()`, the gate has become an economics gate.
    src = open(os.path.join(_root, "strategy", "criteria.py"),
               encoding="utf-8").read()
    fn = next((n for n in ast.walk(ast.parse(src))
               if isinstance(n, ast.FunctionDef) and n.name == "stop_survivable"),
              None)
    body = ast.unparse(fn) if fn else ""
    check("V5 stop_survivable never consults the relaxed flag",
          "relaxed" not in body.lower() and "mode()" not in body)

    # ── V6 — the sweep applies it BEFORE the R hurdle ────────────────────
    # ⚠️ ORDER MATTERS: R is muted under relaxed, so a viability gate placed
    # after it would be reached only when R already passed.
    ssrc = open(os.path.join(_root, "strategy", "sweep_credit_spread.py"),
                encoding="utf-8").read()
    nc = "\n".join(l for l in ssrc.split("\n")
                   if not l.strip().startswith("#"))
    i_v = nc.find("stop_survivable(")
    i_r = nc.find("t.executable()")
    check("V6 the sweep checks survivability BEFORE the R hurdle",
          i_v != -1 and i_r != -1 and i_v < i_r, f"viab@{i_v} r@{i_r}")

    check("V7 the sweep declares stop_vs_spread as a plan check",
          "stop_vs_spread" in ssrc)

    # ── 🔴 V8 — A SPENT LEVEL DOES NOT RE-ARM ────────────────────────────
    # The second half of the CVX loop: nothing remembered the previous attempt,
    # so the level re-qualified every time price wandered back to its side.
    # `LiquiditySweep.invalidated` (LIQ.3) answers "has the TAPE accepted
    # through" — it cannot answer "did WE already try this and lose".
    import strategy.sweep_credit_spread as scs
    scs._SPENT.clear()
    scs._SPENT_DAY = ""
    check("V8 a fresh level is not spent",
          not scs.is_spent("CVX", "put", 198.0)[0])
    scs.mark_spent("CVX", "put", 198.0, "stopped out")
    check("V9 a stopped-out level is spent",
          scs.is_spent("CVX", "put", 198.0)[0])
    # ⚠️ ROUNDED TO THE CENT — the pool is recomputed per tick and drifts in the
    # last decimal; an exact-float key would never match itself and the lock
    # would silently never fire.
    check("V10 float drift still matches the spent key",
          scs.is_spent("CVX", "put", 198.004)[0])
    check("V11 the other side of the same price is a different level",
          not scs.is_spent("CVX", "call", 198.0)[0])
    check("V12 a different level is untouched",
          not scs.is_spent("CVX", "put", 201.0)[0])

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_structure_viable: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
