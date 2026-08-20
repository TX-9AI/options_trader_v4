#!/usr/bin/env python3
"""
tests/check_gates.py  v4.1

v4.1  2026-08-20  AUDIT F1: import-resolving detector. See _relaxed_bindings.
Every strategy declares its gates, and the code cannot relax a FOUNDATIONAL one.

v4.0  2026-08-20  Built at the OTV4 split. WA 36.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

WHY THIS IS A SCRIPT AND NOT A PYTEST FILE.
Its first version was `tests/test_gate_categories.py` and it **failed the land
command on the box** - not because the code was wrong but because the active
venv had no pytest. A verification that goes red on ENVIRONMENT rather than on
CONTENT teaches the operator to ignore reds, which is exactly the failure CV.1
records. `check_imports.py` and `gen_file_map.py` are plain scripts with exit
codes and they run anywhere; this one was the odd one out, and it was the one
that broke.

WHY IT CHECKS THE CODE AND NOT ONLY THE PROSE.
The first version asserted that the WORDS "FOUNDATIONAL", "SELECTION" and
"FEASIBILITY" appeared in a docstring. That verifies somebody wrote the right
words, not that the code respects them - and it also asserted on exact source
strings, which is the brittleness WA 21 warns about and which I did anyway.

**Now each strategy declares its gates as DATA** - a module-level `GATES` dict
mapping each constant to its category - and this checks that no
`relaxed.widen(...)` or `relaxed.window(...)` call touches a constant declared
FOUNDATIONAL or FEASIBILITY. That is a property of the code, not of the comment
above it.

THE THREE CATEGORIES (WA 36):
  SELECTION    measured preferences. Loosening one gives a WORSE example of the
               same trade - which is what a debug session wants. Relaxable.
  FOUNDATIONAL the conditions that define the setup's IDENTITY. **A gate can be
               perfectly winnable and still be foundational** - relax the
               runaway's held 50% TP and you get plenty of fills, every one an
               ORB plus a guess. NEVER.
  FEASIBILITY  the vetoes that make a trade unwinnable however good it looks.
               Below 0.05% ATR the required move was reached on 0% of 5,517
               measured bars. NEVER.
"""

import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STRAT = os.path.join(HERE, "..", "strategy")
HELPERS = {"relaxed.py", "structure.py", "base_strategy.py",
           "credit_vertical.py", "condor_roll.py", "__init__.py"}
CATEGORIES = {"SELECTION", "FOUNDATIONAL", "FEASIBILITY"}
RELAX_CALLS = {"widen", "window"}


def strategies():
    for f in sorted(os.listdir(STRAT)):
        if f.endswith(".py") and f not in HELPERS:
            yield f, os.path.join(STRAT, f)


def declared_gates(tree):
    """The module-level GATES dict, as {constant: category}."""
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == "GATES":
                out = {}
                if isinstance(node.value, ast.Dict):
                    for k, v in zip(node.value.keys, node.value.values):
                        if isinstance(k, ast.Constant) and isinstance(v, ast.Constant):
                            out[str(k.value)] = str(v.value)
                return out
    return None


def _relaxed_bindings(tree):
    """Every local name bound to strategy.relaxed or its functions.

    ⚠️ AUDIT F1 (2026-08-20): the old detector matched the SPELLING
    `relaxed.widen(NAME)` and the literal import string. A mutation with
    `from strategy import relaxed as rx` + `rx.widen(FOUNDATIONAL_X, 99)` ran
    GREEN — two compounding escape hatches, and the aliased import was also
    treated as "not relaxable" and skipped entirely. Same shape as the scope
    hole this file already documents: an exemption that is the default for
    any spelling but one. Imports are resolved now; the module is matched,
    not the word.
    """
    mods, funcs = set(), {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name in ("strategy.relaxed",):
                    mods.add(a.asname or "strategy")
        elif isinstance(node, ast.ImportFrom):
            if node.module == "strategy":
                for a in node.names:
                    if a.name == "relaxed":
                        mods.add(a.asname or "relaxed")
            elif node.module == "strategy.relaxed":
                for a in node.names:
                    if a.name in RELAX_CALLS or a.name == "tag":
                        funcs[a.asname or a.name] = a.name
    return mods, funcs


def relaxed_calls(tree):
    """(constant_name | None, callsite_lineno) for every resolved relax call.
    None means the argument was not a plain Name — a widened value nobody can
    categorize, which is itself refused."""
    mods, funcs = _relaxed_bindings(tree)
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        hit = False
        if isinstance(fn, ast.Attribute) and fn.attr in RELAX_CALLS:
            v = fn.value
            if isinstance(v, ast.Name) and v.id in (mods | {"relaxed"}):
                hit = True
            elif (isinstance(v, ast.Attribute) and v.attr == "relaxed"
                  and isinstance(v.value, ast.Name)):
                hit = True                      # strategy.relaxed.widen(...)
        elif isinstance(fn, ast.Name) and funcs.get(fn.id) in RELAX_CALLS:
            hit = True                          # from strategy.relaxed import widen
        if not hit:
            continue
        # EVERY Name in the call is a gate constant to categorize — the
        # window() signature mixes literals (values) with constants (gates),
        # e.g. relaxed.window("00:00", CUTOFF_ET, "00:00", "14:00"). A call
        # with NO Name at all is opaque and refused: nothing to categorize.
        names = [a.id for a in node.args if isinstance(a, ast.Name)]
        names += [k.value.id for k in node.keywords
                  if isinstance(k.value, ast.Name)]
        if names:
            out.extend((n, node.lineno) for n in names)
        else:
            out.append((None, node.lineno))
    return out


def main(argv):
    problems = []
    checked = 0
    for name, path in strategies():
        src = open(path, encoding="utf-8").read()
        # ⚠️ SCOPE HOLE CLOSED 2026-08-20. This used to skip any strategy that
        # did not import `relaxed` - so **ORB, the one strategy with a positive
        # record, was invisible to the checker simply by not importing it.**
        # A checker a file can escape by omission is a checker with a growing
        # blind spot, and the escape hatch is the DEFAULT for a new strategy.
        # Every strategy declares GATES; only a relaxable one is checked for
        # relaxing the wrong category.
        checked += 1
        tree = ast.parse(src)
        gates = declared_gates(tree)

        if gates is None:
            problems.append(
                f"{name}: declares no GATES dict. "
                "Name every gate constant and its category - SELECTION, "
                "FOUNDATIONAL or FEASIBILITY. See WA 36.")
            continue

        bad_cat = {k: v for k, v in gates.items() if v not in CATEGORIES}
        if bad_cat:
            problems.append(f"{name}: unknown categories {bad_cat} "
                            f"(expected one of {sorted(CATEGORIES)})")

        # ⚠️ THE CHECK THAT MATTERS. Prose can say anything; this reads the code.
        # Every strategy is walked — "relaxable" is no longer a spelling test
        # a file can fail its way out of (AUDIT F1). Zero relax calls is fine.
        for n, ln in relaxed_calls(tree):
            if n is None:
                problems.append(
                    f"{name}:{ln}: a relaxed.* call whose argument is not a "
                    "plain constant Name - it cannot be categorized, so it is "
                    "refused. Name the gate.")
                continue
            cat = gates.get(n)
            if cat is None:
                problems.append(
                    f"{name}: `{n}` is passed to relaxed.* but is not in GATES. "
                    "An undeclared gate is one nobody decided the category of.")
            elif cat != "SELECTION":
                problems.append(
                    f"{name}: `{n}` is declared {cat} and is being RELAXED. "
                    "Only SELECTION gates may be loosened - "
                    + ("relaxing this makes it a different trade."
                       if cat == "FOUNDATIONAL"
                       else "relaxing this admits trades that cannot win."))

    print(f"  {checked} relaxable strategy(ies) checked")
    if problems:
        print(f"  {len(problems)} problem(s):")
        for p in problems:
            print(f"    {p}")
        return 1
    print("  every gate is declared, and only SELECTION gates are relaxed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
