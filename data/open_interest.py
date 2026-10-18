"""
data/open_interest.py  v4.3
v4.3  2026-10-18  r493 / OI.2 — the fetch runs on tasty_client's shared background loop
      (run_coroutine_threadsafe, 15 s bound), not under asyncio.run(): the throw-away
      loop bound the Session's one pooled httpx connection and was then closed, so the
      next SDK call failed "Event loop is closed" (fleet: 19-43 days per box, the 10:00
      ET structure refresh; on QQQ/SPX 304 OI-batch failures the other way round). On a
      live box the victim is the first entry's buying-power read. Found by OTV4TEST's
      10-18 audit (MSG-QQQ-1018-04). Operator, 10-18: "Yes, please".
v4.2  2026-09-09  r324 — FIX (ported from OTV4TEST r6): one event loop per fetch, immediate retry on
      a closed loop — the first batch of every cycle failed "Event loop is closed".
v4.1  2026-08-21  get_market_data_by_type IS A COROUTINE and was called
      without await - GEX has run WITHOUT open interest on every cycle since
      the port, logging a warning nobody actioned. Bridged for both call
      contexts.
Real open interest, fetched once per session over REST. GEX has never had it.

v4.0  2026-08-19  Built at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

────────────────────────────────────────────────────────────────────────────
WHAT THIS FIXES, AND HOW LONG IT WAS BROKEN
────────────────────────────────────────────────────────────────────────────
`OptionContract.open_interest` is declared at `options_chain.py:141` and
**NEVER ASSIGNED ANYWHERE**. It defaults to 0 and stays 0. `_apply_market_data`
takes exactly two maps - greeks and quote - and the chain subscribes to Greeks
and Quote only. **No OI source was ever wired.**

`gex_data` then does this, at lines 173 and 184:

    oi_proxy = open_interest if open_interest > 0 else max(1, int(1000 * gamma))
    gex      = gamma * oi_proxy * 100 * spot

Since OI is always 0, every strike falls to the proxy, so:

    **gex ~ 100,000 * gamma^2 * spot**

⚠️ **GEX HAS NEVER MEASURED DEALER POSITIONING. IT IS A GAMMA-SQUARED SURFACE.**
Three observed consequences, all confirmed in the live SPX log 2026-08-19:
  · **The "pin" is always at the money.** Gamma peaks at ATM by definition and
    squaring sharpens the peak, so the pin reports where price ALREADY IS. The
    log shows `pin = call_wall = $7725` with spot sitting on it.
  · **It churns violently.** gamma^2 near ATM moves with every tick of spot:
    GEX ran 12.4M -> 0.1M -> 2.0M in three minutes, flipping PINNING to NEUTRAL
    and back inside 90 seconds.
  · **The archive is unrecoverable.** 21 dates of chain snapshots carry
    `"oi": 0` on every contract (542 of 542 on SPX 08-19), so the historical
    pin cannot be reconstructed and the butterfly cannot be validated
    retrospectively. **Collection starts now; the trade waits for the data.**

⚠️ AND THE PROXY'S OWN COMMENT SHOWS THE REASONING THAT FAILED: *"Higher gamma
+ tighter spread = more dealer hedging at that strike."* That is a guess, and
squaring gamma is not a proxy for open interest - it is a different quantity.
A stand-in that is never labelled as unavailable becomes indistinguishable from
data, which is the same failure as v3's numeric defaults reading as measured
zeros.

────────────────────────────────────────────────────────────────────────────
WHY REST AND NOT A THIRD SUBSCRIPTION
────────────────────────────────────────────────────────────────────────────
`tastytrade.dxfeed.Summary` DOES carry `open_interest` - verified on the box.
But a Summary subscription is another stream PER CONTRACT, and v3.1 measured
TastyTrade's unpublished concurrent-session cap at ~40; the fleet already runs
~270 subscriptions. **That cost is the likeliest reason OI was never wired and
the proxy was invented instead.**

**OI updates ONCE A DAY.** It does not need a stream. `get_market_data_by_type`
returns `MarketData` carrying `open_interest` for a list of option symbols - one
REST call, cached for the session, zero subscription cost. The cadence of the
data and the cadence of the fetch finally agree.

⚠️ AND ZERO STAYS ZERO HERE. If the fetch fails or a symbol is absent, this
returns NOTHING for that symbol rather than a substitute. **A missing value must
remain missing** - inventing one is exactly how gamma-squared came to be
reported as gamma exposure for the life of the project.
"""

import logging
import asyncio
import concurrent.futures as cf
import time
from typing import Dict, Iterable, Optional

logger = logging.getLogger(__name__)

_CACHE: Dict[str, int] = {}
_CACHE_DAY: Optional[str] = None
_LAST_ATTEMPT: float = 0.0
_RETRY_S = 300.0            # a failed fetch should not hammer the API per tick
_BATCH = 100                # keep REST payloads modest
_FETCH_TIMEOUT_S = 15.0     # r493 — the tick waits at most this (asyncio.run had no bound); measured 10-18: every fetch <= 1 s (~1,500 fetches, QQQ/SPX/NVDA/TSLA, SPX 496 symbols)


def _today() -> str:
    return time.strftime("%Y-%m-%d")


def _await(coro):
    """Run an async SDK call from this SYNCHRONOUS function.

    🔴 v4.1 (2026-08-21) — `get_market_data_by_type` IS A COROUTINE FUNCTION and
    was being called WITHOUT await. Python returned a coroutine object, the
    `for r in rows` below raised "'coroutine' object is not iterable", the
    broad except swallowed it as a warning, and every cycle on every box logged
        OI wiring failed ('coroutine' object is not iterable)
        - GEX runs WITHOUT open interest
    ⚠️ SO GEX HAS NEVER ONCE HAD OPEN INTEREST IN v4. That is the handoff's open
    item "open_interest NON-ZERO in the log - v4's copy of OI.1 has never run":
    it never ran because it could not. The gamma surface has been built from
    volume-weighted greeks alone, and the butterfly's unpark depends on it.
    ⚠️ AND IT FAILED LOUDLY-BUT-HARMLESSLY, which is why it survived: a WARNING
    every cycle, with the run continuing. An error that is logged and then
    ignored is a decision nobody made.

    The SDK offers ONLY async variants (checked: `get_market_data` and
    `get_market_data_by_type` are both `async def`), so the bridge lives here.
    r493: the coroutine runs on tasty_client's background loop, from any thread
    (run_coroutine_threadsafe), bounded by _FETCH_TIMEOUT_S. Reached from the
    shared loop itself it refuses rather than deadlock; the caller's except
    logs it and GEX runs without OI that cycle, retried after _RETRY_S.
    """
    # 🔴 r493 / OI.2 — ON THE SHARED SDK LOOP, NEVER A LOOP OF ITS OWN. The
    # Session holds ONE httpx AsyncClient, and its pooled connection is bound
    # to the loop it was used on. asyncio.run() made a throw-away loop and then
    # closed it, so whichever side came second failed "Event loop is closed":
    # the next run_async call (the 10:00 structure refresh on paper; on a live
    # box the first entry's buying-power read, which refuses the entry), or
    # this fetch itself after a run_async call (GEX without OI that day).
    # Measured 19-43 days per box on the fleet. Everything else reaches the
    # SDK through tasty_client's background loop, so this does too.
    from data import tasty_client as _tc
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None
    if running is not None and running is _tc._loop:
        # blocking the shared loop from inside itself would deadlock it
        coro.close()
        raise RuntimeError("OI fetch reached from the shared SDK loop itself - "
                           "it cannot block that loop; skipped this cycle")
    fut = asyncio.run_coroutine_threadsafe(coro, _tc.get_loop())
    try:
        return fut.result(timeout=_FETCH_TIMEOUT_S)
    except cf.TimeoutError:
        fut.cancel()
        raise


def fetch_open_interest(session, occ_symbols: Iterable[str],
                        force: bool = False) -> Dict[str, int]:
    """{occ_symbol: open_interest}. Cached for the session day.

    ⚠️ RETURNS ONLY WHAT IT ACTUALLY GOT. Symbols the API did not answer for are
    ABSENT from the mapping, never present with a 0 or a guess. A caller that
    finds a symbol missing must treat GEX for that strike as unavailable rather
    than as zero - unavailable and zero are different facts, and conflating them
    is what produced a gamma-squared surface labelled as gamma exposure.
    """
    global _CACHE, _CACHE_DAY, _LAST_ATTEMPT

    day = _today()
    if _CACHE_DAY != day:
        _CACHE, _CACHE_DAY = {}, day

    syms = [s for s in (occ_symbols or []) if s]
    if not syms:
        return dict(_CACHE)

    missing = [s for s in syms if s not in _CACHE]
    if not missing and not force:
        return {s: _CACHE[s] for s in syms if s in _CACHE}

    if not force and (time.time() - _LAST_ATTEMPT) < _RETRY_S and _CACHE:
        # a recent failure; serve what is cached rather than retry every tick
        return {s: _CACHE[s] for s in syms if s in _CACHE}

    _LAST_ATTEMPT = time.time()
    try:
        from tastytrade.market_data import get_market_data_by_type
    except Exception as e:                                     # noqa: BLE001
        logger.warning("OI: SDK market_data unavailable (%s) - GEX will run "
                       "WITHOUT open interest", e)
        return {s: _CACHE[s] for s in syms if s in _CACHE}

    got = 0
    batches = [missing[i:i + _BATCH] for i in range(0, len(missing), _BATCH)]

    async def _all():
        # r324 (ported from OTV4TEST r6) — ONE loop for every batch. Each batch
        # under its own asyncio.run() handed the SDK's async client a CLOSED loop
        # on the next call ("Event loop is closed" on the first batch of every
        # cycle). A closed-loop error is retried once immediately.
        out = []
        for batch in batches:
            rows = None
            for attempt in (1, 2):
                try:
                    rows = await get_market_data_by_type(session, options=batch)
                    break
                except Exception as e:                         # noqa: BLE001
                    if attempt == 1 and "loop is closed" in str(e).lower():
                        continue
                    logger.warning("OI: fetch failed for %d symbol(s): %s", len(batch), e)
            out.append(rows or [])
        return out

    try:
        results = _await(_all())
    except Exception as e:                                     # noqa: BLE001
        logger.warning("OI: fetch failed outright: %s", e)
        results = []
    for rows in results:
        for r in rows or []:
            sym = getattr(r, "symbol", None)
            oi = getattr(r, "open_interest", None)
            if not sym or oi is None:
                continue
            try:
                _CACHE[sym] = int(oi)
                got += 1
            except Exception:                                  # noqa: BLE001
                continue

    if got:
        nz = sum(1 for v in _CACHE.values() if v > 0)
        logger.info("OI: fetched %d symbol(s), %d cached, %d NON-ZERO",
                    got, len(_CACHE), nz)
        if nz == 0:
            # ⚠️ SAY IT LOUDLY. All-zero OI is exactly the condition that made
            # GEX meaningless for the life of v3, and it hid because nothing
            # ever looked.
            logger.warning("OI: every value is ZERO - GEX will be a "
                           "gamma-squared surface, NOT dealer positioning")
    else:
        logger.warning("OI: no open interest retrieved - GEX is running "
                       "WITHOUT it (see data/open_interest.py header)")

    return {s: _CACHE[s] for s in syms if s in _CACHE}


def coverage() -> tuple:
    """(cached, non_zero) - for a caller that wants to report OI health."""
    return len(_CACHE), sum(1 for v in _CACHE.values() if v > 0)
