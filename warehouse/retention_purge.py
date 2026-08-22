#!/usr/bin/env python3
"""
warehouse/retention_purge.py  v1.0
Trim expired LOCAL data. Dry by default. Never runs unless S3 verified first.

v1.0  2026-08-25  Enforces the policy declared inert in `config.py` v4.4
(RETENTION_DAYS / RETENTION_DAYS_ARTIFACTS). Operator's sequencing:
**"We need to write the per tenor retain before writing any kind of per-tenor
purge"** — the numbers were written down first, argued with, and only then
given a consumer.

🔑 IT RUNS INSIDE `self_close`, AFTER VERIFICATION, NOT ON ITS OWN TIMER.
Two reasons, and the second is the important one:
  · The fleet just went from six EOD timers to two. Adding a third undoes that.
  · **self_close purges at the one moment verification has JUST SUCCEEDED.**
    The rule "never delete unverified data" then falls out of the ORDERING
    rather than needing its own check — if the drain came back SHORT the box
    holds up and this is never reached.

🔑 DAILY, NOT ONE-TIME. A one-shot script has to catch up on ~40 days of
accumulation in a single pass — the largest and riskiest deletion this system
would ever run. A daily pass removes one day's worth and stays boring forever.

🔴 DRY BY DEFAULT. `OT_RETENTION_APPLY=1` arms it. **The policy numbers are
ARITHMETIC FROM EMA_ANCHOR=200, NOT MEASUREMENTS** — 200 bars converted to days
per tenor. Running dry for a week costs nothing and says whether 60 days of 1h
is right or whether the fork (which needs only 21 bars) makes it far too
generous.

⚠️ THE LIFECYCLE TABLES ARE EXCLUDED IN CODE, NOT IN CONFIG. character_ledger,
plan_ledger, gate_disposition, strategy_note and fire_snapshot record STATE
TRANSITIONS AS THEY HAPPENED — a recomputation cannot reconstruct a biography,
so they are as unrecoverable as the tape itself. Indicators, forks and surface
ARE pure functions of the candles and are the safe ones to trim. A hard-coded
exclusion cannot be switched off by a config edit.

⚠️ IT REPORTS WHAT IT REMOVED, ALWAYS. A silent purge is how a wrong threshold
is discovered three weeks later, when the data it took is gone.

Run:  python3 warehouse/retention_purge.py            # dry, prints the plan
      OT_RETENTION_APPLY=1 python3 warehouse/retention_purge.py
"""

from __future__ import annotations

import os
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

# ── The policy. Mirrors the (commented-out) block in config.py v4.4. ────────
# ⚠️ DUPLICATED DELIBERATELY, AND THE DUPLICATION IS THE POINT: config's copy
# is INERT so the numbers can be read and argued with without a consumer
# existing. If they diverge, config is the document and this is the code — fix
# this file, and say so.
RETENTION_DAYS = {"1m": 5, "5m": 10, "15m": 20, "1h": 60, "1d": None}

# Non-candle raw artifacts. A RE-PUSH window, not a warm-up requirement:
# verified in source that the surface engine reads a 15-minute window and
# nothing reaches across sessions. Three days rather than two because a Friday
# push that fails silently is not noticed until Monday.
ARTIFACT_DAYS = {
    "greeks_series":     3,
    "quote_series":      3,
    "prints":            3,
    "last_trade":        3,
    "theo_series":       3,
    "underlying_series": 3,
    "session_summary":   3,
}

# 🔴 NEVER PURGED. Not configurable, not overridable.
NEVER_PURGE = {
    "character_ledger", "plan_ledger", "gate_disposition",
    "strategy_note", "fire_snapshot", "level_ledger",
    "exit_counterfactual", "circuit_breaker_events", "trades",
}

DAY = 86400.0


def _log(msg: str) -> None:
    print(f"[retention] {msg}", flush=True)


def _open(path: str):
    if not os.path.exists(path):
        return None
    try:
        return sqlite3.connect(path)
    except sqlite3.Error:
        return None


def purge(apply: bool = False, feed_db: str = "", derived_db: str = "") -> dict:
    """Returns {label: rows_removed}. Reports rather than raising."""
    feed_db = feed_db or os.path.join(HERE, "data", "feed_store.db")
    derived_db = derived_db or os.environ.get(
        "OT_DERIVED_DB", os.path.join(HERE, "data", "derived_store.db"))
    now = time.time()
    removed: dict = {}

    fc = _open(feed_db)
    if fc is not None:
        for interval, days in RETENTION_DAYS.items():
            if not days:
                continue                      # None = keep everything
            cutoff_ms = int((now - days * DAY) * 1000)
            try:
                n = fc.execute(
                    "SELECT COUNT(*) FROM candles WHERE interval=?"
                    " AND ts_epoch_ms < ?", (interval, cutoff_ms)).fetchone()[0]
            except sqlite3.Error:
                continue
            removed[f"candles/{interval}"] = n
            if apply and n:
                fc.execute("DELETE FROM candles WHERE interval=? AND"
                           " ts_epoch_ms < ?", (interval, cutoff_ms))

        for table, days in ARTIFACT_DAYS.items():
            if table in NEVER_PURGE:
                continue                      # belt and braces
            cutoff = now - days * DAY
            try:
                n = fc.execute(f"SELECT COUNT(*) FROM {table}"
                               " WHERE ts_epoch < ?", (cutoff,)).fetchone()[0]
            except sqlite3.Error:
                continue                      # table absent on this box
            removed[table] = n
            if apply and n:
                fc.execute(f"DELETE FROM {table} WHERE ts_epoch < ?", (cutoff,))
        if apply:
            fc.commit()
        fc.close()

    # ── derived: only the RECOMPUTABLE engines ──────────────────────────
    # ⚠️ indicator/fork/surface series are pure functions of the candles, so
    # trimming them costs a recomputation and nothing more. Everything else in
    # this store is lifecycle and is excluded above.
    dc = _open(derived_db)
    if dc is not None:
        for table in ("indicator_series", "fork_series", "surface_series"):
            if table in NEVER_PURGE:
                continue
            cutoff = now - 20 * DAY
            try:
                n = dc.execute(f"SELECT COUNT(*) FROM {table}"
                               " WHERE ts_epoch < ?", (cutoff,)).fetchone()[0]
            except sqlite3.Error:
                continue
            removed[f"derived/{table}"] = n
            if apply and n:
                dc.execute(f"DELETE FROM {table} WHERE ts_epoch < ?", (cutoff,))
        if apply:
            dc.commit()
        dc.close()
    return removed


def main(argv=None) -> int:
    apply = os.environ.get("OT_RETENTION_APPLY") == "1"
    removed = purge(apply=apply)
    total = sum(removed.values())
    if not removed:
        _log("nothing to evaluate (no stores found)")
        return 0
    verb = "removed" if apply else "WOULD remove"
    _log(f"{verb} {total:,} row(s)" + ("" if apply else "  [DRY — set "
                                       "OT_RETENTION_APPLY=1 to arm]"))
    for label in sorted(removed, key=lambda k: -removed[k]):
        if removed[label]:
            _log(f"   {label:<28} {removed[label]:>9,}")
    # ⚠️ VACUUM IS NOT RUN. It rewrites the whole file and would stall the box
    # for minutes at close; SQLite reuses freed pages, so the space returns as
    # new rows land. A purge that blocks the halt is worse than a larger file.
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
