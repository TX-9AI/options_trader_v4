"""
utils/blindness_latch.py  v4.1
Latches and alerts when the bot is flying blind.

v4.1  2026-10-09  r477 / BLIND.1 — AN OPEN GRACE: NO OUTAGE CLOCK BEFORE 09:32 ET. CVX paged
      "BOT IS BLIND" at 09:31 on 10-08 and 10-09 and healed itself 61 s later: the vendor sent
      no regular-hours 09:30 candle for CVX (its first was 09:31) while UNH and CRM got one, and
      at 09:30 the newest regular-hours bar is the prior day's 15:59, so every box reads stale
      until its first bar; CVX's late one crossed the 45 s page threshold. The feed was alive
      (CVX_EXT had a 09:29 bar). Operator: start the check later; "I just don't want it screwing
      up our opening range measurement" — so the grace lives HERE, in the alert decision, and
      market_data (which serves the bars) is untouched. Between 09:30 and OPEN_GRACE_UNTIL_ET
      (09:32, OT_BLIND_OPEN_GRACE) a blindness record is treated as sight: no outage clock, no
      page. A feed still blind at 09:32 starts its clock then and pages at the usual threshold
      (~09:32:45). 🔑 STILL THE SYMPTOM, NOT A CAUSE LIST: the grace is scoped by TIME, never
      by cause. Entries are blocked until 09:35 regardless. Pinned by
      tests/check_blind_open_grace.py — the first test in otv4 to drive this latch at all
      (the test this header names below, tests/test_blindness_latch.py, was never ported).
v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

options_trader_v3/utils/blindness_latch.py — 
WHEN TO PAGE THE OPERATOR BECAUSE THE BOT CANNOT SEE.
The requirement (2026-08-01): if ANY condition blinds the bot — the feed going
down, stale data, a dead heartbeat, or anything else — notify immediately, and
log the exact conditions that caused it.
Two things follow from "anything else", and they shape this file:
  1. The trigger is the SYMPTOM, not a list of causes. Every return-None path in
     market_data funnels through record_blindness(); this latch reads that record
     and never re-derives a cause of its own. A cause list could only ever cover
     the failures already thought of, and the whole point is the ones we haven't.
  2. The forensic snapshot is taken at the FIRST blind tick and held. The latch
     deliberately waits a few ticks before paging, so by the time it fires the
     conditions have often moved — a feed that reconnects mid-outage would
     otherwise report healthy fields alongside an alert, which is the worst
     possible troubleshooting record. First moment wins; later ticks only extend
     the duration.
Lives apart from main.py on purpose: main.py is not importable in the test
environment (SDK, env, systemd), and an alarm nobody can unit-test is an alarm
nobody should trust. See tests/test_blindness_latch.py.
This module decides ONLY when to alert. It sends nothing and reads nothing —
callers pass the blindness record in and act on the returned verdict.
"""

from __future__ import annotations

import os
import time as _time
from typing import Dict, Optional

# Consecutive blind ticks before paging. One transient read failure should not
# reach the operator's phone; a real outage will hold across several. Kept small
# because with 0DTE and live capital, minutes matter.
BLIND_TICKS_BEFORE_ALERT = int(os.environ.get("OT_BLIND_TICKS", "3"))
# Floor on elapsed time as well as tick count, so a fast tick loop cannot page on
# a sub-second flicker.
BLIND_SECONDS_BEFORE_ALERT = float(os.environ.get("OT_BLIND_SECONDS", "45"))

ALERT = "ALERT"
RECOVERED = "RECOVERED"

# r477 / BLIND.1 — the open grace. At 09:30 the newest regular-hours bar is the prior
# session's, so every box reads stale until its first bar prints; a late first print
# (CVX, 10-08 and 10-09) paged for a feed that was alive. HH:MM, ET.
_g = os.environ.get("OT_BLIND_OPEN_GRACE", "09:32").strip()
try:
    OPEN_GRACE_UNTIL_ET = (int(_g.split(":")[0]), int(_g.split(":")[1]))
except (ValueError, IndexError):
    OPEN_GRACE_UNTIL_ET = (9, 32)
_OPEN_ET = (9, 30)


def _in_open_grace(now: float) -> bool:
    """True from 09:30 up to OPEN_GRACE_UNTIL_ET, US Eastern, by the latch's own clock."""
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        t = datetime.fromtimestamp(now, ZoneInfo("America/New_York"))
    except Exception:                                          # noqa: BLE001
        return False                                           # unreadable clock -> no grace (loud side)
    return _OPEN_ET <= (t.hour, t.minute) < OPEN_GRACE_UNTIL_ET


class BlindnessLatch:
    """Feed it every tick. It returns ALERT once per outage, RECOVERED once when
    sight comes back, and None the rest of the time."""

    def __init__(self, ticks_before_alert: int = BLIND_TICKS_BEFORE_ALERT,
                 seconds_before_alert: float = BLIND_SECONDS_BEFORE_ALERT):
        self._ticks_needed = max(1, ticks_before_alert)
        self._seconds_needed = max(0.0, seconds_before_alert)
        self._blind_ticks = 0
        self._blind_since: Optional[float] = None
        self._first_snapshot: Optional[Dict] = None
        self._alerted = False
        # Preserved ACROSS the reset so the recovery notice can still say how
        # long the outage lasted and what caused it. Without this, _reset()
        # wipes the duration a beat before the caller reports it — the recovery
        # message would read "was blind 0s", which is the one number it exists
        # to carry.
        self.last_outage_s: float = 0.0
        self.last_outage_cause: str = ""

    # ── state the caller reports on ──────────────────────────────────────────
    @property
    def snapshot(self) -> Optional[Dict]:
        """The record captured at the FIRST blind tick of this outage."""
        return self._first_snapshot

    def blind_for_s(self, now: Optional[float] = None) -> float:
        if self._blind_since is None:
            return 0.0
        return (now if now is not None else _time.time()) - self._blind_since

    @property
    def is_alerted(self) -> bool:
        return self._alerted

    # ── the one call the tick loop makes ─────────────────────────────────────
    def update(self, blindness: Optional[Dict],
               now: Optional[float] = None) -> Optional[str]:
        """`blindness` is market_data.last_blindness() — None means the bot can
        see. Returns ALERT, RECOVERED, or None.

        ALERT is returned at most once per outage. RECOVERED is returned only if
        an ALERT was actually sent, so a brief blip that never paged does not
        produce an all-clear for an alarm the operator never received.
        """
        now = now if now is not None else _time.time()

        # r477 / BLIND.1 — before 09:32 ET a blindness record starts no outage clock.
        if blindness is not None and _in_open_grace(now):
            blindness = None

        if blindness is None:
            if self._alerted:
                self.last_outage_s = self.blind_for_s(now)
                self.last_outage_cause = (self._first_snapshot or {}).get("cause", "")
                self._reset()
                return RECOVERED
            self._reset()
            return None

        if self._blind_since is None:
            # first blind tick of this outage — capture and hold
            self._blind_since = now
            self._first_snapshot = dict(blindness)
        self._blind_ticks += 1

        if self._alerted:
            return None
        if (self._blind_ticks >= self._ticks_needed
                and (now - self._blind_since) >= self._seconds_needed):
            self._alerted = True
            return ALERT
        return None

    def _reset(self):
        self._blind_ticks = 0
        self._blind_since = None
        self._first_snapshot = None
        self._alerted = False
