#!/usr/bin/env python3
"""tests/check_blind_open_grace.py  v1.0
BLIND.1 — NO "BOT IS BLIND" PAGE FOR A LATE FIRST BAR AT THE OPEN; A DEAD FEED STILL PAGES.

v1.0  2026-10-09  r477. CVX paged blind at 09:31 on 10-08 and 10-09 and healed 61 s later:
      the vendor sent no regular-hours 09:30 candle for CVX while the feed was alive.
      Operator: start the check later, without touching the opening-range path.

Drives the REAL utils.blindness_latch.BlindnessLatch with real epoch times in US Eastern,
on the bot's 15 s tick, with the record shape market_data.record_blindness writes.

  G1  the CVX morning, replayed: blind from 09:30:04 every tick until the first bar at
      09:31:15 -> NO ALERT and NO RECOVERED (nothing reached the phone, nothing to clear)
  G2  a feed DEAD through the open: blind from 09:30:04 onward -> no alert before 09:32,
      then ALERT by 09:32:45 (the usual 45 s / 3 ticks counted from 09:32)
  G3  UNCHANGED mid-session: blind at 11:00:00 -> ALERT at the usual 45 s; RECOVERED after
  G4  a late first bar inside the grace but past the old threshold (09:31:50) -> no alert
  G5  the data path is untouched: data/market_data.py (which serves the bars to the
      opening-range engine) neither imports the latch nor knows the grace

Run:  python3 tests/check_blind_open_grace.py
"""
import datetime as dt
import os
import sys
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
ET = ZoneInfo("America/New_York")
PROBLEMS = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name)


def at(h, m, s=0):
    return dt.datetime(2026, 10, 9, h, m, s, tzinfo=ET).timestamp()


REC = {"cause": "BARS_STALE", "symbol": "CVX", "timeframe": "1m",
       "newest_bar": "2026-10-08 15:59:00-04:00", "age_s": "63064", "limit_s": "180"}


def run(start, end_blind, stop, tick=15.0):
    """Feed the latch a blind record every tick from `start` until `end_blind`
    (exclusive), then sight until `stop`. Returns [(epoch, verdict)] for non-None."""
    from utils.blindness_latch import BlindnessLatch
    lt = BlindnessLatch()
    out, t = [], start
    while t < stop:
        v = lt.update(dict(REC) if t < end_blind else None, now=t)
        if v:
            out.append((t, v))
        t += tick
    return out


def hm(t):
    return dt.datetime.fromtimestamp(t, ET).strftime("%H:%M:%S")


def main():
    print("check_blind_open_grace")
    try:
        import utils.blindness_latch  # noqa: F401
    except Exception as exc:                                        # noqa: BLE001
        print(f"  FAIL  latch import: {type(exc).__name__}: {exc}")
        return 1

    v1 = run(at(9, 30, 4), at(9, 31, 15), at(9, 34))
    check("G1 the CVX morning (first bar 09:31:15): no ALERT, no RECOVERED", v1 == [],
          f"verdicts={[(hm(t), v) for t, v in v1]}")

    v2 = run(at(9, 30, 4), at(9, 40), at(9, 40))
    alerts = [t for t, v in v2 if v == "ALERT"]
    check("G2 a feed dead through the open: ALERT, not before 09:32, by 09:32:45",
          len(alerts) == 1 and at(9, 32) <= alerts[0] <= at(9, 32, 45) + 15,
          f"alerts={[hm(t) for t in alerts]}")

    v3 = run(at(11, 0), at(11, 2), at(11, 5))
    a3 = [t for t, v in v3 if v == "ALERT"]
    r3 = [t for t, v in v3 if v == "RECOVERED"]
    check("G3 unchanged mid-session: ALERT at ~45 s, RECOVERED after",
          len(a3) == 1 and at(11, 0, 45) <= a3[0] <= at(11, 1) and len(r3) == 1,
          f"verdicts={[(hm(t), v) for t, v in v3]}")

    v4 = run(at(9, 30, 4), at(9, 31, 50), at(9, 35))
    check("G4 a first bar at 09:31:50 (past the old 45 s threshold): no alert", v4 == [],
          f"verdicts={[(hm(t), v) for t, v in v4]}")

    md = open(os.path.join(ROOT, "data", "market_data.py"), encoding="utf-8").read()
    check("G5 market_data (the bars the opening range is built from) neither imports the latch nor knows the grace",
          "blindness_latch" not in md and "OPEN_GRACE" not in md, "market_data references the latch/grace")

    print()
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {', '.join(p.split()[0] for p in PROBLEMS)}")
        return 1
    print("GREEN — every check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
