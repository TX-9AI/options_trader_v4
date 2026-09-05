#!/usr/bin/env python3
"""
tests/check_age_gate_gone.py  v1.0
v1.0  2026-09-04  r241 — THE AGE GATE IS REMOVED, NOT RAISED.

🔴 Operator, 2026-09-04: *"I don't give a rat's ass how old the level is, it's
still a level. Why are we still measuring the age of them?"* Because I only
half-shipped his 2026-08-11 ruling. SWP.5 said LIVENESS REPLACES THE CLOCK;
r230 found it had never reached the code and raised the ceiling 6 → 48 instead
of deleting the gate. That was my call, not his.

🔑 AGE MEASURES THE RAID, NOT THE LEVEL. A level swept at 09:45 that has held
since is the SAME LEVEL at 13:00 — arguably better, having held longer. And
levels are swept all day; the morning's is not the only one on the board.

🔴 MEASURED FLEET-WIDE, 2026-08-31..09-04: `age` failed 46,791 of 61,641 (76%),
and on 333 ticks — 26% of every tick that was ONE gate short — it was the ONLY
thing refusing. Complete setups, declined for being old.
"""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name)


def main():
    from strategy import sweep_credit_spread as scs
    src = open(scs.__file__, encoding="utf-8").read()
    tree = ast.parse(src)
    S = scs.SweepCreditSpreadStrategy

    # ══ A1 — NO CEILING, IN ANY FORM ══════════════════════════════════════
    # ⚠️ AST, not a grep: the changelog names MAX_AGE_BARS while explaining its
    # removal, so a string search would match the explanation (§20).
    bound = [n.lineno for n in ast.walk(tree)
             if isinstance(n, ast.Assign)
             and any(getattr(t, "id", "") == "MAX_AGE_BARS" for t in n.targets)]
    check("A1 MAX_AGE_BARS is not bound", not bound, str(bound))
    check("A1b and the module does not expose it",
          not hasattr(scs, "MAX_AGE_BARS"))

    # ══ A2 — `age` IS NOT A GATE ══════════════════════════════════════════
    check("A2 'age' is not a declared condition", "age" not in S.CONDITIONS,
          str(sorted(S.CONDITIONS)))
    conds = [n.lineno for n in ast.walk(tree)
             if isinstance(n, ast.Call)
             and getattr(n.func, "attr", "") == "cond"
             and n.args and isinstance(n.args[0], ast.Constant)
             and n.args[0].value == "age"]
    check("A2b nothing calls prep.cond('age', ...)", not conds, str(conds))
    check("A2c and it is not in PLAN_CHECKS", "age" not in S.PLAN_CHECKS)

    # ══ A3 — THE MEASUREMENT SURVIVES ═════════════════════════════════════
    # 🔑 r241 removes the GATE, not the NUMBER. `sig.sweep_age_bars` still
    # carries it to the trade row: knowing how old a level was is useful for
    # fitting, DECIDING with it is what was ruled out. Deleting the field would
    # have thrown away the evidence along with the rule.
    check("A3 the age is still recorded on the signal",
          "sig.sweep_age_bars = prep.age" in src)
    check("A3b and still on the preparation's slots", "\"age\"" in src)

    # ══ A4 — UNMEASURABLE IS NOT OLD ══════════════════════════════════════
    # 🔴 A 999 sentinel means `bars_ago` could not be read AT ALL — a DATA
    # fault, not a staleness judgement. Admitting it silently would be the
    # absent-is-not-zero failure this repo keeps paying for; it refuses under
    # its own name so the panel can tell the two apart.
    check("A4 the sentinel refuses by its own name",
          "sweep_unmeasurable" in src and "_AGE_UNMEASURABLE = 999" in src)
    unmeas = [n for n in ast.walk(tree)
              if isinstance(n, ast.Compare)
              and "_AGE_UNMEASURABLE" in ast.unparse(n)]
    check("A4b and it is a sentinel comparison, not a threshold",
          any(">=" in ast.unparse(n) for n in unmeas), str(len(unmeas)))

    # ══ A5 — LIVENESS IS `invalidated`, AS SWP.5 SAID ═════════════════════
    # It fails 73% fleet-wide: price accepting through a level is a market
    # fact, not a defect, and that gate is doing exactly its job.
    check("A5 'invalidated' remains a declared condition",
          "invalidated" in S.CONDITIONS)

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — 9 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
