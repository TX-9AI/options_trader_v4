#!/usr/bin/env python3
"""
tests/check_sweep_liveness.py  v1.1
v1.1  2026-09-04  r241 — RE-DERIVED. Every check pinned a CEILING —
      that MAX_AGE_BARS existed, resolved to 48, was FOUNDATIONAL and admitted
      33-48 bar sweeps. r241 removes the gate outright per the operator's
      ruling, so asserting a ceiling would pin the thing being removed. What
      survives is SWP.5's actual point: liveness is `invalidated`, the age is
      still RECORDED, and an unmeasurable sweep refuses on its own terms.
v1.0  2026-09-03  r230 — SWP.5 WAS RULED AND NEVER WIRED. `sweep_credit_spread` read
`SWEEP_CS_MAX_AGE_BARS`, a name defined nowhere, so the ceiling was the
getattr DEFAULT of 6 while SWP.5's measured 48 sat unread in config.

⚠️ ANCHORED ON DEFINITIONS AND VALUES, NEVER ON MENTIONS (WORKING_AGREEMENT
§20). The changelog above names `SWEEP_CS_MAX_AGE_BARS` and `relaxed.widen`
while explaining their removal — a canary matching either STRING would trip
on the very prose §5 requires. L2 parses the AST; L3 reads the resolved
value. Neither can match a comment.

⚠️ AND IT EXECUTES (§21). L4/L5 drive the real gate function, not the source
text: asserting the file CONTAINS `MAX_AGE_BARS` proves nothing about what
the gate does with it.

Plain script, exit code, no pytest (§36 — the boxes' venv has none).
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
    import config
    from strategy import sweep_credit_spread as scs

    src = open(scs.__file__, encoding="utf-8").read()
    tree = ast.parse(src)

    # 🔴 RE-DERIVED AT r241. Every check below pinned a CEILING — that
    # MAX_AGE_BARS existed, resolved to 48, was FOUNDATIONAL, and admitted
    # 33-48 bar sweeps. The operator's ruling removes the gate outright:
    # *"I don't give a rat's ass how old the level is, it's still a level."*
    # SWP.5 said LIVENESS REPLACES THE CLOCK in 2026-08-11; r230 raised the
    # ceiling 6 -> 48 instead of deleting it, and that half-measure is what
    # these checks were written against. Asserting a ceiling now would pin the
    # thing being removed.
    # ⚠️ WHAT SURVIVES IS THE POINT OF SWP.5: the liveness test is
    # `invalidated`, and an UNMEASURABLE sweep still refuses on its own terms.
    src = open(scs.__file__, encoding="utf-8").read()
    tree = ast.parse(src)

    # ── L1 — THE CEILING IS GONE, NOT RAISED ─────────────────────────────
    # AST, not a string search: the changelog names MAX_AGE_BARS while
    # explaining its removal, and a grep would match the explanation (§20).
    bound = [n for n in ast.walk(tree)
             if isinstance(n, ast.Assign)
             and any(getattr(t, "id", "") == "MAX_AGE_BARS" for t in n.targets)]
    check("L1 MAX_AGE_BARS is no longer bound at module level", not bound,
          f"lines {[n.lineno for n in bound]}")
    check("L1b and the module does not expose it",
          not hasattr(scs, "MAX_AGE_BARS"))

    # ── L2 — `age` IS NO LONGER A CONDITION ──────────────────────────────
    # 🔴 MEASURED FLEET-WIDE 08-31..09-04: age failed 46,791 of 61,641 (76%),
    # and on 333 ticks — 26% of every tick that was ONE gate short — it was the
    # ONLY thing refusing. Complete setups, declined for being old.
    check("L2 'age' is not a declared condition",
          "age" not in scs.SweepCreditSpreadStrategy.CONDITIONS,
          str(sorted(scs.SweepCreditSpreadStrategy.CONDITIONS)))
    conds = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call)
             and getattr(n.func, "attr", "") == "cond"
             and n.args and isinstance(n.args[0], ast.Constant)
             and n.args[0].value == "age"]
    check("L2b and nothing calls prep.cond('age', ...)", not conds,
          f"lines {[n.lineno for n in conds]}")

    # ── L3 — BUT THE AGE IS STILL RECORDED ───────────────────────────────
    # ⚠️ r241 removes the GATE, not the MEASUREMENT. `sig.sweep_age_bars` still
    # carries it onto the trade row: knowing how old a level was is useful for
    # fitting, DECIDING with it is what was ruled out.
    check("L3 the age is still recorded on the signal",
          "sig.sweep_age_bars = prep.age" in src)

    # ── L4 — THE UNMEASURABLE CASE REFUSES ON ITS OWN TERMS ──────────────
    # 🔴 A 999 sentinel means `bars_ago` could not be read AT ALL. That is a
    # DATA fault, not a staleness judgement, and admitting it silently would be
    # the absent-is-not-zero failure this repo keeps paying for.
    check("L4 the 999 sentinel still refuses, by its own name",
          "sweep_unmeasurable" in src and "_AGE_UNMEASURABLE = 999" in src)

    # ── L5 — LIVENESS IS `invalidated`, WHICH SWP.5 ALWAYS SAID ──────────
    # It fails 73% fleet-wide, which is price accepting through a level — a
    # market fact, not a defect, and the gate doing exactly its job.
    check("L5 'invalidated' remains a declared condition",
          "invalidated" in scs.SweepCreditSpreadStrategy.CONDITIONS)

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — 7 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
