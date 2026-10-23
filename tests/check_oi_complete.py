#!/usr/bin/env python3
"""
tests/check_oi_complete.py  v1.0
v1.0  2026-10-23  r498 / OI.3 — A RATE-LIMITED OI BATCH IS RETRIED IN SECONDS, THE DAY'S OI
      IS FETCHED BEFORE THE BELL, AND A HALF-GUESSED PIN IS NOT TRADED.

  Measured on S3 chain snapshots 10-09..10-22 (130 mainline box-days): OI was short on 2,
  both at the 09:30 fetch (META 10-20 61 of 131 non-zero, QQQ 10-22 82 of 280), healed by the
  5-minute retry by 09:40; SPX-TEST 10-22 09:30:04 lost 94 symbols to the broker's 429 page.
  The pre-open rehearsal stops at the opening-range gate before it asks for a chain, so every
  box's first OI fetch fell at 09:30, all on one login. Drives the REAL fetch_open_interest
  (on tasty_client's shared loop), the REAL OptionsChainFetcher.fetch_chain, compute_gex and
  GEXPinButterflyStrategy.prepare/generate_signal, against a fake broker:
  O1  a broker whose rate bucket is empty (429 twice, then an answer, for every batch):
      ONE fetch of 250 symbols (3 batches) gets all 250 (pre-r498: one immediate retry,
      also 429, and the batch was lost until the 5-minute retry)
  O2  a broker that always answers 429: at most 4 calls per batch, the fetch returns inside
      15 s, and the log counts the symbols still missing
  O3  a non-429 failure is not retried (1 call; pre-r498 the attempt loop fell through and
      re-sent EVERY failure once at once, which is what retried a 429 into a second 429)
  O4  a success does not delay a new strike: the next fetch asks for it at once
  O5  control: after a FAILED fetch the next attempt waits _RETRY_S
  O6  the cache day is the ET date (the boxes run UTC)
  O7  fetch_chain with one batch failing: unanswered contracts read oi_known False,
      answered True; compute_gex counts oi_missing = the unanswered ones; a chain with no OI
      source (oi_known None) counts 0
  O8  the butterfly does not fire on a snapshot with oi_missing > 0 (STARVED open_interest);
      the same snapshot with oi_missing 0 is not starved on it
  O9  pre-open warm, no controller (operator 10-23): each process's own random draw places
      its warm inside the time it has left before the open (capped at 1 h, ending 180 s
      before the bell — OTV4TEST critique (d): inside 120 s the loop sleeps to 09:29:55):
      two draws give two different slots, the window is honoured at both ends, nothing is
      due after the open or on an evening; _warm_open_interest fills the cache through the
      real fetch_chain, after which the 09:30 fetch_chain makes NO broker call; the warm is
      ONE-SHOT (not due again that morning once its chain had OI for every contract)
  O10 main's pre-open branch calls the warm BEFORE the rehearsal-off flag can skip the pass
  O11 a fetch cut off by its 15 s bound KEEPS the batches already answered (critique (e)):
      a broker that hangs on the third batch, bound shortened to 1 s: the first 200 cached

Run:  python3 tests/check_oi_complete.py   (exit 0 green, 1 red)
"""
import ast
import asyncio
import glob as _glob
import logging
import os
import sys
import time
import types
from datetime import date, datetime, timezone

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


class _Cap(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.lines = []

    def emit(self, record):
        self.lines.append(record.getMessage())


E429 = "Couldn't parse response: <html><title>429 Too Many Requests</title></html>"


class Broker:
    """get_market_data_by_type stand-in. mode: ok | burst429 | all429 | err | fail_first_batch."""
    def __init__(self, mode="ok"):
        self.mode, self.calls, self.n, self.per = mode, [], 0, {}

    async def by_type(self, session, options=None, **_):
        self.n += 1
        self.calls.append(list(options or []))
        await asyncio.sleep(0)
        key = tuple(options or [])
        self.per[key] = self.per.get(key, 0) + 1
        if self.mode == "burst429" and self.per[key] <= 2:
            raise Exception(E429)
        if self.mode == "all429":
            raise Exception(E429)
        if self.mode == "err":
            raise ValueError("boom")
        if self.mode == "fail_first_batch" and self.n == 1:
            raise ValueError("first batch lost")
        return [types.SimpleNamespace(symbol=s, open_interest=100 + i)
                for i, s in enumerate(options or [])]


def main():
    import tastytrade.market_data as md
    from data import open_interest as OI
    cap = _Cap()
    OI.logger.addHandler(cap)
    OI.logger.setLevel(logging.DEBUG)
    OI.logger.propagate = False

    def use(b):
        md.get_market_data_by_type = b.by_type

    def reset():
        OI._CACHE, OI._CACHE_DAY, OI._LAST_ATTEMPT = {}, None, 0.0
        if hasattr(OI, "_LAST_FAIL"):
            OI._LAST_FAIL = 0.0
        cap.lines.clear()

    syms = [f"QQQ   261023C{700000 + 1000 * i:08d}" for i in range(250)]

    # O1 — an empty rate bucket: 429, 429, then an answer, per batch
    reset(); b = Broker("burst429"); use(b)
    got = OI.fetch_open_interest(None, syms)
    check("O1 429 twice per batch, then an answer: one fetch of 250 symbols gets all 250",
          len(got) == 250, f"got {len(got)} of 250 in {b.n} broker calls")

    # O2 — always 429: bounded
    reset(); b = Broker("all429"); use(b)
    t0 = time.monotonic()
    got = OI.fetch_open_interest(None, syms[:100])
    took = time.monotonic() - t0
    still = [ln for ln in cap.lines if "still missing" in ln or "no open interest yet" in ln]
    check("O2 always 429: at most 4 calls for the batch, back inside 15 s, the missing are counted",
          2 <= b.n <= 4 and took < 15 and len(got) == 0
          and any("100 symbol(s) have no open interest yet" in ln for ln in still),
          f"calls={b.n} took={took:.1f}s got={len(got)} lines={still[-2:]}")

    # O3 — control: a non-429 failure is not retried
    reset(); b = Broker("err"); use(b)
    OI.fetch_open_interest(None, syms[:10])
    check("O3 a non-429 failure is not retried", b.n == 1, f"calls={b.n}")

    # O4 — a success does not delay a new strike
    reset(); b = Broker("ok"); use(b)
    OI.fetch_open_interest(None, syms[:50])
    got = OI.fetch_open_interest(None, syms[:51])
    check("O4 a success does not delay a new strike: the next fetch asks for it at once",
          syms[50] in got and b.n == 2 and b.calls[-1] == [syms[50]],
          f"new strike answered={syms[50] in got} calls={b.n} last={b.calls[-1][:2]}")

    # O5 — control: after a failure the next attempt waits
    reset(); b = Broker("ok"); use(b)
    OI.fetch_open_interest(None, syms[:50])
    b.mode = "err"
    OI.fetch_open_interest(None, syms[:51])
    n_after_fail = b.n
    b.mode = "ok"
    got = OI.fetch_open_interest(None, syms[:51])
    check("O5 control: after a failed fetch the next attempt waits _RETRY_S",
          b.n == n_after_fail and syms[50] not in got, f"calls {n_after_fail}->{b.n}")

    # O6 — the cache day is the ET date
    import utils.time_utils as TU
    from zoneinfo import ZoneInfo
    real_now = TU.now_et
    TU.now_et = lambda: datetime(2026, 3, 2, 21, 0, tzinfo=ZoneInfo("America/New_York"))
    try:
        d = OI._today()
    finally:
        TU.now_et = real_now
    check("O6 the cache day is the ET date (21:00 ET on 03-02 is 03-02, not the UTC 03-03)",
          d == "2026-03-02", f"_today() = {d}")

    # ── fetch_chain fixtures (the SDK's own Option model) ──────────────────────
    from tastytrade.instruments import Option
    from data import options_chain as OC
    from data.gex_data import compute_gex
    OC.get_session = lambda: None
    try:
        import analysis.tenor_publish as TP
        TP.publish_aux_tenors = lambda *a, **k: {}
    except Exception:                                        # noqa: BLE001
        pass
    D = date(2026, 10, 23)
    SPOT = 705.0
    strikes = [655 + i for i in range(101)]                   # 202 contracts: 3 batches

    def _opt(cp, k):
        sym = f"QQQ   {D.strftime('%y%m%d')}{cp}{int(k * 1000):08d}"
        return Option(**{
            "instrument-type": "Equity Option", "symbol": sym, "active": True,
            "strike-price": str(k), "root-symbol": "QQQ", "underlying-symbol": "QQQ",
            "expiration-date": D.isoformat(), "exercise-style": "American",
            "shares-per-contract": 100, "option-type": cp, "option-chain-type": "Standard",
            "expiration-type": "Weekly", "settlement-type": "PM",
            "stops-trading-at": datetime(D.year, D.month, D.day, 20, 0, tzinfo=timezone.utc).isoformat(),
            "market-time-instrument-collection": "Equity Option",
            "days-to-expiration": 0, "is-closing-only": False,
            "streamer-symbol": f".QQQ{D.strftime('%y%m%d')}{cp}{k:g}"})

    opts = [_opt(cp, k) for k in strikes for cp in ("C", "P")]
    g, q = {}, {}
    for o in opts:
        k = float(o.strike_price)
        cp = "C" if o.option_type.value == "C" else "P"
        dl = max(-0.99, min(0.99, (0.5 - (k - SPOT) / 50) if cp == "C" else -(0.5 + (k - SPOT) / 50)))
        g[o.streamer_symbol] = types.SimpleNamespace(delta=dl, gamma=0.02, theta=-0.5, vega=0.1,
                                                     volatility=0.2)
        q[o.streamer_symbol] = types.SimpleNamespace(bid_price=1.00, ask_price=1.10)

    def fetcher():
        f = OC.OptionsChainFetcher()
        f._get_chain_structure = lambda session, symbol: {D: opts}
        f._fetch_greeks_and_quotes = lambda session, s, expiry=None: (g, q)
        return f

    # O7 — one batch lost: missing is counted, not guessed silently
    reset(); b = Broker("fail_first_batch"); use(b)
    ch = fetcher().fetch_chain("QQQ", expiry=D.isoformat())
    allc = (ch.calls + ch.puts) if ch else []
    f_ = [c for c in allc if getattr(c, "oi_known", "absent") is False]
    t_ = [c for c in allc if getattr(c, "oi_known", "absent") is True]
    gx = compute_gex(ch, SPOT) if ch else None
    miss = getattr(gx, "oi_missing", None)
    # a chain built with no OI source at all (paper fixture): oi_known None, nothing counted
    ch0 = OC.OptionsChain(underlying="QQQ", expiry=D.isoformat(),
                          calls=[OC.OptionContract(symbol="x", strike=700, gamma=0.02, mark=1.0,
                                                   option_type="C")],
                          puts=[OC.OptionContract(symbol="y", strike=700, gamma=0.02, mark=1.0,
                                                  option_type="P")])
    miss0 = getattr(compute_gex(ch0, SPOT), "oi_missing", None)
    check("O7 a lost batch: its contracts read oi_known False, the rest True, and compute_gex "
          "counts oi_missing = 100; a chain with no OI source counts 0",
          len(allc) == 202 and len(f_) == 100 and len(t_) == 102 and miss == 100 and miss0 == 0,
          f"contracts={len(allc)} False={len(f_)} True={len(t_)} oi_missing={miss} no-source={miss0}")

    # O8 — the butterfly does not fire on a half-guessed pin
    from strategy.gex_pin_butterfly import GEXPinButterflyStrategy
    from data.gex_data import GEXSnapshot

    def snap(missing):
        s = GEXSnapshot(net_gex=5e6, pin_strike=707.0, gex_environment="PINNING",
                        pin_concentration=0.5, spot_price=SPOT, valid=True)
        s.oi_missing = missing
        return s
    import strategy.gex_pin_butterfly as GB
    _in = GB.EARLIEST_ET                             # the slot's first minute (config sets it)
    st = GEXPinButterflyStrategy()
    p1 = st.prepare(gex=snap(3), price_now=SPOT, now_et=_in, atm_iv=0.2, chain=ch)
    sig1 = st.generate_signal(gex=snap(3), price_now=SPOT, now_et=_in, atm_iv=0.2, chain=ch)
    p0 = GEXPinButterflyStrategy().prepare(gex=snap(0), price_now=SPOT, now_et=_in,
                                           atm_iv=0.2, chain=ch)
    check("O8 oi_missing > 0: STARVED on open_interest, no signal; oi_missing 0 is not starved on it",
          "open_interest" in p1.starved and sig1 is None and "open_interest" not in p0.starved,
          f"starved(3)={p1.starved} signal={sig1 is not None} starved(0)={p0.starved}")

    # O9 — the pre-open warm, through the real fetch_chain
    src = open(os.path.join(_root, "main.py")).read()
    tree = ast.parse(src)
    fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    ok9, d9 = False, "main has no _oi_warm_due / _warm_open_interest"
    if "_oi_warm_due" in fns and "_warm_open_interest" in fns:
        consts = {}
        for n in tree.body:                               # main's own module constants
            if (isinstance(n, ast.Assign) and len(n.targets) == 1
                    and getattr(n.targets[0], "id", "") in ("OI_WARM_LEAD_S", "OI_WARM_FLOOR_S")):
                consts[n.targets[0].id] = ast.literal_eval(n.value)
        ns = {"logger": logging.getLogger("t"), "_OI_WARM_FRAC": 0.5, "_OI_WARM_SLOT": None,
              "_OI_WARM_DONE": False, **consts}
        for name in ("_oi_warm_slot", "_oi_warm_due", "_warm_open_interest"):
            if name in fns:
                exec(compile(ast.Module([fns[name]], []), "main.py", "exec"), ns)
        slot = ns.get("_oi_warm_slot")
        # booted at 09:17 (780 s to go): frac 0 -> 780, frac 1 -> 180, two fracs -> two slots
        slots = [round(slot(780, f), 2) for f in (0.0, 0.25, 0.999)] if slot else []
        late = slot(150, 0.7) if slot else None            # first looked inside the floor
        capped = slot(7200, 0.0) if slot else None         # up 2 h early: window capped at 1 h

        def walk(frac, ticks):
            ns["_OI_WARM_SLOT"], ns["_OI_WARM_DONE"] = None, False
            return [ns["_oi_warm_due"](x, frac) for x in ticks]
        w_mid = walk(0.5, [780, 500, 480, 300, 30])        # slot 480: due from 480 on
        w_eve = walk(0.5, [36000, 0])                      # evening / after the open
        due = (consts == {"OI_WARM_LEAD_S": 3600, "OI_WARM_FLOOR_S": 180}
               and slots == [780.0, 630.0, 180.6] and late == 150 and capped == 3600
               and w_mid == [False, False, True, True, True] and w_eve == [False, False])
        ns["_OI_WARM_SLOT"], ns["_OI_WARM_DONE"] = None, False
        reset(); b = Broker("ok"); use(b)
        f9 = fetcher()
        real_get = OC.get_chain_fetcher
        OC.get_chain_fetcher = lambda: f9
        try:
            ns["_warm_open_interest"]()
            warm_calls = b.n
            ch9 = f9.fetch_chain("QQQ", expiry=D.isoformat())     # the 09:30 tick
        finally:
            OC.get_chain_fetcher = real_get
        open_calls = b.n - warm_calls
        known = sum(1 for c in (ch9.calls + ch9.puts) if c.oi_known) if ch9 else 0
        ns["_OI_WARM_SLOT"] = 600.0
        again = ns["_oi_warm_due"](400, 0.5)               # inside the slot, after a good warm
        ok9 = (due and warm_calls == 3 and open_calls == 0 and known == 202
               and ns.get("_OI_WARM_DONE") is True and again is False)
        d9 = (f"consts={consts} slots={slots} late={late} capped={capped} walk={w_mid} "
              f"eve={w_eve} warm broker calls={warm_calls} 09:30 broker calls={open_calls} "
              f"answered={known} done={ns.get('_OI_WARM_DONE')} due-again={again}")
    check("O9 each box's own draw sets its warm inside the pre-open window; the warm fills the "
          "cache and the 09:30 chain asks nothing", ok9, d9)

    # O10 — the warm runs before the rehearsal-off flag can skip the pass
    i_rth = src.find("            if not is_rth():\n                if state.session_reset_done:")
    i_warm = src.find("if _oi_warm_due(seconds_until_rth_open()):", i_rth)
    i_off = src.find("if _rehearsal_disabled():", i_rth)
    check("O10 main's pre-open branch warms OI before the rehearsal-off flag can skip it",
          0 < i_rth < i_warm < i_off, f"is_rth={i_rth} warm={i_warm} flag={i_off}")

    # O11 — a fetch cut off by its bound keeps what already landed
    class Hang(Broker):
        async def by_type(self, session, options=None, **_):
            self.n += 1
            if self.n == 3:
                await asyncio.sleep(30)
            return [types.SimpleNamespace(symbol=s, open_interest=7) for s in (options or [])]
    reset(); h = Hang(); use(h)
    real_to = OI._FETCH_TIMEOUT_S
    OI._FETCH_TIMEOUT_S = 1.0
    try:
        t0 = time.monotonic()
        got = OI.fetch_open_interest(None, syms)
        took = time.monotonic() - t0
    finally:
        OI._FETCH_TIMEOUT_S = real_to
    check("O11 a fetch cut off by its bound keeps the 200 symbols already answered",
          len(got) == 200 and took < 5, f"kept {len(got)} of 250 (want 200) took={took:.1f}s")

    print()
    if FAILED:
        print(f"RED: {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
