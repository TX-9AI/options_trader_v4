#!/usr/bin/env python3
"""tests/check_exit_deadline.py  v1.1
F1 — A LIVE CLOSE BLOCKS THE TICK LOOP FOR ~14 s, NOT ~36 s, AND NEVER GOES SILENT TO THE WATCHDOG.

v1.1  2026-10-20  r494 / WDOG.3 (port of OTV4TEST r295 LIVE.2). OT_HEARTBEAT_FILE in a scratch dir
      (the live poll loop now touches the heartbeat); D5 is OTV4TEST's block verbatim: the
      never-filling close touches the heartbeat on every broker poll (>= 4 in 8 s at a 2 s poll).
      D6 (mainline's): the entry poll (confirm_order_fill) and flatten_all touch it on every
      iteration (AST). D7: an unwritable heartbeat returns False and does not raise.

v1.0  2026-10-05  r474. Operator: "get it down to eight seconds." A live close
      waited up to LIVE_FILL_DEADLINE_SECONDS (30) for a fill, then a 6 s cancel
      grace, with nothing else in the bot evaluated meanwhile.

Drives the REAL ExitEngine._confirm_and_book_live_exit in LIVE mode, against a
REAL TradeLogger on a temp DB, with a broker whose order never fills and a FAKE
CLOCK inside exit_engine (time.monotonic / time.sleep), so the timing is
measured, not assumed, and the check takes no real time.

  D1  config.LIVE_FILL_DEADLINE_SECONDS defaults to 8 (fresh interpreter, no
      override)
  D2  the cancel is sent at 8 s on the fake clock (not 30)
  D3  the call returns, unconfirmed, by ~14 s (8 + the 6 s cancel grace)
  D4  UNCHANGED: an order that fills at 3 s books at 3 s, with no cancel
  D5  the never-filling close touches the heartbeat on every poll, in the SCRATCH file
  D6  confirm_order_fill's poll loop and flatten_all's per-record loop touch it first thing
  D7  utils.heartbeat.touch on an unwritable path returns False, never raises

Run:  python3 tests/check_exit_deadline.py   (needs the venv's tastytrade)
"""
import ast
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OT_INSTRUMENT", "SYN")
_SCR = tempfile.mkdtemp(prefix="chk_exit_deadline_")
os.environ["OT_HEARTBEAT_FILE"] = os.path.join(_SCR, "BOT_HEARTBEAT")   # r494: never the live file
PROBLEMS = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name)


class _Clock:
    def __init__(self):
        self.t = 1000.0

    def monotonic(self):
        return self.t

    def sleep(self, s):
        self.t += float(s)

    def time(self):
        return self.t


class _Order:
    def __init__(self, oid, status, fill=None):
        self.id, self.status, self._fill, self.reject_reason = oid, status, fill, None


def main():
    print("check_exit_deadline")
    env = {k: v for k, v in os.environ.items() if k != "OT_LIVE_FILL_DEADLINE_SECONDS"}
    r = subprocess.run([sys.executable, "-c",
                        f"import sys; sys.path.insert(0, {ROOT!r}); import config; "
                        f"print(config.LIVE_FILL_DEADLINE_SECONDS)"],
                       capture_output=True, text=True, env=env, timeout=120)
    got = (r.stdout.strip().splitlines() or ["?"])[-1]
    check("D1 LIVE_FILL_DEADLINE_SECONDS defaults to 8", got == "8.0", f"got {got!r} rc={r.returncode}")

    try:
        from tastytrade.order import OrderStatus
    except ImportError as exc:
        print(f"NOT RUN — this interpreter cannot import tastytrade ({exc}); run under the venv")
        return 2
    import config as _cfg
    _cfg.LOG_FILE = os.path.join(tempfile.mkdtemp(), "bot.log")
    import database.trade_logger as TL
    import execution.exit_engine as EE

    tmp = tempfile.mkdtemp()
    tl = TL.TradeLogger(os.path.join(tmp, "t.db"), paper_trading=False)
    TL._trade_logger = tl
    clock = _Clock()
    EE.time = clock

    class _Broker:
        def __init__(self, fill_at=None):
            self.fill_at, self.cancel_at, self.submitted = fill_at, None, 0

        def get_order(self, session, oid):
            if self.fill_at is not None and clock.t - 1000.0 >= self.fill_at:
                return _Order(oid, OrderStatus.FILLED, (5.0, 1.10))
            return _Order(oid, OrderStatus.LIVE)

        def delete_order(self, session, oid):
            if self.cancel_at is None:
                self.cancel_at = clock.t - 1000.0
            return None

    def run(fill_at=None, tid="F1"):
        clock.t = 1000.0
        broker = _Broker(fill_at)
        EE.get_session = lambda: "S"
        EE.get_account = lambda: broker
        e = EE.ExitEngine(paper_trading=False)
        e._net_fill_price = lambda record, placed: placed._fill
        e._alert_live_exit_once = lambda *a, **k: None

        def submit(record, contracts, mark, reason=""):
            broker.submitted += 1
            return _Order(f"O{broker.submitted}", OrderStatus.LIVE)
        e._submit_live_close = submit
        rec = TL.make_record(trade_id=tid, symbol="SYN", strategy="ORBStrategy", setup_type="ORB",
                             option_side="call", contracts=5, entry_premium=1.50, total_cost=750.0,
                             max_loss=750.0, stop_premium=0.0, option_symbol="SYN   261016C00100000",
                             expiry="2099-01-01")
        tl.log_entry(rec)
        with tl._db() as conn:
            row = conn.execute("SELECT * FROM trades WHERE trade_id=?", (tid,)).fetchone()
        res = e._confirm_and_book_live_exit(TL.make_record(**dict(row)), "target", 1.10)
        return res, broker, clock.t - 1000.0

    res, b, elapsed = run(None, "F1-never")
    check("D2 the cancel is sent at 8 s on the fake clock, not 30",
          b.cancel_at is not None and 8.0 <= b.cancel_at < 10.0, f"cancel_at={b.cancel_at}")
    check("D3 the call returns unconfirmed by ~14 s (8 + 6 s grace)",
          (not res.confirmed) and elapsed <= 16.0, f"confirmed={res.confirmed} elapsed={elapsed}")
    res2, b2, el2 = run(3.0, "F1-fills")
    check("D4 unchanged: an order filling at 3 s books at ~3 s, no cancel",
          res2.confirmed and b2.cancel_at is None and el2 <= 4.0,
          f"confirmed={res2.confirmed} cancel_at={b2.cancel_at} elapsed={el2}")

    # r295 (LIVE.2) — the heartbeat is touched on EVERY poll of a working close, through the real writer
    touches = []
    try:
        _orig_hb = EE._hb_touch
        EE._hb_touch = lambda note="", file_path=None: (touches.append(note), _orig_hb(note, file_path))[1]
        try:
            run(None, "F1-hb")
        finally:
            EE._hb_touch = _orig_hb
        hb_file = os.environ["OT_HEARTBEAT_FILE"]
        body = open(hb_file).read().split() if os.path.exists(hb_file) else []
        check("D5 a never-filling close touches the heartbeat on every poll (>= 4 in 8 s), in the SCRATCH file",
              len(touches) >= 4 and all(t == "live-exit poll" for t in touches) and len(body) >= 2
              and body[1] == "live-exit" if len(body) > 1 else False,
              f"touches={len(touches)} {touches[:2]} file={body}")
    except AttributeError as exc:
        check("D5 a never-filling close touches the heartbeat on every poll (>= 4 in 8 s), in the SCRATCH file",
              False, f"no heartbeat writer in the exit engine: {exc}")

    # r494 — the entry poll and the flatten loop touch it first thing in every iteration
    def _first_touch(path, fn_name, loop_type):
        tree = ast.parse(open(os.path.join(ROOT, path)).read())
        fn = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == fn_name), None)
        if fn is None:
            return f"no {fn_name}"
        loops = [n for n in ast.walk(fn) if isinstance(n, loop_type)]
        if not loops:
            return f"no loop in {fn_name}"
        st = loops[0].body[0]
        ok = (isinstance(st, ast.Expr) and isinstance(st.value, ast.Call)
              and getattr(st.value.func, "id", "") == "_hb_touch")
        return "" if ok else f"{fn_name}: first statement of the loop is not _hb_touch(...)"
    bad = [x for x in (_first_touch("execution/order_confirm.py", "confirm_order_fill", ast.While),
                       _first_touch("execution/position_manager.py", "flatten_all", ast.For)) if x]
    check("D6 the entry poll and flatten_all touch the heartbeat on every iteration", not bad, "; ".join(bad))

    try:
        from utils import heartbeat as HB
        rv = HB.touch("x", os.path.join(_SCR, "no-such-dir", "BOT_HEARTBEAT"))
        check("D7 an unwritable heartbeat returns False and does not raise", rv is False, f"returned {rv!r}")
    except Exception as exc:                                    # noqa: BLE001
        check("D7 an unwritable heartbeat returns False and does not raise", False, f"{type(exc).__name__}: {exc}")

    print()
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {', '.join(p.split()[0] for p in PROBLEMS)}")
        return 1
    print("GREEN — every check passed")
    return 0


if __name__ == "__main__":
    try:
        _rc = main()
    finally:
        import shutil
        shutil.rmtree(_SCR, ignore_errors=True)
    sys.exit(_rc)
