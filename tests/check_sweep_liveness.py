#!/usr/bin/env python3
"""
tests/check_sweep_liveness.py  v1.0
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

    # ── L1 — SWP.5's constant exists and is the ruled value ──────────────
    hard = getattr(config, "SWEEP_STALE_HARD_BARS", None)
    check("L1 config.SWEEP_STALE_HARD_BARS is SWP.5's 48",
          hard == 48, f"got {hard!r}")

    # ── L2 — the module binds it DIRECTLY, no getattr fallback ───────────
    # AST, not a string search: a getattr default is the defect, and the
    # changelog names it.
    binding = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "MAX_AGE_BARS":
                    binding = node.value
    check("L2 MAX_AGE_BARS is bound at module level", binding is not None)
    is_attr = (isinstance(binding, ast.Attribute)
               and binding.attr == "SWEEP_STALE_HARD_BARS")
    check("L2b MAX_AGE_BARS = config.SWEEP_STALE_HARD_BARS (not getattr)",
          is_attr, ast.unparse(binding) if binding is not None else "absent")

    # ── L3 — the RESOLVED value, which is what actually gates ────────────
    check("L3 module MAX_AGE_BARS resolves to 48",
          scs.MAX_AGE_BARS == 48, f"got {scs.MAX_AGE_BARS!r}")

    # ── L4 — no relax call touches it, in EITHER form ────────────────────
    # Operator ruling 2026-09-03: eliminate relaxed from the age question.
    # Scoped to a CALL whose arguments include the Name, so the comment
    # explaining the removal cannot match.
    relaxed_on_age = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        nm = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
        if nm not in ("widen", "window"):
            continue
        args = [a.id for a in node.args if isinstance(a, ast.Name)]
        args += [k.value.id for k in node.keywords if isinstance(k.value, ast.Name)]
        if "MAX_AGE_BARS" in args:
            relaxed_on_age.append(node.lineno)
    check("L4 no relaxed.widen/window call on MAX_AGE_BARS",
          not relaxed_on_age, f"lines {relaxed_on_age}")

    # ── L5 — declared FOUNDATIONAL, so check_gates enforces L4 forever ───
    check("L5 GATES declares MAX_AGE_BARS FOUNDATIONAL",
          scs.GATES.get("MAX_AGE_BARS") == "FOUNDATIONAL",
          repr(scs.GATES.get("MAX_AGE_BARS")))

    # ── L6 — the gate ADMITS today's real refusals ───────────────────────
    # 2026-09-03, measured from plan_check: QQQ `age` FAILED 761/761 at
    # 33-48 bars. Every one of those clears at 48. This is the whole point
    # of the revision and it is asserted on the arithmetic the gate runs.
    todays = [33, 40, 44, 48]
    admitted = [a for a in todays if a <= scs.MAX_AGE_BARS]
    check("L6 QQQ's 33-48 bar sweeps all clear the backstop",
          admitted == todays, f"admitted {admitted} of {todays}")

    # ── L7 — and it still REFUSES beyond the backstop ────────────────────
    # A gate that admits everything is not a backstop. 999 is the module's
    # own absent-sentinel and must not be treated as a live reading.
    check("L7 a 999-bar sentinel is still refused",
          not (999 <= scs.MAX_AGE_BARS))

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — 8 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
