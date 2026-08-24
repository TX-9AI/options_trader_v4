"""
risk/session_guard.py  v4.2
v4.2  2026-08-24  r102: can_enter(rehearsal=True) evaluates every gate instead
      of short-circuiting at RTH, so the outside-RTH dispatch pass reaches the
      strategies. The verdict stays honest — outside RTH a pass is reported as
      "rehearsal", never as permission, and placement is refused at the order
      choke points, not here.

v4.1  2026-08-21  r60: the unauthorized global 14:00 entry cutoff deleted;
      butterfly keeps its own reviewed cutoff. See the doctrine at the site.
RTH gating and session boundaries.

v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

risk/session_guard.py — Session boundary enforcement.
DOC SYNC (no logic change). The header claimed a 3:00 PM ET
        butterfly cutoff. That was never reachable (main.py never passes
        is_butterfly=True) and 14:00 is the intended rule; config v3.1 sets
        BUTTERFLY_ENTRY_CUTOFF_ET = (14, 0) to match live behaviour.
ORB-formation lockout: no entries until the 9:30–9:35 ET
        opening-range candle has CLOSED (is_orb_complete → time >= 9:35:00).
        Universal floor across ALL strategies that guarantees nothing fires
        during the opening candle (9:30:00–9:34:59). Closes the sweep-reversal
        hole specifically: the sweep's ORB-break gate returns True while the
        range is still unestablished — i.e. exactly this window — so without
        this floor a sweep could pass can_enter() and fire pre-9:35. The gate
        is a FLOOR, not a delay: it opens the instant the range candle closes
        (9:35:00 sharp), so a break registered on/after that close is
        unaffected and every strategy that hinges on the opening-range candle
        still fires on time.
v1.0 — original release
use BUTTERFLY_ENTRY_CUTOFF_ET from config (15:00)
        instead of hardcoded 15:30
repo-wide v3.0 bump: Yahoo-Finance purge & data stream
        mapping optimization (all market data now flows from the single
        shared TastyTrade candle feed — see data/candle_feed.py). No logic
        change in this file.
Entry gates (evaluated in order; first failing gate blocks):
  - RTH — 9:30–16:00 ET, weekdays
  - ORB-formation lockout — no entries before 9:35 ET (opening range must close)
  - Hard close — no new entries at/after 15:45 ET
  - Entry cutoff — 2:00 PM ET for ALL strategies (butterfly included, v3.1:
    BUTTERFLY_ENTRY_CUTOFF_ET is now 14:00). Post-14:00 tape turns erratic on
    dealer hedging. NOTE: main.py calls can_enter() without is_butterfly=True,
    so that branch is inert; it is retained only as a future hook.
  - Macro — VIX-crisis lockout
"""

import logging
from typing import Optional
from datetime import datetime, time as dtime

from utils.time_utils import (
    is_rth, is_orb_complete, is_hard_close_time,
    now_et, fmt_et_short, seconds_until_rth_open
)
from data.macro_data import MacroSnapshot
from config import BUTTERFLY_ENTRY_CUTOFF_ET

logger = logging.getLogger(__name__)

# Convert config tuple (15, 0) to time object
_BUTTERFLY_CUTOFF = dtime(BUTTERFLY_ENTRY_CUTOFF_ET[0], BUTTERFLY_ENTRY_CUTOFF_ET[1])


class SessionGuard:
    """
    Gate keeper for all session-level rules.
    Called at the start of each attempt_new_entry() loop.
    """

    def can_enter(self, macro: Optional[MacroSnapshot] = None,
                  is_butterfly: bool = False,
                  rehearsal: bool = False) -> tuple:
        """
        Check all pre-entry gates.

        Args:
            macro:        Current macro snapshot
            is_butterfly: True for butterfly — allowed until BUTTERFLY_ENTRY_CUTOFF_ET
            rehearsal:    r102 — evaluate EVERY gate instead of stopping at the
                          RTH one, for the outside-RTH dispatch pass. The verdict
                          is still honest: a rehearsal that would be blocked
                          reports blocked, and the RTH refusal is reported LAST
                          so the caller learns what else would have stopped it.

        Returns:
            (allowed: bool, reason: str)
        """
        # ── RTH gate ──────────────────────────────────────────────────────────
        # 🔴 r102 — THIS LINE ENDED THE REHEARSAL ONE CALL SHORT OF ANYTHING
        # WORTH REHEARSING. r101 ran the dispatch outside RTH so a never-called
        # path would surface at 07:40 instead of 09:30:01; the pass reached
        # here, took the short-circuit, and returned at DEBUG. Measured on all
        # 15 boxes 2026-08-24 16:53: decided=0 chain=0 — the pass was running
        # and proving nothing.
        # ⚠️ THE SHORT-CIRCUIT IS RIGHT FOR TRADING AND WRONG FOR REHEARSING.
        # Under `rehearsal` the remaining gates are evaluated and reported; the
        # RTH refusal is appended rather than substituted, so nothing reads a
        # rehearsal as permission. ORDER PLACEMENT IS NOT GATED HERE AT ALL —
        # it is refused at the two order choke points, which check is_rth()
        # themselves. A gate that says "no" is not what stops a fill; the
        # choke point is.
        # ⚠️ ONLY THE CLOCK GATES ARE DEFERRED. A rehearsal exists precisely
        # because the session is not running, so "outside RTH" and "past the
        # hard close" are the two refusals it cannot honour and still test
        # anything. They are COLLECTED and reported, never dropped. Every other
        # gate below stays terminal — the 09:35 floor, the butterfly cutoff and
        # the VIX crisis gate refuse a rehearsal exactly as they refuse a
        # trading pass, because those are the answers we want tested.
        _noted: list = []
        if not is_rth():
            if not rehearsal:
                return False, f"outside RTH ({fmt_et_short()})"
            _noted.append("outside RTH")

        # ── ORB-formation lockout ─────────────────────────────────────────────
        # No entries until the 9:30–9:35 ET opening-range candle has CLOSED.
        # This is the universal floor for EVERY strategy: the ORB itself cannot
        # fire pre-9:35 (no established range), but the sweep reversal otherwise
        # could — its ORB-break gate (_sweep_broke_orb) returns True while the
        # range is unestablished, i.e. exactly this window. is_orb_complete() is
        # True at >= 9:35:00, so this OPENS the gate the instant the opening
        # candle closes and never delays a break registered on/after that close.
        if not is_orb_complete():
            return False, f"opening range still forming (<9:35 ET) — no entries ({fmt_et_short()})"

        # ── Hard close ────────────────────────────────────────────────────────
        if is_hard_close_time():
            if not rehearsal:
                return False, "past 15:45 ET hard close — no new entries"
            _noted.append("past the hard close")

        # ── Entry cutoff ──────────────────────────────────────────────────────
        # r60 (2026-08-21): the GLOBAL 14:00 block is DELETED — an unauthorized
        # v3 hardcode (full provenance in config.py) that silently vetoed every
        # strategy's afternoon, logged only at DEBUG, and helped produce the
        # 15-box zero-trade session of 2026-08-21. Each structure's own
        # operator-set window bounds entries now, as designed. The butterfly's
        # cutoff below is ITS OWN reviewed constant and stays.
        if is_butterfly and now_et().time() >= _BUTTERFLY_CUTOFF:
            return False, f"past {_BUTTERFLY_CUTOFF.strftime('%H:%M')} ET butterfly cutoff"

        # ── Macro gates ───────────────────────────────────────────────────────
        if macro and not macro.new_entries_allowed:
            return False, f"VIX crisis ({macro.vix:.1f}) — no new entries"

        # r102 — every substantive gate passed. If any CLOCK gate was deferred,
        # this is a REHEARSAL PASS and never a permission: the reason names each
        # deferral so neither a caller nor a log reader can mistake the two.
        if _noted:
            return True, ("rehearsal (%s — %s)"
                          % (", ".join(_noted), fmt_et_short()))

        return True, ""

    def must_close_all(self) -> bool:
        return is_hard_close_time()

    def seconds_to_open(self) -> float:
        return seconds_until_rth_open()

    def log_session_state(self, macro: Optional[MacroSnapshot] = None):
        allowed, reason = self.can_enter(macro)
        logger.info(
            f"Session [{fmt_et_short()}]: "
            f"rth={is_rth()} "
            f"entry={'OK' if allowed else 'BLOCKED: ' + reason} "
            f"hard_close={is_hard_close_time()} "
            f"vix={macro.vix:.1f if macro else 'N/A'} "
            f"fed_day={macro.is_fed_day if macro else False}"
        )


_session_guard: Optional[SessionGuard] = None


def get_session_guard() -> SessionGuard:
    global _session_guard
    if _session_guard is None:
        _session_guard = SessionGuard()
    return _session_guard
