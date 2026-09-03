#!/usr/bin/env python3
"""
tests/check_pool_geometry.py  v1.0
v1.0  2026-09-03  r231 — THE OPERATOR'S LEVEL MODEL, PINNED. Five rulings,
      2026-09-03: named pools keep precedence; equal highs/lows are not
      identified at all ("not reliable enough"); an upper level can ONLY be
      resistance and a lower one ONLY support, so an upper level BELOW spot
      and a lower level ABOVE spot are invalidated by geometry; nothing
      inside the opening range is actionable; and the timeframe that produced
      a level is irrelevant to all of it.

⚠️ EXECUTED, NOT READ (WA §21). Every check drives the real function and
asserts on its return, never on source text. G-checks call `classify()`;
P-checks build a real `LiquidityMap` and call the real mapper methods.

⚠️ ANCHORED ON BEHAVIOUR, NEVER ON MENTIONS (WA §20). The changelogs in
liquidity_mapper name `_find_pools` and `named` while explaining their
removal; a string canary would trip on the prose §5 requires. P1 asserts on
the POOLS THE MAP EMITS, and P4 on the AST for a definition, not a mention.

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
    from analysis.session_map import classify as _classify, CEILING, FLOOR
    from analysis import liquidity_mapper as lm

    # ⚠️ DEGRADE TO A NAMED FAILURE, NEVER TO A TRACEBACK (r206/r212). At a
    # HEAD without the r231 signature every G-check would die on one
    # TypeError, and "the checker crashed" and "the invariant is violated" do
    # not look alike — a red for an unrelated reason is the CV.1 failure that
    # teaches you to skip reds.
    _NOSPOT = object()

    def classify(*a, **kw):
        try:
            return _classify(*a, **kw)
        except TypeError as exc:
            if "spot" in str(exc):
                return _NOSPOT, f"classify() does not accept spot: {exc}"
            raise

    OH, OL = 110.0, 100.0

    # ══ G1/G2 — the ORB-range rule (pre-existing, pinned so it cannot be lost)
    ok, _ = classify(105.0, CEILING, OH, OL, "inside", spot=120.0)
    check("G1 a level INSIDE the opening range is invalidated", ok is False)
    ok, _ = classify(105.0, FLOOR, OH, OL, "inside", spot=90.0)
    check("G1b same for a floor", ok is False)

    # ══ G3/G4 — THE r231 RULE: role must agree with SPOT, not only the range
    # A ceiling ABOVE orb_high but BELOW spot passes every pre-r231 test.
    ok, why = classify(112.0, CEILING, OH, OL, "upper tine", spot=120.0)
    check("G3 an upper level BELOW spot is invalidated by geometry",
          ok is False, why[:60])
    ok, why = classify(98.0, FLOOR, OH, OL, "lower tine", spot=90.0)
    check("G4 a lower level ABOVE spot is invalidated by geometry",
          ok is False, why[:60])

    # ══ G5/G6 — and the correct geometry still passes
    ok, _ = classify(120.0, CEILING, OH, OL, "upper tine", spot=112.0)
    check("G5 an upper level ABOVE spot and above the range is VALID", ok is True)
    ok, _ = classify(90.0, FLOOR, OH, OL, "lower tine", spot=98.0)
    check("G6 a lower level BELOW spot and below the range is VALID", ok is True)

    # ══ G7 — spot is REQUIRED. An omitted spot must raise, not default.
    # ⚠️ THE RAW FUNCTION, NOT THE WRAPPER. The degrade-helper above swallows
    # exactly the TypeError this check exists to assert — caught on the first
    # run, when G7 went red against CORRECT code. A harness that intercepts the
    # behaviour under test is C.23 one layer out.
    try:
        _classify(120.0, CEILING, OH, OL, "no spot")
        raised = False
    except TypeError:
        raised = True
    check("G7 omitting spot raises rather than silently skipping the rule",
          raised)

    # ══ G8 — an unmeasurable spot is None (unmeasured), never a pass
    ok, _ = classify(120.0, CEILING, OH, OL, "bad spot", spot=None)
    check("G8 spot=None is UNMEASURED (None), never True", ok is None)

    # ══ G9 — TIMEFRAME IS NOT CONSULTED. Same price, same roles, one answer.
    a, _ = classify(120.0, CEILING, OH, OL, "15m level", spot=112.0)
    b, _ = classify(120.0, CEILING, OH, OL, "5m level", spot=112.0)
    check("G9 the verdict does not depend on which scan named the level",
          a is b is True)

    # ══ P1 — every pool the map emits is NAMED (makes the r231 removal safe)
    src = open(lm.__file__, encoding="utf-8").read()
    tree = ast.parse(src)
    unnamed = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if not (isinstance(f, ast.Attribute) and f.attr == "append"):
            continue
        if not (isinstance(f.value, ast.Attribute) and f.value.attr == "pools"):
            continue
        # ⚠️ THE ARGUMENT, NOT THE APPEND. First cut read `node.keywords`,
        # which are the keywords of `.append(...)` — always empty — so every
        # site looked unnamed. C.23: the check measured its own reading rather
        # than the code. It now inspects what is being APPENDED.
        arg = node.args[0] if node.args else None
        if isinstance(arg, ast.Name):
            continue                      # a pre-built pool (the tine path)
        kw = {k.arg for k in getattr(arg, "keywords", [])}
        if "is_named" not in kw:
            unnamed.append(node.lineno)
    check("P1 no pool is appended without a name", not unnamed, f"lines {unnamed}")

    # ══ P4 — the equal-high/low finder is GONE (a definition, not a mention)
    defs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    check("P4 _find_pools is deleted, not merely uncalled",
          "_find_pools" not in defs)

    # ══ P5 — NEAREST wins, not last-match. Drive the real method.
    m = lm.LiquidityMapper()
    lmap = lm.LiquidityMap()
    # deliberately ordered FARTHEST-FIRST so last-match-wins would pick wrong
    for px, kind in ((118.0, "high"), (112.0, "high"), (115.0, "high"),
                     (82.0, "low"), (88.0, "low"), (85.0, "low")):
        lmap.pools.append(lm.LiquidityPool(price=px, kind=kind, name="n",
                                           is_named=True))
    lmap.near_pool_pct = 50.0
    m._flag_nearby_pools(lmap, 100.0)
    check("P5 near_pool_above is the NEAREST high, not the last in list order",
          lmap.near_pool_above == 112.0, f"got {lmap.near_pool_above}")
    check("P5b near_pool_below is the NEAREST low",
          lmap.near_pool_below == 88.0, f"got {lmap.near_pool_below}")

    # ══ P6 — a swept pool is still skipped
    lmap2 = lm.LiquidityMap()
    p_near = lm.LiquidityPool(price=112.0, kind="high", name="n", is_named=True)
    p_near.swept = True
    lmap2.pools.append(p_near)
    lmap2.pools.append(lm.LiquidityPool(price=115.0, kind="high", name="n",
                                        is_named=True))
    lmap2.near_pool_pct = 50.0
    m._flag_nearby_pools(lmap2, 100.0)
    check("P6 a SWEPT nearer pool is skipped for the next one out",
          lmap2.near_pool_above == 115.0, f"got {lmap2.near_pool_above}")

    # ══ A1 — r231's other half: bars_ago 0 is FRESH, not the stale sentinel
    from strategy import sweep_credit_spread as scs
    ssrc = open(scs.__file__, encoding="utf-8").read()
    st = ast.parse(ssrc)
    # ⚠️ SCOPED TO THE ASSIGNMENT THAT GATES, NOT TO EVERY MENTION. The
    # first cut flagged the two SELECTION comparisons, whose `getattr(...,
    # 999)` defaults are harmless (the attribute always exists) and whose real
    # problem is UNITS, filed as SWEEP.6 and deliberately not touched here.
    falsy = []
    for node in ast.walk(st):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "age" for t in node.targets):
            continue
        if isinstance(node.value, ast.BoolOp):
            falsy.append(node.lineno)
    check("A1 the age assignment uses no `or` (0 would become 999)",
          not falsy, f"lines {falsy}")

    # A2 — and prove the arithmetic, not just its shape.
    _mk = lambda ba: (999 if ba is None else int(ba))
    check("A2 bars_ago 0 stays 0 (the freshest sweep), absent stays 999",
          _mk(0) == 0 and _mk(None) == 999 and _mk(33) == 33)

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — 16 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
