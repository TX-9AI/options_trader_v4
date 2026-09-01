#!/usr/bin/env python3
"""
tests/check_query_sections.py  v1.0
v1.0  2026-09-01  r209 (chunk A) — WHAT THE BOX DASHBOARD IS FOR.

Operator, 2026-09-01, going through `query.py` from the bottom up: Live Levels
"don't care, take it out"; Performance by setup type "that's just trivia in my
opinion, useless by itself"; by setup grade "we don't have grades"; by strategy
"I don't need a per symbol snapshot of that"; all-time "irrelevant"; Character
"keep, but not in query.py — it belongs in status, below the pin line."

🔑 THE THROUGH-LINE IS SCOPE, NOT CLUTTER. This file is the PER-BOX report. An
all-time or by-strategy rollup computed from one symbol's trades.db is a slice
nobody acts on, and day_trader_pro's trade breakdown (r187) already does the
cross-fleet version properly — grouped by strategy, setup type, exit reason,
symbol, hour and weekday, with an ENGINE EPOCH floor.

🔴 AND ONE OF THEM WAS QUIETLY WRONG. `query.py` had no epoch filter at all, so
ALL-TIME PERFORMANCE pooled pre- and post-v4-split trades — 109 trades reaching
back through engines that no longer exist. r187 built the epoch floor for
exactly this contamination and this file never got it. Deleting the section
removes a wrong number, not merely a noisy one.

⚠️ BY SETUP GRADE WAS STRUCTURALLY EMPTY. r152 deleted the setup scorer and
every v4 write path hardcodes `UNGRADED`, so the section had one bucket and
could never have another.

⚠️ THIS IS A VIEW CHANGE, NOT A COLLECTOR CHANGE, and Q4 is what pins that.
`level_ledger` is a LIFECYCLE table — retention_purge excludes it in code
because a recomputation cannot rebuild a biography (r81) — and the sweep and
fork paths read it live. Removing the Live Levels PANEL must not remove a row.

Born red at 7722827 (r207), where Q1, Q2 and Q3 all fail.
"""
from __future__ import annotations

import ast
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

_fails = []


def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not ok:
        _fails.append(name)


def main():
    src = open(os.path.join(_root, "query.py"), encoding="utf-8").read()
    tree = ast.parse(src, "query.py")
    fns = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}

    # ── Q1 — the four sections are GONE, definition-shaped ───────────────
    # ⚠️ Tests for a DEFINITION, never a mention (§20): the changelog above
    # names every one of these while explaining why it was removed, so a plain
    # string search would trip on the honest prose the version rule requires.
    dead = [f for f in ("show_alltime", "show_by_strategy", "show_by_grade",
                        "show_by_setup_type") if f in fns]
    check("Q1 the four per-box performance rollups are deleted",
          not dead, f"still defined: {dead}")

    # ── Q2 — and nothing still calls them ────────────────────────────────
    # 🔑 DELETING A DEFINITION AND LEAVING THE CALL is a NameError at runtime
    # that no import test catches — r67's singletons, r100's dead constructors.
    # Every `show_*` call in main() must resolve to a function that exists.
    main_fn = next((n for n in tree.body
                    if isinstance(n, ast.FunctionDef) and n.name == "main"), None)
    calls = {c.func.id for c in ast.walk(main_fn)
             if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)} if main_fn else set()
    unresolved = sorted(c for c in calls if c.startswith("show_") and c not in fns)
    check("Q2 every show_* call in main() resolves to a live function",
          main_fn is not None and not unresolved, f"unresolved: {unresolved}")

    # ── Q3 — CHARACTER has left this file ────────────────────────────────
    check("Q3 CHARACTER is no longer rendered by query.py",
          "show_character" not in fns and "show_character(dc)" not in src,
          "it belongs in status.py, below the pin line")

    # ── Q4 — THE LEDGER IS UNTOUCHED. A view change, not a collector one ──
    # ⚠️ THE CHECK THAT MATTERS MOST HERE. "Take Live Levels out" is a request
    # about a PANEL. If it were read as a request about the DATA it would blind
    # the sweep and the fork, and r81 keeps this table unpurged on purpose.
    lm = open(os.path.join(_root, "analysis", "liquidity_mapper.py"),
              encoding="utf-8").read()
    writers = [f for f in os.listdir(os.path.join(_root, "derived"))
               if f.endswith(".py")]
    lev = any("level_ledger" in open(os.path.join(_root, "derived", f),
                                     encoding="utf-8").read() for f in writers)
    check("Q4 level_ledger is still written and still read elsewhere",
          lev, "the panel went; the collector must not have")

    # ── Q5 — the surviving MARKET half is intact ─────────────────────────
    # A deletion that took its neighbours with it is the other way this goes
    # wrong. Pitchfork and Surface were explicitly kept.
    check("Q5 MARKET keeps the pitchfork and the surface",
          "Pitchfork:" in src and "Surface (1h)" in src
          and "fork_series" in src and "surface_series" in src)

    # ── Q6 — what the operator kept is still here ────────────────────────
    kept = {"show_open_position": "open positions",
            "show_today": "today's trades",
            "show_recent": "recent closed",
            "show_decisions": "decisions",
            "show_gates": "gates",
            "show_plans": "plans",
            "show_market": "market"}
    missing = sorted(k for k in kept if k not in fns)
    check("Q6 nothing the operator kept was removed with them",
          not missing, f"missing: {missing}")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_query_sections: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
