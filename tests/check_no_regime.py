#!/usr/bin/env python3
"""
tests/check_no_regime.py  v4.0
No strategy reads a regime label to decide anything. Plain script, exit code.

v4.0  2026-08-20  Built at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

WHY THIS IS WORTH A STANDING CHECK.
v4 exists because the regime label picked the correct SIDE on 44.9% of 715
directional trades - 95% CI [41.3%, 48.6%], entirely below a coin flip, and
34.2% on puts. `assemble_market_state` therefore classifies nothing and
`primary_regime` is permanently UNKNOWN.

⚠️ **A LEFTOVER REGIME GATE DOES NOT ERROR. IT SILENTLY REFUSES EVERYTHING.**
Found 2026-08-20 in `iron_condor_strategy`: THREE live gates survived the port -
one refusing every condor at entry, one cancelling every pending leg, and one
stamping a label nothing computed onto the trade record. **The condor was dead
and said nothing about it**, and it would have stayed that way until somebody
wondered why it never fired.

That is the whole failure class this repo was built to escape: a plausible
silence. So it gets a checker rather than a habit.

WHAT COUNTS AS A VIOLATION: a live read of `primary_regime` or `Regime.<X>` in
a strategy. **Docstrings and comments are exempt** - the reasoning for removing
them is worth keeping, and a checker that flags prose is one whose reds get
skimmed (learned the same day, from a first version of check_condor_spec).

`Regime.UNKNOWN` is permitted as a WRITE: a signal that must fill the field
should say it measured nothing rather than invent a label.
"""

import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STRAT = os.path.join(HERE, "..", "strategy")
SKIP = {"__init__.py"}

# ⚠️ NO EXEMPTIONS, AND THAT IS DELIBERATE. There was briefly a list of three
# "inert shells" excused from this check - butterfly, continuation and
# sweep_reversal. They were not future work: they were the v3 IMPLEMENTATIONS
# THE NEW SPECS REPLACE, and a permanent exemption for superseded code is a
# growing blind spot that an audit will ask about. **They were deleted instead.**
INERT_SHELLS = set()
ALLOWED = {"UNKNOWN"}          # writing "I measured nothing" is honest


def docstring_lines(tree):
    out = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list) or not body:
            continue
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) \
                and isinstance(first.value.value, str):
            out.update(range(first.lineno,
                             getattr(first, "end_lineno", first.lineno) + 1))
    return out


def main(argv):
    problems, checked, shells = [], 0, []
    for f in sorted(os.listdir(STRAT)):
        if not f.endswith(".py") or f in SKIP:
            continue
        if f in INERT_SHELLS:
            shells.append(f)
            continue
        path = os.path.join(STRAT, f)
        src = open(path, encoding="utf-8").read()
        tree = ast.parse(src)
        docs = docstring_lines(tree)
        checked += 1

        for node in ast.walk(tree):
            # not every node carries a line number - Module does not
            ln = getattr(node, "lineno", None)
            if ln is None or ln in docs:
                continue
            # primary_regime read
            if isinstance(node, ast.Attribute) and node.attr == "primary_regime":
                problems.append(f"{f}:{node.lineno} reads `primary_regime` - "
                                "permanently UNKNOWN in v4, so this gate "
                                "refuses everything SILENTLY")
            # Regime.<X> other than the allowed writes
            if isinstance(node, ast.Attribute) and \
                    isinstance(node.value, ast.Name) and node.value.id == "Regime" \
                    and node.attr not in ALLOWED:
                problems.append(f"{f}:{node.lineno} uses `Regime.{node.attr}` - "
                                "v4 strategies decide on STRUCTURE, not labels")

    print(f"  {checked} live strategy file(s) checked")
    if shells:
        print(f"  {len(shells)} inert shell(s) exempt and listed: "
              + ", ".join(sorted(shells)))
    if problems:
        print(f"  {len(problems)} live regime reference(s):")
        for p in sorted(set(problems)):
            print(f"    {p}")
        return 1
    print("  no strategy decides on a regime label")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
