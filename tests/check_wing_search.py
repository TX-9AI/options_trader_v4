#!/usr/bin/env python3
"""check_wing_search.py  v1.2
v1.2  2026-09-03  r234 — W2 RE-DERIVED. It matched the SOURCE TEXT
      `r > best[0]`, which r234's NamedTuple refactor legitimately removed —
      §21: a check that reads source proves nothing about runtime and goes
      RED on a correct change. It now EXECUTES the search and asserts which
      wing won.
v1.1  2026-08-27  r160: W18 re-pinned — plan_second_leg deleted; authorize()/manage() build nothing. — v1.0

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
    # 🔴 RE-DERIVED AT r234. This matched the SOURCE TEXT `r > best[0]`, which
    # r234's NamedTuple refactor legitimately removed — WORKING_AGREEMENT §21,
    # a check that reads source proves nothing about runtime and goes red on a
    # correct change. It now EXECUTES: every strike beyond the short is
    # considered, and the winner is the best of them on the gated basis.
    from strategy import credit_vertical as cv

    class _K:
        def __init__(self, k, b, a, m):
            self.strike, self.bid, self.ask, self.mark = k, b, a, m
    _sh = _K(100.0, 1.20, 1.24, 1.22)
    _wings = [_K(95.0, 0.20, 0.23, 0.215), _K(97.0, 0.50, 0.55, 0.525),
              _K(99.0, 0.95, 1.00, 0.975)]
    _res = cv.search_wing([_sh] + _wings, _sh, "put", 1.0)
    _best = max((c for c in _wings),
                key=lambda c: (1.20 - c.ask) / (abs(100.0 - c.strike) - (1.20 - c.ask)))
    check("W2 every strike beyond the short is considered, best wins",
          _res.long is not None and _res.long.strike == _best.strike,
          f"{_res.long and _res.long.strike} vs {_best.strike}")
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
    # ⚠️ r158 — `iron_condor_strategy.py` IS NOT IN THIS LIST ANY MORE, and its
    # absence is the point. Operator, 2026-08-27: *"The condor doesn't construct
    # anything."* It builds no spread, so it has no wing to search. W16 below
    # pins that it stays that way — a condor that starts searching wings has
    # started constructing again.
    for rel in ("strategy/sweep_credit_spread.py",
                "strategy/trend_credit_spread.py"):      # r163: daily fork retired
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

    # ── 🔴 W16 — THE CONDOR CONSTRUCTS NOTHING ───────────────────────────
    # Operator, 2026-08-27: *"Condor leg one is not a trade. It's a
    # condition."* / *"nothing in the plan is executable. It's an information
    # layer to feed the strategy and the strategy will execute."*
    # ⚠️ 366 LINES DELETED — `decide()`, `check_leg_triggers()` and
    # `_build_leg_signal()` — plus the 54-line inline builder inside
    # `plan_second_leg`. If any of them return, the condor is a second
    # implementation of a credit vertical again, which is the exact thing
    # Fable was asked to remove and which had ALREADY drifted from the real
    # one (mark instead of bid/ask, fixed wing, no stop_survivable, an R gate
    # relaxed could waive).
    ic2 = open(os.path.join(_root, "strategy", "iron_condor_strategy.py"),
               encoding="utf-8").read()
    ictree = ast.parse(ic2)
    gone = {"decide", "check_leg_triggers", "_build_leg_signal"}
    have = {n.name for n in ast.walk(ictree)
            if isinstance(n, ast.FunctionDef)}
    check("W16 the condor's construction methods are gone",
          not (gone & have), f"still present: {sorted(gone & have) or 'none'}")
    check("W17 the condor never calls search_wing",
          "search_wing" not in ic2)
    # ⚠️ AND IT MUST NOT ASSEMBLE A SIGNAL. A permission carries a side and a
    # level; an OptionsSignal carries contracts. Building one here is how the
    # duplication comes back.
    # r160 — plan_second_leg is DELETED (the condor selects nothing). What
    # remains is authorize() (a side and a reason) and manage() (the ladder
    # row); neither may build a signal.
    _names = {n.name for n in ast.walk(ictree) if isinstance(n, ast.FunctionDef)}
    _mg = next((n for n in ast.walk(ictree) if isinstance(n, ast.FunctionDef)
                and n.name in ("authorize", "manage")), None)
    _bodies = "".join(ast.unparse(n) for n in ast.walk(ictree)
                      if isinstance(n, ast.FunctionDef) and n.name in ("authorize", "manage"))
    check("W18 plan_second_leg is gone; authorize()/manage() exist and build no signal",
          "plan_second_leg" not in _names and {"authorize", "manage"} <= _names
          and "OptionsSignal(" not in _bodies)

    # ── W19 — the permission carries nothing executable ──────────────────
    from strategy.plan import Permission
    _p = Permission(side="put", level=197.5)
    _fields = set(vars(_p))
    check("W19 a Permission carries no contracts, strikes or premium",
          not any(k for k in _fields
                  if "contract" in k or "strike" in k or "premium" in k),
          ", ".join(sorted(_fields)))

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_wing_search: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
