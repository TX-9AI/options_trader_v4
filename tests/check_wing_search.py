#!/usr/bin/env python3
"""check_wing_search.py — v1.0

🔴 R IS A CONSTRUCTION TARGET, NOT A FILTER. THE WING IS SEARCHED.

Operator, 2026-08-27: *"strike selection must net r of 1 or better"* and
*"make the r-value a requirement outright... and relax something else to loosen
the entry"* and *"the integrity of the trade mechanics comes first."*

WHAT THIS REPLACES: a single wing at `WING_WIDTH = 5.0` — a FIXED DOLLAR
amount, one strike increment on SPX and SIX on CVX. R was then checked after
the fact and, under relaxed, MUTED. That is how a 6-wide spread collecting
$0.58 (R 0.13) looked normal to the code and got entered SEVENTEEN times.

THE SHORT STRIKE IS STRUCTURAL — it comes from the level and never moves. The
wing is the only free variable, and the tradeoff is monotonic: narrower wing ->
less credit, less risk, HIGHER R. So "the wing that best clears the floor" is
computable, and "no wing does" is a definite answer.

⚠️ MEASURED ON THE CHAIN THAT LOOPED (CVX short put 197.5, bid $0.80):
    wing 196.5 (1.0 wide)  credit 0.20  risk 0.80  R 0.250
    wing 195.5 (2.0 wide)  credit 0.37  risk 1.63  R 0.227
    wing 194.5 (3.0 wide)  credit 0.48  risk 2.52  R 0.190
    wing 192.5 (5.0 wide)  credit 0.58  risk 4.42  R 0.131  <- the old fixed wing
    wing 190.0 (7.5 wide)  credit 0.67  risk 6.83  R 0.098
**No wing clears 1.00.** The trade is refused by STRUCTURE. And the old fixed
$5 wing was the second-worst choice on the board.

⚠️ NOT MUTED BY RELAXED. Relaxed keeps widening the EVIDENCE dials it always
did (sweep_max_age_bars 8->24, sweep_pierce_ceiling 0.25->0.75, level_hold_min
0.75->0.50); it no longer waives the economics. `R_FLOOR` is read directly,
NOT through `r_hurdle()`, which returns None under relaxed.

⚠️ EXPECTED CONSEQUENCE, STATED UP FRONT: relaxed now produces FEWER trades,
not more. Every setup must find a wing that pays for its own risk. That is the
cost of the trade being real, and the operator accepted it explicitly.
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


def _best_wing(short_bid, short_strike, wings, side="put"):
    """Mirror of the search, used only to state the arithmetic in the checks."""
    best = None
    for k, ask in wings:
        w = abs(short_strike - k)
        cr = max(0.0, short_bid - ask)
        rk = w - cr
        if cr <= 0 or rk <= 0:
            continue
        r = cr / rk
        if best is None or r > best[0]:
            best = (r, k, cr, w)
    return best


def main():
    from strategy.criteria import R_FLOOR
    src = open(os.path.join(_root, "strategy", "sweep_credit_spread.py"),
               encoding="utf-8").read()
    code = "\n".join(l for l in src.split("\n")
                     if not l.strip().startswith("#"))

    # ── 🔴 W1 — THE FIXED WING IS NO LONGER THE SELECTION ────────────────
    # ⚠️ Match CODE, not the comment explaining the removal.
    check("W1 the wing is not a single fixed-width lookup",
          "_long = cv.find_contract_at_strike(_contracts, _long_strike)"
          not in code)
    # ⚠️ r157 — the search lives in `credit_vertical.search_wing`, ONE
    # implementation shared by all four credit strategies. Four copies would
    # drift, and the drift would be silent.
    cvsrc = "\n".join(
        l for l in open(os.path.join(_root, "strategy", "credit_vertical.py"),
                        encoding="utf-8").read().split("\n")
        if not l.strip().startswith("#"))
    check("W2 every strike beyond the short is a candidate",
          "def search_wing" in cvsrc and "r > best[0]" in cvsrc)
    check("W2b the sweep calls the SHARED searcher",
          "cv.search_wing(" in code)

    # ── 🔴 W3 — R IS READ DIRECTLY, NOT THROUGH THE MUTED HURDLE ─────────
    # `r_hurdle()` returns None under relaxed. If the search consulted it, the
    # floor would vanish in exactly the mode that produced the loop.
    check("W3 the search reads R_FLOOR, not r_hurdle()",
          "R_FLOOR" in code and "r_hurdle" not in code)

    # ── W4 — the CVX chain that looped is REFUSED ────────────────────────
    cvx = [(196.5, 0.60), (195.5, 0.43), (194.5, 0.32),
           (192.5, 0.22), (190.0, 0.13)]
    best = _best_wing(0.80, 197.5, cvx)
    check("W4 the CVX 2026-08-27 chain clears no wing",
          best is not None and best[0] < R_FLOOR,
          f"best R {best[0]:.3f} at wing {best[1]} ({best[3]:.1f} wide)")

    # ── W5 — and the OLD fixed wing was not even the best of a bad set ───
    old = [c for c in cvx if abs(197.5 - c[0] - 5.0) < 0.01]
    if old:
        w = abs(197.5 - old[0][0])
        cr = 0.80 - old[0][1]
        check("W5 the old fixed $5 wing was worse than the narrowest",
              cr / (w - cr) < best[0],
              f"fixed {cr/(w-cr):.3f} vs best {best[0]:.3f}")

    # ── W6 — a chain that DOES clear the floor is taken ──────────────────
    # ⚠️ The gate must not be unpassable. A near-the-money short with a tight
    # wing clears 1.00 and must be selected.
    rich = [(197.0, 0.55), (196.0, 0.30), (195.0, 0.15)]
    b2 = _best_wing(1.40, 198.0, rich)
    check("W6 a chain that clears the floor selects a wing",
          b2 is not None and b2[0] >= R_FLOOR,
          f"R {b2[0]:.3f} at wing {b2[1]} ({b2[3]:.1f} wide)")

    # ── W7 — the refusal explains that this is STRUCTURE ─────────────────
    check("W7 the refusal says relaxed does not waive it",
          "relaxed does not" in src and "structure, not selection" in src)

    # ── 🔴 W8 — RELAXED STILL LOOSENS THE EVIDENCE DIALS ─────────────────
    # The trade was not "stop relaxing"; it was "relax evidence, never
    # economics". If CRITERIA ever loses these, relaxed stops doing anything.
    from strategy.criteria import CRITERIA
    for k in ("sweep_max_age_bars", "sweep_pierce_ceiling", "level_hold_min"):
        check(f"W8 {k} is still a relaxable evidence dial",
              k in CRITERIA and CRITERIA[k][0] != CRITERIA[k][1],
              f"{CRITERIA.get(k)}")

    # ── 🔴 W9 — ALL FOUR CREDIT STRATEGIES, NOT JUST THE SWEEP ───────────
    # r156 shipped the sweep alone; the other three kept fixed dollar wings
    # (TCS_WING_WIDTH_*, CONDOR_WING_WIDTH_*) split only two ways — SPX vs QQQ
    # — so every other symbol took the QQQ number regardless of its price or
    # strike ladder.
    for rel in ("strategy/sweep_credit_spread.py",
                "strategy/trend_credit_spread.py",
                "strategy/iron_condor_strategy.py",
                "strategy/daily_fork_credit_spread.py"):
        c = "\n".join(l for l in open(os.path.join(_root, rel),
                                      encoding="utf-8").read().split("\n")
                      if not l.strip().startswith("#"))
        name = os.path.basename(rel)
        check(f"W9 {name} searches the wing",
              "cv.search_wing(" in c or "search_wing(" in c)
        check(f"W10 {name} reads R_FLOOR, never the muted hurdle",
              "R_FLOOR" in c and "r_hurdle" not in c)
        # ⚠️ THE FIXED WIDTH MUST NOT DRIVE THE EXECUTED SPREAD. The condor and
        # the fork still call `_wing_width()` when DECLARING a plan (the chain
        # may not be loaded then), but the executing path searches and
        # overrides it. What must never come back is a long strike being
        # LOOKED UP at a fixed offset and traded.
        check(f"W11 {name} does not look up a wing at a fixed offset",
              "find_contract_at_strike(contracts, long_strike)" not in c
              and "_find_contract_at_strike(contracts, long_strike)" not in c)

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_wing_search: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
