#!/usr/bin/env python3
"""check_fixture_fidelity.py — v1.0

🔴 THE 2026-08-26 LESSON, AND IT IS THE SHARPEST ONE OF THE DAY.

`derived/plans.py` called `ctm.all()`. The real `CondorTriggerMap` exposes
`all_rails()`. There is no `all()`. So on EVERY live tick the fork builder
raised AttributeError, a bare `except` swallowed it, and the builder returned
None — no row, no starved row, and no "[plans] failed" log line either, because
the exception was caught inside the builder and never reached derive()'s
handler. ForkCreditSpread was simply absent from plan_tick for an entire
session while five other plans wrote 60+ rows each.

⚠️ EVERY TEST PASSED. The fixture I wrote exposed `.all()` — because I invented
both the fixture and the caller in the same sitting, from the same wrong
assumption. **A GREEN TEST AGAINST A DOUBLE I AUTHORED PROVES ONLY THAT I AM
CONSISTENT WITH MYSELF.** The double has to be checked against the real class.

This file pins the ATTRIBUTES production code actually reaches for on objects
it does not own, against the REAL classes. It imports the real modules; it
never asserts against a stand-in.
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


def main():
    # ── the trigger map — the object that caused this ─────────────────────
    from analysis.condor_trigger_map import CondorTriggerMap, ForkTrigger

    src = open(os.path.join(_root, "derived", "plans.py"), encoding="utf-8").read()
    tree = ast.parse(src)

    # Every attribute production code calls on a `ctm` object.
    called = set()
    for n in ast.walk(tree):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and isinstance(n.func.value, ast.Name)
                and n.func.value.id in ("ctm",)):
            called.add(n.func.attr)
    real = {a for a in dir(CondorTriggerMap) if not a.startswith("_")}
    bogus = called - real
    check("X1 every method plans.py calls on the trigger map EXISTS on it",
          not bogus,
          f"called {sorted(called) or 'none'}; missing from the real class: "
          f"{sorted(bogus) or 'none'}")

    # ⚠️ AND THE FIELDS READ OFF EACH TRIGGER. `getattr(t, name, default)`
    # NEVER raises, so a wrong field name here fails SILENTLY as a default
    # value — worse than the AttributeError, because nothing breaks at all.
    fields = set()
    for n in ast.walk(tree):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "getattr" and len(n.args) >= 2
                and isinstance(n.args[0], ast.Name) and n.args[0].id == "t"
                and isinstance(n.args[1], ast.Constant)):
            fields.add(n.args[1].value)
    real_f = set(getattr(ForkTrigger, "__annotations__", {})) | {
        a for a in dir(ForkTrigger) if not a.startswith("_")}
    bad_f = fields - real_f
    check("X2 every ForkTrigger field plans.py reads EXISTS on the dataclass",
          not bad_f,
          f"read {sorted(fields) or 'none'}; not on ForkTrigger: "
          f"{sorted(bad_f) or 'none'}")

    # ── the sweep object Rule 4 interrogates ──────────────────────────────
    msrc = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
    mtree = ast.parse(msrc)
    fn = next((n for n in ast.walk(mtree)
               if isinstance(n, ast.FunctionDef)
               and n.name == "_sweep_has_rejection"), None)
    sweep_fields = set()
    if fn is not None:
        for n in ast.walk(fn):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id == "getattr" and len(n.args) >= 2
                    and isinstance(n.args[1], ast.Constant)):
                sweep_fields.add(n.args[1].value)
    try:
        from analysis.liquidity_mapper import SweepState as _SW
    except Exception:                                          # noqa: BLE001
        _SW = None
    if _SW is None:
        # Find whatever class actually carries `reclaimed`.
        import analysis.liquidity_mapper as _lm
        _SW = next((getattr(_lm, n) for n in dir(_lm)
                    if isinstance(getattr(_lm, n), type)
                    and "reclaimed" in getattr(getattr(_lm, n),
                                               "__annotations__", {})), None)
    if _SW is None:
        check("X3 the sweep state class was located", False, "not found")
    else:
        real_s = set(getattr(_SW, "__annotations__", {})) | {
            a for a in dir(_SW) if not a.startswith("_")}
        bad_s = sweep_fields - real_s
        check("X3 every sweep field Rule 4 reads EXISTS on the real class",
              not bad_s,
              f"read {sorted(sweep_fields) or 'none'}; not on {_SW.__name__}: "
              f"{sorted(bad_s) or 'none'}")

    # ── no builder may vanish on an exception ─────────────────────────────
    # ⚠️ An exception caught INSIDE a builder never reaches derive()'s handler,
    # so `return None` there is invisible twice over: no row AND no log.
    silent = []
    for n in ast.walk(tree):
        if (isinstance(n, ast.FunctionDef)
                and n.name in ("_butterfly", "_participation", "_sweep",
                               "_runaway", "_condor", "_roll", "_fork")):
            # ⚠️ NESTED HELPERS ARE EXEMPT AND MUST BE. A helper that returns
            # a PRICE uses None to mean "unpriceable", which is correct and is
            # handled by its caller. Only the BUILDER's own except handlers —
            # the ones whose None becomes a missing plan row — are in scope.
            _inner = {id(x) for f in ast.walk(n)
                      if isinstance(f, ast.FunctionDef) and f is not n
                      for x in ast.walk(f)}
            for h in ast.walk(n):
                if isinstance(h, ast.ExceptHandler) and id(h) not in _inner:
                    for st in ast.walk(h):
                        if isinstance(st, ast.Return) and (
                                st.value is None
                                or (isinstance(st.value, ast.Constant)
                                    and st.value.value is None)):
                            silent.append(f"{n.name}:{st.lineno}")
    check("X4 no builder returns None from an except — every failure speaks",
          not silent, ", ".join(silent) or "none")

    # ── 🔴 X5 — A RAISING BUILDER MUST BE LOUD AND MUST LEAVE A ROW ──────
    # ⚠️ IronCondor produced NO row and NO INFO line for a whole session. The
    # only shape that fits is a raise in derive()'s handler — which logged at
    # DEBUG into a journal handler set to INFO, so the exception appeared
    # NOWHERE. plan_tick, journalctl and logs/ all came back empty in a way
    # that looked exactly like "this builder does not exist".
    import ast as _a
    _d = next(n for n in _a.walk(tree)
              if isinstance(n, _a.FunctionDef) and n.name == "derive")
    _du = _a.unparse(_d)
    check("X5 derive() logs a raising builder at WARNING, not DEBUG",
          "logger.warning" in _du and "logger.debug" not in _du)

    check("X6 a raising builder still yields a plan row",
          "verdict': 'NO PLAN'" in _du or '"verdict": "NO PLAN"' in _du,
          "raise -> NO PLAN row")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_fixture_fidelity: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
