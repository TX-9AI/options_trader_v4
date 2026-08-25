#!/usr/bin/env python3
"""
tools/probe_aux_streams.py  v1.0

r113 — WHY ARE `underlying_series` AND `theo_series` EMPTY?

The manifold board has shown both RED on every box since the streams were added
(2026-08-22). Established on 2026-08-24, in this order:

  · the subscribe BLOCK RUNS — journalctl -u candle-feed shows "subscribed <SYM>
    Underlying" and "... TheoPrice" once per connection, 15/15 boxes, and ZERO
    "SUBSCRIBE FAILED". So it is not a dead code path and not a refused request.
  · THREE OF THE FIVE STREAMS IN THAT SAME BLOCK POPULATE — Trade -> last_trade,
    TimeAndSale -> prints, Summary -> session_summary, all green. So the loop,
    the drain and the writers work.
  · only Underlying and TheoPrice are silent.

TWO CANDIDATES REMAIN AND THEY NEED DIFFERENT FIXES:

  (a) WRONG SYMBOL SPACE. `TheoPrice` is computed PER OPTION CONTRACT, not for
      the equity. `candle_feed` subscribes all five aux events to
      `[self.dx_symbol]` — the plain ticker — while Greeks and Quote subscribe
      to the CHAIN's streamer symbols and both flow. A subscription to a symbol
      that has no publisher is ACCEPTED and then silent forever, which is
      exactly what we observe.
  (b) NOT CARRIED. Trade/TimeAndSale/Summary are the exchange's own prints;
      Underlying and TheoPrice are dxFeed-COMPUTED analytics. A vendor plan may
      carry the first group and not the second.

⚠️ THIS PROBE DECIDES BETWEEN THEM AND CHANGES NOTHING. It opens its own
streamer, subscribes each event to BOTH symbol spaces, waits, and counts what
arrives. It writes no tables, touches no service, and holds no locks. Run it on
ONE box; it exits on its own.

  (a) -> option symbols yield TheoPrice events, the ticker does not: fix is to
         move TheoPrice into the per-contract subscribe beside Greeks/Quote.
  (b) -> NOTHING arrives on either space for either event, while Trade does:
         it is the plan. Relabel those two bulbs "not carried" rather than
         leaving two permanent reds that mean nothing.

Run:  cd ~/options-trader && venv/bin/python tools/probe_aux_streams.py [SECONDS]
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.expanduser("~/options-trader"))

from tastytrade import DXLinkStreamer
from tastytrade.dxfeed import Greeks, Quote, Trade, Underlying, TheoPrice

from data.tasty_client import get_session
from data.options_chain import get_chain_fetcher
from config import INSTRUMENT

SECONDS = float(sys.argv[1]) if len(sys.argv) > 1 else 45.0


async def main() -> None:
    session = get_session()
    # The SAME option symbols the feed already subscribes Greeks/Quote to — the
    # ones that demonstrably tick. A handful is plenty; this is a yes/no.
    opts: list = []
    try:
        chain = get_chain_fetcher().fetch_chain()
        for c in (list(getattr(chain, "calls", []))[:6]
                  + list(getattr(chain, "puts", []))[:6]):
            s = getattr(c, "streamer_symbol", "") or ""
            if s:
                opts.append(s)
    except Exception as exc:                                   # noqa: BLE001
        print(f"chain fetch failed ({exc}) — option-symbol arm will be skipped")

    print(f"instrument   : {INSTRUMENT}")
    print(f"ticker arm   : {INSTRUMENT}")
    print(f"option arm   : {len(opts)} symbols" + (f", e.g. {opts[0]}" if opts else ""))
    print(f"listening    : {SECONDS:.0f}s\n")

    got = {"Trade": 0, "Greeks": 0, "Quote": 0, "Underlying": 0, "TheoPrice": 0}
    theo_syms: set = set()
    und_syms: set = set()

    async with DXLinkStreamer(session) as streamer:
        # Trade on the ticker is the POSITIVE CONTROL: it is in the same block
        # in candle_feed and it populates, so if this probe sees no Trade the
        # probe itself is wrong and nothing else it reports means anything.
        await streamer.subscribe(Trade, [INSTRUMENT])
        await streamer.subscribe(Underlying, [INSTRUMENT])
        await streamer.subscribe(TheoPrice, [INSTRUMENT])
        if opts:
            await streamer.subscribe(TheoPrice, opts)
            await streamer.subscribe(Underlying, opts)
            await streamer.subscribe(Greeks, opts)      # second positive control
            await streamer.subscribe(Quote, opts)
        print("subscribed; waiting...\n")

        async def drain(ev, name):
            while True:
                e = streamer.get_event_nowait(ev)
                if e is None:
                    return
                got[name] += 1
                sym = str(getattr(e, "event_symbol", "") or "")
                if name == "TheoPrice":
                    theo_syms.add(sym)
                elif name == "Underlying":
                    und_syms.add(sym)

        # ⚠️ A MONOTONIC CLOCK, NOT THE LOOP'S. The boxes run PYTHON 3.14,
        # where asking asyncio for the running loop the deprecated way RAISES
        # rather than warning — the probe died on line 111 before it listened
        # to anything. time.monotonic() needs no loop at all.
        import time as _t
        end = _t.monotonic() + SECONDS
        while _t.monotonic() < end:
            await asyncio.sleep(0.5)
            for ev, name in ((Trade, "Trade"), (Greeks, "Greeks"),
                             (Quote, "Quote"), (Underlying, "Underlying"),
                             (TheoPrice, "TheoPrice")):
                await drain(ev, name)

    print("── EVENTS RECEIVED " + "─" * 36)
    for k in ("Trade", "Greeks", "Quote", "Underlying", "TheoPrice"):
        print(f"  {k:<12} {got[k]}")
    if theo_syms:
        print(f"\n  TheoPrice symbols seen : {sorted(theo_syms)[:4]}")
    if und_syms:
        print(f"  Underlying symbols seen: {sorted(und_syms)[:4]}")

    print("\n── VERDICT " + "─" * 44)
    if got["Trade"] == 0 and got["Greeks"] == 0:
        print("  INCONCLUSIVE — the controls are silent too. Outside RTH with a")
        print("  quiet tape this is expected; re-run during the session.")
    elif got["TheoPrice"] or got["Underlying"]:
        print("  (a) SYMBOL SPACE. The events DO arrive — read the symbols above")
        print("      to see which space published them, and move that")
        print("      subscription in candle_feed to match.")
    else:
        print("  (b) NOT CARRIED. Controls flowed, neither analytic event did on")
        print("      EITHER symbol space. This is the vendor plan, not our code —")
        print("      relabel the two bulbs rather than leaving permanent reds.")


if __name__ == "__main__":
    asyncio.run(main())
