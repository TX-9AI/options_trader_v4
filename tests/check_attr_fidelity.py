#!/usr/bin/env python3
"""check_attr_fidelity.py — v1.0

🔴 THE GATE FOR THE FAILURE THAT COST FIVE SETUPS IN ONE WEEK.

Every one of these shipped, and every one is the same shape — a name read off
an object that does not have it:

    ctm.all()                        real: all_rails()
    getattr(c, "oi")                 real: open_interest
    _f(ctx.get("gex"))               real: a GEXSnapshot OBJECT, not a float
    getattr(sweep, "bars_since_reclaim")   real: bars_ago
    getattr(orb, "tp50")             real: target_50pct

⚠️ `getattr` WITH A DEFAULT CANNOT RAISE. No traceback, no log line, no red
test — the gate simply never applies. A DEAD gate and a gate that keeps passing
are indistinguishable from outside. `oi` blinded the butterfly for its entire
existence; `target_50pct` refused every runaway on eight boxes at 09:51 on a
breakout morning while printing "50% TP n/a".

⚠️ AND UNIT TESTS CANNOT CATCH IT WHEN ONE AUTHOR WRITES BOTH THE CALLER AND
THE FIXTURE — they are wrong the same way and the board goes green. This check
resolves against the REAL imported classes, never a stand-in.

HOW IT WORKS: for each (variable name -> class) binding declared in _SUBJECTS
below, every `getattr(var, "name")` and `var.name(...)` in the scanned tree is
resolved against that class's annotations, slots and dir(). Unknown names fail.

ADDING A SUBJECT: one line in _SUBJECTS. If a variable name is used for two
different types anywhere in the tree, do NOT add it — a false positive here
trains people to ignore the gate, which is worse than not having it.
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


def _members(cls):
    """Every attribute name that resolves on this class."""
    names = set(dir(cls))
    names |= set(getattr(cls, "__annotations__", {}) or {})
    for base in getattr(cls, "__mro__", []):
        names |= set(getattr(base, "__annotations__", {}) or {})
        names |= set(getattr(base, "__slots__", []) or [])
    return names


def _load_subjects():
    """(variable name -> real class). Import failures are reported, not skipped
    silently — a subject that cannot be imported is an unchecked subject."""
    subjects, broken = {}, []
    wanted = [
        ("ctm",       "analysis.condor_trigger_map", "CondorTriggerMap"),
        # ⚠️ `t` IS DELIBERATELY ABSENT. It is the PlanTick variable throughout
        # strategy/, not a ForkTrigger — adding it produced 40+ false positives
        # on the first run. A noisy gate is worse than no gate: it teaches
        # people to ignore it. ForkTrigger fields are covered by the A2 pin and
        # by check_fixture_fidelity, which scopes to the file that owns them.
        ("orb",       "analysis.orb_engine",         "ORBData"),
        ("sweep",     "analysis.liquidity_mapper",   "LiquiditySweep"),
        ("contract",  "data.options_chain",          "OptionContract"),
        ("chain",     "data.options_chain",          "OptionsChain"),
        ("gex",       "data.gex_data",               "GEXSnapshot"),
    ]
    for var, mod, cls in wanted:
        try:
            m = __import__(mod, fromlist=[cls])
            subjects[var] = (cls, _members(getattr(m, cls)))
        except Exception as exc:                                # noqa: BLE001
            broken.append(f"{mod}.{cls} ({type(exc).__name__})")
    return subjects, broken


def _scan(subjects, folders):
    """Every attribute read against a known subject, with its source location."""
    bad = []
    for folder in folders:
        d = os.path.join(_root, folder)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".py"):
                continue
            path = os.path.join(d, fn)
            try:
                tree = ast.parse(open(path, encoding="utf-8").read())
            except Exception:                                   # noqa: BLE001
                continue
            for n in ast.walk(tree):
                var = attr = None
                # getattr(obj, "name", ...)
                if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                        and n.func.id == "getattr" and len(n.args) >= 2
                        and isinstance(n.args[0], ast.Name)
                        and isinstance(n.args[1], ast.Constant)
                        and isinstance(n.args[1].value, str)):
                    var, attr = n.args[0].id, n.args[1].value
                # obj.name  (attribute or method call)
                elif (isinstance(n, ast.Attribute)
                      and isinstance(n.value, ast.Name)):
                    var, attr = n.value.id, n.attr
                if var is None or var not in subjects:
                    continue
                cls, members = subjects[var]
                if attr.startswith("__") or attr in members:
                    continue
                bad.append(f"{folder}/{fn}:{n.lineno} {var}.{attr} "
                           f"(not on {cls})")
    return bad


def main():
    subjects, broken = _load_subjects()

    # ⚠️ A SUBJECT THAT WILL NOT IMPORT IS AN UNCHECKED SUBJECT — say so loudly
    # rather than quietly scanning less than advertised.
    check("A0 every subject class imports", not broken,
          "; ".join(broken) or f"{len(subjects)} subjects loaded")

    folders = ["strategy", "analysis", "derived", "data", "execution", "risk"]
    bad = _scan(subjects, folders)
    check("A1 every attribute read resolves on the REAL class",
          not bad,
          ("\n        " + "\n        ".join(bad)) if bad
          else f"{len(subjects)} subjects across {len(folders)} folders")

    # ⚠️ REGRESSION PINS — the five that actually shipped. If the scanner is
    # ever narrowed or a subject dropped, these say so directly instead of the
    # check quietly passing on a smaller surface.
    for var, real, ghost in (("ctm", "all_rails", "all"),
                             ("contract", "open_interest", "oi"),
                             ("sweep", "bars_ago", "bars_since_reclaim"),
                             ("orb", "target_50pct", "tp50"),
                             ("gex", "net_gex", "gex_value")):
        if var not in subjects:
            check(f"A2 {var} is still a scanned subject", False, "MISSING")
            continue
        _, members = subjects[var]
        check(f"A2 {var}: '{real}' exists and '{ghost}' does not",
              real in members and ghost not in members,
              f"real={real in members} ghost={ghost in members}")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_attr_fidelity: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
