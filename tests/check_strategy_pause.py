#!/usr/bin/env python3
"""tests/check_strategy_pause.py  v1.0
PAUSE.1 — TCS AND ORB TAKE NO NEW ENTRIES FOR THE WEEK OF 2026-10-05.

v1.0  2026-10-04  r471. Operator: "For this week, disable sweep, TCS, and orb",
      then "Re-enable sweep then." config.STRATEGIES_PAUSED names ORB and TCS; main._safe_strategy returns no
      signal for a paused name WITHOUT ASKING the strategy.

  P1  each paused name (ORB, TrendCreditSpread): _safe_strategy returns None and
      the strategy function is NEVER CALLED
  P2  NOT PAUSED: SweepCreditSpread, SweepForLeg2 (re-enabled by the operator),
      RunawayContinuation and GEXPinButterfly are asked and their signal returned
  P3  the default set is exactly those two names (fresh interpreter, override
      unset); OT_PAUSED_STRATEGIES="" pauses nothing
  P4  every dispatch name main.py passes for ORB / TCS is in the set, so a
      rename cannot silently un-pause one

main's file handler is pointed at a scratch log BEFORE `import main`, so this
check never writes into a live bot.log. Run:  python3 tests/check_strategy_pause.py
"""
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_INSTRUMENT", "SYN")
WANT = {"ORB", "TrendCreditSpread"}
PROBLEMS = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name)


def default_set(env_extra):
    env = {k: v for k, v in os.environ.items() if k != "OT_PAUSED_STRATEGIES"}
    env.update(env_extra)
    code = ("import sys; sys.path.insert(0, %r)\nimport config\n"
            "print(sorted(getattr(config, 'STRATEGIES_PAUSED', ['<absent>'])))\n") % ROOT
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                       env=env, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"rc={r.returncode}: {r.stderr[-300:]}")
    return r.stdout.strip().splitlines()[-1]


def main():
    print("check_strategy_pause")
    try:
        import config as _cfg
        _cfg.LOG_FILE = os.path.join(tempfile.mkdtemp(), "bot.log")
        import main as M
    except ImportError as exc:
        print(f"NOT RUN — this interpreter cannot import the trading stack ({exc}); run under the venv")
        return 2

    for name in sorted(WANT):
        called = []
        got = M._safe_strategy(name, lambda: called.append(1) or "SIGNAL")
        check(f"P1 {name}: no signal, strategy never asked",
              got is None and not called, f"returned={got!r} asked={bool(called)}")

    for name in ("SweepCreditSpread", "SweepForLeg2", "RunawayContinuation", "GEXPinButterfly"):
        called = []
        got = M._safe_strategy(name, lambda: called.append(1) or "SIGNAL")
        check(f"P2 {name} unchanged: asked, signal returned",
              got == "SIGNAL" and called, f"returned={got!r} asked={bool(called)}")

    try:
        d = default_set({})
        e = default_set({"OT_PAUSED_STRATEGIES": ""})
        check("P3 default pauses exactly ORB and TCS; an empty override pauses nothing",
              d == str(sorted(WANT)) and e == "[]", f"default={d} empty={e}")
    except Exception as exc:                                    # noqa: BLE001
        check("P3 (did not run)", False, f"{type(exc).__name__}: {exc}")

    src = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
    names = set(re.findall(r'_safe_strategy\("([A-Za-z0-9]+)"', src))
    targets = {n for n in names if re.search(r"ORB|TrendCredit", n)}
    check("P4 every ORB / TCS dispatch name in main.py is paused",
          targets and targets <= getattr(M, "STRATEGIES_PAUSED", set()),
          f"dispatch names={sorted(targets)} paused={sorted(getattr(M, 'STRATEGIES_PAUSED', []))}")

    print()
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {', '.join(p.split()[0] for p in PROBLEMS)}")
        return 1
    print("GREEN — every check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
