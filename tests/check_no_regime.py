#!/usr/bin/env python3
"""
tests/check_no_regime.py  v4.2

v4.2  2026-08-21  PHASE B (r58) COMPLETE: countdown dicts emptied, macro_data
      exemption removed after the vix_band rename, and CARRIES NOW FAIL — a
      carry after the purge is a regression, not pending work. Verified by
      planting a vix_regime getattr and watching red. Zero carries tree-wide.
NOTHING IN THE TREE reads a regime label to decide anything. Plain script.

v4.1  2026-08-21  SCOPE WIDENED from `strategy/` to the whole tree, after the
      fleet's first session produced ZERO trades: the hard gate that vetoes all
      dispatch is in main.py, which this check never looked at. See the block
      above SCAN_DIRS.
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
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
SKIP = {"__init__.py"}

# ── v4.1 (2026-08-21) — THE SCAN IS NOW TREE-WIDE. IT WAS `strategy/` ONLY. ──
# 🔴 THIS IS WHY THE FLEET TRADED NOTHING ON ITS FIRST SESSION. The regime
# HARD GATE that vetoes ALL strategy dispatch lives in `main.py`, not in
# `strategy/`, so it was never in scope. Eleven green checks over a fleet that
# could not place an order. Three more dead gates sat in `execution/
# exit_engine.py` — the butterfly's regime-flip exit and the adverse-trend exit
# for calls and puts — exits that have never once run.
#
# ⚠️ THE LESSON IS ABOUT SCOPE, NOT ABOUT THE RULE. v4.0's rule was right and
# its doctrine below is still the best statement of the failure class. It was
# aimed at the place the LAST leftover was found (iron_condor_strategy) instead
# of at the place the DECISION is made. **A check scoped to yesterday's crime
# scene is not a check on the codebase.**
SCAN_DIRS = ("analysis", "data", "database", "execution", "notifications",
             "risk", "shadow", "strategy", "utils", "warehouse")
SCAN_ROOT_FILES = ("main.py", "config.py", "status.py", "query.py",
                   "eod_summary.py")

# Files whose regime references are NOT the retired classifier. Each needs a
# stated reason; an exemption without one is how a blind spot grows.
# PHASE B (r58): the exemption list is EMPTY, deliberately. macro_data's
# entry is gone because vix_regime is now vix_band — the live measurement no
# longer wears the word, so nothing needs excusing. An exemption that outlives
# its reason is a blind spot with a receipt.
EXEMPT = {}

# ── PHASE B HANDOFF LIST (2026-08-21) ────────────────────────────────────────
# Sites that PASS a regime value as an argument rather than gating on it. They
# are reroutes, not deletions: each carries a live measurement that rides on
# `RegimeState` and needs pointing at its real source before the type can be
# deleted. Owned by Phase B — see docs/HANDOFF_REGIME_PURGE.md.
#
# ⚠️ THIS LIST IS A COUNTDOWN, NOT AN EXEMPTION. It exists so the board can be
# honestly green for "no regime GATES anything" while these remain visible and
# counted. **Phase B is done when it is empty.** This file's own doctrine warns
# what a permanent exemption becomes; every entry is dated, named, and has a
# stated destination.
# Whole files whose regime use is telemetry, not control flow. `main.py`'s own
# doctrine records that trade_readiness "Gates NOTHING - no fire decision
# changes anywhere". Its label comparisons still take the wrong branch every
# tick, so its graded readiness is quietly wrong — a real defect, but an
# OBSERVABILITY one. Listing it here keeps the severity honest instead of
# calling a log line a veto.
# PHASE B (r58): COMPLETE. trade_readiness's label arms were rebuilt on
# measured inputs (see its v4.1 entry); the file is scanned like any other.
PHASE_B_FILES = {}

# ⚠️ KEYED ON THE SOURCE LINE'S TEXT, NOT ITS NUMBER. The first draft used
# (file, lineno) and every entry went stale the instant a deletion above it
# shifted the file - the board went red on three sites that had not changed,
# naming line numbers that no longer meant anything. A countdown list that
# breaks when you make progress is worse than none.
# PHASE B (r58): COMPLETE — the countdown reached zero and the dicts stay
# EMPTY as the proof the handoff defined. The three pinned sites: the gap
# measure reads BotState.prev_trend_direction (committed each tick — the old
# carrier was NEVER ASSIGNED, so prior_dir had been a silent 0 since the
# split); chain_snapshot no longer receives the label; position_manager
# receives regime=None and the exit label arms are deleted.
PHASE_B = {}


# ⚠️ NO EXEMPTIONS, AND THAT IS DELIBERATE. There was briefly a list of three
# "inert shells" excused from this check - butterfly, continuation and
# sweep_reversal. They were not future work: they were the v3 IMPLEMENTATIONS
# THE NEW SPECS REPLACE, and a permanent exemption for superseded code is a
# growing blind spot that an audit will ask about. **They were deleted instead.**
INERT_SHELLS = set()
ALLOWED = {"UNKNOWN"}          # writing "I measured nothing" is honest

# ── v4.1 — THE LABELS AS BARE STRINGS ────────────────────────────────────────
# 🔴 v4.0 CAUGHT ONLY `primary_regime` AND `Regime.<X>`. It missed every gate
# that compares a plain string, and those were the dead EXITS:
#     exit_engine.py:1412  TRENDING_REGIMES = {"TRENDING_BULL", ...}
#     exit_engine.py:1608  if option_side == "call" and regime in ("TRENDING_BULL", ...)
#     orb_engine.py:639    if regime == "SWEEP_REVERSAL" ...
# The enum was the SPELLING, not the concept. A checker that knows only one
# spelling of a dead idea will certify the other spellings green — which is
# exactly what happened to the butterfly's regime-flip exit and the
# adverse-trend exit, neither of which has ever run.
LABELS = {"TRENDING_BULL", "TRENDING_BEAR", "BREAKOUT_VOLATILE",
          "COMPRESSION", "RANGING", "SWEEP_REVERSAL"}


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


def _targets():
    """Every live source file in scope, as repo-relative paths."""
    out = []
    for f in SCAN_ROOT_FILES:
        p = os.path.join(ROOT, f)
        if os.path.exists(p):
            out.append(p)
    for d in SCAN_DIRS:
        dp = os.path.join(ROOT, d)
        if not os.path.isdir(dp):
            continue
        for f in sorted(os.listdir(dp)):
            if f.endswith(".py") and f not in SKIP:
                out.append(os.path.join(dp, f))
    return out


def _gate_lines(tree):
    """Lines that sit inside a branch TEST — i.e. lines that DECIDE something.

    ⚠️ v4.1 SPLITS SEVERITY, AND THE SPLIT IS THE POINT. A regime label that
    GATES control flow means the fleet cannot trade (main.py:1951 cost a whole
    session). A regime label that is merely CARRIED — written to a record,
    printed, pushed to S3 — is dead weight, not a veto.

    Conflating them forces a choice between shipping a red board and laundering
    a green one. Separated: GATES are fatal and must be zero; CARRIES are
    listed, counted and printed so they cannot be forgotten, but they do not
    block a deploy that makes the fleet functional again.
    """
    out = set()
    for n in ast.walk(tree):
        test = None
        if isinstance(n, (ast.If, ast.While, ast.IfExp)):
            test = n.test
        elif isinstance(n, ast.Assert):
            test = n.test
        if test is None:
            continue
        for sub in ast.walk(test):
            ln = getattr(sub, "lineno", None)
            if ln is not None:
                out.add(ln)
        # a set/tuple literal built one line above a membership test is part of
        # the gate in practice - exit_engine.py:1412 defines TRENDING_REGIMES
        # then tests against it on the very next line.
        t0 = getattr(test, "lineno", None)
        if t0:
            out.add(t0 - 1)
    return out


def main(argv):
    problems, carries, checked, shells, exempt = [], [], 0, [], []
    for path in _targets():
        rel = os.path.relpath(path, ROOT)
        f = rel
        if rel in EXEMPT:
            exempt.append(f"{rel} ({EXEMPT[rel]})")
            continue
        if os.path.basename(path) in INERT_SHELLS:
            shells.append(f)
            continue
        src = open(path, encoding="utf-8").read()
        tree = ast.parse(src)
        docs = docstring_lines(tree)
        gates = _gate_lines(tree)
        checked += 1

        for node in ast.walk(tree):
            # not every node carries a line number - Module does not
            ln = getattr(node, "lineno", None)
            if ln is None or ln in docs:
                continue
            # primary_regime read
            if isinstance(node, ast.Attribute) and node.attr == "primary_regime":
                (problems if node.lineno in gates else carries).append(
                    f"{f}:{node.lineno} reads `primary_regime`"
                    + (" - GATE: permanently UNKNOWN, refuses everything SILENTLY"
                       if node.lineno in gates else " - carried, not a gate"))
            # 🔴 v4.1 — `getattr(x, "primary_regime", None)` IS A READ, AND THE
            # FIRST DRAFT OF THIS RULE MISSED IT. main.py:1951 — the gate that
            # vetoed EVERY dispatch on EVERY box for the whole first session —
            # is written exactly that way, so an Attribute-node rule walks
            # straight past the single most expensive line in the repo. A
            # dynamic read is still a read.
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                    and node.func.id == "getattr" and len(node.args) >= 2 \
                    and isinstance(node.args[1], ast.Constant) \
                    and isinstance(node.args[1].value, str) \
                    and "regime" in node.args[1].value.lower():
                (problems if node.lineno in gates else carries).append(
                    f"{f}:{node.lineno} getattr(..., "
                    f"\"{node.args[1].value}\")"
                    + (" - GATE: dynamic regime read, refuses everything SILENTLY"
                       if node.lineno in gates else " - carried, not a gate"))
            # v4.1 — a bare label string is the same gate in a different
            # spelling. Docstrings are already excluded above.
            if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                    and node.value in LABELS:
                (problems if node.lineno in gates else carries).append(
                    f"{f}:{node.lineno} label string \"{node.value}\""
                    + (" - GATE: this branch can never be taken"
                       if node.lineno in gates else " - carried, not a gate"))
            # Regime.<X> other than the allowed writes
            if isinstance(node, ast.Attribute) and \
                    isinstance(node.value, ast.Name) and node.value.id == "Regime" \
                    and node.attr not in ALLOWED:
                (problems if node.lineno in gates else carries).append(
                    f"{f}:{node.lineno} uses `Regime.{node.attr}`"
                    + (" - GATE: decides on a label v4 never computes"
                       if node.lineno in gates else " - carried, not a gate"))

    print(f"  {checked} live source file(s) checked (tree-wide)")
    if exempt:
        print(f"  {len(exempt)} exempt with stated reason: " + "; ".join(exempt))
    if shells:
        print(f"  {len(shells)} inert shell(s) exempt and listed: "
              + ", ".join(sorted(shells)))
    if carries:
        by_file = {}
        for c in sorted(set(carries)):
            by_file.setdefault(c.split(":", 1)[0], 0)
            by_file[c.split(":", 1)[0]] += 1
        print(f"  PHASE B PENDING - {len(set(carries))} regime reference(s) "
              f"CARRIED but not gating, in {len(by_file)} file(s):")
        for fn, n in sorted(by_file.items()):
            print(f"      {fn}: {n}")
        print("      (dead weight, not a veto. Purge target - see "
              "docs/HANDOFF_REGIME_PURGE.md)")
    # NB: the message text contains colons, so split on the FILE:LINE prefix
    # only. A naive p.split(":")[1] raised ValueError on the first message that
    # carried one - caught by running it, not by reading it.
    def _key(msg):
        m = re.match(r"^(\S+?):(\d+)\b", msg)
        return (m.group(1), int(m.group(2))) if m else (None, None)

    def _deferred(msg):
        fn, ln = _key(msg)
        if fn in PHASE_B_FILES:
            return PHASE_B_FILES[fn]
        try:
            txt = open(os.path.join(ROOT, fn), encoding="utf-8").read()
            line = txt.splitlines()[ln - 1].strip()
        except Exception:                                      # noqa: BLE001
            return None
        for frag, why in PHASE_B.items():
            if frag in line:
                return why
        return None

    deferred = [p for p in set(problems) if _deferred(p)]
    problems = [p for p in set(problems) if p not in deferred]
    if deferred:
        print(f"  PHASE B COUNTDOWN - {len(deferred)} value-carrying site(s) "
              f"left, each with a named destination:")
        for d in sorted(deferred):
            k = _key(d)
            print(f"      {k[0]}:{k[1]} -> {_deferred(d)}")
    if problems:
        print(f"  {len(set(problems))} REGIME GATE(S) - the fleet cannot trade "
              f"through these:")
        for p in sorted(set(problems)):
            print(f"    {p}")
        return 1
    print("  no regime label GATES anything in the tree")
    if carries:
        # PHASE B COMPLETE (r58): a carry is no longer pending work - it is a
        # REGRESSION. The countdown reached zero; anything that reappears was
        # added after the purge and fails the board. Found by planting a
        # getattr(..., "vix_regime") read and watching this checker stay GREEN:
        # carries printed a warning but exited 0, which is a report, not a
        # guard. A checker that cannot fail is the audit's oldest finding.
        print("  (REGRESSION - carries reappeared after Phase B)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
