"""tests/check_db_handles.py — v1.0
v1.0  2026-09-25  r430 / OPS.54 — mirrored verbatim from OTV4TEST r143.
EVERY STORE CONNECTION THE BOT OPENS IS CLOSED, AND A FAILED HEARTBEAT READ SAYS SO.

🔑 MIRRORED VERBATIM FROM OTV4TEST r143 (their DB.1), on purpose. The defect is
shared ancestry — `with self._connect() as conn:` commits and does NOT close, at
22 sites here and 22 there — so the FIX and its GATE are shared too. A second
gate measuring the same property a different way is how two trees drift on what
"fixed" means, which this repo paid for once already when `_STRAT_ABBR` diverged
between otv4 and dtp unnoticed (OPS.50).

🔴 GC IS DISABLED FOR H1/H2 AND THAT IS THE WHOLE TEST. These connections sit in
a reference cycle, so only the cyclic collector ever frees them — with the
collector running, BROKEN CODE PASSES ON TIMING. Their harness found that; mine
would not have.

📊 MUST-FAIL CONTROL, run before the fix on this tree: H1 measured 2 -> 902
handles and H2 1 -> 452, identical to theirs. After the fix both read 0 -> 0.

  H1 trade_logger calls hold trades.db handles flat   H2 resting_orders calls hold its handles flat
  H3 a write is committed (fresh connection reads it)  H4 an exception in _db() rolls back AND closes
  H5 a raised heartbeat read says READ FAILED + error; an old one says its age
  H6 no line-anchored block-form connect remains
"""
from __future__ import annotations
import gc, os, re, sqlite3, sys, tempfile
import glob as _glob
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:
        sys.path.insert(1, _sp)
sys.path.insert(0, _root)
_s = tempfile.mkdtemp(prefix="check_db_handles_", dir="/var/tmp" if os.path.isdir("/var/tmp") else None)
TR = os.path.join(_s, "trades.db"); RE = os.path.join(_s, "resting.db")
os.environ["OT_TRADES_DB"] = TR
os.environ["OT_RESTING_DB"] = RE
os.environ.setdefault("OT_DERIVED_DB", os.path.join(_s, "derived_store.db"))
os.environ.setdefault("OT_PAPER_TRADING", "1")
FAIL: list = []
N = 150

def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name.split()[0])

def premium_on_disk(tid):
    c = sqlite3.connect(TR)
    try:
        r = c.execute("SELECT current_premium FROM trades WHERE trade_id=?", (tid,)).fetchone()
    finally:
        c.close()
    return None if r is None else r[0]

def fds(path):
    rp = os.path.realpath(path); n = 0
    for f in os.listdir("/proc/self/fd"):
        try:
            if os.path.realpath(f"/proc/self/fd/{f}") == rp:
                n += 1
        except OSError:
            pass
    return n

from database.trade_logger import TradeLogger, make_record
gc.collect(); gc.disable()
try:
    tl = TradeLogger(db_path=TR, paper_trading=True)
    tl.log_entry(make_record(trade_id="h1", symbol="QQQ", strategy="ORBStrategy", direction="long", paper_trade=1))
    before = fds(TR)
    for i in range(N):
        tl.update_current_premium("h1", 1.0 + i / 1000)
        tl.get_open_trades(); tl.count_today("ORBStrategy"); tl.realized_pnl_today(); tl._get_field("h1", "symbol")
    for i in range(N):
        tl.log_entry(make_record(trade_id=f"h1-{i}", symbol="QQQ", strategy="ORBStrategy", direction="short", paper_trade=1))
    after = fds(TR)
    check(f"H1 trade_logger: {N * 6} calls leave the trades.db handles flat", after <= max(before, 1), f"open handles {before} -> {after}")

    from execution import resting_orders as ro
    ro.record_placement(order_id="o0", session_date="2026-09-25", strategy="ORBStrategy", symbol="QQQ", underlying="QQQ", side="call", strike=745.0, offered_qty=1, offer_price=1.0)
    before = fds(RE)
    for i in range(N):
        ro.record_placement(order_id=f"o{i + 1}", session_date="2026-09-25", strategy="ORBStrategy", symbol="QQQ", underlying="QQQ", side="call", strike=745.0, offered_qty=1, offer_price=1.0)
        ro.working("2026-09-25")
        ro.note_seen_qty(f"o{i + 1}", 1)
    ro.close_out("o1", "cancelled", "check")
    after = fds(RE)
    check(f"H2 resting_orders: {N} each of record_placement / working / note_seen_qty leave the handles flat", after <= max(before, 1), f"open handles {before} -> {after}")

    tl.update_current_premium("h1", 2.345)
    v = premium_on_disk("h1")
    check("H3 a write is COMMITTED - a fresh connection reads it back", v is not None and abs(float(v) - 2.345) < 1e-9, f"read {v}" if v is not None else "row absent on disk - nothing was committed")
    check("H3b get_open_trades still returns the open trade", any(r["trade_id"] == "h1" for r in tl.get_open_trades()))

    _db = getattr(tl, "_db", None)
    if _db is None:
        check("H4 an exception inside _db() rolls back and closes", False, "TradeLogger._db does not exist (pre-fix)")
    else:
        before = fds(TR)
        try:
            with _db() as conn:
                conn.execute("UPDATE trades SET current_premium=9.99 WHERE trade_id='h1'")
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        v = premium_on_disk("h1")
        check("H4 an exception inside _db() ROLLS BACK and still closes", v is not None and abs(float(v) - 2.345) < 1e-9 and fds(TR) <= before, f"premium {v}, handles {before} -> {fds(TR)}")
finally:
    gc.enable()

from data import market_data as md
bad = sqlite3.connect(":memory:")
ok = md._feed_alive(bad)
why = (getattr(md, "_ALIVE_WHY", None) or {}).get("why", "<no _ALIVE_WHY>")
check("H5 a heartbeat read that RAISES is reported as a read failure, with the error", ok is False and "READ FAILED" in why and "no such table" in why, repr(why))
old = sqlite3.connect(":memory:")
old.execute("CREATE TABLE feed_meta (symbol TEXT, interval TEXT, last_write_epoch REAL)")
import time as _t
old.execute("INSERT INTO feed_meta VALUES ('__feed__','heartbeat',?)", (_t.time() - 600,))
ok = md._feed_alive(old)
why = (getattr(md, "_ALIVE_WHY", None) or {}).get("why", "<no _ALIVE_WHY>")
check("H5b an OLD heartbeat reports its age, not a read failure", ok is False and re.search(r"heartbeat \d+s old", why or "") is not None, repr(why))

left = []
for rel, pat in (("database/trade_logger.py", r"^\s+with self\._connect\(\) as "), ("execution/resting_orders.py", r"^\s+with _conn\(\) as ")):
    for i, line in enumerate(open(os.path.join(_root, rel)), 1):
        if re.match(pat, line):
            left.append(f"{rel}:{i}")
check("H6 no block-form connect that commits without closing remains", not left, ", ".join(left[:6]))
print(f"\n{'GREEN' if not FAIL else 'RED'} — {len(FAIL)} failed" + (f": {FAIL}" if FAIL else ""))
sys.exit(1 if FAIL else 0)
