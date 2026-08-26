#!/usr/bin/env python3
"""check_chain_ordering.py — v1.0

🔴 THE 2026-08-26 SILENT FAILURE. The chain and GEX were fetched ~20 lines
BELOW `run_analysis()`, but the derived engines run INSIDE it. So every plan
builder hit its `chain is None` guard, `plans` came back empty on every tick,
`_write_tick` was never reached — and `plan_tick`/`plan_check` were never
CREATED. A full session produced nothing and looked, from outside, exactly like
an engine that was never registered.

⚠️ TWO INDEPENDENT DEFECTS, TWO INDEPENDENT PINS:
  C1-C4  the ORDERING — chain is fetched before run_analysis, published on ctx
         before the engines run, and NOT fetched twice.
  C5-C6  the VISIBILITY — tables are created at engine init, so an empty table
         says "ran, found nothing" instead of leaving a missing-table mystery.
"""
import ast
import os
import sqlite3
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


def main():
    src = open(os.path.join(_root, "main.py"), encoding="utf-8").read()

    # ── C1: the fetch happens BEFORE the run_analysis call ────────────────
    # ⚠️ MATCH CODE, NOT PROSE. The comments here TALK about the old ordering,
    # so a raw substring search would find "fetch_chain" in an explanation and
    # pass while the code was still wrong. Strip comments via AST first — the
    # rule that has now fired four times on this codebase.
    tree = ast.parse(src)
    # ⚠️ SEARCH THE WHOLE MODULE. My first version sliced from `def main(` —
    # but this bot's tick loop is not inside a function of that name, so both
    # positions came back -1 and the check "passed by absence". A pin that
    # cannot find the code it is pinning is not a pin.
    # ⚠️ AND SCOPE TO THE TICK LOOP. Module-wide, `run_analysis(state` also
    # matches its own DEFINITION (which sits earlier in the file than the call
    # site), and `fetch_chain()` has other legitimate callers. Both made the
    # check measure the wrong thing. The claim is about ORDER WITHIN ONE TICK,
    # so the scope must be the function that runs the tick.
    _loop = next((n for n in ast.walk(tree)
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                  # ⚠️ LOCATE BY A MARKER THE MUTATION CANNOT MOVE. Keying on
                  # "run_analysis(state, chain=" meant that reverting the fix
                  # made the tick loop UNFINDABLE, so the pin failed with
                  # "could not locate" instead of naming the real regression.
                  # A check should fail for the reason it exists.
                  and "run_analysis(state" in ast.unparse(n)
                  and "POLL_INTERVAL_SECONDS" in ast.unparse(n)), None)
    if _loop is None:
        print("  FAIL  could not locate the tick loop in main.py")
        return 1
    stripped = "\n".join(
        l for l in ast.unparse(_loop).split("\n")
        if not l.strip().startswith("#"))
    i_fetch = stripped.find("fetch_chain()")
    i_run = stripped.find("run_analysis(state, chain=")
    check("C1 the chain is fetched BEFORE run_analysis is called",
          i_fetch != -1 and i_run != -1 and i_fetch < i_run,
          f"fetch@{i_fetch} run@{i_run}")

    # ── C2: run_analysis ACCEPTS it ───────────────────────────────────────
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == "run_analysis"),
              None)
    check("C2 run_analysis takes the chain as a parameter",
          fn is not None and any(a.arg == "chain" for a in fn.args.args),
          ", ".join(a.arg for a in fn.args.args) if fn else "not found")

    # ── C3: ctx["chain"] is set BEFORE run_all inside run_analysis ────────
    body = ast.unparse(fn) if fn else ""
    body_nc = "\n".join(l for l in body.split("\n")
                        if not l.strip().startswith("#"))
    i_set = body_nc.find("ctx['chain'] = chain")
    i_all = body_nc.find("run_all(")
    check("C3 ctx['chain'] is published BEFORE run_all inside run_analysis",
          i_set != -1 and i_all != -1 and i_set < i_all,
          f"set@{i_set} run_all@{i_all}")

    # ── C4: exactly ONE fetch per tick ────────────────────────────────────
    # ⚠️ A second fetch would double the market-data calls AND could disagree
    # with the chain the derived engines just recorded from.
    check("C4 fetch_chain() is called exactly once per tick (no re-fetch)",
          stripped.count("fetch_chain()") == 1,
          f"{stripped.count('fetch_chain()')} call site(s)")

    # ── C5/C6: the tables exist even when NOTHING is produced ─────────────
    from derived.plans import PlanEngine

    class _Store:
        def __init__(self):
            self.conn = sqlite3.connect(":memory:")
        def commit(self):
            self.conn.commit()

    st = _Store()
    PlanEngine(store=st, symbol="TEST", ledger=None)      # construct only
    names = {r[0] for r in st.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    check("C5 plan_tick exists after INIT, with no plan ever produced",
          "plan_tick" in names, ", ".join(sorted(names)) or "none")
    check("C6 plan_check exists after INIT too",
          "plan_check" in names)

    # ── C7: and a tick with NO chain still leaves the tables in place ─────
    # (the empty table is the measurement — "ran, found nothing")
    e = PlanEngine(store=st, symbol="TEST", ledger=None)
    try:
        e.run({"price": 100.0})                # no chain, no triggers
    except Exception:                                          # noqa: BLE001
        pass
    n = st.conn.execute("SELECT count(*) FROM plan_tick").fetchone()[0]
    check("C7 a chainless tick leaves plan_tick present and empty",
          "plan_tick" in names and n == 0, f"{n} rows")

    # ── C8: NO PLAN MAY BE SILENTLY OVERWRITTEN ──────────────────────────
    # ⚠️ plan_tick's key was (ts_epoch, symbol, strategy) — right in r126 when
    # every builder returned ONE plan. The fork returns FOUR, so INSERT OR
    # REPLACE dropped three with no error: 5 produced, 4 stored. `direction`
    # is now part of the key.
    class _C:
        def __init__(s, k, b, a): s.strike, s.bid, s.ask = k, b, a
    class _Ch:
        def __init__(s, c, p): s.calls, s.puts = c, p
    class _T:
        def __init__(s, tf, side, rail):
            s.tf, s.side, s.rail, s.slope = tf, side, rail, 0.05
            s.trigger, s.median, s.active = 0, 200.0, True
    class _CTM:
        def __init__(s, t): s._t = t
        def all(s): return s._t

    px = 201.4
    ch = _Ch([_C(k, max(.03, 3.2-(k-px)*.30), max(.08, 3.4-(k-px)*.30))
              for k in range(195, 231, 5)],
             [_C(k, max(.03, 3.2-(px-k)*.30), max(.08, 3.4-(px-k)*.30))
              for k in range(170, 211, 5)])
    st2 = _Store()
    e2 = PlanEngine(store=st2, symbol="T2", ledger=None)
    made = e2.derive({"price": px, "chain": ch, "condor_triggers": _CTM(
        [_T("1h", "call", 203.2), _T("1h", "put", 196.8),
         _T("1d", "call", 212.5), _T("1d", "put", 188.0)])})
    stored = st2.conn.execute("SELECT count(*) FROM plan_tick").fetchone()[0]
    check("C8 every plan produced is a row stored — none overwritten",
          made == stored and stored >= 4, f"{made} produced, {stored} stored")

    dirs = {r[0] for r in st2.conn.execute(
        "SELECT direction FROM plan_tick WHERE strategy='ForkCreditSpread'")}
    check("C9 all four fork directions survive in one tick",
          dirs == {"1h_call", "1h_put", "1d_call", "1d_put"},
          ", ".join(sorted(dirs)))

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_chain_ordering: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
