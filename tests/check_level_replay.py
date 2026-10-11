#!/usr/bin/env python3
"""
tests/check_level_replay.py  v1.0
v1.0  2026-10-11  r480 / LVL.16 + LVL.20 — A LATE LEVEL IS JUDGED ON THE WHOLE
      STORED SESSION; THE RECORD-ONLY TABLE KEEPS ITS SIDE AND COUNTS BARS.

🔴 LVL.16. A level admitted after bars were consumed (a mid-session name, or
every level a bake re-seeded) started at zero and was flagged `partial`, which
STARVES the named sweep. The flag's premise was that only control holds the
tape. The box's `feed_store.db` keeps the whole session's 1m bars, so the late
level is now REPLAYED through the same counter. The proof is EQUIVALENCE: a
level that joins at 13:00 must end the day with exactly the counters of the
same level present from 09:30.
🔴 LVL.20. `derived/levels.py` re-derived a named pool's side from live price
every tick, so price crossing a resistance pool turned it into support, which
can never be accepted through. And it counted on the FORMING 5m bar every tick.
Both are record-only, and dtp's sweep forensics reads `touch_count`.

  R1  a level joining at 13:00 (store stubbed) ends EQUAL to one present from
      09:30: touches, holds, breaches, contact_bars, visit state, last result
  R1b at admission it already equals the from-open level at 13:00, so the
      replay stops at `last_bar_ts` and nothing is counted twice
  R2  a store that starts at 10:15 leaves the level `partial` (box says so)
  R3  a store that cannot answer leaves `partial`, counters zero (r378 path)
  R4  a store with no 09:30 bar but a 09:31 one is covered (BLIND.1 grace)
  R5  a frame that starts after a gap (a bake longer than the frame) is
      backfilled from the store, oldest first; the book ends EQUAL to the
      unbroken one
  R6  a cold book whose frame starts at 12:00 is backfilled from the open
  R7  the restart path: same-date hydrate + a NEW seed is replayed, not zeroed
  D1  a resistance pool keeps its side after price crosses it, and two
      closed 5m bars beyond retire it ACCEPTED_THROUGH
  D2  one CLOSED 5m bar counts once across many ticks; the forming bar is
      never counted
  D3  a restarted engine RESUMES today's row; yesterday's row at the same id
      does not resume
  S1  the sweep records `level_visit_open` and `level_hold_age_min`, both
      record-only (no gate), and the age is None, never 0, with no resolved test

Run:  python3 tests/check_level_replay.py
"""
import ast
import os
import random
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
os.environ["OT_LEDGER_ROOT"] = tempfile.mkdtemp(prefix="lvl_replay_")
os.environ["OT_LEVEL_HISTORY_ROOT"] = tempfile.mkdtemp(prefix="lvl_hist_")

import pandas as pd                                             # noqa: E402

import analysis.liquidity_ledger as ll                          # noqa: E402

FAILS = []
DATE = "2026-09-14"
LEVEL = 100.0


def check(name, ok, det=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {det}" if det else ""))
    if not ok:
        FAILS.append(name)


def session(start="09:30", end="15:59"):
    """A deterministic 1m session wandering across LEVEL, many visits."""
    idx = pd.date_range(f"{DATE} {start}", f"{DATE} {end}", freq="1min",
                        tz="America/New_York")
    rnd = random.Random(480)
    px, rows = 101.0, []
    for _ in idx:
        px += rnd.uniform(-0.35, 0.35) + (LEVEL + 0.8 - px) * 0.04
        hi, lo = px + rnd.uniform(0.02, 0.3), px - rnd.uniform(0.02, 0.3)
        rows.append((px, hi, lo, px + rnd.uniform(-0.1, 0.1)))
    return pd.DataFrame(rows, index=idx, columns=["open", "high", "low", "close"])


TAPE = session()


def as_store(df):
    return [(str(ts), float(r["high"]), float(r["low"]), float(r["close"]))
            for ts, r in df.iterrows()]


def stub(bars):
    ll._store_session_bars = lambda sym, date: (None if bars is None else list(bars))


def feed(led, df):
    """The production entry point: frame plus one forming row."""
    led.feed_frame(pd.concat([df, df.iloc[-1:]]) if len(df) else df)


def state(lv):
    return (lv.touches, lv.holds, lv.breaches, lv.contact_bars, lv.visit_open,
            lv.visit_bars, lv.last_result, lv.last_touch)


def fresh():
    led = ll.LiquidityLedger("TEST")
    led.date = DATE
    return led


def lvl(led, price=LEVEL):
    return [x for x in led.levels if x.price == price][0]


def frame_upto(hm):
    return TAPE[TAPE.index <= pd.Timestamp(f"{DATE} {hm}", tz="America/New_York")]


def frame_from(hm):
    return TAPE[TAPE.index >= pd.Timestamp(f"{DATE} {hm}", tz="America/New_York")]


print("\ncheck_level_replay\n")
stub(as_store(TAPE))

# ── reference: the level present from the open ──────────────────────────────
ref = fresh()
ref.add_level(LEVEL, "low", "PDL", True)
ref.add_level(120.0, "high", "FAR", True)          # keeps the book non-trivial
feed(ref, frame_upto("13:00"))
ref_13 = state(lvl(ref))
feed(ref, TAPE)
ref_end = state(lvl(ref))
check("R0  the tape actually tests the level (fixture is not vacuous)",
      ref_end[0] >= 3 and ref_end[1] >= 1, f"{ref_end[:3]}")

# ── R1/R1b — the same level admitted at 13:00 ───────────────────────────────
late = fresh()
late.add_level(120.0, "high", "FAR", True)
feed(late, frame_upto("13:00"))
late.add_level(LEVEL, "low", "PDL", True)
at_join = state(lvl(late))
check("R1b at admission the late level equals the from-open level at 13:00",
      at_join == ref_13 and lvl(late).partial is False,
      f"late {at_join} vs ref {ref_13}, partial={lvl(late).partial}")
feed(late, TAPE)
check("R1  a level joining at 13:00 ends EQUAL to one present from 09:30",
      state(lvl(late)) == ref_end, f"late {state(lvl(late))} vs ref {ref_end}")

# ── R2 — a store that does not reach the open ───────────────────────────────
stub(as_store(frame_from("10:15")))
s2 = fresh()
feed(s2, frame_upto("13:00"))
s2.add_level(LEVEL, "low", "PDL", True)
check("R2  a store starting 10:15 leaves the level partial", lvl(s2).partial is True)

# ── R3 — a store that cannot answer ─────────────────────────────────────────
stub(None)
s3 = fresh()
feed(s3, frame_upto("13:00"))
s3.add_level(LEVEL, "low", "PDL", True)
check("R3  no store -> partial, counters zero (the r378 path)",
      lvl(s3).partial is True and lvl(s3).touches == 0,
      f"partial={lvl(s3).partial} touches={lvl(s3).touches}")

# ── R4 — no 09:30 candle, a 09:31 one (BLIND.1) ─────────────────────────────
stub(as_store(frame_from("09:31")))
s4 = fresh()
feed(s4, frame_upto("13:00"))
s4.add_level(LEVEL, "low", "PDL", True)
check("R4  a store whose first bar is 09:31 is covered", lvl(s4).partial is False)

# ── R5 — a gap longer than the frame ────────────────────────────────────────
stub(as_store(TAPE))
s5 = fresh()
s5.add_level(LEVEL, "low", "PDL", True)
feed(s5, frame_upto("11:00"))
window = TAPE[(TAPE.index >= pd.Timestamp(f"{DATE} 13:00", tz="America/New_York"))
              & (TAPE.index <= pd.Timestamp(f"{DATE} 13:59", tz="America/New_York"))]
feed(s5, window)                                     # bake 11:00 -> 13:00
feed(s5, TAPE)
check("R5  a frame after a gap is backfilled from the store; book EQUAL",
      state(lvl(s5)) == ref_end, f"{state(lvl(s5))} vs {ref_end}")

# ── R6 — a cold book whose frame starts at noon ─────────────────────────────
s6 = fresh()
s6.add_level(LEVEL, "low", "PDL", True)
feed(s6, frame_from("12:00"))
check("R6  a cold book is backfilled from the open; book EQUAL",
      state(lvl(s6)) == ref_end, f"{state(lvl(s6))} vs {ref_end}")

# ── R7 — the restart: hydrate today's file, then a NEW seed ─────────────────
r7 = fresh()
r7.add_level(120.0, "high", "FAR", True)
feed(r7, frame_upto("13:00"))
r7._dirty = True
r7.write(force=True)
again = ll.LiquidityLedger("TEST")
again.reset_for_session(DATE, seeds=[(120.0, "high", "FAR", True),
                                     (LEVEL, "low", "PDL", True)])
check("R7  restart: a new seed after a same-date hydrate is replayed",
      state(lvl(again)) == ref_13 and lvl(again).partial is False,
      f"{state(lvl(again))} vs {ref_13}, partial={lvl(again).partial}")

# ── D1-D3 — the record-only table ───────────────────────────────────────────
from data.derived_store import DerivedStore                     # noqa: E402
from derived.levels import LevelEngine                          # noqa: E402


class _Pool:
    def __init__(self, name, price, kind):
        self.name, self.price, self.kind, self.timeframe = name, price, kind, "1h"


class _Liq:
    def __init__(self, pools):
        self.pools = pools


def five(closes, start_epoch):
    idx = pd.to_datetime([start_epoch + 300 * i for i in range(len(closes))],
                         unit="s", utc=True).tz_convert("America/New_York")
    return pd.DataFrame({"close": closes}, index=idx)


def row(store, prov):
    return store.conn.execute(
        "SELECT kind, touch_count, closes_beyond, retired_reason FROM level_ledger"
        " WHERE provenance=?", (prov,)).fetchone()


import derived.levels as dl                                     # noqa: E402

T0 = int(time.time()) // 300 * 300 - 3600   # whole seconds: a float T0 made
# start + 300 == now round either way, and the boundary tick flaked
dpath = os.path.join(tempfile.mkdtemp(prefix="lvl_d_"), "derived.db")
st1 = DerivedStore(dpath)
eng = LevelEngine(store=st1, symbol="TEST")
liq = _Liq([_Pool("PDH", 100.0, "high")])
real_time = dl.time.time
try:
    # first seen below the pool: resistance
    dl.time.time = lambda: T0 + 600
    eng.derive({"liq_map": liq, "price": 99.0, "symbol": "TEST",
                "df_5m": five([99.0, 99.0, 99.0], T0)})
    # price crosses: two CLOSED bars beyond, live price above the pool
    dl.time.time = lambda: T0 + 1500
    eng.derive({"liq_map": liq, "price": 101.0, "symbol": "TEST",
                "df_5m": five([99.0, 99.0, 99.0, 101.0, 101.0, 101.0], T0)})
    dl.time.time = lambda: T0 + 1800
    eng.derive({"liq_map": liq, "price": 101.0, "symbol": "TEST",
                "df_5m": five([99.0, 99.0, 99.0, 101.0, 101.0, 101.0, 101.0], T0)})
    r = row(st1, "PDH")
    check("D1  a resistance pool keeps its side and retires ACCEPTED_THROUGH",
          r is not None and r[0] == "resistance" and r[3] == "ACCEPTED_THROUGH", f"{r}")

    # D2 — one closed bar over many ticks, at the level
    st2 = DerivedStore(os.path.join(tempfile.mkdtemp(prefix="lvl_d2_"), "d.db"))
    e2 = LevelEngine(store=st2, symbol="TEST")
    liq2 = _Liq([_Pool("PDL", 100.0, "low")])
    frame = five([100.05, 100.02, 100.03], T0)        # last row FORMING, AT the level
    for k in range(6):
        dl.time.time = lambda k=k: T0 + 601 + 10 * k  # bar 1 closed, bar 2 forming
        e2.derive({"liq_map": liq2, "price": 100.0, "symbol": "TEST", "df_5m": frame})
    r2 = row(st2, "PDL")
    check("D2  one closed 5m bar counts ONCE across six ticks; forming bar never",
          r2 is not None and r2[1] == 1, f"touch_count={r2 and r2[1]}")

    # D3 — a restarted engine resumes today's row; yesterday's does not
    e3 = LevelEngine(store=st2, symbol="TEST")
    dl.time.time = lambda: T0 + 901
    e3.derive({"liq_map": liq2, "price": 100.0, "symbol": "TEST",
               "df_5m": five([100.05, 100.02, 100.01, 100.4], T0)})
    r3 = row(st2, "PDL")
    st2.conn.execute("UPDATE level_ledger SET created_ts=created_ts-86400*2")
    e4 = LevelEngine(store=st2, symbol="TEST")
    e4.derive({"liq_map": liq2, "price": 100.0, "symbol": "TEST",
               "df_5m": five([100.05, 100.02, 100.01, 100.02, 100.4], T0)})
    r4 = row(st2, "PDL")
    check("D3  restart resumes today's row (1 -> 2); a 2-day-old row does not (-> 1)",
          r3 is not None and r3[1] == 2 and r4 is not None and r4[1] == 1,
          f"resumed={r3 and r3[1]} stale={r4 and r4[1]}")
finally:
    dl.time.time = real_time

# ── S1 — the sweep records, and does not gate ───────────────────────────────
from strategy.sweep_credit_spread import _hold_age_min          # noqa: E402

src = open(os.path.join(REPO, "strategy", "sweep_credit_spread.py")).read()
calls = {}
for n in ast.walk(ast.parse(src)):
    if (isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "check" and n.args
            and isinstance(n.args[0], ast.Constant)
            and n.args[0].value in ("level_visit_open", "level_hold_age_min")):
        calls[n.args[0].value] = (len(n.args) >= 3 and isinstance(n.args[2], ast.Constant)
                                  and n.args[2].value is None)
from datetime import datetime, timezone                         # noqa: E402
now = datetime(2026, 9, 14, 17, 50, tzinfo=timezone.utc)
age = _hold_age_min("2026-09-14 10:00:00-04:00", now)
check("S1  both quantities recorded with no threshold; age 230.0, None when absent",
      calls == {"level_visit_open": True, "level_hold_age_min": True}
      and age == 230.0 and _hold_age_min("", now) is None,
      f"calls={calls} age={age}")

print()
if FAILS:
    print(f"check_level_replay: FAIL ({len(FAILS)}): {', '.join(FAILS)}")
    sys.exit(1)
print("check_level_replay: ALL PASS")
