#!/usr/bin/env python3
"""
tests/check_exit_replay_streams.py  v1.1
v1.1  2026-09-09  r328 — E1 now asserts STREAMING, and that `load_series` is
      never reached at all. The r326 version asserted one DATE per call, which
      the code satisfied while still being OOM-killed on that one date: the
      list was the problem, not the window. A gate can be right about the
      thing it measures and wrong about the thing that matters.
v1.0  2026-09-09  r326 — the land gate for exit_replay's S3 path.

🔴 WHAT IT CATCHES. v1.3 called `load_series("quote_series", dates)` with the
WHOLE window, so every batch row for every date sat in one list before a
trade was replayed. quote_series is the highest-volume stream in the
warehouse; over `all` history the kernel killed the process mid-listing and
the menu printed `Killed`. There is no traceback in that failure and no
Python-level error to assert on — so the property has to be checked at the
CALL, not at the outcome.

  E1  run_s3 STREAMS quote_series per symbol-day; it never calls load_series
  E2  a date with no closed trades never loads quotes at all
  E3  every date that HAS trades is replayed
  E4  render() still draws from a filled accumulator
  E5  accumulate() adds to an accumulator rather than replacing it

⚠️ IT DRIVES run_s3 WITH A STUB `warehouse_source`. Asserting on the source
text would pass against any rewrite that reintroduced a whole-window load by
another route.
"""
import os
import sys
import types
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

FAILS = []


def check(name, ok, detail=""):
    print("  {:<4} {}  {}".format(name, "PASS" if ok else "FAIL", detail))
    if not ok:
        FAILS.append(name)


class _Meta:
    def __init__(self, label):
        self.label = label
        self.error = None

    def banner(self):
        return "SOURCE: {}".format(self.label)


def main():
    calls = {"series": [], "trades": [], "load_series": []}
    DATES = ["2026-09-01", "2026-09-02", "2026-09-03"]
    WITH_TRADES = {"2026-09-02"}

    ws = types.ModuleType("warehouse_source")
    ws.dates_of = lambda a: list(DATES)

    def load_trades(dates, s3=None):
        calls["trades"].append(list(dates))
        d = dates[0]
        rows = ([{"status": "closed", "trade_id": 1, "strategy": "S",
                  "option_side": "call", "symbol": "NVDA",
                  "short_symbol": ".X"}] if d in WITH_TRADES else [])
        return rows, _Meta("trades " + d)

    def load_series(table, dates, symbols=None, s3=None):
        # 🔴 r328 — REACHING THIS AT ALL IS THE FAILURE. load_series returns a
        # list, which is what got the process OOM-killed on a single date.
        calls["load_series"].append((table, list(dates)))
        return [], _Meta("{} {}".format(table, dates[0]))

    def iter_series(table, dates, meta, symbols=None, s3=None):
        calls["series"].append((table, list(dates), list(symbols or [])))
        meta.read = 1
        return iter([{"streamer_symbol": ".X", "ts_epoch": 1.0,
                      "bid_price": 1.0, "ask_price": 1.1}])

    ws.Meta = _Meta
    ws.load_trades = load_trades
    ws.load_series = load_series
    ws.iter_series = iter_series
    sys.modules["warehouse_source"] = ws

    import exit_replay as er

    seen = []
    er.accumulate = lambda rows, fetch, acc: seen.append(len(rows))
    rc = er.run_s3(types.SimpleNamespace(all_history=True))

    one_date = all(len(d) == 1 and len(sy) == 1 for _t, d, sy in calls["series"])
    check("E1", bool(calls["series"]) and one_date and not calls["load_series"],
          "iter_series {} · load_series {}".format(calls["series"],
                                                   calls["load_series"] or "never"))
    check("E2", len(calls["series"]) == len(WITH_TRADES),
          "{} streamed load(s) for {} date(s) with trades, {} dates total"
          .format(len(calls["series"]), len(WITH_TRADES), len(DATES)))
    check("E3", seen == [1], "replayed batches: {}".format(seen))

    # E4/E5 — the accumulator split itself.
    import importlib
    del sys.modules["exit_replay"]
    er = importlib.import_module("exit_replay")
    if not hasattr(er, "blank_acc") or not hasattr(er, "render"):
        # ⚠️ NAMED, NOT A TRACEBACK. A gate that dies with AttributeError reads
        # as a broken environment, which is the shape that teaches an operator
        # to skip a red run (r54c).
        check("E4", False, "exit_replay has no blank_acc/render — run() is not split")
        check("E5", False, "same")
        print("")
        print("FAILED: {}".format(", ".join(FAILS)))
        return 1
    acc = er.blank_acc()
    acc["counts"][("S", "call")] = 3
    acc["totals"][("S", "call")]["recorded"] = 120.0
    acc["totals"][("S", "call")]["stop 0.25"] = 90.0
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        er.render(acc)
    out = buf.getvalue()
    check("E4", "n=3 replayed" in out and "recorded" in out,
          "render drew {} line(s)".format(len(out.splitlines())))

    acc2 = er.blank_acc()
    acc2["counts"][("S", "call")] = 5
    er.accumulate([], lambda *a: [], acc2)
    check("E5", acc2["counts"][("S", "call")] == 5 and rc == 0,
          "accumulate preserved prior counts; run_s3 rc={}".format(rc))

    print("")
    if FAILS:
        print("FAILED: {}".format(", ".join(FAILS)))
        return 1
    print("ALL PASS (5)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
