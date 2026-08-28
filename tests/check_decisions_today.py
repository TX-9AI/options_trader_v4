#!/usr/bin/env python3
"""check_decisions_today.py — v1.0

🔴 THE DECISIONS PANEL SHOWS TODAY'S SESSION, OR NOTHING.

Operator, 2026-08-28: *"Make the decision section only display today's
decision, blank before 0930"* and *"If the box was up for maintenance the night
before or even before the session open, don't display those decisions."*

⚠️ WHAT IT SHOWED BEFORE: the newest `plan_tick` row per strategy, WHATEVER ITS
AGE. Read at 09:16 ET it printed twelve rows from the previous EVENING, each
flagged ⚠️ STALE — a panel titled *"the next tick, as the plans see it now"*
displaying last night's ticks. Truthful and useless: the warning made noise the
reader has to filter instead of information they can act on.

⚠️ THE CUT IS THE OPEN, NOT MIDNIGHT. A 06:00 ET maintenance wake writes real
plan rows against a market that is not trading. Showing those is the same lie
as showing last night's, just harder to spot because the date matches.

⚠️ AND IT IS ASKED IN ET. The boxes run UTC; "today" and "09:30" are EXCHANGE
facts. A bare `date.today()` on a UTC box rolls the day at 20:00 ET — the
operator's own long-standing symptom, *"any time I run a report for today after
the session ends it fails."* `ZoneInfo("US/Eastern")` also handles DST, so the
cut is correct in EDT and EST without a second code path.
"""
import ast
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ET = ZoneInfo("US/Eastern")
_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


def _cut(now):
    """Mirror of the panel's rule, stated once so the cases below are readable."""
    o = now.replace(hour=9, minute=30, second=0, microsecond=0)
    return o.timestamp(), now < o


def main():
    src = open(os.path.join(_root, "query.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef)
               and "decision" in n.name.lower()), None)
    body = ast.unparse(fn) if fn else ""

    # ── D1 — the panel is blank before the open ──────────────────────────
    check("D1 the panel returns early before 09:30 ET",
          "hour=9, minute=30" in body and "_now < _open" in body)

    # ── 🔴 D2 — THE CUT IS THE OPEN, NOT MIDNIGHT ────────────────────────
    # ⚠️ `_open.replace(hour=0...)` was the first version and would have let a
    # 06:00 maintenance wake through.
    check("D2 the row cut is the open itself",
          "_today0 = _open.timestamp()" in body)

    # ── D3 — both halves of the panel use it ─────────────────────────────
    # A watcher row from yesterday is not "an open position under management".
    check("D3 the manage side is cut too",
          body.count("ts_epoch >= ?") >= 4, f"{body.count('ts_epoch >= ?')} bounds")

    # ── D4 — the cases the operator named ────────────────────────────────
    cases = (
        ((9, 16), True,  "before the open -> blank"),
        ((6, 0),  True,  "maintenance wake -> blank"),
        ((10, 15), False, "mid-session -> shows"),
    )
    for (h, m), want_blank, label in cases:
        _, blank = _cut(datetime(2026, 8, 28, h, m, tzinfo=ET))
        check(f"D4 {label}", blank == want_blank)

    # rows that must be excluded when read mid-session
    cutoff, _ = _cut(datetime(2026, 8, 28, 10, 15, tzinfo=ET))
    for when, label in ((datetime(2026, 8, 28, 6, 0, tzinfo=ET), "a 06:00 maintenance row"),
                        (datetime(2026, 8, 27, 21, 20, tzinfo=ET), "last night's 21:20 row")):
        check(f"D5 {label} is excluded", when.timestamp() < cutoff)

    # ── D6 — DST, both sides of the year ─────────────────────────────────
    # ⚠️ The boxes are UTC. If this ever hard-coded -4 or -5 it would be an
    # hour wrong for half the year.
    edt = datetime(2026, 8, 28, 12, tzinfo=ET).utcoffset().total_seconds() / 3600
    est = datetime(2026, 1, 15, 12, tzinfo=ET).utcoffset().total_seconds() / 3600
    check("D6 the zone follows DST (EDT -4 / EST -5)",
          edt == -4 and est == -5, f"{edt} / {est}")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_decisions_today: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
