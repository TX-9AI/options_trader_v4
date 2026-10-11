#!/usr/bin/env python3
"""
tests/check_floor_watch.py  v1.0
v1.0  2026-10-11  r482 / EXIT.5 — THE WAIT BETWEEN TICKS WATCHES THE STOPS, AND
      ONLY EVER WAKES THE TICK.

A premium stop was checked every 15 s, so the fill was the first 15-s sample
under it: 200 mainline debit stop exits since 09-13 filled $4,564 beyond their
stops (paper). main's wait now re-reads each watched position's own mark every
2 s and runs the tick early when a FRESH mark is at or below the stop. The tick
still decides. Critiqued by OTV4TEST (MSG-QQQ-1011-36) before build.

This file is meant to be byte-identical across trees (WA §38.9): it drives each
tree's OWN watched_stop and exit decision, so per-tree exclusions live in that
tree's exit_engine header, not here.

  W1  watched_stop IS the level the engine enforces: evaluate() just below it
      closes on a stop; just above it does not (floor, an armed trail, and the
      Runaway through the management plan that decides it first)
  W2  a fresh mark crossing at t+4 s ends a 15-s wait at the next 2-s step
  W3  a STALE quote (> 4 s old) at the stop never wakes
  W4  the watch decides nothing: no exit/close/order call inside it (AST)
  W5  excluded records are never watched (credit, butterfly, short, a working
      live close, a strategy the list does not name), and with nothing to
      watch the wait is ONE plain sleep
  W6  one early wake per position per 10 s
  W7  one mark formula: the chain read uses mark_of
  W8  read_quote reads one chain_marks row as (mark, age); a missing row is None

Run:  python3 tests/check_floor_watch.py
"""
import ast
import os
import sqlite3
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
os.environ.setdefault("OT_PAPER_TRADING", "1")
FAILS = []


def check(name, ok, det=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {det}" if det else ""))
    if not ok:
        FAILS.append(name)


def guarded(name, fn):
    try:
        fn()
    except Exception as exc:                                    # noqa: BLE001
        check(name, False, f"raised {type(exc).__name__}: {exc}")


print("\ncheck_floor_watch\n")


def _orb(**kw):
    r = {"trade_id": "w1-orb-0001", "strategy": "ORBStrategy", "symbol": "TEST",
         "option_side": "call", "direction": "long", "contracts": 1,
         "entry_premium": 2.00, "stop_premium": 1.50, "target_premium": 4.00,
         "trail_activation": 3.00, "trail_stop": None, "strike": 100.0,
         "is_short_position": 0, "is_butterfly": 0, "is_credit_vertical": 0,
         "is_condor_leg": 0, "short_strike": 0.0}
    r.update(kw)
    return r


def w1():
    import datetime as _dt
    from zoneinfo import ZoneInfo
    import execution.exit_engine as EE
    from execution.exit_engine import watched_stop, ExitEngine
    # PINNED TO 10:00 ET (the CHK.12 lesson): after 15:45 the hard close fires
    # first and both sides of the stop would close for the wrong reason.
    _ten = _dt.datetime(2026, 10, 7, 10, 0, tzinfo=ZoneInfo("America/New_York"))
    _real = (EE.now_et, EE.is_hard_close_time)
    EE.now_et = lambda: _ten
    EE.is_hard_close_time = lambda *a, **k: False
    try:
        _w1(watched_stop, ExitEngine)
    finally:
        EE.now_et, EE.is_hard_close_time = _real


def _w1(watched_stop, ExitEngine):
    eng = ExitEngine(paper_trading=True)
    rec = _orb()
    lvl = watched_stop(rec)
    below = eng.evaluate(dict(rec), lvl - 0.01)
    above = eng.evaluate(dict(rec), lvl + 0.01)
    stop_word = lambda d: d.should_exit and ("stop" in str(d.exit_reason))
    check("W1  floor: watched_stop == stop_premium, and the engine closes just below, "
          "not just above", lvl == 1.50 and stop_word(below) and not stop_word(above),
          f"lvl={lvl} below={below.exit_reason!r} above={above.exit_reason!r}")
    rec2 = _orb(trade_id="w1-orb-0002", trail_stop=1.80)
    lvl2 = watched_stop(rec2)
    eng2 = ExitEngine(paper_trading=True)
    b2 = eng2.evaluate(dict(rec2), lvl2 - 0.01)
    eng3 = ExitEngine(paper_trading=True)
    a2 = eng3.evaluate(dict(rec2), lvl2 + 0.01)
    check("W1b an armed trail above the floor is the watched level, and the engine "
          "closes on it just below, not just above",
          lvl2 == 1.80 and stop_word(b2) and not stop_word(a2),
          f"lvl={lvl2} below={b2.exit_reason!r} above={a2.exit_reason!r}")
    from strategy.management import get_management_plan
    mp = get_management_plan()
    rr = _orb(trade_id="w1-run-0004", strategy="RunawayContinuation", stop_premium=1.60)
    lr = watched_stop(rr)
    ib = mp.decide(dict(rr), lr - 0.01, exit_engine=ExitEngine(paper_trading=True))
    ia = mp.decide(dict(rr), lr + 0.01, exit_engine=ExitEngine(paper_trading=True))
    close = lambda i: i is not None and i.action == "CLOSE" and "stop" in str(i.reason)
    check("W1d Runaway (management plan decides): closes on the stop just below the "
          "watched level, not just above", lr == 1.60 and close(ib) and not close(ia),
          f"lvl={lr} below={ib and (ib.action, ib.reason)} above={ia and (ia.action, ia.reason)}")
    rec3 = _orb(trade_id="w1-orb-0003", stop_premium=0.0)
    from config import MAX_LOSS_PCT
    check("W1c no stop_premium -> the engine's own fallback entry*(1-MAX_LOSS_PCT)",
          abs((watched_stop(rec3) or 0) - 2.00 * (1 - MAX_LOSS_PCT)) < 1e-9,
          f"{watched_stop(rec3)}")


guarded("W1  watched_stop agrees with the engine", w1)


class _Clock:
    def __init__(self):
        self.t = 1_000_000.0
        self.sleeps = []

    def now(self):
        return self.t

    def sleep(self, s):
        self.sleeps.append(round(s, 3))
        self.t += s


class _PM:
    def __init__(self, targets):
        self._t = targets

    def watch_targets(self):
        return list(self._t)


def w2_w3_w6():
    import main as M
    M._FLOOR_WAKE_AT.clear()
    c = _Clock()
    t0 = c.t
    read = lambda sym, now: ((1.40, 0.5) if now - t0 >= 4.0 else (1.60, 0.5))
    r = M._floor_watch_sleep(15.0, _PM([("t-w2", ".X", 1.50)]), read=read,
                             clock=c.now, sleep=c.sleep)
    check("W2  a fresh cross at t+4 s ends a 15-s wait at the next 2-s step",
          r is not None and abs((c.t - t0) - 4.0) < 1e-6 and abs(r[4] - 11.0) < 1e-6,
          f"woke at +{c.t - t0:.1f}s ret={r}")
    M._FLOOR_WAKE_AT.clear()
    c = _Clock()
    t0 = c.t
    r = M._floor_watch_sleep(15.0, _PM([("t-w3", ".X", 1.50)]),
                             read=lambda sym, now: (1.40, 6.0),
                             clock=c.now, sleep=c.sleep)
    check("W3  a 6-s-old quote at the stop never wakes; the wait runs its 15 s",
          r is None and abs((c.t - t0) - 15.0) < 1e-6, f"ret={r} slept {c.t - t0:.1f}s")
    M._FLOOR_WAKE_AT.clear()
    c = _Clock()
    pm = _PM([("t-w6", ".X", 1.50)])
    rd = lambda sym, now: (1.40, 0.5)
    first = M._floor_watch_sleep(15.0, pm, read=rd, clock=c.now, sleep=c.sleep)
    c.t += 3.0
    second = M._floor_watch_sleep(5.0, pm, read=rd, clock=c.now, sleep=c.sleep)
    c.t += 8.0
    third = M._floor_watch_sleep(5.0, pm, read=rd, clock=c.now, sleep=c.sleep)
    check("W6  one early wake per position per 10 s", first is not None
          and second is None and third is not None, f"{first is not None} "
          f"{second is not None} {third is not None}")
    c = _Clock()
    M._floor_watch_sleep(15.0, _PM([]), read=rd, clock=c.now, sleep=c.sleep)
    check("W5b nothing to watch -> exactly one plain sleep of the full wait",
          c.sleeps == [15.0], f"{c.sleeps}")


guarded("W2/W3/W6 the wait", w2_w3_w6)


def w4():
    src = open(os.path.join(REPO, "main.py"), encoding="utf-8").read()
    fn = next(n for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.FunctionDef) and n.name == "_floor_watch_sleep")
    bad = [ast.unparse(n.func) for n in ast.walk(fn) if isinstance(n, ast.Call)
           and any(w in ast.unparse(n.func).lower()
                   for w in ("exit", "close", "order", "execute", "evaluate", "decide"))]
    calls = [n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Call)
             and ast.unparse(n.func) == "_floor_watch_sleep"]
    check("W4  the watch calls no exit/close/order/decision function, and main_loop "
          "waits through it", not bad and len(calls) >= 1, f"bad={bad} uses={len(calls)}")


guarded("W4  the watch decides nothing", w4)


def w5():
    from execution.exit_engine import watched_stop
    cases = {
        "credit vertical": _orb(is_credit_vertical=1),
        "butterfly": _orb(is_butterfly=1),
        "short": _orb(is_short_position=1),
        "working live close": _orb(live_exit_state='{"order_id":"x"}'),
        "a short strike (spread/tent)": _orb(short_strike=101.0),
        "condor leg": _orb(is_condor_leg=1),
        "unlisted strategy": _orb(strategy="SweepCreditSpread"),
    }
    got = {k: watched_stop(v) for k, v in cases.items()}
    check("W5  excluded records are never watched", all(v is None for v in got.values()),
          f"{ {k: v for k, v in got.items() if v is not None} }")
    from execution.position_manager import PositionManager
    pm = PositionManager.__new__(PositionManager)
    pm._open_records = [_orb(trade_id="has-sym", _streamer=".X"), _orb(trade_id="no-sym")]
    t = pm.watch_targets()
    check("W5c a record not yet priced by a tick (no contract) is not watched",
          [x[0] for x in t] == ["has-sym"], f"{t}")


guarded("W5  exclusions", w5)


def w7():
    src = open(os.path.join(REPO, "data", "options_chain.py"), encoding="utf-8").read()
    check("W7  one mark formula: the chain read assigns oc.mark = mark_of(bid, ask)",
          "oc.mark = mark_of(bid, ask)" in src
          and "oc.mark = (bid + ask) / 2" not in src)


guarded("W7  one mark formula", w7)


def w8():
    d = tempfile.mkdtemp(prefix="fw_")
    db = os.path.join(d, "feed_store.db")
    with sqlite3.connect(db) as c:
        c.execute("CREATE TABLE chain_marks (streamer_symbol TEXT PRIMARY KEY, bid REAL,"
                  " ask REAL, delta REAL, gamma REAL, theta REAL, vega REAL, iv REAL,"
                  " updated_epoch REAL)")
        c.execute("INSERT INTO chain_marks (streamer_symbol, bid, ask, updated_epoch)"
                  " VALUES ('.X', 1.40, 1.50, 1000.0)")
    os.environ["OT_FEED_DB"] = db
    import data.options_chain as OC
    OC._QUOTE_RO = None
    q = OC.read_quote(".X", now=1003.0)
    miss = OC.read_quote(".NOPE", now=1003.0)
    check("W8  read_quote -> (mid, age) for one row; a missing row is None",
          q is not None and abs(q[0] - 1.45) < 1e-9 and abs(q[1] - 3.0) < 1e-9
          and miss is None, f"q={q} miss={miss}")
    check("W8b mark_of: one side quoting is that side", OC.mark_of(0, 1.2) == 1.2
          and OC.mark_of(1.0, 1.2) == 1.1)


guarded("W8  read_quote", w8)

print()
if FAILS:
    print(f"check_floor_watch: FAIL ({len(FAILS)}): {', '.join(FAILS)}")
    sys.exit(1)
print("check_floor_watch: ALL PASS")
