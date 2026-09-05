"""
shadow/observer.py  v4.3
v4.3  2026-09-05  r268 — the tick SEEDS a cold accumulator from `df_1m`, which
      this function already holds, and stamps `velocity_state` on every record.
      See shadow/primitives.py v4.1 for the failure this closes. ⚠️ The seed is
      never fatal — a failure logs and the tick continues, because raising here
      would cost the whole record and produce exactly the silent gap the change
      exists to remove. ⚠️ And the tick now carries ONE epoch: a first cut
      re-derived it by parsing `prim.ts_et` back into a datetime with the wrong
      format string (that field uses a space, not a `T`), which is a second
      source of truth for a value already in scope.
v4.2  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).


Shadow observer: records primitives without trading them.

v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

shadow/observer.py — the shadow observer service (OBSERVE-ONLY, never trades).
DOCSTRING CORRECTION ONLY, zero code change. The line below
        described the data source as "yfinance candles + quote". That has been
        false since the v3.0 purge: market_data was rewritten behind the preserved
        get_cache() seam and now reads the on-box shared SQLite store written by
        data/candle_feed.py (TastyTrade/DXFeed), read-only and heartbeat-guarded.
        The observer required zero changes and so nobody noticed the docstring rot
        — which is exactly the failure mode that extracting this subsystem from its
        tarballs was meant to expose. There is no yfinance in this repo.
initial release.
Runs as its OWN systemd service (shadow-observer.service) in its OWN process —
zero shared memory with optionsbot.service. Per tick during RTH it:
  1. reads the SAME market data source the bot's analysis reads
     (data_cache -> market_data -> the shared TastyTrade/DXFeed candle store)
     via its own in-process DataCache instance,
  2. runs the SAME analysis engines (volatility/trend/structure/liquidity —
     fresh instances in this process; .analyze() returns new state objects),
  3. computes the shared primitives (velocity/magnitude/position),
  4. (stage 2) runs the per-pattern scorers,
  5. appends one JSON line to data/shadow/<YYYY-MM-DD>/<SYMBOL>.jsonl.
It places no orders, imports nothing from execution//risk//strategy//
notifications/, never opens trades.db, and writes only under data/shadow/.
STAGING (build-order de-risk, per the shadow spec):
  OT_SHADOW_STAGE=1 (default) — primitives measure-only. Log velocity for a few
      sessions and verify against data/OHLC/ that it accelerates through levels
      on breakouts and collapses on rejections BEFORE any scorer consumes it.
  OT_SHADOW_STAGE=2 — enable the sweep-reversal precursor scorer + would-fire
      flags across candidate thresholds. Still zero firing anywhere.
Would-fire thresholds are logged as a RANGE (0.50..0.95) precisely because no
final threshold is chosen yet — the EOD comparator reads each candidate's base
rate off the shadow logs; thresholds are the LAST parameter, set from data.
Usage:  python -m shadow.observer            # this box's OT_INSTRUMENT
        python -m shadow.observer --once     # single tick then exit (smoke test)
"""

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import asdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from config import INSTRUMENT, POLL_INTERVAL_SECONDS, RTH_OPEN_ET, RTH_CLOSE_ET
from data.data_cache import get_cache
from analysis.volatility_engine import get_volatility_engine
from analysis.trend_engine import get_trend_engine
from analysis.structure_analyzer import get_structure_analyzer
from analysis.liquidity_mapper import get_liquidity_mapper
from analysis.market_state import MarketState

from shadow.primitives import TickAccumulator, compute_primitives
from shadow.scorers import build_scorers

ET = ZoneInfo("America/New_York")
THRESHOLDS = [round(0.50 + 0.05 * i, 2) for i in range(10)]   # 0.50 .. 0.95
STAGE = int(os.environ.get("OT_SHADOW_STAGE", "1"))

# Output self-locates inside the repo's data/ dir, mirroring the candle logger —
# no /var/lib, no per-box path. Files: data/shadow/<YYYY-MM-DD>/<SYMBOL>.jsonl
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO_ROOT, "data", "shadow")

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s shadow: %(message)s",
                    stream=sys.stdout)          # journal via systemd, never bot.log
logger = logging.getLogger(__name__)


def _now_et() -> datetime:
    return datetime.now(tz=ET)


def _in_rth(dt: datetime) -> bool:
    if dt.weekday() >= 5:
        return False
    hm = (dt.hour, dt.minute)
    return RTH_OPEN_ET <= hm < RTH_CLOSE_ET


def _seconds_to_next_open(dt: datetime) -> float:
    d = dt
    while True:
        candidate = d.replace(hour=RTH_OPEN_ET[0], minute=RTH_OPEN_ET[1],
                              second=0, microsecond=0)
        if d.weekday() < 5 and candidate > dt:
            return (candidate - dt).total_seconds()
        d = (d + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def _out_path(dt: datetime, symbol: str) -> str:
    day_dir = os.path.join(OUT_DIR, dt.strftime("%Y-%m-%d"))
    os.makedirs(day_dir, exist_ok=True)
    return os.path.join(day_dir, f"{symbol}.jsonl")


# r268 — how many trailing 1m closes a cold accumulator seeds from. 40 covers
# MIN_TYPICAL_SAMPLES (20) with margin on a short session start.
SEED_BARS = 40


def _prim_fields(prim) -> dict:
    d = asdict(prim)
    d.pop("named_levels", None)          # keep lines compact; nearest refs suffice
    return d


def one_tick(symbol: str, acc: TickAccumulator, scorers: list) -> dict:
    """One observation. Read-only over cache + engines; returns the log record."""
    cache = get_cache(symbol)
    data = cache.get_all()
    price = cache.get_price()
    if price is None:
        raise ValueError("no price")

    df_5m, df_1m = data.get("5m"), data.get("1m")
    df_15m, df_1h = data.get("15m"), data.get("1h")
    if df_5m is None or df_5m.empty:
        raise ValueError("no 5m data")
    df_1h_safe = df_1h if df_1h is not None else df_5m

    vol = get_volatility_engine().analyze(df_5m, df_1h_safe, price)
    trend = get_trend_engine().analyze(data)
    structure = get_structure_analyzer().analyze(df_5m, df_15m, df_1h, price)
    liq = get_liquidity_mapper().analyze(df_5m, df_15m, price)

    now = _now_et()
    # ⚠️ ONE EPOCH FOR THE WHOLE TICK. A first cut re-derived it by parsing
    # `prim.ts_et` back into a datetime — with the wrong format string, since
    # that field uses a space and not a `T`. The value is right here; parsing a
    # string the same function just formatted is a second source of truth for
    # no reason.
    epoch_s = time.time()
    prim = compute_primitives(
        acc, epoch_s=epoch_s, ts_et=now.strftime("%Y-%m-%d %H:%M:%S"),
        minute_key=now.strftime("%Y-%m-%dT%H:%M"), price=price,
        vol_state=vol, liq_map=liq,
    )

    # ── 🔴 r268 — SELF-HEALING RECOVERY, NOT A START-TIME DEPENDENCY ─────
    # The accumulator is live-only, so a reboot or a `Restart=always` crash
    # loop enters RTH with an empty deque and emits null velocity for the next
    # five minutes — a record that reads as a quiet tape. `df_1m` is ALREADY
    # HERE and is backfilled from the session open, so recovery is a loop over
    # data this function already fetched. It runs whenever the accumulator is
    # short, which means it covers the first tick of the day, the fourth
    # restart of a crash loop, and every case in between — no timer, and
    # nothing that depends on WHEN the process started.
    if acc.velocity_state(epoch_s) == "warming" and df_1m is not None:
        try:
            bars = [(float(ix.timestamp()), float(cl))
                    for ix, cl in zip(df_1m.index, df_1m["close"])]
            seeded = acc.seed_from_closes(bars[-SEED_BARS:])
            if seeded:
                logger.info(f"velocity seeded from {seeded} 1m close(s) — "
                            f"recovering a cold accumulator")
        except Exception as exc:                                # noqa: BLE001
            # ⚠️ NEVER FATAL. A failed seed costs velocity fidelity for a few
            # minutes; raising here would cost the whole tick.
            logger.warning(f"velocity seed skipped: {exc}")

    rec = {
        "ts": prim.ts_et, "symbol": symbol, "stage": STAGE,
        "price": price,
        # 🔑 PROVENANCE ON EVERY RECORD. `warming` = not enough samples yet,
        # `seeded` = the typical baseline still contains 1m-close ROCs whose
        # magnitudes are on a different scale from live poll-interval ROCs,
        # `live` = ticks only. A null velocity and a quiet tape must never
        # render alike, and a seeded baseline must never be mistaken for a
        # measured one.
        "velocity_state": acc.velocity_state(epoch_s),
        # was hardcoded UNKNOWN and conviction is not computed in v4. Rows
        # before r58 carry "UNKNOWN"/0.0; absent keys after r58 mean r58+.
        "primitives": _prim_fields(prim),
        "scores": [],
    }

    if STAGE >= 2:
        for scorer in scorers:
            res = scorer.score(prim, liq_map=liq)
            entry = {
                "scorer": res.scorer,
                "eligible": res.eligible,
                # null = pattern cannot form here; 0.0 = possible, nothing assembled
                "conviction": res.conviction,
                "direction": res.direction,
                "level": res.level_name, "level_price": res.level_price,
                "stages": res.stages, "invalidated": res.invalidated,
                "notes": res.notes,
            }
            if res.conviction is not None:
                entry["would_fire"] = {
                    str(th): bool(res.conviction >= th) for th in THRESHOLDS
                }
                entry["would_entry_underlying"] = price
            rec["scores"].append(entry)
    return rec


def main():
    ap = argparse.ArgumentParser(description="Shadow observer (observe-only)")
    ap.add_argument("--symbol", default=INSTRUMENT)
    ap.add_argument("--once", action="store_true", help="single tick, then exit")
    args = ap.parse_args()

    symbol = args.symbol
    acc = TickAccumulator()
    scorers = build_scorers()
    logger.info(f"shadow observer up — {symbol}, stage={STAGE}, "
                f"poll={POLL_INTERVAL_SECONDS}s, out={OUT_DIR} — OBSERVE-ONLY")

    while True:
        now = _now_et()
        if not _in_rth(now):
            if args.once:
                logger.info("outside RTH and --once set — exiting")
                return
            wait = _seconds_to_next_open(now)
            logger.info(f"outside RTH — sleeping {wait/3600:.1f}h to next open")
            time.sleep(min(wait, 1800))          # chunked so restarts stay cheap
            continue

        tick_start = time.time()
        try:
            rec = one_tick(symbol, acc, scorers)
            with open(_out_path(now, symbol), "a") as f:
                f.write(json.dumps(rec) + "\n")
        except Exception as e:
            logger.warning(f"tick failed (continuing): {e}")

        if args.once:
            logger.info("--once complete")
            return
        time.sleep(max(0.0, POLL_INTERVAL_SECONDS - (time.time() - tick_start)))


if __name__ == "__main__":
    main()
