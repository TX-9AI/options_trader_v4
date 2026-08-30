#!/usr/bin/env python3
"""
warehouse/retention_purge.py  v1.1
v1.1  2026-08-29  r191 — THE DERIVED-SERIES PURGE LIST BECOMES A CONSTANT,
      and its justification is retired. Behaviour is unchanged: the same
      three tables, the same 20 days. What changes is that
      `DERIVED_ARTIFACT_DAYS` is importable, so `check_purge_pushed` can see
      it — which is why it never noticed that all three were being deleted
      with no push stage. See the block above `purge()`'s derived loop for
      why "pure functions of the candles" does not hold, especially for
      `surface_series`.
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
# 🔴 r191 — THE DERIVED SERIES PURGE IS NOW A CONSTANT, AND IT WAS THE REASON
# NOTHING CAUGHT THIS. These three were deleted at 20 days by a HARDCODED TUPLE
# inside `purge()`, while `tests/check_purge_pushed.py` proves its invariant by
# importing `ARTIFACT_DAYS` and `NEVER_PURGE` — module constants. A purge list
# the checker cannot see is a purge list outside the invariant, so all three
# were being trimmed with NO PUSH STAGE for as long as the purge has been armed
# (r162). Same shape as the v1.0 finding, one level down.
DERIVED_ARTIFACT_DAYS = {
    "indicator_series":  20,
    "fork_series":       20,
    "surface_series":    20,
}

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

    # ── derived: the series the engines recompute ───────────────────────
    # ⚠️ THE ORIGINAL JUSTIFICATION WAS "pure functions of the candles, so
    # trimming them costs a recomputation and nothing more". r191 keeps the
    # policy and RETIRES that reasoning, for two measured objections:
    #   · A recomputation tells you what TODAY'S CODE would have said, not what
    #     the bot ACTUALLY SAW. Those differ exactly when there is a bug, which
    #     is the only time anyone goes looking. The operator made this same
    #     argument about ORB state: the derived value is what the range SHOULD
    #     have been, the recorded value is what was used.
    #   · `surface_series` (charm / vanna / GEX) is NOT a function of the
    #     candles at all. It comes off the options chain and `greeks_series`,
    #     and chain snapshots are explicitly NOT reconstructible after the
    #     session. For that table the premise was simply false.
    # So the purge stands — 20 days of intraday series is a real disk cost —
    # but it is now safe because s3_push v4.5 warehouses all three first, and
    # DERIVED_ARTIFACT_DAYS above puts them inside check_purge_pushed's reach.
    dc = _open(derived_db)
    if dc is not None:
        for table, days in DERIVED_ARTIFACT_DAYS.items():
            if table in NEVER_PURGE:
                continue
            cutoff = now - days * DAY
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
    """`--apply` arms it. So does OT_RETENTION_APPLY=1, for the CLI.

    🔴 r162 — WHY THE ARGUMENT EXISTS. This shipped DRY BY DEFAULT, armed only
    by an environment variable, pending a review of the policy numbers that was
    never scheduled. `self_close` has called `main([])` since it was written —
    an EMPTY argv, with no environment set — so **the purge ran dry every night
    for two months, printed what it WOULD delete, and deleted nothing.**
    ⚠️ THE COST, 2026-08-27: `feed_store.db` reached 1.5-1.8 GB per box, the
    6.7 GiB roots hit 100%, and the fleet went blind MID-SESSION. QQQ and MU
    crash-looped; recovering them cost their swapfiles, a failed VACUUM that
    left the database LARGER, and a 14-box volume rebuild to 10 GiB.
    ⚠️ AND IT WAS INVISIBLE BY CONSTRUCTION. A dry run logs the same line every
    night. **Sixty identical log lines are indistinguishable from a job that
    works** — the same failure class as the pytest chain that was decorative
    for weeks and the tooling check that printed green on a broken environment.
    ⚠️ SO THE ARMING IS NOW EXPLICIT AT THE CALL SITE, not ambient in an
    environment nobody sets. `self_close` passes `--apply`; a human running it
    by hand still gets DRY unless they ask for it.
    """
    argv = list(argv or [])
    apply = ("--apply" in argv) or os.environ.get("OT_RETENTION_APPLY") == "1"
    removed = purge(apply=apply)
    total = sum(removed.values())
    if not removed:
        _log("nothing to evaluate (no stores found)")
        return 0
    verb = "removed" if apply else "WOULD remove"
    _log(f"{verb} {total:,} row(s)" + ("" if apply else "  [DRY — set "
                                       "OT_RETENTION_APPLY=1 to arm]"))
    # ── 🔴 r162 — A DRY PURGE AT SHUTDOWN IS A DEFECT, NOT A LOG LINE ────────
    # ⚠️ THE WHOLE FAILURE WAS SILENCE. Sixty nights of "WOULD remove 1.7M
    # rows" at INFO is indistinguishable from a job that works — nobody reads
    # an unchanging line. Name the consequence so the next silence is visible.
    if not apply and total:
        _log(f"⚠️⚠️ RETENTION IS DRY — {total:,} row(s) were NOT removed. The "
             f"store will keep growing; this is how the fleet reached 100% "
             f"disk and went blind mid-session on 2026-08-27.")
    for label in sorted(removed, key=lambda k: -removed[k]):
        if removed[label]:
            _log(f"   {label:<28} {removed[label]:>9,}")
    # ⚠️ VACUUM IS NOT RUN. It rewrites the whole file and would stall the box
    # for minutes at close; SQLite reuses freed pages, so the space returns as
    # new rows land. A purge that blocks the halt is worse than a larger file.
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
