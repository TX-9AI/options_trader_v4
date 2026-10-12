#!/usr/bin/env python3
"""
tests/check_bar_referee.py  v1.0
v1.0  2026-10-12  FEED.10 — A CLOSED BAR IS JUDGED AGAINST THE BOX'S OWN 1m.

  FEED.9/9b compare two versions of a bar with each other, so an INFLATED
  replay always wins: on 2026-10-12 each boot replay raised today's hourly
  volume (CVX 2x, QQQ 2x, CRM 3x, prices identical) and 9b kept the maximum.
  Design from OTV4TEST's FEED.10 (its r276), with mainline's critique.

  Drives the REAL FeedStore.upsert_candles on a SCRATCH store, clock pinned:
  R1  today's QQQ 1h 15:00 stored at 2x: the 1x replay that matches the 1m is
      TAKEN
  R2  the 10-08 5m 11:55 slice against a complete 1m set: REFUSED
  R3  an index bar (0 volume): the version matching the 1m H/L is taken, and
      the one that does not is refused
  R4  an incomplete 1m set falls back to FEED.9b (a slice is still refused)
  R5  a FORMING bar never reads 1m (counted with a trace callback)
  R6  a tie keeps the stored row
  R7  *_EXT is refereed by *_EXT 1m only, never by the plain route's
  R8  the 09:00 hour is complete with its 30 RTH minutes
  R9  1d is never refereed (last-write-wins)
  R10 a referee failure falls back to FEED.9b and is logged once
  R11 a bar closed less than 60 s ago is not refereed yet (its last minute
      may still be updating)
  R12 an identical replay is silent
  BORN RED on otv4 556bc2c: R1 R3b R6 R7b R8 fail, then R10 raises
  AttributeError (no _referee_minutes).

Run:  python3 tests/check_bar_referee.py
"""
import logging
import os
import sys
import tempfile
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PROBLEMS = []
ET = ZoneInfo("America/New_York")


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name)


def ms(y, mo, d, h, mi):
    return int(datetime(y, mo, d, h, mi, tzinfo=ET).timestamp() * 1000)


def main():
    import data.candle_feed as cf
    st = cf.FeedStore(os.path.join(tempfile.mkdtemp(), "feed_store.db"))
    NOW = ms(2026, 10, 12, 20, 0)
    cf._now_ms = lambda: NOW

    seen = []

    class _H(logging.Handler):
        def emit(self, rec):
            seen.append(rec.getMessage())
    lg = logging.getLogger("data.candle_feed")
    lg.addHandler(_H())
    lg.setLevel(logging.INFO)

    def put(*rows):
        st.upsert_candles(list(rows))
        st.commit()

    def get(sym, iv, ts):
        return st.conn.execute(
            "SELECT open, high, low, close, volume FROM candles WHERE symbol=? "
            "AND interval=? AND ts_epoch_ms=?", (sym, iv, ts)).fetchone()

    def minutes(sym, start, n, vol, lo, hi, first_open=None, last_close=None):
        rows = []
        for i in range(n):
            o = first_open if (i == 0 and first_open is not None) else lo + 0.05
            c = last_close if (i == n - 1 and last_close is not None) else lo + 0.05
            rows.append((sym, "1m", start + i * 60_000, o,
                         hi if i == 1 else lo + 0.10,
                         lo if i == 2 else lo + 0.01, c, vol))
        st.upsert_candles(rows)
        st.commit()

    # R1 — QQQ 1h 15:00 today, stored at 2x
    T1 = ms(2026, 10, 12, 15, 0)
    minutes("QQQ", T1, 60, 27154.1, 745.0, 746.5, 745.5, 746.02)
    put(("QQQ", "1h", T1, 745.5, 746.5, 745.0, 746.02, 3258492.0))
    put(("QQQ", "1h", T1, 745.5, 746.5, 745.0, 746.02, 1629246.0))
    got = get("QQQ", "1h", T1)
    check("R1 an inflated hourly bar is replaced by the replay matching the 1m",
          got is not None and got[4] == 1629246.0, str(got))

    # R2 — the 10-08 slice against a complete 1m set
    T2 = ms(2026, 10, 8, 11, 55)
    minutes("QQQ", T2, 5, 21575.4, 752.39, 752.94, 752.833, 752.91)
    put(("QQQ", "5m", T2, 752.833, 752.94, 752.39, 752.91, 107877.0))
    put(("QQQ", "5m", T2, 752.635, 752.9191, 752.57, 752.91, 33808.0))
    got = get("QQQ", "5m", T2)
    check("R2 the 10-08 slice is refused against a complete 1m set",
          got == (752.833, 752.94, 752.39, 752.91, 107877.0), str(got))

    # R3 — index, 0 volume: H/L referees
    T3 = ms(2026, 10, 9, 10, 0)
    minutes("SPX", T3, 5, 0.0, 7690.0, 7697.52, 7692.0, 7695.0)
    put(("SPX", "5m", T3, 7693.0, 7695.19, 7690.0, 7695.0, 0.0))
    put(("SPX", "5m", T3, 7692.0, 7697.52, 7690.0, 7695.0, 0.0))
    got = get("SPX", "5m", T3)
    check("R3 index: the version matching the 1m H/L is taken",
          got is not None and got[1] == 7697.52, str(got))
    put(("SPX", "5m", T3, 7692.0, 7699.00, 7688.0, 7695.0, 0.0))
    got = get("SPX", "5m", T3)
    check("R3b index: a wider version the 1m does not show is refused",
          got is not None and got[1] == 7697.52, str(got))

    # R4 — incomplete 1m (4 of 5): FEED.9b decides
    T4 = ms(2026, 10, 9, 11, 0)
    minutes("CVX", T4, 4, 3000.0, 211.0, 211.5)
    put(("CVX", "5m", T4, 211.05, 211.5, 211.0, 211.05, 15000.0))
    put(("CVX", "5m", T4, 211.05, 211.4, 211.1, 211.05, 6000.0))
    got = get("CVX", "5m", T4)
    check("R4 an incomplete 1m set falls back to FEED.9b (slice refused)",
          got is not None and got[4] == 15000.0, str(got))

    # R5 — a forming bar never reads 1m
    T5 = ms(2026, 10, 12, 19, 55)
    reads = []
    st.conn.set_trace_callback(
        lambda q: reads.append(q) if "interval='1m'" in q else None)
    put(("QQQ", "5m", T5, 746.0, 746.1, 745.9, 746.0, 1000.0))
    put(("QQQ", "5m", T5, 746.0, 746.2, 745.9, 746.1, 2000.0))
    st.conn.set_trace_callback(None)
    check("R5 a forming bar never reads 1m", not reads, str(reads[:1]))

    # R6 — tie keeps the stored row
    T6 = ms(2026, 10, 9, 12, 0)
    minutes("AMD", T6, 5, 1000.0, 160.0, 160.5)
    put(("AMD", "5m", T6, 160.05, 160.5, 160.0, 160.05, 5100.0))
    put(("AMD", "5m", T6, 160.05, 160.5, 160.0, 160.05, 4900.0))
    got = get("AMD", "5m", T6)
    check("R6 a tie keeps the stored row", got is not None and got[4] == 5100.0,
          str(got))

    # R7 — *_EXT refereed by *_EXT 1m only
    T7 = ms(2026, 10, 9, 13, 0)
    minutes("QQQ", T7, 60, 1000.0, 750.0, 751.0)          # plain only
    put(("QQQ_EXT", "1h", T7, 750.05, 751.0, 750.0, 750.05, 120000.0))
    put(("QQQ_EXT", "1h", T7, 750.05, 751.0, 750.0, 750.05, 60000.0))
    got = get("QQQ_EXT", "1h", T7)
    check("R7 *_EXT without its own 1m is not refereed by the plain 1m",
          got is not None and got[4] == 120000.0, str(got))
    minutes("QQQ_EXT", T7, 60, 1000.0, 750.0, 751.0)
    put(("QQQ_EXT", "1h", T7, 750.05, 751.0, 750.0, 750.05, 60000.0))
    got = get("QQQ_EXT", "1h", T7)
    check("R7b *_EXT with its own complete 1m is refereed",
          got is not None and got[4] == 60000.0, str(got))

    # R8 — the 09:00 hour is complete with 30 RTH minutes
    T8 = ms(2026, 10, 9, 9, 0)
    minutes("NVDA", T8 + 30 * 60_000, 30, 10000.0, 190.0, 191.0)
    put(("NVDA", "1h", T8, 190.05, 191.0, 190.0, 190.05, 600000.0))
    put(("NVDA", "1h", T8, 190.05, 191.0, 190.0, 190.05, 300000.0))
    got = get("NVDA", "1h", T8)
    check("R8 the 09:00 hour is refereed on its 30 RTH minutes",
          got is not None and got[4] == 300000.0, str(got))

    # R9 — 1d is never refereed
    TD = ms(2026, 10, 9, 0, 0)
    put(("NVDA", "1d", TD, 190.0, 195.0, 189.0, 194.0, 5000000.0))
    put(("NVDA", "1d", TD, 190.5, 194.0, 189.5, 194.0, 4000000.0))
    got = get("NVDA", "1d", TD)
    check("R9 1d stays last-write-wins",
          got == (190.5, 194.0, 189.5, 194.0, 4000000.0), str(got))

    # R10 — a referee failure falls back to 9b, logged once
    T10 = ms(2026, 10, 9, 14, 0)
    orig = st._referee_minutes
    st._referee_minutes = lambda *a: (_ for _ in ()).throw(RuntimeError("boom"))
    seen.clear()
    put(("TSLA", "5m", T10, 430.0, 431.0, 429.0, 430.5, 9000.0))
    put(("TSLA", "5m", T10, 430.0, 430.8, 429.2, 430.5, 3000.0))
    put(("TSLA", "5m", T10, 430.0, 430.8, 429.2, 430.5, 2000.0))
    st._referee_minutes = orig
    got = get("TSLA", "5m", T10)
    warns = [m for m in seen if "referee failed" in m]
    check("R10 a referee failure falls back to FEED.9b, logged once",
          got is not None and got[4] == 9000.0 and len(warns) == 1,
          f"{got} warns={len(warns)}")

    # R11 — closed less than 60 s ago: not refereed yet (9b decides)
    T11 = NOW - 300_000 - 30_000                   # closed 30 s ago
    minutes("META", T11, 5, 1000.0, 700.0, 701.0)
    put(("META", "5m", T11, 700.05, 701.0, 700.0, 700.05, 9000.0))
    put(("META", "5m", T11, 700.05, 701.0, 700.0, 700.05, 5000.0))
    got = get("META", "5m", T11)
    check("R11 a bar closed under 60 s ago is left to FEED.9b",
          got is not None and got[4] == 9000.0, str(got))

    # R12 — an identical replay is silent
    seen.clear()
    put(("QQQ", "1h", T1, 745.5, 746.5, 745.0, 746.02, 1629246.0))
    check("R12 an identical replay logs nothing",
          not [m for m in seen if "FEED." in m], str(seen))

    st.close()
    print("ALL PASS" if not PROBLEMS else f"FAIL: {', '.join(PROBLEMS)}")
    return 0 if not PROBLEMS else 1


if __name__ == "__main__":
    sys.exit(main())
