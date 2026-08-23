"""
warehouse/s3_push.py  v4.2
v4.2  2026-08-23  R-PROJECT: THE SERIES TABLES ARE NOW PUSHED. retention_purge
      v1.0 calls its 3 days on greeks/quotes/prints/etc "a RE-PUSH window" —
      but no push stage existed for any of the seven series tables, so the
      moment OT_RETENTION_APPLY=1 lands, the manifold's series data would be
      deleted having NEVER been warehoused: "pruned before you knew you
      needed it", the exact loss the manifold was built to end. Found while
      building tests/exit_replay.py, whose premium paths read quote_series on
      control. push_series batches each table's rows since a per-table
      high-water mark into ONE object per run (push_candles' pattern — a
      per-row object at ~250 chain symbols × 15s would be tens of thousands
      of PUTs/hour). Guarded by tests/check_purge_pushed.py, born red at r84.
v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

Pushes collected data to S3 and verifies what landed.

v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

#!/usr/bin/env python3
# options_trader_v3/warehouse/s3_push.py — v1.9
# WH.6: THE COUNTER COUNTED PUTS, NOT KEYS - AND THE LEDGER
#         PERSISTS. Push the same key twice and n reads 2 while S3 holds 1,
#         FOREVER; a prefix re-pushed once is short for good and the gap only
#         grows. That produced two days of "warehouse NOT confirmed - data
#         stranded on box" alarms.
#         MEASURED 08-18: ten prefixes each short by exactly ONE (1561/1560,
#         1147/1146, 1260/1259, 2280/2279, 2359/2358, 1961/1960, 1197/1196,
#         1263/1262, 2046/2045). Listed the bucket directly: shadow/dt=2026-07-24
#         /sym=META held 1560 and trades/dt=2026-08-17/sym=GS held 33 - exactly
#         what verify's own LIST said. NOTHING WAS EVER MISSING.
#         This file's own 07-27 header called it: "wrong counters make the verify
#         line lie in both directions." There was no evidence until WH.5 stopped
#         truncating the diagnosis at the log boundary.
#         FIX: _confirm dedupes by key within the run; `--reconcile` resets the
#         counters to the live S3 truth for the already-poisoned ledger.
#         RECONCILE IS EXPLICIT, NEVER AUTOMATIC - self-healing on every verify
#         would also silently erase a GENUINE loss. A verification that repairs
#         itself is not a verification.
#         And the SHORT report now names which signature it sees: a small,
#         consistent shortfall across many prefixes is counter drift; a varying
#         one is possible real loss.
"""
"""
Box-side warehouse pusher — ships locally-written archives to S3.

CHANGELOG
    v1.8 — 2026-08-16 — ORB REMOVED. It was ONE stage covering both files, so
           eleven stages become TEN — I first wrote "nine", which was a
           miscount of my own change. `raw/orb_state` had captured ZERO objects in thirty days and
           `raw/orb_range` 81, and nothing consumed either. The operator asked
           the right question — "do we even need it? the orb state could be
           derived by the first 5-minute candle of the RTH" — and the answer is
           that ALL of it is already available:
             * the RANGE recomputes from candles, warehoused at 1m and 5m;
             * the ATTEMPTS are logged individually in the signal journal, with
               price and timestamp — `tests/orb_conversion.py` already derives
               break-attempts from `retest_check` events keyed on
               (symbol, date, direction, attempt) and never opens orb_state.json;
             * the state machine is the only unique part and nothing has ever
               asked for it.
           I had argued the attempt counter was not derivable. That was wrong —
           the attempt number rides on every journal event. **A stream nobody
           consumes that captured nothing is not a capture bug to fix; it is a
           stream to stop collecting.** The 81 existing orb_range objects stay
           in raw/ (which never deletes) and simply stop growing.
           warehouse. FOUND WHILE BUILDING THE READER, NOT BY LOOKING: the
           control-side bundle `fleet_trades_<date>.json` has a
           those two tables inside trades.db — and NOTHING WAS PUSHING THEM. WH.2
           scoped itself to the `trades` table and said the other two would
           follow; WH.3 covered six OTHER streams and they were never picked up.
           A reader built on top would have reproduced two permanently empty
           sections and the WH.11 diff would have shown a gap forever, blamed on
           the reader rather than on the missing push.
           Both are append-only (unlike `trades`, which mutates), so they use the
           same per-row content hash with no CDC semantics needed.
    v1.6 — 2026-08-16 — WH.14: the LIQUIDITY LEDGER joins the warehouse, and
           `<SYM>_EXT` is documented as already handled. LIQ.4 wired
           `data/liquidity_ledger/<date>/<SYMBOL>.json` on 08-15 — the level
           book the mapper builds from — and nothing was pushing it. Whole-file,
           like OHLC: the ledger is rewritten on EVERY closed bar, but this
           timer samples it every 5 minutes, so the object count lands near the
           chain archive's rather than near 390/box/day. Each distinct sampled
           state is its own object, so the intraday EVOLUTION of the level book
           survives instead of only its closing shape.
           FEED.2's extended-hours tape needs NO change here: it lands in
           feed_store as its own store symbol `<SYM>_EXT`, and push_candles
           already does SELECT DISTINCT symbol, so it partitions as
           `sym=<SYM>_EXT` automatically.
    v1.5 — 2026-08-13 — WH.6: SINGLE INSTANCE, AND POLITE. Two pushers could run
           at once — the 5-minute timer plus the EOD conductor's SSH `--verify`,
           which drains before it reports. Both loaded the same ledgers and both
           flushed: last write won, progress was lost and redone, and the
           per-prefix counters could end up wrong — which would make `--verify`
           report OK or SHORT INCORRECTLY. No duplicate objects (content-hash
           keys) and no data loss, but the verify signal is the whole point of
           the EOD gate, so an untrustworthy one is worse than none.
           (a) flock on every invocation path. A normal timer run that finds the
               lock held exits 0 silently — the run already in flight is doing
               the work.
           (b) `--verify` waits up to OT_S3_LOCK_WAIT seconds for the lock. If it
               cannot get it, it SKIPS the drain and verifies anyway, reporting
               `drained=no` so control can tell "nothing left to push" apart from
               "someone else is still pushing".
    v1.4 — 2026-08-13 — WH.5: STREAM ORDER. The first full fleet count exposed
           an ordering fault of mine: the streams ran chains -> trades ->
           journal -> shadow -> ohlc -> eod -> orb -> candles, so the 110,639
           object signal-journal backlog consumed the entire run and everything
           BEHIND it starved. ohlc sat at 108 against an expected ~783, eod at
           8 against ~58, candles at 20 — not corruption, just never reached.
           A timeout must truncate the TAIL, not the head, so the order is now
           smallest-and-most-perishable first and the bulk streams last.
           TimeoutStartSec also went 240s -> 1800s: 240 was a guess made before
           any volume was known. systemd skips a timer trigger while the
           oneshot is still running, so a long drain is safe.
    v1.3 — 2026-08-13 — WH.4: survivable drains and box-side verification.
           (a) INCREMENTAL LEDGER SAVES. v1.0-v1.2 saved the ledger ONCE at the
               end of main(). The unit sets TimeoutStartSec=240, so a backlog
               drain longer than four minutes was killed with NO progress
               recorded — every object re-PUT next run, forever. Content-hashed
               keys meant no duplicates appeared, so it would have livelocked
               silently rather than failing loudly. Ledgers now flush every
               FLUSH_EVERY confirmations.
           (b) PER-PREFIX COUNTERS. Each confirmation increments an O(1)
               {n, bytes} counter for its dt=/sym= prefix. No per-object
               bookkeeping.
           (c) `--verify`. Drains, then reconciles those counters against what
               S3 actually holds — per prefix, on COUNT and BYTES, both of
               which list_objects_v2 returns for free. Prints ONE
               machine-readable line and always exits 0. This is what the EOD
               conductor gates a box's shutdown on, so the box answers for
               itself instead of control modelling the box's local state.
    v1.2 — 2026-08-13 — WH.3: the remaining six streams. signal_journal and
           shadow (append-only jsonl, same offset ledger as chains, with
           `ruleset` and `event` lifted into the envelope); OHLC day-CSVs
           (whole-file objects, not one per candle); feed_store candles (all
           intervals, high-water mark per symbol+interval, VIX only from the
           SPX box); the EOD json pair; and ORB state captured on
           state==ESTABLISHED rather than on a clock time.
    v1.1 — 2026-08-13 — WH.2: trades. Plus a LATENT DUPLICATE BUG FIXED in the
           v1.0 key derivation. v1.0 hashed the whole ENVELOPE, which contains
           `pushed_at_utc` — so the same source line pushed at two different
           seconds produced two different keys, i.e. a duplicate. The v1.0 test
           that claimed to prove idempotency passed only because both pushes
           happened inside the same second. The hash is now taken over the
           RECORD alone, which is genuinely stable, and the test now forces a
           clock change between pushes. The 16,782 chain objects already in the
           bucket carry v1.0-basis keys; their ledgers prevent re-push, so they
           are unaffected in place.
    v1.0 — 2026-08-12 — initial release. Chain snapshots only; other streams
           (trades.db, signal journal, feed_store) land in later versions
           behind the same ledger + verify machinery.

WHY THIS EXISTS
    Option chains are NOT reconstructible after the session. A quote for a
    strike nobody selected is gone permanently at 16:00 — no vendor, no
    backfill, no replay recovers it. Today the only copy lives on the box that
    wrote it, and that box is STOPPED after the session. Because the morning
    selector picks movers, a box that traded today may not wake for weeks; its
    archive is unreachable that whole time and lost outright if the box is
    rebuilt. This module moves each snapshot to durable storage within one
    cadence interval of it being written.

DESIGN RULES
  1. NEVER raises. main() returns 0 unconditionally. A full disk, an expired
     credential, a truncated file, a network partition — all degrade to
     "pushed nothing this run", never to a traceback and never to a non-zero
     exit that would make a fleet fan-out discard the output of every box.
  2. NOT IN THE TRADING LOOP. Runs as its own systemd timer under system
     python. The bot's behaviour is byte-identical whether this module exists
     or not, and installing it requires no bot restart.
  3. STDLIB + boto3 ONLY. System python has boto3 1.40.72 fleet-wide; the bot
     venv does not, and this module must never need it. No pandas, no repo
     imports — it reads files, it does not import the writer.
  4. SILENT WHEN IDLE. On any given day ~14 boxes never trade and therefore
     have no chains at all. "Nothing to push" is the NORMAL state and prints
     nothing. An idle box that looks like a failure is how a real failure gets
     ignored (WORKING_AGREEMENT §17).
  5. CONFIRMED MEANS READ-BACK-AND-COMPARE. A 200 from PutObject proves bytes
     were accepted, not that the object is retrievable, parseable or equal to
     what we sent. Every object is re-read and byte-compared before the ledger
     records it. The ledger is what a future scrub will gate deletion on, so a
     false confirmation there is a data-loss bug, not a reporting bug.

KEY CONVENTION
    raw/chain_snapshots/dt=<YYYY-MM-DD>/sym=<SYM>/<epoch_ms>-<sha256[:16]>.json

    Hive-style dt=/sym= so Athena or Glue can discover partitions without a
    custom parser. The suffix is a CONTENT HASH rather than a uuid4: a uuid
    makes every retry write a duplicate object, while a content hash makes the
    push idempotent — a re-run after a crash mid-verify overwrites the same
    key with identical bytes instead of creating a second copy of one snapshot.
    Collision safety is unchanged (concurrent boxes write different symbols,
    and two identical snapshots ARE the same snapshot).

LEDGER
    ~/.vertigo_warehouse/chain_ledger.json, one entry per source file:
        {"<path>": {"n": <lines confirmed>, "last_sha": ..., "last_key": ...,
                    "confirmed_utc": ...}}
    Source files are append-only, so a confirmed line count is a valid resume
    point. Written atomically (tmp + os.replace) so a kill mid-write cannot
    leave a truncated ledger — which would silently re-push or, worse, look
    like more was confirmed than actually was.

    The ledger lives OUTSIDE the repo. Nothing this module writes lands in the
    working tree, so there is no scaffolding to remember to clean up.
"""

import gzip
import hashlib
import json
import os
import fcntl
import socket
import sqlite3
import sys
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

SCHEMA_VERSION = 1
DATATYPE = "chain_snapshot"

BUCKET = os.environ.get("OT_S3_BUCKET", "vertigo-warehouse-tx9ai")
REGION = os.environ.get("OT_S3_REGION", "us-east-2")
PREFIX = os.environ.get("OT_S3_PREFIX", "raw")
# Kill switch, house style: one env var per change, default ON.
ENABLED = os.environ.get("OT_S3_PUSH", "1") != "0"

_HOME = os.path.expanduser("~")
SRC_ROOT = os.environ.get(
    "OT_CHAIN_ROOT", os.path.join(_HOME, "options-trader", "data", "chain_snapshots")
)
STATE_DIR = os.environ.get("OT_WAREHOUSE_STATE", os.path.join(_HOME, ".vertigo_warehouse"))
LEDGER_PATH = os.path.join(STATE_DIR, "chain_ledger.json")

HOST = socket.gethostname()


def _now_utc() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _canon(rec) -> bytes:
    """Canonical bytes for the SOURCE RECORD ONLY — the basis for every key.

    Deliberately excludes the envelope. The envelope carries `pushed_at_utc`,
    which changes every run, so hashing it made the key a function of WHEN the
    push happened rather than WHAT was pushed: the same line pushed twice in
    different seconds landed as two objects. Keys must be a pure function of
    content or idempotency is a coincidence.
    """
    return json.dumps(rec, sort_keys=True, separators=(",", ":"),
                      default=str).encode("utf-8")


def _et_day(iso_ts: str) -> str:
    """Trading day (ET) from any ISO timestamp carrying an offset.

    `dt=` MUST mean the same thing in every stream or joins silently return
    nothing. Chain snapshots, the journal and OHLC all bucket by ET date, so
    trades — whose timestamps are UTC — are converted rather than truncated.
    """
    try:
        dt = datetime.fromisoformat(str(iso_ts))
        if dt.tzinfo is None:
            return str(iso_ts)[:10]
        return dt.astimezone(ZoneInfo("America/New_York")).date().isoformat()
    except Exception:
        return str(iso_ts)[:10]


def _epoch_ms(rec: dict, fallback_ms: int) -> int:
    """Snapshot time in epoch ms, from the record's own ET timestamp."""
    try:
        dt = datetime.fromisoformat(str(rec.get("ts_et", "")))
        if dt.tzinfo is None:
            return fallback_ms
        return int(dt.timestamp() * 1000)
    except Exception:
        return fallback_ms


def read_lines(path: str):
    """All COMPLETE lines from a multi-member gzip file.

    The bot appends to this file while we read it, so the final member may be
    partially written. gzip raises at that point; every line already yielded
    is intact, so we keep those and stop. The partial line is picked up on the
    next run once the writer has finished it.
    """
    out = []
    try:
        with gzip.open(path, "rb") as f:
            for raw in f:
                out.append(raw)
    except Exception:
        pass
    if out and not out[-1].endswith(b"\n"):
        out.pop()
    return out


def load_ledger(path: str = LEDGER_PATH) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data = data if isinstance(data, dict) else {}
    except Exception:
        data = {}
    _OPEN[path] = data          # register for mid-drain flushing
    return data


def flush_all():
    """Persist every open ledger. Called mid-drain, not just at the end.

    The whole point: a drain killed at TimeoutStartSec must leave PROGRESS
    behind. Saving only at the end meant a long backlog could never finish and
    would silently repeat itself forever.
    """
    ok = True
    for path, data in _OPEN.items():
        if not save_ledger(data, path):
            ok = False
    return ok


def acquire_lock(wait_s: int = 0):
    """Exclusive flock, or None. Guards EVERY invocation path.

    The timer and the EOD conductor's `--verify` are different entrypoints to
    the same work, and nothing else was stopping them overlapping. Two
    processes sharing one ledger is not a duplicate-object problem — the keys
    are content-hashed — it is a LOST PROGRESS and WRONG COUNTERS problem, and
    wrong counters make the verify line lie in both directions.
    """
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        fh = open(LOCK_PATH, "w")
    except Exception:
        return None
    deadline = time.time() + max(0, wait_s)
    while True:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fh
        except OSError:
            if time.time() >= deadline:
                try:
                    fh.close()
                except Exception:
                    pass
                return None
            time.sleep(1)


_SEEN_KEYS = set()          # WH.6: keys confirmed in THIS process


def _confirm(key: str, body: bytes, counters: dict):
    """Record one confirmed object: bump its prefix counters, flush if due.

    ⚠️ WH.6 (2026-08-18) — THIS COUNTED PUTS, NOT KEYS, AND THE LEDGER PERSISTS.
    Push the same key twice and `n` reached 2 while S3 held 1 — **permanently**,
    because the ledger is saved to disk and the gap can only ever grow. A prefix
    re-pushed once was short forever.
    That is what produced two days of *"warehouse NOT confirmed — data stranded
    on box"* alarms. **Verified 2026-08-18: S3 held 1560 objects for
    `raw/shadow/dt=2026-07-24/sym=META/` and the LIST agreed — the counter said
    1561. NOTHING WAS EVER MISSING.** Ten prefixes, ten off-by-ones: the
    signature of a systematic count error, not of data loss, which scatters.
    This module's own header called the hazard on 2026-07-27: *"wrong counters
    make the verify line lie in both directions."* It did.

    ⚠️ THE SET IS PER-PROCESS, NOT PERSISTED. Bounding it by run size keeps it
    small (a drain pushes hundreds, not the 40k+ objects in history), and the
    cross-run case is handled by `--reconcile` instead. A persisted key set
    would be a second ledger with its own drift.
    """
    prefix = key.rsplit("/", 1)[0] + "/"
    c = counters.setdefault(prefix, {"n": 0, "bytes": 0})
    if key in _SEEN_KEYS:
        return                  # same key, same content-hash: S3 has ONE object
    _SEEN_KEYS.add(key)
    c["n"] += 1
    c["bytes"] += len(body)
    _SINCE_FLUSH[0] += 1
    if _SINCE_FLUSH[0] >= FLUSH_EVERY:
        _SINCE_FLUSH[0] = 0
        flush_all()


def save_ledger(ledger: dict, path: str = LEDGER_PATH) -> bool:
    """Atomic write. A torn ledger is worse than no ledger: it can claim more
    lines confirmed than actually landed, and a future scrub keys on it."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(ledger, f, separators=(",", ":"))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        return True
    except Exception:
        return False


def envelope(rec: dict, sym: str, day: str, line_idx: int, src_file: str) -> bytes:
    """Wrap the raw snapshot with provenance and a schema version.

    The version is stamped per object, never inferred from the key, because
    journal shapes have already changed several times this month and a
    warehouse that cannot tell v1 rows from v3 rows pools incompatible data.
    """
    env = {
        "schema_version": SCHEMA_VERSION,
        "datatype": DATATYPE,
        "symbol": sym,
        "dt": day,
        "src_host": HOST,
        "src_file": src_file,
        "src_line": line_idx,
        "pushed_at_utc": _now_utc(),
        "record": rec,
    }
    return json.dumps(env, separators=(",", ":"), default=str).encode("utf-8")


def put_and_verify(s3, bucket: str, key: str, body: bytes, counters=None) -> bool:
    """PUT then GET then byte-compare. Anything short of equality is False.

    On success the object is recorded against its dt=/sym= prefix counters,
    which is what `--verify` later reconciles against S3.
    """
    try:
        s3.put_object(Bucket=bucket, Key=key, Body=body)
    except Exception:
        return False
    try:
        got = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    except Exception:
        return False
    if got != body:
        return False
    if counters is not None:
        _confirm(key, body, counters)
    return True


def push_file(s3, bucket, path, day, sym, ledger, counters=None):
    """Push every unconfirmed line of one source file. Returns (pushed, failed)."""
    lines = read_lines(path)
    entry = ledger.get(path) or {}
    start = int(entry.get("n", 0) or 0)
    if start > len(lines):
        # File shrank — a rotation, a rebuild, or a different file at the same
        # path. Resuming from a stale offset would skip real data, so restart.
        start = 0

    pushed = 0
    failed = 0
    mtime_ms = 0
    try:
        mtime_ms = int(os.path.getmtime(path) * 1000)
    except Exception:
        pass

    for idx in range(start, len(lines)):
        raw = lines[idx]
        try:
            rec = json.loads(raw)
        except Exception:
            # Not valid JSON yet. Stop here rather than skipping: skipping
            # would advance the offset past a line that never got pushed.
            break
        sha = _sha256(_canon(rec))       # content only — never the envelope
        body = envelope(rec, sym, day, idx, os.path.basename(path))
        key = "{}/{}s/dt={}/sym={}/{}-{}.json".format(
            PREFIX, DATATYPE, day, sym, _epoch_ms(rec, mtime_ms), sha[:16]
        )
        if not put_and_verify(s3, bucket, key, body, counters):
            failed += 1
            break  # stop this file; next run retries from the same offset
        ledger[path] = {
            "n": idx + 1,
            "last_sha": sha,
            "last_key": key,
            "confirmed_utc": _now_utc(),
        }
        pushed += 1
    return pushed, failed


def discover(root: str = SRC_ROOT, suffix: str = ".jsonl.gz"):
    """(path, day, symbol) for every <date>/<SYM><suffix> file under root.

    All four date-partitioned trees on a box share this shape — chain
    snapshots, the signal journal, shadow and OHLC — so one walker serves them
    all rather than four near-identical copies drifting apart.
    """
    found = []
    try:
        for day in sorted(os.listdir(root)):
            day_dir = os.path.join(root, day)
            if not os.path.isdir(day_dir):
                continue
            for name in sorted(os.listdir(day_dir)):
                if not name.endswith(suffix):
                    continue
                found.append((os.path.join(day_dir, name), day, name[: -len(suffix)]))
    except Exception:
        pass
    return found


# ─────────────────────────────────────────────────────────────────────────────
# TRADES  (WH.2)
# ─────────────────────────────────────────────────────────────────────────────
TRADES_DB = os.environ.get(
    "OT_TRADES_DB", os.path.join(_HOME, "options-trader", "trades.db"))
TRADES_LEDGER = os.path.join(STATE_DIR, "trades_ledger.json")


def trade_envelope(rec: dict, sym: str, day: str) -> bytes:
    env = {
        "schema_version": SCHEMA_VERSION,
        "datatype": "trade",
        "symbol": sym,
        "dt": day,
        "trade_id": rec.get("trade_id"),
        "status": rec.get("status"),
        "src_host": HOST,
        "src_file": "trades.db",
        "pushed_at_utc": _now_utc(),
        "record": rec,
    }
    return json.dumps(env, separators=(",", ":"), default=str).encode("utf-8")


def push_trades(s3, bucket: str, db_path: str, ledger: dict, counters=None):
    """Push every trade row whose CONTENT has changed since last push.

    Trade rows MUTATE — written at entry, rewritten at exit. So this is not
    append-only like the chain archive, and a line-offset resume would be
    wrong. Instead the ledger holds one content hash per trade_id: an
    unchanged row costs a hash and nothing else, and each distinct STATE of a
    row lands as its own immutable object. That is change-data-capture for
    free, and it preserves more than `fleet_trades_<date>.json` does today —
    that file only ever sees the end state.

    SELECT * deliberately: the schema is 84 columns and has grown before
    (consolidate_trades.py's docstring still says ~55). Enumerating columns
    here would silently drop any future ALTER TABLE ADD COLUMN.
    """
    pushed = failed = 0
    try:
        con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True, timeout=5)
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT * FROM trades").fetchall()
        con.close()
    except Exception:
        return 0, 0          # no db, locked, or no table — nothing to push

    for row in rows:
        rec = dict(row)
        tid = str(rec.get("trade_id", ""))
        sha = _sha256(_canon(rec))
        if ledger.get(tid) == sha:
            continue                      # unchanged since last push
        sym = str(rec.get("symbol") or "UNKNOWN")
        ts = rec.get("entry_time") or ""
        day = _et_day(ts)
        try:
            ems = int(datetime.fromisoformat(str(ts)).timestamp() * 1000)
        except Exception:
            ems = 0
        key = "%s/trades/dt=%s/sym=%s/%d-%s.json" % (PREFIX, day, sym, ems, sha[:16])
        if not put_and_verify(s3, bucket, key, trade_envelope(rec, sym, day), counters):
            failed += 1
            break
        ledger[tid] = sha
        pushed += 1
    return pushed, failed


# ─────────────────────────────────────────────────────────────────────────────
# WH.3 — the remaining streams
# ─────────────────────────────────────────────────────────────────────────────
_OT = os.path.join(_HOME, "options-trader")
JOURNAL_ROOT = os.path.join(_OT, "data", "signal_journal")
SHADOW_ROOT  = os.path.join(_OT, "data", "shadow")
OHLC_ROOT    = os.path.join(_OT, "data", "OHLC")
LIQ_ROOT     = os.path.join(_OT, "data", "liquidity_ledger")
FEED_DB      = os.path.join(_OT, "data", "feed_store.db")
EOD_DIR      = os.path.join(_HOME, "eod")

LOCK_PATH     = os.path.join(STATE_DIR, "s3_push.lock")
LOCK_WAIT     = int(os.environ.get("OT_S3_LOCK_WAIT", "120"))
COUNTERS_PATH = os.path.join(STATE_DIR, "prefix_counters.json")
FLUSH_EVERY   = int(os.environ.get("OT_S3_FLUSH_EVERY", "200"))

# Every ledger this process has opened, so a mid-drain flush can persist all of
# them. Registered by load_ledger; flushed by _confirm.
_OPEN = {}
_SINCE_FLUSH = [0]

MISC_LEDGER   = os.path.join(STATE_DIR, "misc_ledger.json")
CANDLE_LEDGER = os.path.join(STATE_DIR, "candle_ledger.json")


def _eod_day(eod_dir):
    """Trading day for the EOD pair, taken from pnl_today.json's own date_et.

    The filenames carry no date and are overwritten each SESSION, so a box idle
    since July still holds July's file. Bucketing by today would file it under
    the wrong day; the file states its own.
    """
    try:
        with open(os.path.join(eod_dir, "pnl_today.json"), encoding="utf-8") as fh:
            d = json.load(fh).get("date_et")
        if d:
            return str(d)[:10]
    except Exception:
        pass
    return datetime.now(tz=timezone.utc).astimezone(
        ZoneInfo("America/New_York")).date().isoformat()


def own_symbol():
    """This box's instrument, read off disk.

    `data/OHLC/<date>/<SYM>.csv` is written for every box every session, so the
    basename IS the instrument. Preferred over OT_INSTRUMENT because this
    process does not inherit the bot unit's environment, and over an EC2 tag
    lookup because the box role deliberately carries no ec2:Describe.
    """
    try:
        days = sorted(d for d in os.listdir(OHLC_ROOT)
                      if os.path.isdir(os.path.join(OHLC_ROOT, d)))
        for day in reversed(days):
            for n in os.listdir(os.path.join(OHLC_ROOT, day)):
                if n.endswith(".csv"):
                    return n[:-4]
    except Exception:
        pass
    return os.environ.get("OT_INSTRUMENT", "")


def _wrap(datatype, rec, sym, day, extra=None):
    env = {
        "schema_version": SCHEMA_VERSION,
        "datatype": datatype,
        "symbol": sym,
        "dt": day,
        "src_host": HOST,
        "pushed_at_utc": _now_utc(),
        "record": rec,
    }
    if extra:
        env.update(extra)
    return json.dumps(env, separators=(",", ":"), default=str).encode("utf-8")


def push_table(s3, bucket, db_path, table, ts_col, datatype, ledger, me, counters=None):
    """Push every row of an append-only table in trades.db, one object per row.

    do not mutate, so there is no change-data-capture to reason about: a row's
    content hash is stable for its lifetime and the ledger simply records which
    hashes have landed.

    `SELECT *` for the same reason as trades — a future ALTER TABLE ADD COLUMN
    is carried automatically instead of silently dropped.
    """
    pushed = failed = 0
    try:
        con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True, timeout=5)
        con.row_factory = sqlite3.Row
        rows = [dict(r) for r in con.execute("SELECT * FROM %s" % table)]
        con.close()
    except Exception:
        return 0, 0          # table absent on an older schema — not an error

    seen = ledger.setdefault(table, {})
    for rec in rows:
        sha = _sha256(_canon(rec))
        rid = str(rec.get("id") or sha[:16])
        if seen.get(rid) == sha:
            continue
        ts = rec.get(ts_col) or ""
        day = _et_day(ts)
        try:
            ems = int(datetime.fromisoformat(str(ts)).timestamp() * 1000)
        except Exception:
            ems = 0
        sym = str(rec.get("symbol") or me or "UNKNOWN")
        key = "%s/%s/dt=%s/sym=%s/%d-%s.json" % (PREFIX, datatype, day, sym, ems, sha[:16])
        body = _wrap(datatype, rec, sym, day, {"row_id": rec.get("id")})
        if not put_and_verify(s3, bucket, key, body, counters):
            failed += 1
            break
        seen[rid] = sha
        pushed += 1
    return pushed, failed


def push_jsonl_tree(s3, bucket, root, datatype, ledger, counters=None):
    """signal_journal and shadow: <date>/<SYM>.jsonl, append-only, plain text.

    Same offset-resume contract as the chain archive. `ruleset` and `event` are
    lifted into the envelope: ruleset fingerprints the DEPLOYED LOGIC that
    produced the event, and pooling journal events across a deploy boundary
    without grouping by it blends incompatible decision-making.
    """
    pushed = failed = 0
    for path, day, sym in discover(root, ".jsonl"):
        entry = ledger.get(path) or {}
        start = int(entry.get("n", 0) or 0)
        try:
            with open(path, "rb") as fh:
                lines = fh.readlines()
        except Exception:
            continue
        if lines and not lines[-1].endswith(b"\n"):
            lines.pop()                      # writer mid-line
        if start > len(lines):
            start = 0
        for idx in range(start, len(lines)):
            try:
                rec = json.loads(lines[idx])
            except Exception:
                break
            sha = _sha256(_canon(rec))
            extra = {"src_line": idx}
            for f in ("ruleset", "event"):
                if isinstance(rec, dict) and rec.get(f) is not None:
                    extra[f] = rec[f]
            body = _wrap(datatype, rec, sym, day, extra)
            ems = _epoch_ms(rec, 0) if isinstance(rec, dict) else 0
            key = "%s/%s/dt=%s/sym=%s/%d-%s.json" % (PREFIX, datatype, day, sym, ems, sha[:16])
            if not put_and_verify(s3, bucket, key, body, counters):
                failed += 1
                break
            ledger[path] = {"n": idx + 1, "last_sha": sha, "confirmed_utc": _now_utc()}
            pushed += 1
    return pushed, failed


def push_whole_files(s3, bucket, items, datatype, ledger, counters=None):
    """One object per FILE, not per row. For OHLC day-CSVs and the EOD pair.

    A day-CSV holds ~390 candles; one object per candle would be 390x the
    request count for data that is only ever read as a day. The file is pushed
    as a unit and re-pushed only when its CONTENT hash changes, so a day still
    filling produces one object per distinct state and a finished day settles.
    """
    pushed = failed = 0
    for path, day, sym in items:
        try:
            with open(path, "rb") as fh:
                raw = fh.read()
        except Exception:
            continue
        if not raw:
            continue
        sha = _sha256(raw)
        if ledger.get(path) == sha:
            continue
        body = _wrap(datatype, raw.decode("utf-8", "replace"), sym, day,
                     {"src_file": os.path.basename(path), "content_sha256": sha})
        key = "%s/%s/dt=%s/sym=%s/%s-%s.json" % (PREFIX, datatype, day, sym,
                                                 os.path.basename(path), sha[:16])
        if not put_and_verify(s3, bucket, key, body, counters):
            failed += 1
            continue
        ledger[path] = sha
        pushed += 1
    return pushed, failed


def push_candles(s3, bucket, db_path, ledger, me, counters=None):
    """feed_store candles — ALL intervals, high-water mark per symbol+interval.

    The store is a rolling window (pruned), not an archive, so re-reading it
    every run would re-push the same bars. A high-water mark pushes only bars
    newer than the last confirmed one, batched into a single object per
    symbol+interval per run.

    VIX is logged by EVERY box. Operator's decision: SPX owns it, the other 28
    skip it — otherwise the warehouse takes 29 identical copies. Safe because
    SPX trades every day without exception.
    """
    pushed = failed = 0
    try:
        con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True, timeout=5)
        con.row_factory = sqlite3.Row
        pairs = [(r["symbol"], r["interval"]) for r in
                 con.execute("SELECT DISTINCT symbol, interval FROM candles")]
    except Exception:
        return 0, 0
    for sym, iv in pairs:
        if str(sym).upper() in ("VIX", "^VIX") and me != "SPX":
            continue                                  # SPX owns VIX
        lk = "%s|%s" % (sym, iv)
        hwm = int(ledger.get(lk, 0) or 0)
        try:
            rows = [dict(r) for r in con.execute(
                "SELECT * FROM candles WHERE symbol=? AND interval=? AND ts_epoch_ms>?"
                " ORDER BY ts_epoch_ms", (sym, iv, hwm))]
        except Exception:
            continue
        if not rows:
            continue
        top = int(rows[-1]["ts_epoch_ms"])
        day = datetime.fromtimestamp(top / 1000, tz=timezone.utc).astimezone(
            ZoneInfo("America/New_York")).date().isoformat()
        sha = _sha256(_canon(rows))
        body = _wrap("candles", rows, sym, day,
                     {"interval": iv, "n_bars": len(rows),
                      "ts_from": int(rows[0]["ts_epoch_ms"]), "ts_to": top})
        key = "%s/candles/dt=%s/sym=%s/interval=%s/%d-%s.json" % (
            PREFIX, day, sym, iv, top, sha[:16])
        if put_and_verify(s3, bucket, key, body, counters):
            ledger[lk] = top
            pushed += 1
        else:
            failed += 1
    con.close()
    return pushed, failed




SERIES_TABLES = ("greeks_series", "quote_series", "prints", "last_trade",
                 "session_summary", "theo_series", "underlying_series")
SERIES_BATCH_ROWS = int(os.environ.get("OT_S3_SERIES_BATCH", "50000"))


def push_series(s3, bucket, db_path, ledger, me, counters=None):
    """The seven manifold series tables — batched, high-water per table.

    Same contract as push_candles: rows are append-only and keyed on
    ts_epoch, so a per-table high-water mark pushes only what is new, as ONE
    object per table per run (capped at SERIES_BATCH_ROWS; a backlog drains
    over successive runs, tail-safe like every other stage). Key carries the
    batch's top ts + content hash, so a retry overwrites the same object.

    ⚠️ THE LEDGER KEY IS NAMESPACED `series|<table>` — the candle ledger holds
    `SYM|interval` in the same file, and two shapes in one dict is the r82
    class. The namespace makes a collision impossible rather than unlikely.
    """
    pushed = failed = 0
    try:
        con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True, timeout=5)
        con.row_factory = sqlite3.Row
    except Exception:
        return 0, 0
    day = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    for table in SERIES_TABLES:
        lk = "series|%s" % table
        hwm = float(ledger.get(lk, 0) or 0)
        try:
            rows = [dict(r) for r in con.execute(
                "SELECT * FROM %s WHERE ts_epoch > ? ORDER BY ts_epoch"
                " LIMIT ?" % table, (hwm, SERIES_BATCH_ROWS))]
        except Exception:
            continue                     # table absent on an older schema
        if not rows:
            continue
        top = float(rows[-1]["ts_epoch"])
        sha = _sha256(_canon(rows))
        body = _wrap(table, rows, me or "UNKNOWN", day,
                     {"n_rows": len(rows), "ts_from": float(rows[0]["ts_epoch"]),
                      "ts_to": top})
        key = "%s/%s/dt=%s/sym=%s/%d-%s.json" % (
            PREFIX, table, day, me or "UNKNOWN", int(top * 1000), sha[:16])
        if put_and_verify(s3, bucket, key, body, counters):
            ledger[lk] = top
            pushed += 1
        else:
            failed += 1
    con.close()
    return pushed, failed


def _push_chain_tree(s3, ledger, counters, files):
    """Chain snapshots across every day-file, as one stage."""
    pushed = failed = 0
    for path, day, sym in files:
        a, b = push_file(s3, BUCKET, path, day, sym, ledger, counters)
        pushed += a
        failed += b
    return pushed, failed


def reconcile(s3, bucket: str, counters: dict):
    """Reset every prefix counter to the live S3 truth. Returns {prefix: (was, now)}.

    ⚠️ EXPLICIT, NEVER AUTOMATIC — and that is a deliberate refusal. Self-healing
    the counter on every verify would ALSO silently erase a genuine loss: if S3
    really dropped an object, reconciling would quietly agree with the smaller
    number and the alarm we built this to raise would never fire again.
    **A verification that repairs itself is not a verification.**

    So this runs only on `--reconcile`, and only makes sense once a human has
    established that the objects are actually present — which they were on
    2026-08-18: LIST said 1560, the bucket held 1560, the counter said 1561.
    """
    fixed = {}
    for prefix in sorted(counters.keys()):
        n = b = 0
        try:
            pg = s3.get_paginator("list_objects_v2")
            for page in pg.paginate(Bucket=bucket, Prefix=prefix):
                for o in page.get("Contents", []) or []:
                    n += 1
                    b += int(o.get("Size", 0) or 0)
        except Exception:                                      # noqa: BLE001
            continue
        was = int((counters[prefix] or {}).get("n", 0))
        if was != n:
            fixed[prefix] = (was, n)
        counters[prefix] = {"n": n, "bytes": b}
    return fixed


def verify(s3, bucket: str, counters: dict):
    """Reconcile this box's confirmations against what S3 actually holds.

    Per dt=/sym= prefix, on COUNT and BYTES. Both come back from
    list_objects_v2 at no extra cost, so this is a handful of LIST calls
    rather than a HEAD per object — fast enough to gate a wake/verify/stop
    cycle on.

    Deliberately NOT a content hash: every object was already read back and
    byte-compared at PUT time, so content was verified against the source when
    it landed. The failure still live afterwards is "it never arrived", which
    counts catch, and "it arrived short", which bytes catch.
    """
    short = []
    tot_local = tot_s3 = 0
    for prefix, exp in sorted(counters.items()):
        n = b = 0
        try:
            pg = s3.get_paginator("list_objects_v2")
            for page in pg.paginate(Bucket=bucket, Prefix=prefix):
                for o in page.get("Contents", []) or []:
                    n += 1
                    b += int(o.get("Size", 0) or 0)
        except Exception:
            short.append((prefix, exp["n"], -1))
            continue
        tot_local += int(exp["n"])
        tot_s3 += n
        if n < int(exp["n"]) or b < int(exp["bytes"]):
            short.append((prefix, exp["n"], n))
    return short, tot_local, tot_s3


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    report = "--report" in argv
    do_verify = "--verify" in argv
    do_reconcile = "--reconcile" in argv

    try:
        if not ENABLED:
            if report:
                print("s3_push: DISABLED via OT_S3_PUSH=0")
            return 0

        files = discover()
        if (not files and not report and not do_verify
                and not os.path.exists(TRADES_DB)
                and not os.path.isdir(OHLC_ROOT)):
            return 0  # idle box with nothing at all. Say nothing.

        # ── ONE PUSHER AT A TIME ────────────────────────────────────────────
        # A normal run that loses the race exits silently: the run already in
        # flight is doing exactly this work. --verify waits, because the EOD
        # conductor is blocking on its answer, and falls back to verify-only.
        lock = acquire_lock(LOCK_WAIT if do_verify else 0)
        drained = lock is not None
        if lock is None and not do_verify:
            return 0

        import boto3  # imported late so a missing SDK cannot break --report

        s3 = boto3.client("s3", region_name=REGION)
        counters = load_ledger(COUNTERS_PATH)
        ledger = load_ledger()
        t_ledger = load_ledger(TRADES_LEDGER)
        misc = load_ledger(MISC_LEDGER)
        c_ledger = load_ledger(CANDLE_LEDGER)
        me = own_symbol()
        total_pushed = 0
        total_failed = 0

        eod_items = []
        try:
            for n in sorted(os.listdir(EOD_DIR)):
                if n.endswith(".json"):
                    eod_items.append((os.path.join(EOD_DIR, n), _eod_day(EOD_DIR), me))
        except Exception:
            pass

        # ── ORDER MATTERS, AND THIS IS THE ORDER ────────────────────────────
        # Smallest and most perishable first; bulk last. A run that runs out of
        # time then loses the TAIL, not the head. Before v1.4 the journal sat
        # third and starved everything behind it for a full evening.
        #   trades  — feeds reports 40/41, small, mutates
        #   eod     — one day only, overwritten per session, silent loss
        #   orb     — ephemeral, rewritten every tick, no log anywhere
        #   ohlc    — one object per day-file, bounded
        #   candles — high-water mark, small batches
        #   chains  — large, but already drained and unreconstructable
        #   shadow  — moderate
        #   journal — largest by far, and the most tolerant of lag
        stages = [
            ("trades", lambda: push_trades(s3, BUCKET, TRADES_DB, t_ledger, counters)),
            ("circuit_breaker", lambda: push_table(
                s3, BUCKET, TRADES_DB, "circuit_breaker_events", "event_time",
                "circuit_breaker", t_ledger, me, counters)),
            ("eod", lambda: push_whole_files(s3, BUCKET, eod_items, "eod", misc, counters)),
            ("ohlc", lambda: push_whole_files(
                s3, BUCKET, discover(OHLC_ROOT, ".csv"), "ohlc", misc, counters)),
            ("candles", lambda: push_candles(s3, BUCKET, FEED_DB, c_ledger, me, counters)),
            # v4.2 — after candles (same store, same perishability), before the
            # bulk streams so a timeout cannot starve the only copy of the
            # greeks/quote tape. Batched: one object per table per run.
            ("series", lambda: push_series(s3, BUCKET, FEED_DB, c_ledger, me, counters)),
            ("liquidity_ledger", lambda: push_whole_files(
                s3, BUCKET, discover(LIQ_ROOT, ".json"), "liquidity_ledger",
                misc, counters)),
            ("chain_snapshots", lambda: _push_chain_tree(s3, ledger, counters, files)),
            ("shadow", lambda: push_jsonl_tree(
                s3, BUCKET, SHADOW_ROOT, "shadow", misc, counters)),
            ("signal_journal", lambda: push_jsonl_tree(
                s3, BUCKET, JOURNAL_ROOT, "signal_journal", misc, counters)),
        ]

        for name, fn in stages:
            if not drained:
                break                  # verify-only: another pusher holds the lock
            try:
                p_, f_ = fn()
            except Exception:
                p_, f_ = 0, 1          # rule 1: a stream may fail, never raise
            total_pushed += p_
            total_failed += f_
            if p_ or f_:
                flush_all()            # a stage's progress survives the next one

        flush_all()      # always: a run that pushed nothing may still have
                         # nothing to save, and one that did must not lose it

        if do_verify:
            # ONE machine-readable line. The EOD conductor parses this to decide
            # whether a box may be stopped, so it must be stable and exit 0.
            if not drained:
                # Another pusher is mid-drain and owns the ledgers; re-read from
                # disk so we verify against ITS progress, not our stale copy.
                counters = load_ledger(COUNTERS_PATH)
            short, loc, remote = verify(s3, BUCKET, counters)
            print("DRAIN host={} sym={} drained={} pushed={} failed={} "
                  "prefixes={} local={} s3={} short={} {}".format(
                      HOST, me or "?", "yes" if drained else "no",
                      total_pushed, total_failed, len(counters),
                      loc, remote, len(short),
                      "OK" if (not short and not total_failed) else "SHORT"))
            for pfx, exp, got in short[:5]:
                print("  SHORT {} expected>={} got={}".format(pfx, exp, got))
            # ⚠️ WH.6 — SAY WHICH KIND OF SHORTFALL THIS LOOKS LIKE. A counter
            # that over-counted duplicate PUTs is short by a SMALL, CONSISTENT
            # amount on many prefixes; genuine loss scatters. On 2026-08-18 ten
            # prefixes were each short by exactly ONE and the bucket held every
            # object — two days of "data stranded" alarms for a fencepost.
            # The heuristic does not decide anything; it tells the reader which
            # question to ask first.
            _gaps = [e - g for _p, e, g in short if g >= 0]
            if _gaps and max(_gaps) <= 2 and len(short) >= 3:
                print("  ⚠️ SMALL, CONSISTENT SHORTFALL ON {} PREFIXES (max {}). "
                      "That is the signature of COUNTER DRIFT, not data loss — "
                      "duplicate PUTs inflate the ledger permanently. VERIFY "
                      "with `aws s3 ls <prefix> --recursive | wc -l` and, if the "
                      "objects are present, run `--reconcile` once."
                      .format(len(short), max(_gaps)))
            elif _gaps:
                print("  ⚠️ SHORTFALL VARIES (max {}) — that is NOT the counter-"
                      "drift signature. Treat as possible real loss."
                      .format(max(_gaps)))

        if do_reconcile:
            _fixed = reconcile(s3, BUCKET, counters)
            # 🔴 THIS WROTE THE PREFIX COUNTERS OVER `chain_ledger.json` — the
            # FILE-OFFSET ledger — instead of `prefix_counters.json`. Found
            # 2026-08-23 after three reconcile/verify cycles made the numbers
            # WORSE each time (222 -> 300 while S3 held 74).
            # ⚠️ THE MECHANISM: chain_ledger maps SOURCE PATH -> lines already
            # pushed. Overwriting it with {prefix: {n, bytes}} means the next
            # `push_file` looks up its path, FINDS NOTHING, starts at line 0 and
            # RE-PUSHES THE WHOLE FILE. So every reconcile destroyed the record
            # of what had been sent, and the next verify re-sent everything —
            # which is what inflated the counter reconcile had just fixed.
            # ⚠️ NOTHING WAS LOST: keys are content-hashed, so the re-pushes
            # overwrote identical objects. The cost was PUTs and a counter that
            # climbed every cycle.
            save_ledger(counters, COUNTERS_PATH)
            print("reconcile: {} prefix counter(s) reset to the S3 truth"
                  .format(len(_fixed)))
            for _p2, (_was, _now) in sorted(_fixed.items())[:10]:
                print("  {} {} -> {}".format(_p2, _was, _now))
            if len(_fixed) > 10:
                print("  ... and {} more".format(len(_fixed) - 10))
            return 0

        if total_pushed or total_failed or report:
            print(
                "s3_push host={} files={} pushed={} failed={} bucket={}".format(
                    HOST, len(files), total_pushed, total_failed, BUCKET
                )
            )
        return 0
    except Exception as exc:  # noqa: BLE001 — rule 1
        try:
            print("s3_push: run aborted, nothing confirmed: {}".format(exc))
        except Exception:
            pass
        return 0


if __name__ == "__main__":
    sys.exit(main())
