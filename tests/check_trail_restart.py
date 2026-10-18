#!/usr/bin/env python3
"""
tests/check_trail_restart.py  v1.0
v1.0  2026-10-18  r493 / EXIT.6 — A RESTART KEEPS THE LOCKED TRAIL.

  _seed_trail_from_record restored the persisted trail_stop but re-armed
  _trail_active only for ADOPTED. For every other strategy (mainline: Runaway,
  orb_trail_stop) the first tick at or above trail_activation took
  _update_trail's first-activation branch and wrote entry x (1 + TRAIL_LOCK_PCT)
  over the recovered level. Found by OTV4TEST's 2026-10-18 audit
  (MSG-QQQ-1018-04; its repro: entry 1.00, peak 2.00, trail 1.50, mark 1.45 ->
  continuous exits, a fresh engine HOLDS at 1.0875).

  Drives the REAL ExitEngine.evaluate (clock pinned off the hard close):
  T1  Runaway: the uninterrupted engine's trail sequence over 1.10 .. 1.70 is
      byte-for-byte the pre-r493 one (pinned values) and exits at 1.70
  T2  a restart after the 2.40 tick (persisted 1.92, peak 2.40) exits at 1.70
      exactly as the uninterrupted engine does (pre-r493: HOLD, trail 1.4625)
  T3  the recovered level is never lowered by the first armed tick (1.95)
  T4  OTV4TEST's repro (entry 1.00, peak 2.00, trail 1.50, mark 1.45) exits
  T5  no peak on the row: a recovered level at/above the activation seed arms
  T6  a PRE-activation FVG level (peak below trail_activation) stays un-armed:
      the restart then follows the uninterrupted engine through activation
  T7  ADOPTED still re-arms (unchanged)

Run:  python3 tests/check_trail_restart.py   (exit 0 green, 1 red)
"""
import glob as _glob
import logging
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)
os.environ.setdefault("OT_INSTRUMENT", "QQQ")

FAILED = []

# the pre-r493 uninterrupted sequence, measured on 0bd66e9: (mark, trail, exit)
PINNED = [(1.10, 0.0, False), (1.30, 1.04, False), (1.55, 1.25, False),
          (1.90, 1.52, False), (2.40, 1.92, False), (1.95, 1.92, False),
          (1.70, 1.92, True)]


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def rec(tid, strategy="RunawayContinuation", act=1.50, **kw):
    r = {"trade_id": tid, "symbol": "QQQ", "strategy": strategy, "setup_type": "x",
         "direction": "long", "option_side": "call", "contracts": 10,
         "entry_premium": 1.00, "stop_premium": 0.80, "target_premium": 3.0,
         "trail_activation": act, "underlying_entry": 720.0, "underlying_stop": 0.0,
         "underlying_target": 725.0, "status": "open", "is_butterfly": 0,
         "is_condor_leg": 0, "trail_stop": 0.0}
    r.update(kw)
    return r


def main():
    logging.disable(logging.CRITICAL)
    import execution.exit_engine as XE
    from execution.exit_engine import ExitEngine
    XE.is_hard_close_time = lambda *a, **k: False

    def trail(e, tid):
        return round(float(e._trail_stops.get(tid, 0.0) or 0.0), 4)

    # T1 — the uninterrupted path, pinned
    a = ExitEngine(paper_trading=True)
    seq = []
    for px, _, _ in PINNED:
        d = a.evaluate(rec("u1"), px)
        seq.append((px, trail(a, "u1"), bool(d.should_exit)))
    check("T1 the uninterrupted trail sequence is the pre-r493 one", seq == PINNED,
          f"got {seq}")

    # T2 / T3 — restart after the 2.40 tick: persisted 1.92, peak 2.40
    b = ExitEngine(paper_trading=True)
    r = rec("r1", trail_stop=1.92, mfe_premium=2.40, max_premium_seen=2.40)
    d1 = b.evaluate(dict(r), 1.95)
    t_after = trail(b, "r1")
    d2 = b.evaluate(dict(r), 1.70)
    check("T2 a restart exits at 1.70 exactly as the uninterrupted engine does",
          (not d1.should_exit) and d2.should_exit and "orb_trail_stop" in (d2.exit_reason or ""),
          f"1.95 -> exit={d1.should_exit}; 1.70 -> exit={d2.should_exit} {d2.exit_reason!r} "
          f"trail={trail(b, 'r1')}")
    check("T3 the first armed tick after a restart keeps 1.92", t_after == 1.92,
          f"trail after 1.95 = {t_after} (pre-r493: 1.4625)")

    # T4 — OTV4TEST's repro
    c = ExitEngine(paper_trading=True)
    d = c.evaluate(rec("q1", act=1.20, trail_stop=1.50, mfe_premium=2.00), 1.45)
    check("T4 OTV4TEST's repro (peak 2.00, trail 1.50, mark 1.45) exits",
          d.should_exit, f"exit={d.should_exit} trail={trail(c, 'q1')}")

    # T5 — no peak on the row, level at/above the activation seed (1.25)
    e5 = ExitEngine(paper_trading=True)
    d = e5.evaluate(rec("n1", act=1.20, trail_stop=1.50), 1.45)
    check("T5 no peak: a recovered 1.50 (>= seed 1.25) arms and exits at 1.45",
          d.should_exit, f"exit={d.should_exit} trail={trail(e5, 'n1')}")

    # T6 — a pre-activation FVG level: restart after the 1.30 tick (persisted
    # 1.04, peak 1.30 < 1.50); the activation tick must seed 1.25 as T1 does
    f = ExitEngine(paper_trading=True)
    r6 = rec("p1", trail_stop=1.04, mfe_premium=1.30, max_premium_seen=1.30)
    f.evaluate(dict(r6), 1.55)
    t6 = trail(f, "p1")
    check("T6 a pre-activation FVG level stays un-armed; activation seeds 1.25",
          t6 == 1.25, f"trail after 1.55 = {t6} (uninterrupted: 1.25)")

    # T7 — ADOPTED unchanged
    g = ExitEngine(paper_trading=True)
    g._seed_trail_from_record(rec("a1", strategy="ADOPTED", trail_stop=1.10))
    check("T7 ADOPTED still re-arms its trail flag", g._trail_active.get("a1") is True,
          f"_trail_active={g._trail_active.get('a1')!r}")

    print()
    if FAILED:
        print(f"RED: {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
