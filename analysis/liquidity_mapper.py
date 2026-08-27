"""
analysis/liquidity_mapper.py  v4.2
v4.2  2026-08-27  r163 — THE FORK'S TINES ARE MOVING LIQUIDITY LEVELS, AND A
      TOUCH IS THEIR EVENT. Operator, 2026-08-27: *"it's basically a moving
      level that sweep is allowed to use, but with a touch, not a reject. The
      plan would still need to select a strike beyond the move that caused
      the touch."* And: *"a moving target liquidity mapper but with the
      elements of slope and time."*
      · `LiquidityPool` gains `moving`, `slope_per_min`, `as_of` — a tine is a
        named pool whose price is a function of TIME: `price_at(ts)` =
        price − slope·(minutes to now). PDH/PDL have slope 0 and are unchanged.
      · `LiquiditySweep` gains `touch` (the event was a TOUCH, not a reclaim)
        and `moving`, so consumers can key a spent lock by NAME rather than by
        a price that drifts every bar.
      · `publish_tines(lmap, ctm, df_1m)` — called at the assembly point after
        the condor trigger map is built: each active rail ("1h upper tine",
        "1d lower tine") becomes a moving named pool, and `_detect_touches`
        walks the last TOUCH_LOOKBACK_BARS 1m bars evaluating the rail WHERE
        IT WAS ON EACH BAR (slope × bars back), not where it is now. A bar
        whose high reaches the upper rail(t) (low reaches the lower) is a
        touch; the event is born READY (`reclaimed=True` — the touch IS the
        trigger); `sweep_price` is the EXTREME of the touching move so the
        plan selects the short strike beyond it; ACCEPT_CLOSES closes beyond
        rail(t) since the first touch INVALIDATE it (a tine that is broken
        is not a tine). Emitted as a `LiquiditySweep` with kind high_sweep /
        low_sweep so `boundary_from_sweep` and the sweep's plan need no
        special case. The tine's per-tick position also lands on the map as
        a pool, so the session map's geometry ruling applies to it.
v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

Named liquidity pools, session sections, and the 3-deep ladder.

v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

analysis/liquidity_mapper.py — AUDIT A2: THE INPUT COULD NOT
SWP.11: COUNT ACCEPTANCE AFTER THE RECLAIM, NOT DURING
        THE REJECTION. `window` starts at the SWEEP BAR, and on a high sweep
        price is BY DEFINITION above the pool there - so the sweep's OWN close
        counted as "acceptance", and so did every bar of the rejection still
        working back. THE VETO WINDOW AND THE CONFIRMATION WINDOW WERE THE SAME
        WINDOW.
        MEASURED 2026-08-15: `closes_beyond >= 2` blocked 64.5% of named-pool
        ticks; of 25,792 vetoed ticks post-08-11, 100% WERE RECLAIMED AND 0%
        WERE GENUINE ACCEPTANCE. SWP.9 measured it at 67% of the 95.9% vetoed.
        WICKS AND BODIES: a wick is a touch, a close is a decision. Acceptance
        only means something ONCE PRICE HAS RETURNED - a close beyond AFTER the
        reclaim means price left again and stayed. Before that it is the move.
        NOT A BLANKET UNGATE: post-reclaim closes beyond the level still veto,
        and a test asserts it.
        ALSO FIXED HERE: the first draft used `_rc_bar` in `closes_beyond`
        while defining it FOURTEEN LINES LATER - a NameError on every sweep
        evaluation, the same class as the `ctx` P0 that stopped boxes trading
        on 08-18. An import check cannot catch it; the tests now EXECUTE the
        path (WA 21).
SWP.10: AGE THE SWEEP FROM THE RECLAIM, NOT THE SWEEP BAR.
        `bars_ago` counted from the sweep bar, but the setup IS NOT TRADEABLE
        until price closes back inside. The mapper runs on 5m/15m with
        SWEEP_REJECTION_CANDLES=3, so confirmation lands 5-20 MINUTES later and
        `age_decay = 0.5**(age/3)` charged the signal for a delay it could not
        act inside.
        MEASURED (SWP.9, 269,027 named rows / 27 sessions): 95.9% hard-vetoed
        to 0.000 (67% of those by veto_accept); of the 4.1% surviving,
        age_decay median 0.062 = ~12 bars = ~60 MINUTES, while trend_opp median
        was 1.000 - age was the SOLE binding damper. Median surviving score
        ~0.031 against SWEEP_SETUP_FLOOR 0.05: THE SURVIVORS DID NOT CLEAR
        THEIR OWN DISPATCH FLOOR.
        NOT A RECALIBRATION. No constant changed - not SWEEP_HALFLIFE_BARS, not
        the floor. At the observed median the score moves 0.031 -> 0.062, past
        the floor on the arithmetic alone.
        Both sweep directions fixed; `bar_index` still records the sweep bar as
        the diagnostic anchor, `reclaim_bar_index` is new.
        CARRY LIQ.6, AND FOUR SMALLER DEFECTS.
audit #2 fixes:
        (A2.1) SECTION_LOOKBACK_DAYS=10 read df_5m, which the cache caps at
        100 bars (~8.3h of 24h tape). Truncated sections were admitted as
        closed pools at WRONG prices (reproduced: true Asia High 101.10
        emitted as 97.10), and rung prices MUTATED intraday as the window
        slid — the self-rewriting level, back through the input. Fixes:
        `analyze()` takes `named_df` (a deep store frame main now supplies;
        1h bars, hour granularity is all the section masks use), and a
        section is admitted ONLY if the frame reaches its start instant —
        a left-truncated section is skipped, on ANY input depth.
        (A2.5) the NY section was fixed at 13-20 UTC while RTH is defined
        in ET: from 2026-11-01 (EST) the mask would have admitted TODAY'S
        FORMING RTH extreme as a pool from 3:00pm ET. NY hours now derive
        from the date's ET offset via ZoneInfo (13-20 EDT / 14-21 EST) —
        never a hardcoded offset. Still-forming is now an INSTANT test
        (tape must reach the section's end), not an hour comparison.
        (A2.6) NAMED_POOLS_INCLUDE_SESSIONS removed: the LIQ.6 ladder never
        consulted it, so the knob was dead and its test asserted the
        opposite of production. Session rungs are ON by doctrine; the
        invariant the tests now pin is "no still-forming section is a pool".
        (A2.7) `_add_named_pool` more-extreme-wins REPLACED the name
        wholesale, so PDH could vanish from the map when a rung within the
        0.2% zone out-priced it (reproduced). The merge is now symmetric:
        a collision never deletes a fact in either direction.
        (A2.8) the candle-count fallback still built OLD-definition session
        pools, and any exception in the LIQ.6 path silently reverted a tick
        emits PDH/PDL only, and the exception path warns ONCE per process.
        Hygiene: dead ASIA/LONDON/NY_START/END constants (values
        contradicted SECTIONS) and the never-read RTH_OPEN_UTC deleted.
LIQ.1 + LIQ.3.
        Two changes, both found by running the REAL code over real tape and a
        fabricated tape rather than by reading it.
        LIQ.1(a) LONDON/ASIA ARE NO LONGER SWEEPABLE POOLS. Operator: "the
        London session in particular was creating a moving target and that has
        to go." The window is 07:00-16:00 UTC against RTH 13:30-20:00 — A 2.5
        HOUR OVERLAP — so from 09:30 to 12:00 ET "London High" is set by the
        price being traded right now. Sweeping it sweeps a level RTH made
        seconds ago. ⚠️ THIS RETROACTIVELY UNDERMINES THE SHADOW OBSERVER'S
        61.3% LONDON SHARE: London was NEAREST because it TRACKS PRICE, so
        SWP.3's London bonus was fitted to an artefact. The lmap FIELDS stay
        populated (shadow/primitives.py reads them); only the POOL goes.
        OT_LIQ_SESSION_POOLS=1 restores.
        LIQ.1(b) THE DEDUPE DELETED THE NAMED SWEEP. A PDH/PDL almost always
        ALSO sits on an equal-high/low cluster — that coincidence is WHY it is
        liquidity — so one raid makes TWO sweeps with identical kind, pool_price
        and bars_ago. They collide on the dedupe key; `mins < cmins` is FALSE on
        equality, so the FIRST-inserted survived and unnamed pools are found
        first. `swept_named_level` came back EMPTY, L1's `veto_loc` hard-vetoed,
        and THE SWEEP SCORE WAS EXACTLY 0.000 on a perfect raid. Measured on a
        fabricated PDL raid: 0.000 before, 1.000 after. It also made v3.1's
        "named takes precedence" filter DEAD CODE — that filter reads the
        ALREADY-DEDUPED list.
        ⚠️ LIVE INCIDENCE UNKNOWN: the 08-11 corpus shows veto_loc PASSING on
        99.6% of ticks, so this is real but may be rare.
        LIQ.3 RUNNING INVALIDATION — `sweep_invalidated`, recomputed EVERY TICK.
        Operator: "if the market makers are driving the price to either extreme
        what difference does it make if it takes an hour or if it takes all
        day?" None — what ends the thesis is the LEVEL FAILING. `closes_beyond`
        already asks exactly that question but is a BIRTH-TIME snapshot, counted
        over the 2-3 bars after the raid and NEVER UPDATED, so nothing ever
        re-checked whether the level still held. MEASURED over 90 real
        symbol-days: of the stale sweeps the 8-bar gate refused, **32.9% still
        had a LIVE thesis** (854 of 2,593) — ~9.5 valid setups discarded per
        symbol-day on a clock rather than on invalidation.
        ⚠️ REJECTED ALTERNATIVE, recorded so it is not re-proposed: scoping
        named-precedence to FRESH sweeps (LIQ.2, built and measured 2026-08-11)
        moved refusals 98.6% -> 98.4% and evicts exactly the stale-but-live
        setups this change exists to keep. Dropped.
AS-OF named levels.
        _find_named_levels derived 'today' from the wall clock, so (a) every
        tape replay saw ZERO named pools (measured: 0 of 1,367 evals across
        3 symbols × 26 sessions — the sweep chain's first link, severed), and
        (b) live Mondays had no PDH/PDL (calendar-minus-one = Sunday). Dates
        now derive from the frame's last bar; 'yesterday' is the previous
        TRADING day present in the frame. Session windows unchanged.
--- original header follows --- — Institutional liquidity mapping.
Tracks equal highs/lows, stop clusters, liquidity sweeps, and
imbalance fills. Core input for the sweep reversal strategy.
SWEEP DEFINITION CORRECTION (rejection, not just penetration).
        The old rejection_pct measured distance from the wick to the LAST close in
        the window — it never checked whether price came back INSIDE the swept
        level. A breakout candle that poked a pool and CLOSED THROUGH it (accepted)
        scored a high rejection_pct and was stamped a confirmed sweep. That is the
        defect that let breakouts (AVGO 380+ open-air ladder) be classified as
        sweeps. A sweep BY DEFINITION requires penetration AND rejection — price
        thrown back and holding inside the level. Now each LiquiditySweep also
        records `reclaimed` (did closes return inside the pool and hold) and
        `closes_beyond` (how many closes ACCEPTED through it). rejection_pct is now
        measured off a close that is actually back inside the level. Acceptance
        (closes_beyond >= ACCEPT_CLOSES) is no longer a sweep — it is a breakout.
        Calibration constants (ACCEPT_CLOSES, hold bars) are placeholders to be
        tightened as candle-logger sessions accumulate; the reclaim REQUIREMENT
        itself is definitional, not a tunable.
detection fixes: recent_sweep is now selected by ACTUAL
        TIME (own-timeframe bars_ago × tf minutes), not raw cross-timeframe bar
        index; sweep_age_bars reported in consistent 5m-equivalent bars (fixes
        fresh sweeps look stale); duplicate same-level sweeps are collapsed.
repo-wide v3.0 bump: Yahoo-Finance purge & data stream
        mapping optimization (all market data now flows from the single
        shared TastyTrade candle feed — see data/candle_feed.py). No logic
        change in this file.
v1.1 additions:
- Previous Day High/Low (PDH/PDL) as named high-value liquidity pools
- Previous Session High/Low (Asia, London, NY) as named pools
- Named pools carry higher confluence weight in sweep reversal strategy
LIQ.6 (2026-08-15) — A WHOLESALE CHANGE TO WHAT A NAMED POOL IS.
    Everything before this was correct FOR ITS TIME and is incorrect under the
    clearer rules. Four changes, all from the operator:
    1. SECTIONS ARE NON-OVERLAPPING AND CONTIGUOUS in UTC — Asia 00-08,
       London 08-13, NY 13-20. A bar belongs to exactly one. The old windows
       overlapped (Asia 00-08, London 07-16, NY 13-22), which is how
       "London High" could be set by a price RTH traded seconds ago and why
       LIQ.1 had to remove London wholesale. Only the OVERLAPPING TAIL was ever
       the problem; the pre-RTH London extreme is a real level and is back.
    2. A SECTION IS A POOL ONCE IT IS CLOSED. The test is COMPLETED vs STILL
       FORMING, never the calendar date. Today's Asia and pre-RTH London are
       valid from the open. **TODAY'S RTH IS NEVER A POOL** — it is
       `session_high`/`session_low`, already tracked by the not-exceeded filter.
       The old code named today's forming RTH extreme "NY High", a level that
       rewrote itself on every new print.
    3. `NY High/Low` IS SESSION-TYPE, NOT DATE-RELATIVE. PDH/PDL means literally
       yesterday. An RTH extreme from five days ago that nothing has taken is
       still "NY High" and is still where the stops are.
    4. A LADDER THREE DEEP, AND A BROKEN LEVEL IS NOT A POOL. "More extreme
       means the less extreme level was already invalidated" — if a later
       section printed a higher high, price went THROUGH the earlier one to get
       there and those stops are gone. Rung 1 is the next liquidity; rungs 2-3
       are where price runs if it takes rung 1. The rung is always in the name.
    ⚠️ CONSEQUENCE FOR ANALYSIS: every sweep in the archive was scored against
    the OLD definition. The 2026-08-15 reads (accept-veto at 64.5%, the retreat
    distribution, the SWEEP tape gap) describe a mapper that no longer exists —
    bake. **The retreat probe must be re-run, and the sweep TIMING change waits
    until this has collected**, or neither can be attributed.
"""

import logging
import time
import os as _os
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import pandas as pd

from config import (
    EQUAL_HIGH_LOW_LOOKBACK, EQUAL_LEVEL_PCT,
    SWEEP_REJECTION_CANDLES, IMBALANCE_MIN_SIZE_PCT
)
from utils.math_utils import within_pct

logger = logging.getLogger(__name__)


@dataclass
class LiquidityPool:
    """A cluster of equal highs or lows (stop resting zone)."""
    price:          float
    kind:           str    = "high"     # "high" or "low"
    touch_count:    int    = 0
    timeframe:      str    = ""
    swept:          bool   = False
    swept_index:    int    = -1
    rejection_confirmed: bool = False
    # Named pools carry extra confluence weight
    name:           str    = ""         # e.g. "PDH", "PDL", "Asia High", "London Low"
    is_named:       bool   = False      # True for PDH/PDL/session levels
    # v4.2 — a MOVING level (a fork tine): price is a function of time
    moving:         bool   = False
    slope_per_min:  float  = 0.0        # signed price drift per WALL minute
    as_of:          float  = 0.0        # epoch of `price`

    def price_at(self, ts_epoch: float) -> float:
        """The level where it WAS at `ts_epoch`. A fixed pool returns itself."""
        if not self.moving or not self.as_of:
            return self.price
        return self.price - self.slope_per_min * ((self.as_of - float(ts_epoch)) / 60.0)


@dataclass
class LiquiditySweep:
    """A confirmed liquidity sweep event."""
    pool_price:     float
    sweep_price:    float
    kind:           str     # "high_sweep" or "low_sweep"
    rejection_candles: int  = 0
    rejection_pct:  float   = 0.0
    confirmed:      bool    = False
    bar_index:      int     = 0
    reclaim_bar_index: int  = 0      # SWP.10: bar the close returned INSIDE
    bars_ago:       int     = 0      # SWP.10: bars since the RECLAIM (was: since
                                     #   the sweep). The setup is not tradeable
                                     #   until price closes back inside, so aging
                                     #   from the sweep bar charged the signal
                                     #   for confirmation latency it could not
                                     #   act inside.
    timeframe:      str     = ""
    # Was this sweep of a named level? (PDH/PDL/session)
    swept_named_level: str  = ""        # Name of the level swept, if any
    # v1.3 — rejection vs acceptance (the truth that makes it a sweep, not a breakout)
    reclaimed:      bool    = False     # price closed back INSIDE the level and held
    closes_beyond:  int     = 0         # # of closes that ACCEPTED through the level
    # ⚠️ LIQ.3 (2026-08-11) — `closes_beyond` above is a BIRTH-TIME snapshot,
    # counted over the 2-3 bars right after the raid and NEVER UPDATED. It
    # answers "did price accept beyond immediately?", not "is the level still
    # holding?". The fields below carry what a RUNNING invalidation test needs.
    invalidated:    bool    = False     # LIQ.3: price has since ACCEPTED beyond
    closes_beyond_live: int = 0         # LIQ.3: closes beyond SINCE the sweep
    # v4.2 — a TOUCH of a MOVING level (a fork tine): born ready, no reclaim
    touch:          bool    = False
    moving:         bool    = False


@dataclass
class LiquidityMap:
    """Complete liquidity landscape."""
    pools:          List[LiquidityPool]  = field(default_factory=list)
    sweeps:         List[LiquiditySweep] = field(default_factory=list)
    recent_sweep:   Optional[LiquiditySweep] = None
    sweep_age_bars: int                  = 999
    sweep_invalidated: bool              = False   # LIQ.3 — running liveness

    # Named key levels
    prev_day_high:      Optional[float] = None
    prev_day_low:       Optional[float] = None
    asia_session_high:  Optional[float] = None
    asia_session_low:   Optional[float] = None
    london_session_high: Optional[float] = None
    london_session_low:  Optional[float] = None
    ny_session_high:    Optional[float] = None
    ny_session_low:     Optional[float] = None

    # Stop cluster levels
    stop_clusters_above: List[float]    = field(default_factory=list)
    stop_clusters_below: List[float]    = field(default_factory=list)

    near_pool_above:     Optional[float] = None
    near_pool_below:     Optional[float] = None
    near_pool_pct:       float           = 0.05


_ACCEPT_CLOSES = 2      # LIQ.3 — mirrors SWEEP_ACCEPT_CLOSES
# A2.6 (2026-08-15): NAMED_POOLS_INCLUDE_SESSIONS removed. The LIQ.6 ladder
# never consulted it — the knob was dead while a green test asserted sessions
# were off. Session rungs are ON by LIQ.6 doctrine (rule 1); the protection
# LIQ.1 actually needs — no still-forming section is ever a pool — is a
# structural rule below, not a switch.


class LiquidityMapper:
    """
    Maps institutional liquidity levels and detects sweep events.
    Includes Previous Day High/Low and session highs/lows as named pools.
    Named pools provide extra confluence when swept.
    """

    # Session hours in UTC
    # ── LIQ.6 (2026-08-15) — A POOL IS A CLOSED SESSION'S EXTREME ────────────
    # Operator: "The current day's levels must be excluded BY DEFINITION because
    # they are still forming. Exception: overnight low/high are still today, but
    # an EARLIER session and therefore valid."
    #
    # The test is COMPLETED vs STILL FORMING, not the calendar date:
    #   · Asia (00:00-08:00 UTC) is closed before RTH opens -> VALID, today.
    #   · London BEFORE RTH open is closed -> VALID. London AFTER 13:30 is the
    #     moving target LIQ.1 removed. **LIQ.1 removed the WHOLE session when
    #     only the overlapping tail was the problem** — the pre-RTH London
    #     extreme is exactly the kind of level worth naming, so the window is
    #     now CLIPPED rather than gated off.
    #   · TODAY'S RTH high/low is NEVER a pool. It is `session_high`/
    #     `session_low`, which the not-exceeded filter already tracks.
    #
    # ⚠️ AND `NY High/Low` MEANS SOMETHING DIFFERENT FROM `PDH/PDL`.
    # PDH/PDL is DATE-RELATIVE — literally yesterday. NY High/Low is
    # SESSION-TYPE: the last UNBROKEN RTH extreme, whenever it formed. Operator:
    # "If one of the last extremes was NY H/L but it was 5 days ago, then it's
    # not PDH/PDL — it accurately is NY H/L." An untouched extreme is where the
    # stops are REGARDLESS of when it formed, which is what makes it liquidity.
    # The old code named TODAY'S FORMING RTH extreme "NY High/Low" — neither
    # yesterday's nor the last unbroken one — so it was a self-rewriting level.
    # MEASURED (LIQ.5 retreat probe): NY levels showed a retreat mean of 4.1-4.2
    # against PDH/PDL's 1.1-1.2. **That gap was the artefact of a moving target,
    # not evidence of a better level.**
    # Contiguous, NON-OVERLAPPING sections in UTC. A bar belongs to exactly
    # one. RTH is 13:30-20:00 UTC; hour-granularity masks use 13 and 20.
    # Asia and London are fixed-UTC sections BY THE OPERATOR'S DEFINITION
    # ("just use the UTC day/times"). The NY section is the RTH session and
    # RTH is defined in ET — its UTC hours therefore depend on the DATE.
    # A2.5 (2026-08-15): hardcoded (13,20) admitted today's FORMING RTH
    # extreme as a pool from 3:00pm ET all winter, and left 20-21 UTC winter
    # bars (3-4pm ET) in no section at all. Never a fixed offset — the repo
    # already paid for one of those once (would have broken 2026-11-01).
    SECTIONS_FIXED = (("Asia",   0,  8),
                      ("London", 8,  13))

    @staticmethod
    def _ny_utc_hours(d) -> tuple:
        """RTH (09:30-16:00 ET) at hour granularity, in UTC, for date d."""
        off = datetime(d.year, d.month, d.day, 12,
                       tzinfo=ZoneInfo("America/New_York")).utcoffset()
        return (13, 20) if off == timedelta(hours=-4) else (14, 21)

    def _sections_for(self, d) -> tuple:
        h0, h1 = self._ny_utc_hours(d)
        return self.SECTIONS_FIXED + (("NY", h0, h1),)
    SECTION_LOOKBACK_DAYS = 10
    LADDER_DEPTH = 3         # most recent unbroken H/L, next, 3rd

    def analyze(self, df_5m: pd.DataFrame, df_15m: pd.DataFrame,
                current_price: float,
                named_df: pd.DataFrame = None) -> LiquidityMap:
        """`named_df` (A2.1): a DEEP frame for named levels only. The cached
        5m frame is 100 bars (~8.3h) — it cannot carry a 10-day section
        lookback, and a section truncated by the frame edge was being
        admitted at a WRONG price. main supplies a store-read 1h frame;
        replay/tests that pass nothing keep their own tape (the truncation
        guard below protects both paths). Sweeps/pools still scan the live
        frames — only NAMED level extraction reads the deep one."""
        lmap = LiquidityMap()

        primary = df_15m if (df_15m is not None and not df_15m.empty) else df_5m
        if primary is None or primary.empty:
            return lmap

        # Standard equal high/low pools
        self._find_pools(lmap, primary, "15m")
        if df_5m is not None and not df_5m.empty:
            self._find_pools(lmap, df_5m, "5m")

        # Named key levels (PDH/PDL, session ladder). Deep frame when the
        # caller has one (A2.1); otherwise the live frame, guarded.
        _ndf = named_df if (named_df is not None and
                            not getattr(named_df, "empty", True) and
                            len(named_df) >= 50) else None
        if _ndf is not None:
            self._find_named_levels(lmap, _ndf)
        elif df_5m is not None and not df_5m.empty:
            self._find_named_levels(lmap, df_5m)
        elif primary is not None:
            self._find_named_levels(lmap, primary)

        # Sweep detection
        self._detect_sweeps(lmap, primary, "15m")
        if df_5m is not None and not df_5m.empty:
            self._detect_sweeps(lmap, df_5m, "5m")

        # Stop clusters
        self._identify_stop_clusters(lmap, primary, current_price)

        # Nearby pools
        self._flag_nearby_pools(lmap, current_price)

        # Most recent sweep — selected by ACTUAL TIME, not raw bar index.
        # bar_index is per-timeframe, so comparing a 15m index to a 5m index (as
        # the old max-by-bar_index did) was meaningless and produced a nonsense
        # (often negative) age. We convert each sweep's own-timeframe bars_ago
        # into minutes, dedupe same-level sweeps found on multiple scans, pick
        # the most recent by minutes, and report age in 5m-equivalent bars so
        # the downstream <=8 thresholds stay consistent across timeframes.
        confirmed = [s for s in lmap.sweeps if s.confirmed]
        if confirmed:
            deduped = self._dedupe_sweeps(confirmed)
            # v3.1: NAMED sweeps take precedence. Unnamed pools (equal-high/low
            # clusters) are swept every few minutes, so recency-across-all-pools
            # meant a genuine PDH/session-level raid was displaced from this
            # slot almost immediately — the classifier (which requires
            # swept_named_level, definitionally) could ~never see one.
            # Measured: sweep_detected on 100% of evals, sweep_is_named on 0%,
            # across 3 symbols × 26 sessions. The freshness gate (age ≤ 8)
            # still applies downstream — this only stops noise from evicting
            # the signal.
            named = [s for s in deduped if s.swept_named_level]
            pick_from = named if named else deduped
            recent = min(pick_from, key=lambda s: s.bars_ago * self._tf_minutes(s.timeframe))
            minutes_ago = recent.bars_ago * self._tf_minutes(recent.timeframe)
            lmap.recent_sweep   = recent
            lmap.sweep_age_bars = max(0, round(minutes_ago / 5.0))   # 5m-equivalent bars
            # ── LIQ.3 — RUNNING INVALIDATION, recomputed every tick ──────────
            # Operator: "if the market makers are driving the price to either
            # extreme what difference does it make if it takes an hour or if it
            # takes all day?" None — what matters is whether the LEVEL STILL
            # HOLDS. MEASURED over 90 real symbol-days: of the stale sweeps the
            # 8-bar gate refuses, **32.9% still had a live thesis** (854 of
            # 2,593) — price had never accepted back through the raided level
            # and was still on the correct side. ~9.5 valid setups discarded
            # per symbol-day, on a clock rather than on invalidation.
            # This counts closes beyond the level SINCE the sweep, on the
            # primary frame, so the strategy can ask liveness instead of age.
            try:
                self._mark_liveness(lmap, primary, current_price)
            except Exception as exc:                              # noqa: BLE001
                logger.debug(f"liveness check failed: {exc}")

        named_levels = [p.name for p in lmap.pools if p.is_named]
        logger.debug(
            f"Liquidity: pools={len(lmap.pools)} sweeps={len(lmap.sweeps)} "
            f"named={named_levels} "
            f"recent_sweep={'YES' if lmap.recent_sweep else 'NO'} "
            f"age={lmap.sweep_age_bars}bars"
        )
        return lmap

    def _mark_liveness(self, lmap, df, current_price: float):
        """LIQ.3 — is the swept level STILL holding, as of this tick?

        DEAD when price has ACCEPTED back through the level: >= SWEEP_ACCEPT
        _CLOSES closes beyond it since the raid, or price simply sitting on the
        wrong side now. Otherwise LIVE, however old the raid is.
        ⚠️ THIS IS DELIBERATELY THE SAME TEST `veto_accept` ALREADY MAKES — the
        only change is that it is asked EVERY TICK instead of once at birth.
        """
        sw = lmap.recent_sweep
        if sw is None or df is None or df.empty:
            return
        tfm = self._tf_minutes(sw.timeframe)
        bars_back = max(1, int(round(sw.bars_ago * tfm / self._tf_minutes("5m"))))
        since = df["close"].tail(bars_back + 1)
        pool = float(sw.pool_price)
        if sw.kind == "low_sweep":
            beyond = int((since < pool).sum())
            wrong_side = current_price < pool
        else:
            beyond = int((since > pool).sum())
            wrong_side = current_price > pool
        sw.closes_beyond_live = beyond
        sw.invalidated = bool(beyond >= _ACCEPT_CLOSES or wrong_side)
        lmap.sweep_invalidated = sw.invalidated

    @staticmethod
    def _tf_minutes(tf: str) -> int:
        """Minutes per bar for a timeframe label."""
        return {"1m": 1, "5m": 5, "15m": 15, "1h": 60}.get(tf, 5)

    @staticmethod
    def _dedupe_sweeps(sweeps):
        """Collapse sweeps of the same side + price level (found on multiple
        timeframe scans) to a single entry, keeping the most recent by
        minutes-ago. Prevents duplicate/phantom sweeps from skewing selection."""
        best = {}
        for s in sweeps:
            key = (s.kind, round(s.pool_price, 2))
            mins = s.bars_ago * LiquidityMapper._tf_minutes(s.timeframe)
            cur = best.get(key)
            if cur is None:
                best[key] = s
                continue
            cmins = cur.bars_ago * LiquidityMapper._tf_minutes(cur.timeframe)
            if mins < cmins or (mins == cmins
                                and s.swept_named_level
                                and not cur.swept_named_level):
                best[key] = s
        return list(best.values())

    def _find_named_levels(self, lmap: LiquidityMap, df: pd.DataFrame):
        """
        Extract Previous Day High/Low and session highs/lows from candle data.
        These are the most important liquidity levels — institutions specifically
        target these for stop hunts before reversing.
        """
        if df is None or len(df) < 50:
            return

        now_utc = datetime.now(timezone.utc)

        # Build candle timestamp index if available
        has_timestamps = hasattr(df.index, 'hour') or (
            hasattr(df.index, 'dtype') and 'datetime' in str(df.index.dtype)
        )

        if has_timestamps:
            self._find_named_levels_from_timestamps(lmap, df, now_utc)
        else:
            # Fallback: estimate from candle count (5m candles)
            self._find_named_levels_from_candle_count(lmap, df)

    def _find_named_levels_from_timestamps(self, lmap: LiquidityMap,
                                            df: pd.DataFrame, now_utc: datetime):
        """Extract named levels using actual timestamps."""
        try:
            idx = pd.DatetimeIndex(df.index)
            if idx.tz is None:
                idx = idx.tz_localize('UTC')
            else:
                idx = idx.tz_convert('UTC')

            # v3.1 AS-OF FIX: derive 'today' from the FRAME'S LAST BAR, not the
            # wall clock. now_utc.date() made every tape replay blind to named
            # levels (historical bars never match the real today), so the
            # merely coincidentally right. 'yesterday' is now the previous
            # TRADING day actually present in the frame (calendar-minus-one
            # returned Sunday every Monday: no PDH/PDL to start the week).
            today = idx[-1].date() if len(idx) else now_utc.date()
            earlier = sorted({d for d in idx.date if d < today})
            yesterday = earlier[-1] if earlier else (today - timedelta(days=1))

            # Previous trading day
            prev_day_mask = idx.date == yesterday
            if prev_day_mask.any():
                prev_day_data = df[prev_day_mask]
                pdh = float(prev_day_data["high"].max())
                pdl = float(prev_day_data["low"].min())
                lmap.prev_day_high = pdh
                lmap.prev_day_low  = pdl
                self._add_named_pool(lmap, pdh, "high", "PDH")
                self._add_named_pool(lmap, pdl, "low", "PDL")

            # Today's sessions
            today_mask = idx.date == today

            # ── LIQ.6 — SECTIONS IN TIME, THEN A LADDER 3 DEEP ──────────────
            # Operator: "Just use the UTC day/times to record the extremes in
            # each section & treat every session as a section in time" and
            # "the mapper should run 3 levels deep: most recent h/l, next most,
            # 3rd most."
            #
            # SECTIONS ARE NON-OVERLAPPING AND CONTIGUOUS, so a bar belongs to
            # exactly one and no extreme is double-counted. The old windows
            # overlapped (Asia 00-08 vs London 07-16 vs NY 13-22), which is how
            # "London High" could be set by a price RTH traded seconds ago.
            #
            # A SECTION IS A POOL ONCE IT IS CLOSED — completed vs still
            # forming, never the calendar date. Today's Asia and pre-RTH London
            # are valid from the open; **today's RTH is never a pool** (it is
            # `session_high`/`session_low`, already tracked by the not-exceeded
            # filter).
            #
            # ⚠️ AND A BROKEN LEVEL IS NOT A POOL. Operator: "more extreme means
            # the less extreme level was already invalidated." If a later
            # section printed a higher high, price went THROUGH the earlier one
            # to get there — those stops are gone. So the ladder keeps only
            # UNBROKEN extremes, newest first, three deep. Rung 1 is the next
            # liquidity above/below; rungs 2 and 3 are where price runs if it
            # takes rung 1.
            sections = []
            frame_start, frame_end = idx[0], idx[-1]
            _order = ("Asia", "London", "NY")
            for d in sorted({dt for dt in idx.date})[-self.SECTION_LOOKBACK_DAYS:]:
                for label, h0, h1 in self._sections_for(d):
                    m = (idx.date == d) & (idx.hour >= h0) & (idx.hour < h1)
                    if not m.any():
                        continue
                    start = pd.Timestamp(datetime(d.year, d.month, d.day, h0,
                                                  tzinfo=timezone.utc))
                    end = pd.Timestamp(datetime(d.year, d.month, d.day, h1,
                                                tzinfo=timezone.utc))
                    # A2.1 — LEFT-TRUNCATED: the frame does not reach the
                    # section's start, so its extreme CANNOT be proven. A rolling
                    # 100-bar frame was admitting partial sections at wrong
                    # prices (m.any() passes on ONE surviving bar).
                    if frame_start > start:
                        continue
                    # A2.5 — STILL FORMING is an INSTANT test: the tape must
                    # reach the section's end. Bar stamps are bar STARTS, so a
                    # bar stamped >= end proves every in-section bar has closed.
                    # (The old `idx[-1].hour < h1` read today's NY as closed at
                    # 3:00pm ET every winter afternoon.)
                    if frame_end < end:
                        continue
                    sd = df[m]
                    sections.append((d, label, float(sd["high"].max()),
                                     float(sd["low"].min())))
            sections.sort(key=lambda x: (x[0], _order.index(x[1])))

            # canonical single-value fields, unchanged consumers (shadow reads them)
            for d, label, hi, lo in reversed(sections):
                if label == "NY" and lmap.ny_session_high is None:
                    lmap.ny_session_high, lmap.ny_session_low = hi, lo
                if label == "Asia" and d == today and lmap.asia_session_high is None:
                    lmap.asia_session_high, lmap.asia_session_low = hi, lo
                if label == "London" and d == today and lmap.london_session_high is None:
                    lmap.london_session_high, lmap.london_session_low = hi, lo

            # THE LADDER: newest first, keep only what nothing later exceeded.
            hi_rungs, lo_rungs, seen_hi, seen_lo = [], [], None, None
            for d, label, hi, lo in reversed(sections):
                if len(hi_rungs) < self.LADDER_DEPTH and (seen_hi is None or hi > seen_hi):
                    hi_rungs.append((d, label, hi))
                    seen_hi = hi if seen_hi is None else max(seen_hi, hi)
                elif seen_hi is None:
                    seen_hi = hi
                else:
                    seen_hi = max(seen_hi, hi)
                if len(lo_rungs) < self.LADDER_DEPTH and (seen_lo is None or lo < seen_lo):
                    lo_rungs.append((d, label, lo))
                    seen_lo = lo if seen_lo is None else min(seen_lo, lo)
                elif seen_lo is None:
                    seen_lo = lo
                else:
                    seen_lo = min(seen_lo, lo)

            # ⚠️ THE RUNG IS ALWAYS IN THE NAME. A consumer sizing off "how deep
            # is this level" must not have to infer position from which producer
            # happened to win a collision. Without the suffix the ladder read
            # `London High / PDH / NY High #3` and rung 2 was invisible.
            for n, (d, label, px) in enumerate(hi_rungs, 1):
                self._add_named_pool(lmap, px, "high", f"{label} High (R{n})")
            for n, (d, label, px) in enumerate(lo_rungs, 1):
                self._add_named_pool(lmap, px, "low", f"{label} Low (R{n})")
            if hi_rungs or lo_rungs:
                logger.debug("LIQ.6 ladder highs=%s lows=%s",
                             [(str(d), l, round(p, 2)) for d, l, p in hi_rungs],
                             [(str(d), l, round(p, 2)) for d, l, p in lo_rungs])

        except Exception as e:
            # A2.8 — this fallback used to be SILENT (debug) and the fallback
            # built OLD-definition pools: any exception here reverted the tick
            # per-tick coin toss over what a named pool IS. Warn ONCE.
            if not getattr(self, "_fallback_warned", False):
                self._fallback_warned = True
                logger.warning("Named level extraction failed (%s) — falling "
                               "back to PDH/PDL-only estimates. LIQ.6 sections "
                               "are OFF on the affected ticks.", e)
            else:
                logger.debug(f"Named level extraction failed: {e}")
            self._find_named_levels_from_candle_count(lmap, df)

    def _find_named_levels_from_candle_count(self, lmap: LiquidityMap, df: pd.DataFrame):
        """
        Fallback: estimate session levels from candle count.
        5m candles: 288/day, 96/session (8hrs), 48/4hrs
        """
        n = len(df)
        if n < 50:
            return

        # Previous day = candles 288-576 ago (rough)
        prev_day_start = min(n, 576)
        prev_day_end   = min(n, 288)
        if prev_day_start > prev_day_end:
            prev_day = df.iloc[n - prev_day_start : n - prev_day_end]
            if len(prev_day) > 0:
                pdh = float(prev_day["high"].max())
                pdl = float(prev_day["low"].min())
                lmap.prev_day_high = pdh
                lmap.prev_day_low  = pdl
                self._add_named_pool(lmap, pdh, "high", "PDH")
                self._add_named_pool(lmap, pdl, "low",  "PDL")

        # A2.8 — the session estimate is GONE. Without timestamps this path
        # cannot express LIQ.6 sections (closed-only, ladder, rung names), and
        # what it produced was the pre-LIQ.6 definition wearing current names —
        # two definitions of a pool in one file, chosen by an exception. PDH/PDL
        # estimates above are retained; sessions require the timestamped path.

    def _add_named_pool(self, lmap: LiquidityMap, price: float,
                         kind: str, name: str):
        """Add a named liquidity pool. On a collision, THE MORE EXTREME WINS.

        ⚠️ LIQ.6 (2026-08-15) — this used to return on ANY named pool within
        0.2%, so FIRST-ADDED WON and the more extreme level was silently
        discarded. PDH/PDL is computed before the sections, so a more extreme
        NY High could never replace it.

        Operator's rule: **whichever is more extreme wins** — the outermost
        level is where the resting stops actually are, regardless of which
        producer found it. For a high that is the LARGER price; for a low, the
        SMALLER.

        This matters because the collision is the NORM, not the exception:
        yesterday's full-day extreme and yesterday's RTH extreme are usually the
        same print. LIQ.1(b) hit the same coincidence — "a PDH almost always
        ALSO sits on an equal-high cluster; that coincidence is WHY it is
        liquidity" — and it produced a real dedupe bug then.
        """
        for pool in lmap.pools:
            if not (pool.is_named and within_pct(pool.price, price, 0.002)):
                continue
            if pool.kind != kind:
                continue
            more_extreme = (price > pool.price if kind == "high"
                            else price < pool.price)
            if more_extreme:
                # A2.7 — take the outer price, but a collision NEVER deletes a
                # fact in EITHER direction. Wholesale name replacement made PDH
                # vanish from the map when a rung within the 0.2% zone
                # out-priced it (reproduced: rungs at 100.05/100.15 absorbed
                # PDH=100.00 twice). Mirror the merge below: when exactly one
                # party carries a rung suffix, the composed name keeps both
                # facts, same shape as the shipped direction.
                m_new = re.search(r"\(R\d\)$", name or "")
                m_old = re.search(r"\(R\d\)$", pool.name or "")
                if m_new and not m_old:
                    pool.name = f"{pool.name} {m_new.group(0)}"
                elif m_old and not m_new:
                    pool.name = f"{name} {m_old.group(0)}"
                else:
                    pool.name = name
                pool.price = price
                return
            # ⚠️ MERGE THE RUNG RATHER THAN DISCARD IT. PDH/PDL is added BEFORE
            # the ladder, so a rung landing on the same price used to be dropped
            # entirely and the ladder read "London High (R1) / PDH / NY High
            # (R3)" — rung 2 invisible. Yesterday's full-day extreme and
            # yesterday's RTH extreme are usually the SAME PRINT, so this
            # collision is the norm. Keep both facts: it is PDH, and it is R2.
            m = re.search(r"\(R\d\)$", name or "")
            if m and "(R" not in (pool.name or ""):
                pool.name = f"{pool.name} {m.group(0)}"
            return

        lmap.pools.append(LiquidityPool(
            price=price,
            kind=kind,
            touch_count=1,
            timeframe="daily" if "PD" in name else "session",
            name=name,
            is_named=True
        ))

    def _find_pools(self, lmap: LiquidityMap, df: pd.DataFrame, tf: str):
        """Find equal highs and equal lows."""
        highs = df["high"].tolist()
        lows  = df["low"].tolist()
        n     = min(len(highs), EQUAL_HIGH_LOW_LOOKBACK)

        used_h = [False] * n
        for i in range(n - 1, 0, -1):
            if used_h[i]:
                continue
            cluster = [highs[-(n) + i]]
            for j in range(i - 1, max(i - 20, -1), -1):
                if not used_h[j] and within_pct(highs[-(n)+i], highs[-(n)+j], EQUAL_LEVEL_PCT):
                    cluster.append(highs[-(n)+j])
                    used_h[j] = True
            used_h[i] = True
            if len(cluster) >= 2:
                avg = sum(cluster) / len(cluster)
                if not any(within_pct(p.price, avg, EQUAL_LEVEL_PCT)
                           for p in lmap.pools if p.kind == "high"):
                    lmap.pools.append(LiquidityPool(
                        price=avg, kind="high",
                        touch_count=len(cluster), timeframe=tf
                    ))

        used_l = [False] * n
        for i in range(n - 1, 0, -1):
            if used_l[i]:
                continue
            cluster = [lows[-(n) + i]]
            for j in range(i - 1, max(i - 20, -1), -1):
                if not used_l[j] and within_pct(lows[-(n)+i], lows[-(n)+j], EQUAL_LEVEL_PCT):
                    cluster.append(lows[-(n)+j])
                    used_l[j] = True
            used_l[i] = True
            if len(cluster) >= 2:
                avg = sum(cluster) / len(cluster)
                if not any(within_pct(p.price, avg, EQUAL_LEVEL_PCT)
                           for p in lmap.pools if p.kind == "low"):
                    lmap.pools.append(LiquidityPool(
                        price=avg, kind="low",
                        touch_count=len(cluster), timeframe=tf
                    ))

    def _detect_sweeps(self, lmap: LiquidityMap, df: pd.DataFrame, tf: str):
        """Detect sweep events with named level tagging."""
        if not lmap.pools:
            return

        highs  = df["high"].tolist()
        lows   = df["low"].tolist()
        closes = df["close"].tolist()
        n      = len(highs)

        for pool in lmap.pools:
            for i in range(1, n):
                if pool.kind == "high" and highs[i] > pool.price and not pool.swept:
                    # A sweep of a HIGH requires REJECTION: after poking above the
                    # pool, price must CLOSE BACK BELOW it (inside) and hold. Closes
                    # that stay ABOVE the pool are ACCEPTANCE — a breakout, not a sweep.
                    window = range(i, min(i + SWEEP_REJECTION_CANDLES + 1, n))
                    # ── SWP.11 (2026-08-19) — COUNT ACCEPTANCE AFTER THE
                    # RECLAIM, NOT DURING THE REJECTION. The window starts at
                    # `i`, the SWEEP BAR — and on a high sweep price is BY
                    # DEFINITION above the pool at `i`; that is what a sweep is.
                    # So the sweep bar's own close counted as "acceptance", and
                    # so did every bar of the rejection still working back.
                    # **THE VETO WINDOW AND THE CONFIRMATION WINDOW WERE THE
                    # SAME WINDOW.**
                    # MEASURED 2026-08-15: `closes_beyond >= 2` blocked 64.5% of
                    # named-pool ticks, and of 25,792 vetoed ticks post-08-11,
                    # **100% were reclaimed and 0% were genuine acceptance.**
                    # SWP.9 put it at 67% of the 95.9% vetoed population.
                    # ⚠️ WICKS AND BODIES: a wick is a touch, a close is a
                    # decision. Acceptance is only meaningful ONCE PRICE HAS
                    # RETURNED — a close beyond AFTER the reclaim means price
                    # left again and stayed. Before that it is the move itself.
                    # ⚠️ COMPUTED FIRST — `closes_beyond` below consumes it.
                    # v4.2 defined this AFTER the use and would have raised
                    # NameError on every sweep evaluation: the same defect class
                    # as the `ctx` P0 that stopped boxes trading on 08-18.
                    _rc_bar = next((k for k in window
                                    if closes[k] <= pool.price), i)
                    closes_beyond = sum(1 for k in window
                                        if k > _rc_bar and closes[k] > pool.price)
                    reclaimed = closes[i] <= pool.price or any(
                        closes[k] <= pool.price for k in window)
                    # ── SWP.10 (2026-08-19) — AGE FROM THE RECLAIM, NOT THE
                    # SWEEP. `bars_ago` counted from bar `i`, the sweep bar, but
                    # the setup is NOT TRADEABLE until price closes back inside.
                    # The mapper runs on 5m/15m with SWEEP_REJECTION_CANDLES=3,
                    # so confirmation lands 5-20 MINUTES after the sweep — and
                    # `age_decay = 0.5**(age/3)` charged the signal for every
                    # bar of a delay it had no way to act inside.
                    # MEASURED (SWP.9, 269,027 named rows): age_decay median
                    # **0.062**, which solves to ~12 bars = ~60 MINUTES on 5m.
                    # The median scored sweep was an hour old before scoring.
                    # ⚠️ THIS IS NOT A RECALIBRATION. No constant changes. It
                    # corrects WHAT the age measures; if the median lifts on its
                    # own, SWEEP_HALFLIFE_BARS was never the problem.
                    # rejection measured off a close that is actually back INSIDE
                    reject_close = min((closes[k] for k in window
                                        if closes[k] <= pool.price), default=closes[i])
                    rejection_pct = (highs[i] - reject_close) / highs[i]
                    if reclaimed and rejection_pct >= 0.002:
                        sweep = LiquiditySweep(
                            pool_price=pool.price,
                            sweep_price=highs[i],
                            kind="high_sweep",
                            rejection_candles=SWEEP_REJECTION_CANDLES,
                            rejection_pct=rejection_pct,
                            confirmed=True,
                            bar_index=i,
                            reclaim_bar_index=_rc_bar,
                            bars_ago=(n - 1 - _rc_bar),
                            timeframe=tf,
                            swept_named_level=pool.name if pool.is_named else "",
                            reclaimed=reclaimed,
                            closes_beyond=closes_beyond
                        )
                        lmap.sweeps.append(sweep)
                        pool.swept = True
                        pool.swept_index = i
                        pool.rejection_confirmed = True

                elif pool.kind == "low" and lows[i] < pool.price and not pool.swept:
                    # A sweep of a LOW requires REJECTION: after poking below the
                    # pool, price must CLOSE BACK ABOVE it (inside) and hold. Closes
                    # that stay BELOW the pool are ACCEPTANCE — a breakdown, not a sweep.
                    window = range(i, min(i + SWEEP_REJECTION_CANDLES + 1, n))
                    # SWP.11: acceptance is counted AFTER the reclaim — see the
                    # high-sweep branch for the measurement and the reasoning.
                    # SWP.11: computed first — see the high-sweep branch.
                    _rc_bar = next((k for k in window
                                    if closes[k] >= pool.price), i)
                    closes_beyond = sum(1 for k in window
                                        if k > _rc_bar and closes[k] < pool.price)
                    reclaimed = closes[i] >= pool.price or any(
                        closes[k] >= pool.price for k in window)
                    # SWP.10: age from the reclaim — see the high-sweep branch.
                    reject_close = max((closes[k] for k in window
                                        if closes[k] >= pool.price), default=closes[i])
                    rejection_pct = (reject_close - lows[i]) / lows[i]
                    if reclaimed and rejection_pct >= 0.002:
                        sweep = LiquiditySweep(
                            pool_price=pool.price,
                            sweep_price=lows[i],
                            kind="low_sweep",
                            rejection_candles=SWEEP_REJECTION_CANDLES,
                            rejection_pct=rejection_pct,
                            confirmed=True,
                            bar_index=i,
                            reclaim_bar_index=_rc_bar,
                            bars_ago=(n - 1 - _rc_bar),
                            timeframe=tf,
                            swept_named_level=pool.name if pool.is_named else "",
                            reclaimed=reclaimed,
                            closes_beyond=closes_beyond
                        )
                        lmap.sweeps.append(sweep)
                        pool.swept = True
                        pool.swept_index = i
                        pool.rejection_confirmed = True

    def _identify_stop_clusters(self, lmap: LiquidityMap,
                                 df: pd.DataFrame, current_price: float):
        if df is None or len(df) < 10:
            return
        recent = df.iloc[-30:] if len(df) >= 30 else df
        highs_above = [float(h) * 1.001 for h in recent["high"].tolist()
                       if float(h) > current_price]
        lmap.stop_clusters_above = sorted(set([round(h, 0) for h in highs_above]))[:5]
        lows_below = [float(l) * 0.999 for l in recent["low"].tolist()
                      if float(l) < current_price]
        lmap.stop_clusters_below = sorted(set([round(l, 0) for l in lows_below]),
                                          reverse=True)[:5]

    def _flag_nearby_pools(self, lmap: LiquidityMap, price: float):
        buffer = price * lmap.near_pool_pct / 100
        for pool in lmap.pools:
            if pool.swept:
                continue
            if pool.kind == "high" and pool.price > price:
                if pool.price - price < buffer:
                    lmap.near_pool_above = pool.price
            elif pool.kind == "low" and pool.price < price:
                if price - pool.price < buffer:
                    lmap.near_pool_below = pool.price

    def is_near_pool(self, lmap: LiquidityMap, price: float,
                     direction: str, buffer_pct: float = 0.003) -> bool:
        for pool in lmap.pools:
            if pool.swept:
                continue
            dist_pct = abs(pool.price - price) / price
            if dist_pct <= buffer_pct:
                if direction == "long" and pool.kind == "high" and pool.price > price:
                    return True
                if direction == "short" and pool.kind == "low" and pool.price < price:
                    return True
        return False

    def recent_sweep_exists(self, lmap: LiquidityMap, max_bars: int = 10) -> bool:
        return lmap.recent_sweep is not None and lmap.sweep_age_bars <= max_bars


_liquidity_mapper: Optional[LiquidityMapper] = None


# ══════════════════════════════════════════════════════════════════════════
# v4.2 — TINES AS MOVING LIQUIDITY LEVELS; A TOUCH IS THE EVENT
# ══════════════════════════════════════════════════════════════════════════
TOUCH_LOOKBACK_BARS = 30        # 1m bars searched for a touch (SELECTION)
_TF_MINUTES_WALL = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "1d": 390}


def _rail_slope_per_min(slope_per_bar: float, tf: str) -> float:
    return float(slope_per_bar or 0.0) / float(_TF_MINUTES_WALL.get(tf, 60))


def publish_tines(lmap: LiquidityMap, ctm, df_1m) -> int:
    """Put every active fork tine on the liquidity map as a MOVING named pool
    and detect TOUCHES of it on the 1m tape. Returns the number of touch
    events emitted. Never raises.

    ⚠️ THE RAIL IS EVALUATED WHERE IT WAS ON EACH BAR. `price_at(bar_ts)`
    walks the slope back in wall minutes; a bar that would reach today's
    value of the rail but did not reach the rail as it stood then is NOT a
    touch. That is the "slope and time" the operator named.
    """
    try:
        if lmap is None or ctm is None:
            return 0
        rails = list(ctm.all_rails())
    except Exception:                                          # noqa: BLE001
        return 0
    if not rails:
        return 0
    try:
        now_ts = float(df_1m.index[-1].timestamp()) if df_1m is not None and len(df_1m) else time.time()
    except Exception:                                          # noqa: BLE001
        now_ts = time.time()
    emitted = 0
    # drop yesterday's tine pools/touches before re-publishing this tick's
    lmap.pools = [p for p in lmap.pools if not getattr(p, "moving", False)]
    lmap.sweeps = [sw for sw in lmap.sweeps if not getattr(sw, "moving", False)]
    for r in rails:
        try:
            tf = str(getattr(r, "tf", "") or "")
            side = str(getattr(r, "side", "") or "")
            rail = float(getattr(r, "rail", 0.0) or 0.0)
            slope = _rail_slope_per_min(getattr(r, "slope", 0.0), tf)
        except Exception:                                      # noqa: BLE001
            continue
        if rail <= 0 or side not in ("call", "put"):
            continue
        kind = "high" if side == "call" else "low"
        name = f"{tf} {'upper' if side == 'call' else 'lower'} tine"
        pool = LiquidityPool(price=round(rail, 4), kind=kind, timeframe=tf,
                             name=name, is_named=True, moving=True,
                             slope_per_min=slope, as_of=now_ts)
        lmap.pools.append(pool)
        ev = _detect_touch(pool, df_1m, now_ts)
        if ev is not None:
            lmap.sweeps.append(ev)
            emitted += 1
            if lmap.recent_sweep is None or ev.bars_ago < getattr(lmap.recent_sweep, "bars_ago", 999):
                lmap.recent_sweep = ev
    return emitted


def _detect_touch(pool: LiquidityPool, df_1m, now_ts: float) -> Optional[LiquiditySweep]:
    """A TOUCH of a moving level on the last TOUCH_LOOKBACK_BARS 1m bars.

    upper tine: a bar's HIGH >= rail(t)  ·  lower tine: a bar's LOW <= rail(t)
    sweep_price = the EXTREME of the touching move (the strike goes beyond it)
    invalidated = ACCEPT_CLOSES closes beyond rail(t) since the FIRST touch
    bars_ago    = bars since the LAST touch
    """
    try:
        if df_1m is None or len(df_1m) < 2:
            return None
        df = df_1m.tail(TOUCH_LOOKBACK_BARS)
        highs = df["high"].astype(float).tolist()
        lows = df["low"].astype(float).tolist()
        closes = df["close"].astype(float).tolist()
        stamps = [float(t.timestamp()) for t in df.index]
    except Exception:                                          # noqa: BLE001
        return None
    upper = pool.kind == "high"
    first = last = -1
    extreme = None
    beyond = 0
    for i, ts in enumerate(stamps):
        lvl = pool.price_at(ts)
        hit = highs[i] >= lvl if upper else lows[i] <= lvl
        if hit:
            if first < 0:
                first = i
            last = i
            ex = highs[i] if upper else lows[i]
            extreme = ex if extreme is None else (max(extreme, ex) if upper else min(extreme, ex))
        if first >= 0:
            if (closes[i] > lvl) if upper else (closes[i] < lvl):
                beyond += 1
    if first < 0:
        return None
    n = len(stamps)
    level_now = pool.price
    px = closes[-1] or level_now
    pierce = abs(float(extreme) - level_now) / px if px else 0.0
    return LiquiditySweep(
        pool_price=round(level_now, 4),
        sweep_price=round(float(extreme), 4),
        kind="high_sweep" if upper else "low_sweep",
        rejection_candles=0,
        rejection_pct=round(pierce, 6),
        confirmed=True,
        bar_index=first,
        reclaim_bar_index=last,
        bars_ago=(n - 1) - last,
        timeframe=pool.timeframe,
        swept_named_level=pool.name,
        reclaimed=True,                 # the TOUCH is the trigger
        closes_beyond=0,
        invalidated=beyond >= _ACCEPT_CLOSES,
        closes_beyond_live=beyond,
        touch=True,
        moving=True,
    )


def get_liquidity_mapper() -> LiquidityMapper:
    global _liquidity_mapper
    if _liquidity_mapper is None:
        _liquidity_mapper = LiquidityMapper()
    return _liquidity_mapper
