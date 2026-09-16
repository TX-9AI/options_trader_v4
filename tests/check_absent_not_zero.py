#!/usr/bin/env python3
"""
tests/check_absent_not_zero.py  v1.0

v1.0  2026-09-16  r383 / ORB.13 + CFG.3 — THE TAPE WINDOW MEASURES THE FIGHT,
      AND A FIELD NOBODY COMPUTED IS NULL RATHER THAN ZERO.

Two defects, one shape: a measurement that renders as a plausible number while
meaning nothing. Both were found by auditing which context fields were actually
POPULATED on the 56 trades of 2026-09-14 and 09-15, not by reading code.

🔴 ORB.13 — THE TAPE-AT-LEVEL WINDOW WAS ~16 SECONDS WIDE.
`tape_at_level.measure` is contracted to span *"from the break to the fire...
THE FIGHT — everything that traded while the level was being contested"*.
`orb_strategy` fed it `_confirmed_epoch()` — the RETEST CONFIRM — and the fire
happens on the NEXT TICK after the confirming candle closes. So the window was
one tick and the measurement was silently empty.
📊 `tape_vol_at_level` live on 6/7 and 7/9 RunawayContinuation trades and
**0/15 and 1/11 on ORB** — dead on the only strategy that trades levels.
⚠️ THE INVERSION IS THE TELL: nothing but `orb_strategy` sets `orb_break_ts`, so
the runaway leaves it 0.0 and `entry_engine` falls back to a flat 900s window.
The path with the "real" value failed; the path with the dumb fallback worked.

🔴 CFG.3 — TWO WRITE PATHS, ONE OF THEM ENRICHED.
`main` computes `ctx["gap"]` and `ctx["level_near"]` EVERY TICK FOR EVERY
STRATEGY. `main._execute_condor_leg` was their only reader, so the four credit
verticals recorded the gap and the graded level while `entry_engine.enter()` —
ORB and RunawayContinuation, 433 of 493 banked trades — recorded neither.
📊 `gap_pct` 0/15 and 0/11 on ORB against 4/4 and 3/3 on sweeps. MU gapped
**-7.09%** and its row's `gap_pct` is NULL.
📊 `chain_iv_rank` **0/56, every strategy**: `OptionsChain.iv_rank` defaults to
0.0 and nothing ever assigns it — `get_iv_rank()` already guards `> 0`, so the
code knew. MU entered at 89.7% IV with its IV rank reading zero.

⚠️ THREE KINDS OF CHECK LIVE HERE AND THEY ARE LABELLED HONESTLY, because the
first cut of this file called two of them CONTROLS when they FAIL at HEAD — and
a control that goes red at HEAD is not a control, it is a red check wearing the
word. §0.6 says a check that does not fail at the previous HEAD proves nothing;
the converse is that a check which CANNOT RUN at HEAD proves nothing either way,
and pretending otherwise dresses up the born-red record.

  RED AT HEAD (the defect)      W1, W3, N1, N2b, N3, N4, N5
  CONTROL (green BOTH ways)     W2
  OVERBREADTH (build only)      N2, N3b — they cannot run at HEAD because the
                                function does not exist there. They are not
                                evidence the defect was real; they are evidence
                                the FIX is not a blanket `return None`, which is
                                the easy wrong version of it.

  W1  the window handed to `measure()` spans the BREAK to the fire, not the
      confirm to the fire
  W2  CONTROL — the runaway path still gets its 900s fallback, untouched
  W3  the field's NAME and its VALUE agree: `orb_break_ts` is the break
  N1  the `chain_iv_rank` write is GUARDED, not a bare default copy
  N2  OVERBREADTH — a chain with a REAL iv_rank of 0.4 still records 0.4
  N2b an absent iv_rank (0.0) becomes None
  N3  `level_strength` unmeasured resolves to None, not 0.0
  N3b OVERBREADTH — a REAL grade survives, and a signal's own value still wins
  N4  `gap_pct` is resolved from ctx, and is None when ctx has no gap
  N5  ONE IMPLEMENTATION — both write paths resolve through the same function,
      so they cannot drift apart again (C.23)
"""
from __future__ import annotations

import ast
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

_fails: list = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("  PASS  " if ok else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not ok:
        _fails.append(name)


# ── MU 2026-09-14's real geometry, as in check_orb_underwater_entry ───────────
MU_ORB_HIGH = 914.55
MU_ORB_LOW = 904.40
MU_BREAK = (914.335, 918.40, 914.14, 918.195)      # 09:46
MU_RETEST = (916.365, 917.04, 913.39, 914.8042)    # 09:50


def _frame(rows, start="2026-09-14 09:46"):
    import pandas as pd
    return pd.DataFrame(
        [{"open": o, "high": h, "low": l, "close": c} for o, h, l, c in rows],
        index=pd.date_range(start, periods=len(rows), freq="1min"))


def main() -> int:
    print("check_absent_not_zero — the tape window measures the fight, and a "
          "field nobody computed is NULL")
    print()

    # ── W1 / W3 — the window ────────────────────────────────────────────────
    # ⚠️ DRIVEN, NOT GREPPED. The claim is about the NUMBER handed to the
    # measurement, and asserting that the source says `_break_epoch` would pass
    # against a call that never runs (§21, the r201 shape).
    try:
        from analysis.orb_engine import ORBEngine, ORBState
        import strategy.orb_strategy as OS

        eng = ORBEngine()
        d = eng._data
        d.orb_high, d.orb_low = MU_ORB_HIGH, MU_ORB_LOW
        d.orb_width = MU_ORB_HIGH - MU_ORB_LOW
        d.state = ORBState.WAITING_FOR_BREAK
        o, h, l, c = MU_BREAK
        eng._check_for_break(_frame([(o, h, l, c), (c, c + 0.1, c - 0.1, c)]))
        # four more 1m bars pass, then the retest confirms — MU's real shape:
        # break 09:46, confirm on the 09:50 candle, so 4-5 bars of fight.
        for i in range(4):
            eng._check_for_retest(_frame(
                [(916.0, 917.0, 915.5, 916.5), (916.5, 916.6, 916.4, 916.5)],
                start="2026-09-14 09:{:02d}".format(47 + i)))
        o, h, l, c = MU_RETEST
        eng._check_for_retest(_frame([(o, h, l, c), (c, c + 0.05, c - 0.05, c)],
                                     start="2026-09-14 09:50"))

        confirmed = OS._confirmed_epoch(eng._data)
        bars = int(getattr(eng._data, "bars_since_break", 0) or 0)

        if not hasattr(OS, "_break_epoch"):
            check("W1 the window spans the BREAK to the fire, not the confirm",
                  False, "_break_epoch does not exist — the strategy still "
                         "passes the confirm")
            check("W3 `orb_break_ts`'s name and value agree", False,
                  "_break_epoch does not exist")
        else:
            got = OS._break_epoch(eng._data)
            span = confirmed - got
            check("W1 the window spans the BREAK to the fire, not the confirm",
                  span >= 120.0,
                  f"break is {span:.0f}s before the confirm "
                  f"(bars_since_break={bars}); a confirm-based window is 0s")
            check("W3 `orb_break_ts`'s name and value agree — it is the break",
                  abs(got - (confirmed - max(bars, 1) * 60.0)) < 1e-6,
                  f"break={got:.1f} confirm={confirmed:.1f} bars={bars}")

        # ── W2 — CONTROL. The runaway sets no `orb_break_ts`, so it must keep
        # the 900s fallback. If this reds, the fix leaked onto a path that was
        # already working — the opposite of the repair.
        from strategy.base_strategy import OptionsSignal
        sig = OptionsSignal(strategy_name="RunawayContinuation")
        check("W2 CONTROL the runaway still carries no break stamp and keeps "
              "its fallback window",
              float(getattr(sig, "orb_break_ts", 0.0) or 0.0) == 0.0,
              f"orb_break_ts={getattr(sig, 'orb_break_ts', None)}")
    except Exception as exc:                                     # noqa: BLE001
        for n in ("W1", "W2", "W3"):
            check(n, False, f"the ORB path did not run: {exc}")

    # ── N3 / N3b / N4 / N5 — the resolvers ──────────────────────────────────
    try:
        from analysis.level_grade import (resolve_level_strength,
                                          resolve_gap_pct)
        check("N3 `level_strength` unmeasured is None, never 0.0",
              resolve_level_strength(0.0, {}) is None
              and resolve_level_strength(None, None) is None,
              f"empty ctx -> {resolve_level_strength(0.0, {})!r}")
        got_ctx = resolve_level_strength(0.0, {"level_near": ("PDH", 1.0, 0.0004)})
        got_sig = resolve_level_strength(0.7, {"level_near": ("PDH", 1.0, 0.0004)})
        check("N3b OVERBREADTH a real grade survives, and the signal's own "
              "value still wins over the ctx fallback",
              got_ctx == 1.0 and got_sig == 0.7,
              f"ctx-> {got_ctx!r}  signal-> {got_sig!r}")
        check("N4 `gap_pct` comes from ctx, and is None when ctx has none",
              resolve_gap_pct({"gap": {"gap_pct": -7.09}}) == -7.09
              and resolve_gap_pct({}) is None
              and resolve_gap_pct(None) is None,
              f"populated-> {resolve_gap_pct({'gap': {'gap_pct': -7.09}})!r}")
    except ImportError as exc:
        for n in ("N3", "N3b", "N4"):
            check(n, False, f"resolvers do not exist: {exc}")

    # ── N5 — ONE IMPLEMENTATION. Both write paths must route to the same
    # function. Anchored on the CALL, not on a string: the AST is asked which
    # function each site invokes, so a comment naming it cannot satisfy this
    # (§20) and a second inline copy cannot hide behind one (C.23).
    try:
        def _calls_in(path, fname):
            tree = ast.parse(open(path, encoding="utf-8").read(), path)
            for node in ast.walk(tree):
                if (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and node.name == fname):
                    return {n.func.attr if isinstance(n.func, ast.Attribute)
                            else getattr(n.func, "id", "")
                            for n in ast.walk(node) if isinstance(n, ast.Call)}
            return set()

        leg = _calls_in(os.path.join(_root, "main.py"), "_execute_condor_leg")
        ent = _calls_in(os.path.join(_root, "execution", "entry_engine.py"),
                        "enter")
        shared = {"_resolve_level_strength_ctx"} & leg
        shared_e = {"_resolve_level_strength"} & ent
        check("N5 both write paths resolve `level_strength` through the shared "
              "implementation",
              bool(shared) and bool(shared_e),
              f"condor_leg={sorted(shared)} enter={sorted(shared_e)}")
    except Exception as exc:                                     # noqa: BLE001
        check("N5 both write paths resolve `level_strength` through the shared "
              "implementation", False, f"AST read failed: {exc}")

    # ── N1 / N2 — chain_iv_rank ─────────────────────────────────────────────
    # ⚠️ Read off the SOURCE EXPRESSION rather than executed, and that limit is
    # stated rather than hidden: the write happens inside
    # `_capture_entry_contract`, whose live path needs a broker round trip. The
    # assertion is scoped to the CONDITIONAL SHAPE — a bare `getattr(chain,
    # "iv_rank", None)` with no `> 0` test cannot satisfy it — which is the
    # narrowest source claim that still distinguishes the two versions.
    try:
        src = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
        tree = ast.parse(src, "main.py")
        found = None
        for node in ast.walk(tree):
            if (isinstance(node, ast.Dict)
                    and any(isinstance(k, ast.Constant)
                            and k.value == "chain_iv_rank" for k in node.keys)):
                for k, v in zip(node.keys, node.values):
                    if isinstance(k, ast.Constant) and k.value == "chain_iv_rank":
                        found = v
        if found is None:
            check("N1 `chain_iv_rank` is None when nothing assigned it", False,
                  "no chain_iv_rank entry found in main.py")
            check("N2 OVERBREADTH a real iv_rank of 0.4 still records 0.4",
                  False, "no chain_iv_rank entry found")
            check("N2b an absent iv_rank (0.0) becomes None", False,
                  "no chain_iv_rank entry found")
        else:
            expr = ast.unparse(found)
            guarded = (">" in expr and "None" in expr)
            check("N1 `chain_iv_rank` is None when nothing assigned it, not 0.0",
                  guarded, f"expression: {expr[:90]}")
            # N2 — CONTROL, and this one EXECUTES: the guard must be a filter on
            # absence, not a blanket None. Evaluated on the real expression.
            ok_real = ok_absent = None
            try:
                _f = eval("lambda _v: " + expr.replace(
                    'getattr(chain, "iv_rank", None)', "_v").replace(
                    "getattr(chain, 'iv_rank', None)", "_v"))
                ok_real = _f(0.4)
                ok_absent = _f(0.0)
            except Exception:                                    # noqa: BLE001
                pass
            # ⚠️ SPLIT, because the two halves belong to different kinds.
            # N2 is OVERBREADTH — it cannot run at HEAD in any meaningful way
            # and only proves the guard is not a blanket None. N2b is the RED
            # half: at HEAD a 0.0 stays 0.0 and that is the defect.
            check("N2 OVERBREADTH a real iv_rank of 0.4 still records 0.4",
                  ok_real == 0.4, f"0.4-> {ok_real!r}")
            check("N2b an absent iv_rank (0.0) becomes None",
                  ok_absent is None, f"0.0-> {ok_absent!r}")
    except Exception as exc:                                     # noqa: BLE001
        for n in ("N1", "N2", "N2b"):
            check(n, False, f"main.py read failed: {exc}")

    print()
    if _fails:
        print("FAILED: " + ", ".join(_fails))
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
