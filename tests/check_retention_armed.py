#!/usr/bin/env python3
"""check_retention_armed.py — v1.0 (landed r162)

🔴 THE NIGHTLY PURGE MUST ACTUALLY DELETE.

`warehouse/retention_purge.py` shipped DRY BY DEFAULT, armed only by
`OT_RETENTION_APPLY=1`, pending a review of the policy numbers that was never
scheduled. `self_close` called `main([])` — an EMPTY argv, with no environment
set — so **the purge ran dry every night for two months, printed what it WOULD
delete, and deleted nothing.**

⚠️ THE COST, 2026-08-27: `feed_store.db` reached 1.5–1.8 GB per box, the 6.7
GiB roots hit 100%, and the fleet went blind MID-SESSION during RTH. QQQ and MU
crash-looped; recovering them cost their swapfiles, a failed VACUUM that left
the database LARGER, and a 14-box volume rebuild.

⚠️ AND IT WAS INVISIBLE BY CONSTRUCTION. A dry run logs the same line every
night at INFO. **Sixty identical log lines are indistinguishable from a job
that works** — nobody reads an unchanging line. Same failure class as the
pytest chain that was decorative for weeks and the tooling check that printed
green on a broken environment: a green light nobody read.

WHAT THIS PINS:
  R1  `self_close` passes `--apply` — arming is EXPLICIT at the call site, not
      ambient in an environment nobody sets.
  R2  `main()` honours it.
  R3  a hand-run is still DRY (a human must ask before deleting).
  R4  a dry purge with rows pending is LOUD, so the next silence is visible.
"""
import ast
import contextlib
import io
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
    sc = open(os.path.join(_root, "warehouse", "self_close.py"),
              encoding="utf-8").read()
    code = "\n".join(l for l in sc.split("\n")
                     if not l.strip().startswith("#"))

    # ── 🔴 R1 — THE SHUTDOWN PATH ARMS IT ────────────────────────────────
    # ⚠️ Match CODE, not the comment that explains the fix — that comment
    # quotes the old `main([])` call.
    check("R1 self_close calls the purge with --apply",
          'retention_purge.main(["--apply"])' in code)
    check("R1b the un-armed call is gone",
          "retention_purge.main([])" not in code)

    # ── R2/R3 — the flag works, and a hand-run does not delete ───────────
    os.environ.pop("OT_RETENTION_APPLY", None)
    from warehouse import retention_purge as rp
    _real = rp.purge
    rp.purge = lambda apply=False: {"quote_series": 1000, "prints": 500}
    try:
        b = io.StringIO()
        with contextlib.redirect_stdout(b):
            rp.main(["--apply"])
        armed = b.getvalue()
        check("R2 --apply arms the purge",
              "removed 1,500" in armed and "WOULD" not in armed)

        b = io.StringIO()
        with contextlib.redirect_stdout(b):
            rp.main([])
        dry = b.getvalue()
        # ⚠️ A HUMAN MUST ASK. Defaulting a hand-run to delete is how someone
        # purges a box they were only inspecting.
        check("R3 a hand-run with no flag is still DRY",
              "WOULD remove" in dry)
        # ── 🔴 R4 — AND IT IS LOUD ABOUT IT ──────────────────────────────
        check("R4 a dry purge with rows pending warns explicitly",
              "RETENTION IS DRY" in dry and "NOT removed" in dry)
    finally:
        rp.purge = _real

    # ── R5 — VACUUM is still not run, deliberately ───────────────────────
    # ⚠️ NOT AN OVERSIGHT. VACUUM rewrites the whole file and would stall the
    # box for minutes at close. With the purge ARMED, SQLite reuses freed
    # pages and the file reaches steady state — VACUUM is only needed if the
    # retention windows are shortened and the difference is wanted back as
    # disk. A purge that blocks the halt is worse than a larger file.
    # ⚠️ PARSE, DO NOT GREP. The first version stripped comment LINES and then
    # searched for the word — which the module DOCSTRING contains (it recounts
    # the failed VACUUM of 2026-08-27), so the check went red on prose. Walk
    # the AST for an actual execute("VACUUM") call instead.
    import ast as _ast
    rp_tree = _ast.parse(open(os.path.join(_root, "warehouse",
                                           "retention_purge.py"),
                              encoding="utf-8").read())
    _vac = [n for n in _ast.walk(rp_tree)
            if isinstance(n, _ast.Call)
            and any(isinstance(a, _ast.Constant)
                    and isinstance(a.value, str)
                    and "vacuum" in a.value.lower() for a in n.args)]
    check("R5 VACUUM is still not EXECUTED at shutdown",
          not _vac, f"{len(_vac)} vacuum call(s)")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_retention_armed: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
