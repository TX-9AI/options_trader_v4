#!/usr/bin/env python3
"""
tests/check_trail_activation_keep.py  v1.0
v1.0  2026-10-20  r497 / EXIT.7 — THE 50% TRAIL'S FIRST TICK NEVER LOWERS THE STOP.

  On the tick the 50% trail activates, _update_fvg_trail writes first (armed at +20%:
  >= 80% of the mark) and _update_trail's first-activation branch then wrote
  entry x 1.25 OVER it, against the code's own "the higher of the two governs".
  Measured 10-20 by replaying the 124 mainline Runaway/ORB trades that reached
  activation (09-01..10-13) through the real engine both ways: lowered on 72 of
  103 activations, 17 exits change, net +$767.

  Drives the REAL ExitEngine.evaluate (Runaway, no bars: the FVG trail is its %
  floor, mark x 0.80, clamped at 0.90; clock pinned off the hard close).
  Entry 1.00, trail_activation 1.50, target 2.00:
  K1  1.45 then 1.70: the activation tick keeps the FVG trail 1.36
      (pre-r497: 1.275 = max(1.25 seed, 0.75 x 1.70))
  K2  ... then 1.32: exits on orb_trail_stop (pre-r497: HOLD above 1.275)
  K3  a post-target trail is kept: 2.10 (post-target trail 0.75 x 2.10 = 1.575) then
      1.90 below target — the first activation keeps 1.575 (pre-r497: 1.425)
  K4  control: where the seed is the higher (the stored FVG 1.24 at 1.55) it still
      seeds 1.25, and the 0.75 ratchet still raises the trail after activation
  K5  control: below activation (1.45) nothing is armed and the trail is the FVG one
  K6  every first activation logs the level it chose; it names the kept trail
      when the stored one won
  (OTV4TEST critique MSG-QQQ-1020-29:)
  K7  a restart with a persisted PRE-activation level ABOVE the seed (1.30, peak
      1.45 < 1.50) keeps 1.30 at activation (1.55), exactly as an uninterrupted
      engine holding 1.30 does (pre-r497: both 1.25)

Run:  python3 tests/check_trail_activation_keep.py   (exit 0 green, 1 red)
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


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


def rec(tid, **kw):
    r = {"trade_id": tid, "symbol": "QQQ", "strategy": "RunawayContinuation",
         "setup_type": "x", "direction": "long", "option_side": "call", "contracts": 10,
         "entry_premium": 1.00, "stop_premium": 0.80, "target_premium": 2.00,
         "trail_activation": 1.50, "underlying_entry": 720.0, "underlying_stop": 0.0,
         "underlying_target": 725.0, "status": "open", "is_butterfly": 0,
         "is_condor_leg": 0, "trail_stop": 0.0}
    r.update(kw)
    return r


class _Cap(logging.Handler):
    def __init__(self):
        super().__init__(logging.INFO)
        self.lines = []

    def emit(self, record):
        self.lines.append(record.getMessage())


def main():
    import execution.exit_engine as XE
    from execution.exit_engine import ExitEngine
    XE.is_hard_close_time = lambda *a, **k: False
    cap = _Cap()
    XE.logger.addHandler(cap)
    XE.logger.setLevel(logging.INFO)
    XE.logger.propagate = False

    def trail(e, tid):
        return round(float(e._trail_stops.get(tid, 0.0) or 0.0), 4)

    def run(tid, marks):
        e, r, out = ExitEngine(paper_trading=True), rec(tid), []
        for px in marks:
            d = e.evaluate(r, px)
            out.append((px, trail(e, tid), bool(d.should_exit), d.exit_reason or ""))
            if d.should_exit:
                break
        return e, out

    # K1 / K2 — the FVG trail survives activation, and the trade exits inside the gap
    e, out = run("k1", [1.45, 1.70, 1.32])
    t17 = out[1][1] if len(out) > 1 else None
    check("K1 the activation tick keeps the FVG trail 1.36", t17 == 1.36,
          f"trail after 1.70 = {t17} (pre-r497: 1.275)")
    last = out[-1]
    check("K2 then 1.32 exits on orb_trail_stop", last[0] == 1.32 and last[2]
          and "orb_trail_stop" in last[3], f"path={out}")

    # K3 — a post-target trail is not overwritten when the mark falls back below target
    e3, out3 = run("k3", [1.45, 2.10, 1.90])
    pt = out3[1][1]
    t19 = out3[2][1] if len(out3) > 2 else None
    check("K3 a post-target trail survives the first activation below target",
          pt == 1.575 and t19 == 1.575,
          f"post-target {pt}, after 1.90 {t19} (pre-r497: 1.425)")

    # K4 — control: the seed governs when it is the higher, the ratchet still ratchets
    e4, out4 = run("k4", [1.30, 1.55, 1.90])
    check("K4 the seed still governs when higher (1.25 over the stored 1.24); the ratchet "
          "raises it (1.52 at 1.90)",
          [x[1] for x in out4] == [1.04, 1.25, 1.52] and not any(x[2] for x in out4),
          f"path={out4}")

    # K5 — control: below activation nothing arms
    e5, out5 = run("k5", [1.45])
    check("K5 below activation: un-armed, the FVG trail 1.16 stands",
          out5[0][1] == 1.16 and not e5._trail_active.get("k5"), f"path={out5} "
          f"armed={e5._trail_active.get('k5')}")

    # K7 — restart and no-restart agree when the stored level is above the seed
    g = ExitEngine(paper_trading=True)
    rr = rec("k7", trail_stop=1.30, mfe_premium=1.45, max_premium_seen=1.45)
    g.evaluate(dict(rr), 1.55)
    h = ExitEngine(paper_trading=True)
    h._trail_stops["k7"] = 1.30                     # uninterrupted, same stored level
    h.evaluate(rec("k7"), 1.55)
    check("K7 a restart's persisted 1.30 (pre-activation) is kept at activation, as the "
          "uninterrupted engine keeps it", trail(g, "k7") == 1.30 and trail(h, "k7") == 1.30
          and g._trail_active.get("k7") is True,
          f"restart {trail(g, 'k7')} uninterrupted {trail(h, 'k7')} (pre-r497: 1.25, 1.25)")

    # K6 — the log line
    acts = [ln for ln in cap.lines if "TRAIL ACTIVATED" in ln]
    named = [ln for ln in acts if "k1"[:8] in ln]
    check("K6 the activation logs its level and names a kept trail",
          any("initial_trail=$1.36" in ln and "kept the stored trail" in ln for ln in named)
          and any("initial_trail=$1.25" in ln and "kept" not in ln for ln in acts),
          f"lines={acts}")

    print()
    if FAILED:
        print(f"RED: {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
