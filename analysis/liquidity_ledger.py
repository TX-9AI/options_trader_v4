"""
analysis/liquidity_ledger.py  v4.2
v4.2  2026-09-13  r379 — THE DELIVERED DEFENSE HISTORY IS READ, AND IT CAN ONLY
      CARRY DURABILITY. `load_history()` reads `data/level_history/<SYM>.json`,
      built on CONTROL from banked tape by `day_trader_pro/tools/
      build_level_history.py` and pushed to the box. Operator, 2026-09-12:
      *"I'm not saying the bots would 'pull' from s3. I'm saying we could
      construct their ledgers from that data."* — so no trading box ever reaches
      S3, and §30's *the bot owns its own level book* still holds.
      🔑 IT ANSWERS [[LVL.16]] AS WELL AS THE FIT. A level admitted at 14:00 is
      `partial` because the box holds ~60 1m bars and can never backfill its
      morning; only control has the tape. The history does not repair today's
      session counters — nothing can — but it means a late level still arrives
      with a defense record instead of nothing.
      🔴 DURABILITY ONLY, AND THE ARTIFACT IS INCAPABLE OF EXPRESSING AN EVENT.
      `_stamp_history` writes `prior_*` and nothing else; `last_result` and
      `last_touch` stay empty, and the file itself carries no such field. A hold
      from three days ago must never fire a trade today, and the guarantee is
      structural rather than a rule someone remembers.
      ⚠️ THE SCHEMA AND THE TOLERANCE ARE BOTH CHECKED. r378 changed what
      `touches` COUNTS — a bar under a half-plane, a visit under containment,
      16.5x apart on measured tape — so a file built for another schema is
      REFUSED and named, and so is one clustered at a different `touch_tol_pct`.
      ⚠️ MATCHED BY PRICE AND KIND, NEVER BY NAME: Monday's PDH is a different
      price from Friday's, and [[LVL.15]] found the names are not unique anyway.
Per-level touch / hold / breach accounting across the session.

v4.1  2026-09-12  r378 — THE READ SIDE GETS A READER, WHICH IS THE ONLY THING
      THIS FILE WAS MISSING. Since the port it has carried the comment
      *"read side (nothing gates on this in v1)"* while implementing the
      operator's own interaction rule — wick reaches = touch, close beyond =
      breach (acceptance), close back on the origin side = hold (rejection) —
      on every closed bar, persisted per box. LVL.11's one-sentence finding was
      that the MEMORY side records and the MEMORYLESS side trades; `liq_map` is
      rebuilt every tick and cannot answer "is this floor holding", so the
      answer existed and nothing asked for it.
      🔑 `interaction_at(price, kind)` is that ask. It returns the matched
      level's LATEST closed-bar verdict plus its running counters, so the sweep
      can be gated on the level's own definition of an interaction instead of on
      a retreat-magnitude band that never had definitional standing.
      ⚠️ IT RETURNS None RATHER THAN A DEFAULT when no level matches, and the
      caller's contract is that None means STARVED, not REFUSED. A level the
      ledger has not seeded yet (`main.py` defers seeding until the mapper
      produces named pools) is an ABSENT INPUT; answering "no interaction" would
      turn the first minutes of every session into silent refusals, which is the
      plausible-silence class in docs/PORT_STATE.md.
      🔴 AND THE COUNTING WAS WRONG, WHICH THE READER FOUND IMMEDIATELY.
      `reached` was a HALF-PLANE test — `low <= price + tol` for a low level — so
      every bar on the FAR SIDE of a level counted as a fresh touch and a fresh
      breach. AMZN 2026-09-09: PDL 254.75, session HIGH 254.62, price never
      reached it; the book recorded 389 TOUCHES and 389 BREACHES. Across 45
      banked books (3 sessions, 15 symbols, 386 level-rows) 67.9% of levels
      showed zero touches and 19.4% showed over 100, median 209 in a 390-bar
      session — bimodal, because it measured which SIDE of a line price sat on.
      🔑 CONTACT IS NOW CONTAINMENT AND A TEST IS NOW A VISIT. Operator,
      2026-09-12: *"Every 'touch' and retreat is a successful defense"* and
      *"Leans on isn't the same as testing it."* So the range must reach the
      level, a visit opens once and counts ONE touch however long it lasts, and
      the bar that ENDS the visit decides hold or breach by which side its close
      departed on. `contact_bars` keeps the duration separately so the two
      questions stop sharing one number.
      ⚠️ SCHEMA_VERSION 1 -> 2. The same field answers a different question now,
      so a v1 book must never hydrate into a v2 run; the mismatch guard already
      refuses it, on LIQ.7's precedent for a changed `touch_tol_pct`.
      ⚠️ CONSEQUENCE FOR THE HISTORY: the 20 banked sessions are NOT comparable
      to the new counters and must be REPLAYED from the 1m tape rather than
      imported. That is the operator's seeding plan and this is why it has to be
      a replay.
v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

analysis/liquidity_ledger.py — options_trader_v3 — v1.1 — AUDIT A2: THE RECORD
        NOW SURVIVES THE RESTART IT EXISTS TO OUTLIVE, AND NO CLOSED BAR IS
        SKIPPED.
audit #2 fixes:
        (A2.3) `reset_for_session` cleared with no load-back — `write()` was
        a writer with NO READER, so every bake wiped the day's touch/hold/
        breach counts and the next write overwrote the good file with zeros
        (reproduced: (1,1) -> (0,0) across a restart). Reset now HYDRATES
        from the same-date JSON first, then merges the caller's seeds
        through add_level (which dedupes). Guards: schema_version and
        touch_tol_pct must match the running process — counts taken under a
        different zone mean something else (LIQ.7) and start clean, loudly.
        (A2.4) the wiring fed only `iloc[-2]` behind a single-stamp guard;
        any tick slower than ~75s silently DROPPED closed bars — and slow
        ticks correlate with busy tape, so the undercount landed exactly on
        the bars most likely to test levels (reproduced). Bar selection now
        lives HERE: `feed_frame(df_1m)` walks every closed bar newer than
        `last_bar_ts` (persisted, so the A2.3 hydrate also recovers the
        bake gap from the 60-bar 1m frame), skips the forming last row,
        and admits only this session's RTH bars (>= 09:30 ET, session
        date) — the session record stays a session record.
THE MISSING OBJECT. `LiquidityMapper.analyze()` opens with
        `lmap = LiquidityMap()` and re-derives every pool from the candle window
        on EVERY CALL. Nothing survives a tick, so:
          · `touch_count` is NOT a running count — it is `len(cluster)`, i.e.
            how many bars in the lookback happened to sit at that level when the
            map was last rebuilt. A floor price hammers into five times today
            does not accumulate.
          · `swept` / `rejection_confirmed` are per-build snapshots. Same defect
            class LIQ.3 already fixed one level down, where `closes_beyond` was
            a birth-time snapshot that had to become a per-tick question.
          · a clean SINGLE-touch low that price respects three times never
            becomes a pool at all — `_find_pools` requires >=2 equal bars within
            EQUAL_LEVEL_PCT.
        So there was no object that could answer "is this floor holding?", and
        nothing was archived: the input to every named-level decision existed
        only in RAM. Same class as the chain archive before 2026-07-23.
        OPERATOR'S SPEC, 2026-08-13, verbatim on the part that matters:
        *"the wick counts as a touch, but only a close counts as acceptance or
        rejection."* Hence THREE counters per level, never one — `touches`
        (wick), `holds` (closed back on the origin side), `breaches` (closed
        beyond). A single number cannot say whether a level is being defended
        or given up, which is the entire question.
        *"It should live on the standalone bot boxes."* Written per-box under
        `data/liquidity_ledger/<date>/<SYMBOL>.json`, next to the chain archive
        and by the same convention. The bot owns its own level book; control is
        a consumer, never the source.
        RESET AT RTH OPEN, seeded with PDH/PDL and the prior session's extremes,
        carrying at least MIN_LEVELS_PER_SIDE highs and lows.
⚠️ FIRE-AND-FORGET. Every public entry point swallows every exception. A ledger
   failure must never reach the trading loop — `chain_snapshot.py` is the model
   and the reason: this is telemetry, and telemetry that can halt trading is a
   liability, not an asset.
⚠️ v1.0 WRITES AND DOES NOT GATE. Nothing reads this to make a decision yet.
   Prove the levels are the ones a human would have drawn before wiring them to
   anything that fires.
STATE, not an event log. The file is the CURRENT book, rewritten atomically on
change. Timing of individual touches is deliberately out of scope for v1 — the
counts are what the floor thesis needs, and an append log can be added later
without changing this schema.
"""

import json
import os
import tempfile
from typing import Dict, List, Optional

import logging

logger = logging.getLogger(__name__)

# 🔴 r378 — BUMPED TO 2 BECAUSE A COUNT MEANS SOMETHING ELSE NOW. `touches` was
# a BAR count under a half-plane contact test; it is a VISIT count under a
# containment test. The same number in the same field answers a different
# question, so a v1 book must not be hydrated into a v2 run — `_hydrate_same_date`
# already refuses on a schema mismatch, and LIQ.7 set the precedent by refusing a
# book taken under a different `touch_tol_pct` for exactly this reason.
SCHEMA_VERSION = 2

# Self-locate: <repo>/analysis/liquidity_ledger.py -> <repo>/data/liquidity_ledger/
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# ⚠️ OVERRIDABLE, AND IT HAS TO BE. The A2.3 hydrate makes `reset_for_session`
# READ THIS PATH BACK, so anything that writes here is state the next run
# inherits. Under test that meant counts ACCUMULATED across invocations
# (`holds == 3` from one bar), and worse: `data/liquidity_ledger/` was not in
# .gitignore, so the deploy line's `git add -A` would have committed live fleet
# data into the repo - the MANIFEST.txt / trades.db precedent exactly.
# Tests point `OT_LEDGER_ROOT` at a temp dir; production is unchanged.
_OUT_ROOT = os.environ.get(
    "OT_LEDGER_ROOT", os.path.join(_REPO_ROOT, "data", "liquidity_ledger"))
# 🔑 r379 / LVL.17 — WHERE THE DELIVERED DEFENSE HISTORY LIVES. Built on CONTROL
# from banked tape and pushed to the box; the bot READS it and never writes it,
# and never reaches S3 itself. Operator: *"I'm not saying the bots would 'pull'
# from s3. I'm saying we could construct their ledgers from that data."*
# ⚠️ UNDER `data/`, LIKE THE BOOK BESIDE IT, so a bake never overwrites it and it
# is not version-controlled runtime state pretending to be source.
_HISTORY_ROOT = os.environ.get(
    "OT_LEVEL_HISTORY_ROOT", os.path.join(_REPO_ROOT, "data", "level_history"))
_HISTORY_CACHE: Dict[str, list] = {}

# Operator: "capture at least 3 previous highs & lows".
MIN_LEVELS_PER_SIDE = 3
# A level is "touched" when a bar's wick reaches within this fraction of it.
# Not zero: an exact float equality on a price never fires.
# ── LIQ.7 (2026-08-15) — ONE DEFINITION OF A ZONE ────────────────────────────
# Was 0.0002 (2bp). Raised to 0.002 (20bp) to MATCH `within_pct(..., 0.002)`,
# the tolerance `liquidity_mapper._add_named_pool` already uses to decide two
# prices are the same level. Operator: *"Reach within a small margin of error is
# good enough. A level is a ZONE, not a fixed number."*
# ⚠️ THE OLD VALUE UNDERCOUNTED EXACTLY WHAT THE SIZING RULE REWARDS. On a $580
# underlying 2bp is 12 CENTS — a clean approach that reversed just short of the
# level did not register as a test at all, so the most-defended levels looked
# untested. 20bp is $1.16 there, which is the zone the rest of the system
# already treats as one level.
# ⚠️ AND IT CHANGES WHAT EVERY LEDGER NUMBER MEANS. Counts before and after this
# are not comparable; the ledger has collected nothing yet, so there is no
# history to invalidate.
TOUCH_TOL_PCT = float(os.environ.get("OT_LEDGER_TOUCH_TOL", "0.002"))


def load_history(symbol: str) -> list:
    """The delivered defense history for `symbol`, as a list of price zones.

    Returns [] when there is no file, and [] IS "no history" — which the caller
    must not confuse with "never defended". `Level.defense_rate()` returns None
    on zero prior tests for exactly that reason.

    🔴 THE SCHEMA IS CHECKED, NOT TRUSTED. A history built against a different
    `SCHEMA_VERSION` counted something else — r378 changed `touches` from a BAR
    count under a half-plane test to a VISIT count under containment, a 16.5x
    difference on measured tape — so a mismatched file is REFUSED and named, on
    the same reasoning as the book hydrate's own guard and LIQ.7's before it.
    ⚠️ AND SO IS THE TOLERANCE, because a zone clustered at a different
    `touch_tol_pct` is not the same zone.
    ⚠️ CACHED PER PROCESS. The file changes weekly and out of hours; re-reading
    it every tick would be a syscall per level per tick for a constant.
    """
    sym = (symbol or "").upper()
    if sym in _HISTORY_CACHE:
        return _HISTORY_CACHE[sym]
    zones: list = []
    path = os.path.join(_HISTORY_ROOT, f"{sym}.json")
    try:
        if os.path.exists(path):
            with open(path) as f:
                payload = json.load(f)
            if int(payload.get("ledger_schema", -1)) != SCHEMA_VERSION:
                logger.warning("[history] %s: built for ledger schema %s but "
                               "this build is %s — the counts are not "
                               "comparable, IGNORING the file",
                               path, payload.get("ledger_schema"), SCHEMA_VERSION)
            elif float(payload.get("touch_tol_pct", -1)) != TOUCH_TOL_PCT:
                logger.warning("[history] %s: clustered at touch_tol %s but this "
                               "build runs %s — the zones are not the same "
                               "zones, IGNORING the file", path,
                               payload.get("touch_tol_pct"), TOUCH_TOL_PCT)
            else:
                zones = [z for z in payload.get("zones", [])
                         if z.get("kind") in ("high", "low") and z.get("price")]
                logger.info("[history] %s: %d zone(s) over %s session(s) "
                            "%s..%s", sym, len(zones),
                            (payload.get("window") or {}).get("sessions"),
                            (payload.get("window") or {}).get("start"),
                            (payload.get("window") or {}).get("end"))
        else:
            logger.debug("[history] no file at %s — no prior defense record", path)
    except Exception as e:                                     # noqa: BLE001
        # ⚠️ NEVER FATAL. An unreadable history must cost the session its
        # CONTEXT, never its trading — and it is logged loudly rather than
        # returning [] quietly, because [] is also the legitimate answer.
        logger.warning("[history] %s unreadable (%s) — continuing with no "
                       "prior record", path, e)
    _HISTORY_CACHE[sym] = zones
    return zones


class Level:
    """One horizontal level and its running contact history.

    THREE COUNTERS, per the operator's rule. `touches` is wick contact and says
    nothing about who won; `holds` and `breaches` are decided by the CLOSE and
    are the only two that carry information about whether the level is being
    defended.
    """

    __slots__ = ("price", "kind", "name", "is_named", "touches", "holds",
                 "breaches", "first_seen", "last_touch", "last_result",
                 # r378 — A VISIT IS ONE TEST, HOWEVER MANY BARS IT LASTS.
                 # Operator, 2026-09-12: *"Leans on isn't the same as testing
                 # it."* `contact_bars` keeps the DURATION so the distinction
                 # stays visible instead of being chosen silently; the open
                 # visit's state is carried because a test spans bars and the
                 # outcome is not known until price leaves.
                 "contact_bars", "visit_open", "visit_bars", "visit_started",
                 "last_visit_started", "last_visit_bars",
                 # 🔴 r378 — HISTORY SEEDS DURABILITY AND NEVER SEEDS AN EVENT.
                 # `prior_*` is the defense record from PREVIOUS sessions, built
                 # from banked tape by a control-side tool and delivered. The
                 # session counters above always start at zero and `last_result`
                 # always starts EMPTY, because a hold from three days ago is not
                 # an interaction that happened today — seeding it would fire a
                 # trade on a stale event, which is this project's oldest defect
                 # shape. One writer per field: the bot never touches `prior_*`
                 # and the seed never touches the session's own.
                 "prior_touches", "prior_holds", "prior_breaches",
                 "prior_sessions",
                 # r378 — TODAY'S OBSERVATION STARTED LATE. `touches == 0` must
                 # not conflate "never tested" with "we were not watching": a
                 # level admitted mid-session (every bake re-seeds) can never
                 # backfill its morning from the box's own 60-bar frame.
                 "partial")

    def __init__(self, price: float, kind: str, name: str = "",
                 is_named: bool = False, first_seen: str = ""):
        self.price = round(float(price), 4)
        self.kind = kind                      # "high" | "low"
        self.name = name                      # PDH / PDL / PRIOR_HIGH_2 / ...
        self.is_named = bool(is_named)
        self.touches = 0
        self.holds = 0
        self.breaches = 0
        self.first_seen = first_seen
        self.last_touch = ""                  # stamp of the bar that RESOLVED
        self.last_result = ""                 # "hold" | "breach" | ""
        self.contact_bars = 0                 # bars in contact, ALL visits
        self.visit_open = False               # a test is in progress
        self.visit_bars = 0                   # bars of the OPEN visit
        self.visit_started = ""
        self.last_visit_started = ""
        self.last_visit_bars = 0
        self.prior_touches = 0
        self.prior_holds = 0
        self.prior_breaches = 0
        self.prior_sessions = 0
        self.partial = False

    def as_dict(self) -> dict:
        return {
            "price": self.price, "kind": self.kind, "name": self.name,
            "is_named": self.is_named, "touches": self.touches,
            "holds": self.holds, "breaches": self.breaches,
            "first_seen": self.first_seen, "last_touch": self.last_touch,
            "last_result": self.last_result,
            "contact_bars": self.contact_bars,
            "visit_open": self.visit_open, "visit_bars": self.visit_bars,
            "visit_started": self.visit_started,
            "last_visit_started": self.last_visit_started,
            "last_visit_bars": self.last_visit_bars,
            "prior_touches": self.prior_touches,
            "prior_holds": self.prior_holds,
            "prior_breaches": self.prior_breaches,
            "prior_sessions": self.prior_sessions,
            "partial": self.partial,
        }

    def defense_rate(self):
        """Prior holds / prior tests, or None when there is no history.

        None IS THE ANSWER when nothing is known, and the caller must not read it
        as 0.0 — a level with no history is not a level that has never held. That
        distinction is the whole reason `prior_sessions` is carried.
        """
        t = int(self.prior_touches or 0)
        if t <= 0:
            return None
        return float(self.prior_holds or 0) / float(t)


class LiquidityLedger:
    """Session-scoped, persistent level book for ONE symbol on ONE box."""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.date = ""
        self.levels: List[Level] = []
        self.last_bar_ts = ""     # A2.4 — newest CLOSED bar fed, ISO w/ offset.
        self._dirty = False

    # ── session lifecycle ────────────────────────────────────────────────────

    def reset_for_session(self, date: str, seeds=None) -> None:
        """Clear and reseed. Called at RTH open.

        `seeds` is an iterable of (price, kind, name, is_named). The CALLER
        supplies them because the ledger must not own a second definition of
        what a prior high is — `LiquidityMapper` already owns that, and a
        competing derivation here is exactly the second-lineage failure
        WORKING_AGREEMENT 7 forbids.
        """
        try:
            self.date = date
            self.levels = []
            self.last_bar_ts = ""
            # A2.3 — a restart happens on every bake, and this reset used to be
            # the wipe: write() had no reader, so the "running record" lost its
            # morning on every mid-session restart and then OVERWROTE the good
            # file with zeros. Same-date state is hydrated back first; the
            # caller's seeds then merge through add_level (which dedupes), so
            # new mapper levels still join.
            self._hydrate_same_date(date)
            for s in (seeds or []):
                self.add_level(*s, first_seen=date)
            self._dirty = True
        except Exception as e:                                 # noqa: BLE001
            logger.debug("ledger reset skipped: %s", e)

    def _hydrate_same_date(self, date: str) -> None:
        """Load this symbol's same-date book back from disk, if one exists."""
        path = os.path.join(_OUT_ROOT, date, f"{self.symbol}.json")
        try:
            if not os.path.exists(path):
                return
            with open(path) as f:
                payload = json.load(f)
            if payload.get("schema_version") != SCHEMA_VERSION:
                logger.warning("[ledger] %s: schema %s != %s — starting clean",
                               path, payload.get("schema_version"),
                               SCHEMA_VERSION)
                return
            # LIQ.7 — counts taken under a different zone MEAN something else.
            if float(payload.get("touch_tol_pct", -1)) != TOUCH_TOL_PCT:
                logger.warning("[ledger] %s: touch_tol %s != running %s — "
                               "counts are not comparable, starting clean",
                               path, payload.get("touch_tol_pct"),
                               TOUCH_TOL_PCT)
                return
            for d in payload.get("levels", []):
                lv = Level(d["price"], d["kind"], d.get("name", ""),
                           d.get("is_named", False), d.get("first_seen", ""))
                lv.touches, lv.holds = int(d.get("touches", 0)), int(d.get("holds", 0))
                lv.breaches = int(d.get("breaches", 0))
                lv.last_touch = d.get("last_touch", "")
                lv.last_result = d.get("last_result", "")
                # r378 — an OPEN visit survives the restart too, or a bake in the
                # middle of a test would resolve it twice: once by the bar that
                # ends it before the restart (lost), once by the next contact
                # after it (counted as a new test).
                lv.contact_bars = int(d.get("contact_bars", 0))
                lv.visit_open = bool(d.get("visit_open", False))
                lv.visit_bars = int(d.get("visit_bars", 0))
                lv.visit_started = d.get("visit_started", "")
                lv.last_visit_started = d.get("last_visit_started", "")
                lv.last_visit_bars = int(d.get("last_visit_bars", 0))
                lv.prior_touches = int(d.get("prior_touches", 0))
                lv.prior_holds = int(d.get("prior_holds", 0))
                lv.prior_breaches = int(d.get("prior_breaches", 0))
                lv.prior_sessions = int(d.get("prior_sessions", 0))
                lv.partial = bool(d.get("partial", False))
                self.levels.append(lv)
            self.last_bar_ts = str(payload.get("last_bar_ts", "") or "")
            logger.info("[ledger] hydrated %d level(s) for %s from disk "
                        "(restart survival, last bar %s)",
                        len(self.levels), date, self.last_bar_ts or "n/a")
        except Exception as e:                                 # noqa: BLE001
            logger.warning("[ledger] hydrate failed (%s) — starting clean", e)
            self.levels = []
            self.last_bar_ts = ""

    def add_level(self, price: float, kind: str, name: str = "",
                  is_named: bool = False, first_seen: str = "") -> None:
        """Admit a level. Idempotent within `TOUCH_TOL_PCT` for the same kind.

        🔴 r378 — A LEVEL THAT JOINS LATE SAYS SO. If bars have already been
        consumed (`last_bar_ts` is set) the new level's session counters can
        never include them: the box holds ~60 1m bars and `feed_frame` refuses
        anything at or before `last_bar_ts`, by design. So it is marked
        `partial`, and a reader must treat `touches == 0` on a partial level as
        NOT OBSERVED rather than NEVER TESTED.
        📊 THIS IS NOT HYPOTHETICAL. `reset_for_session` hydrates then merges the
        caller's seeds, and every BAKE restarts the process — so any level the
        mapper had not yet named at the first seeding joined with zero counts and
        an afternoon `last_bar_ts`. Measured on 2026-09-09, 147 level-rows: 45
        were DEFLATED against a replay of the same tape, `AMD Asia High (R1)`
        banked 0 against 24 real tests and 216 bars of contact.
        ⚠️ THE REAL REPAIR IS THE SEED FILE, NOT THIS FLAG. Only control holds
        the full tape; this flag is how the box states what it could not know.
        """
        try:
            if not price or price <= 0 or kind not in ("high", "low"):
                return
            for lv in self.levels:
                if lv.kind == kind and abs(lv.price - price) <= \
                        abs(price) * TOUCH_TOL_PCT:
                    return                                     # already held
            lv = Level(price, kind, name, is_named, first_seen or self.date)
            self._stamp_history(lv)
            if self.last_bar_ts:
                lv.partial = True
                logger.info("[ledger] %s %s %.2f joined AFTER bar %s — marked "
                            "PARTIAL: its session counters cannot include the "
                            "bars already consumed", self.symbol, name or kind,
                            float(price), self.last_bar_ts)
            self.levels.append(lv)
            self._dirty = True
        except Exception as e:                                 # noqa: BLE001
            logger.debug("ledger add_level skipped: %s", e)

    # ── the update, and the whole point of the module ────────────────────────

    def feed_frame(self, df_1m) -> int:
        """Feed every CLOSED session bar newer than `last_bar_ts`. Returns count.

        A2.4 — the old wiring fed only `iloc[-2]` behind a one-stamp guard: it
        prevented refeeding ONE bar but could not see a GAP, so any tick slower
        than ~75s silently dropped closed bars — on exactly the busy tape most
        likely to be testing levels. This walks the whole frame instead:
          · the LAST row is the forming bar and is never fed;
          · a bar is fed once — `last_bar_ts` (persisted, so a restart plus the
            A2.3 hydrate recovers the bake gap from the 60-bar frame);
          · only THIS session's RTH bars (index date == self.date, >= 09:30 ET)
            — the session record stays a session record; the frame also carries
            yesterday/pre-market rows and those are not the session.
        Timestamps compare as strings: same session, same UTC offset, one
        format — and the DST changeover never lands inside RTH.
        """
        try:
            if df_1m is None or getattr(df_1m, "empty", True) or len(df_1m) < 2:
                return 0
            fed = 0
            for ts, row in df_1m.iloc[:-1].iterrows():         # [-1] is FORMING
                if str(ts.date()) != self.date:
                    continue
                if (ts.hour, ts.minute) < (9, 30):             # index is ET
                    continue
                stamp = str(ts)
                if self.last_bar_ts and stamp <= self.last_bar_ts:
                    continue
                self.on_closed_bar(float(row["high"]), float(row["low"]),
                                   float(row["close"]), ts=stamp)
                fed += 1
            return fed
        except Exception as e:                                 # noqa: BLE001
            logger.debug("ledger feed_frame skipped: %s", e)
            return 0

    def on_closed_bar(self, high: float, low: float, close: float,
                      ts: str = "") -> None:
        """Apply ONE CLOSED bar. A TEST is a VISIT, not a bar.

        THE RULE, and it is the operator's:
          · the bar's RANGE reaches the level      -> the visit is in CONTACT
          · a visit OPENS on the first such bar    -> touches += 1  (ONE per test)
          · the visit CLOSES on the first bar that does NOT reach, and the
            DEPARTING CLOSE decides it:
              origin side -> holds += 1    (a touch and a retreat: a defense)
              far side    -> breaches += 1 (acceptance)
        Operator, 2026-09-12: *"Leans on isn't the same as testing it."* So 40
        bars of price leaning on a level is ONE test, and `contact_bars` keeps
        the duration separately rather than letting it masquerade as 40 tests.

        🔴 WHAT THIS REPLACES, AND IT WAS A LIVE DEFECT. `reached` was a
        HALF-PLANE — `low <= price + tol` for a low level — so every bar on the
        FAR SIDE of a level satisfied it. Once price broke through, every
        subsequent bar re-counted as a fresh touch AND a fresh breach.
        📊 MEASURED ON THE BANKED BOOKS before it was changed, 45 books over 3
        sessions and 15 symbols, 386 level-rows: 67.9% of levels showed ZERO
        touches and 19.4% showed more than 100, median 209 for any level that
        saw one — in a 390-bar session. Bimodal, because it was recording which
        SIDE of a line price sat on rather than contact with it.
        🔴 THE CASE THAT PROVES IT: AMZN 2026-09-09, PDL 254.75, session high
        254.62 — **price never reached the level.** One bar came within the 0.51
        band; 389 were entirely below it. The book recorded **389 touches and 389
        breaches** of a level that was never touched and never crossed.
        ⚠️ CONTAINMENT IS SYMMETRIC AND THAT IS THE POINT. `low - tol <= price <=
        high + tol` asks one question of both kinds of level, so neither side can
        drift into a half-plane again the next time someone edits a branch.
        ⚠️ AN UNRESOLVED VISIT IS NEITHER A HOLD NOR A BREACH. A test still in
        progress at the session close stays open and `last_result` keeps naming
        the last RESOLVED test. Defaulting it either way would invent an outcome,
        and `touches >= holds + breaches` is the invariant that says so.

        ⚠️ CLOSED BARS ONLY. Feeding a forming bar would count a wick that has
        not finished printing and a close that is not a close.
        """
        try:
            high, low, close = float(high), float(low), float(close)
            # A2.4 — the ledger's own high-water mark for "which bars have I
            # consumed". Set HERE (not only in feed_frame) so the invariant
            # holds on every entry point, and so write() persists it for the
            # restart hydrate.
            if ts and ts > (self.last_bar_ts or ""):
                self.last_bar_ts = ts
                self._dirty = True
            for lv in self.levels:
                tol = abs(lv.price) * TOUCH_TOL_PCT
                # CONTACT: does the bar's RANGE reach the level at all?
                reached = (low - tol) <= lv.price <= (high + tol)
                if reached:
                    lv.contact_bars += 1
                    if not lv.visit_open:
                        lv.visit_open = True
                        lv.visit_started = ts
                        lv.visit_bars = 0
                        lv.touches += 1          # ONE touch per TEST
                    lv.visit_bars += 1
                    self._dirty = True
                    continue
                if not lv.visit_open:
                    continue
                # ── THE TEST ENDS HERE, and the departing close decides it. The
                # bar's range does not contain the level, so the close is
                # unambiguously on one side or the other.
                lv.visit_open = False
                origin = (close < lv.price - tol) if lv.kind == "high" \
                    else (close > lv.price + tol)
                if origin:
                    lv.holds += 1
                    lv.last_result = "hold"
                else:
                    lv.breaches += 1
                    lv.last_result = "breach"
                lv.last_touch = ts               # the bar the test RESOLVED on
                lv.last_visit_started = lv.visit_started
                lv.last_visit_bars = lv.visit_bars
                lv.visit_bars = 0
                self._dirty = True
        except Exception as e:                                 # noqa: BLE001
            logger.debug("ledger on_closed_bar skipped: %s", e)

    # ── read side ────────────────────────────────────────────────────────────

    def _stamp_history(self, lv) -> None:
        """Apply the delivered defense record to a NEWLY created level.

        🔴 DURABILITY ONLY, AND NEVER AN EVENT. This writes `prior_*` and nothing
        else. `last_result`, `last_touch` and every session counter stay as the
        constructor left them — empty and zero — because a hold from three days
        ago is not an interaction that happened today, and seeding one would fire
        a trade on a stale event. `check_level_visits` V9 pins it.
        ⚠️ ONE WRITER PER FIELD: the history file owns `prior_*`, the session
        owns the rest. Nothing merges the two, so neither can corrupt the other.
        ⚠️ MATCHED BY PRICE AND KIND, NOT BY NAME. Monday's `PDH` is a different
        price from Friday's, and what carries across sessions is the PRICE — the
        operator's *"walk the tape and pull the historical levels against spot"*.
        [[LVL.15]] is the second reason: level names are not unique.
        ⚠️ NEAREST ZONE WINS inside the tolerance, so a cluster cannot make the
        answer depend on file order.
        """
        try:
            zones = load_history(self.symbol)
            if not zones:
                return
            best, best_d = None, None
            for z in zones:
                if z.get("kind") != lv.kind:
                    continue
                d = abs(float(z["price"]) - lv.price)
                if d > abs(lv.price) * TOUCH_TOL_PCT:
                    continue
                if best_d is None or d < best_d:
                    best, best_d = z, d
            if best is None:
                return
            lv.prior_touches = int(best.get("prior_touches") or 0)
            lv.prior_holds = int(best.get("prior_holds") or 0)
            lv.prior_breaches = int(best.get("prior_breaches") or 0)
            lv.prior_sessions = int(best.get("prior_sessions") or 0)
        except Exception as e:                                 # noqa: BLE001
            logger.debug("ledger _stamp_history skipped: %s", e)

    def interaction_at(self, price: float, kind: str = ""):
        """This level's OWN latest interaction, as recorded on a CLOSED bar.

        Returns a dict — `result` ("hold"|"breach"|""), `last_touch` (the bar's
        stamp, which is the interaction's IDENTITY), `touches`, `holds`,
        `breaches`, `price`, `name` — or **None** when no level matches.

        🔴 None MEANS THE LEDGER CANNOT ANSWER, NOT THAT THE ANSWER IS NO. The
        book is seeded from the mapper's named pools and `main.py` retries every
        tick until they exist, so "not found" is normal early in a session and
        must reach the caller as STARVED. A default verdict here would refuse
        trades invisibly.
        ⚠️ MATCHED BY PRICE WITHIN `TOUCH_TOL_PCT`, THE SAME TOLERANCE THE
        COUNTING USES. The mapper's pool price and this book's level price come
        from one source, but they round independently and an exact == would fail
        on the last decimal — silently, and only for some levels.
        ⚠️ NEAREST WINS when several levels fall inside the tolerance, so a
        cluster cannot make the answer depend on insertion order.
        """
        try:
            px = float(price)
            if px <= 0:
                return None
            best = None
            best_d = None
            for lv in self.levels:
                if kind and lv.kind != kind:
                    continue
                d = abs(lv.price - px)
                if d > abs(px) * TOUCH_TOL_PCT:
                    continue
                if best_d is None or d < best_d:
                    best, best_d = lv, d
            if best is None:
                return None
            return {"result": best.last_result, "last_touch": best.last_touch,
                    "touches": best.touches, "holds": best.holds,
                    "breaches": best.breaches, "price": best.price,
                    "name": best.name,
                    # r378 — the DURATION and the OPEN test, both separate from
                    # the test COUNT. A caller that wants "is price leaning on
                    # this right now" asks `visit_open`; one that wants "how
                    # often has it been defended" asks `holds`. Before r378 one
                    # number was doing both jobs and doing neither.
                    "contact_bars": best.contact_bars,
                    "visit_open": best.visit_open,
                    "visit_bars": best.visit_bars,
                    "last_visit_bars": best.last_visit_bars,
                    "unresolved": best.touches - (best.holds + best.breaches),
                    # r378 — the DEFENSE RECORD, from previous sessions. This is
                    # what the operator ruled the contact gates must be fitted
                    # per level type against: *"those named levels also have
                    # historical defense numbers that the transient fork will
                    # never have."* `defense_rate` is None when there is no
                    # history and must not be read as 0.0.
                    "prior_touches": best.prior_touches,
                    "prior_holds": best.prior_holds,
                    "prior_breaches": best.prior_breaches,
                    "prior_sessions": best.prior_sessions,
                    "defense_rate": best.defense_rate(),
                    "partial": best.partial}
        except Exception as e:                                 # noqa: BLE001
            logger.debug("ledger interaction_at skipped: %s", e)
            return None

    def coverage(self) -> Dict[str, int]:
        highs = sum(1 for lv in self.levels if lv.kind == "high")
        lows = sum(1 for lv in self.levels if lv.kind == "low")
        return {"highs": highs, "lows": lows,
                "meets_minimum": int(highs >= MIN_LEVELS_PER_SIDE
                                     and lows >= MIN_LEVELS_PER_SIDE)}

    # ── persistence ──────────────────────────────────────────────────────────

    def write(self, force: bool = False) -> bool:
        """Atomic rewrite of the current book. Returns True if it wrote.

        Atomic because a strategy may read this file while the loop writes it;
        a half-written JSON would be read as a corrupt or EMPTY level set, and
        an empty level set is indistinguishable from "no levels found" — a
        silent wrong answer rather than a loud failure.
        """
        try:
            if not self._dirty and not force:
                return False
            if not self.date:
                return False
            day_dir = os.path.join(_OUT_ROOT, self.date)
            os.makedirs(day_dir, exist_ok=True)
            path = os.path.join(day_dir, f"{self.symbol}.json")
            payload = {
                "schema_version": SCHEMA_VERSION,
                "symbol": self.symbol,
                "date": self.date,
                "coverage": self.coverage(),
                "touch_tol_pct": TOUCH_TOL_PCT,
                "last_bar_ts": self.last_bar_ts,
                "levels": [lv.as_dict() for lv in self.levels],
            }
            fd, tmp = tempfile.mkstemp(dir=day_dir, suffix=".tmp")
            with os.fdopen(fd, "w") as f:
                json.dump(payload, f, default=str)
            os.replace(tmp, path)                  # atomic on POSIX
            self._dirty = False
            return True
        except Exception as e:                                 # noqa: BLE001
            logger.debug("ledger write skipped: %s", e)
            return False


_LEDGER: Optional[LiquidityLedger] = None


def get_ledger(symbol: str = "") -> LiquidityLedger:
    global _LEDGER
    if _LEDGER is None:
        _LEDGER = LiquidityLedger(symbol or os.environ.get("OT_INSTRUMENT", "?"))
    return _LEDGER
