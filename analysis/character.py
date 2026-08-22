"""
analysis/character.py  v4.0
The tape's CHARACTER — two measured axes, a state, and a duration.

v4.0  2026-08-25  Operator's design. Named CHARACTER deliberately: if the idea
of describing the tape is revived it does so under a word that cannot be
mistaken for the retired artifact.

    trending · ranging · compressing · volatile

🔴 CHARACTER IS A STATE WITH DURATION. AN EVENT IS A MOMENT.
Operator, 2026-08-25: "a sweep is an event, not a character. Breakouts are
events, not character. Volatile is the character."

⚠️ THE OLD SYSTEM COLLAPSED THIS AND IT COST REAL ANALYSIS. SWEEP_REVERSAL and
BREAKOUT_VOLATILE sat in the same six-way argmax as RANGING and COMPRESSION, so
an EVENT and a STATE competed for one slot — SWEEP ended at 0.4% of live ticks,
effectively not participating. And the acceptance work hit the same wall from
the other side: comparing a single-event tag to a session-modal label is a
category error.

**They coexist, and that is informative.** A sweep happens DURING a ranging
tape; a breakout happens OUT OF a compressed one. Events already have homes
(level_ledger, plan_ledger, prints). Character gets its own and displaces
nothing.

🔴 NO SCORING. NO CONVICTION. NO CONSENSUS.
Operator's explicit boundary. **The specific temptation to refuse: combining
the two axes into one strength number is `_combine()` reappearing under a new
name.** The axes stay separate and are reported separately. Scoring comes
later, fitted on derivatives with an honest discretionary split, and even then
it will address POSITION SIZE — not gates.

⚠️ TWO AXES, NOT FOUR BUCKETS. A market can be trending AND compressing (an
orderly grind) or ranging AND volatile (a violent chop). Four exclusive labels
cannot express that; the state name below is a CONVENIENCE READING of the two
axes, never the primitive.

⚠️ NEVER A BOOLEAN VETO. The v3 grammar was multiplicative, so one veto at zero
annihilated a score and DESTROYED THE ORDERING — 41.9% of ticks had nothing to
rank. Everything here is continuous.

🔑 ADX AND ATR RUN PARALLEL, NOT FEEDING — operator's ruling.
They map naturally onto the axes (ADX to persistence, ATR to volatility) and
are RECORDED ALONGSIDE so a study can ask whether they agree. **Blending them
in would make agreement true by construction**, which is the circularity WA §31
exists to prevent. There is also a live reason for caution: ADX swung 16 → 48
on the same symbols across ticks on 2026-08-21, and whether that is market or
Wilder-window artifact is UNSETTLED. Feeding an unresolved wobble into
character would manufacture the churn the acceptance gate exists to catch.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Axis boundaries. Provisional and flagged as such. ────────────────────────
# ⚠️ THESE ARE STARTING POINTS FOR A MEASUREMENT, NOT FITTED PARAMETERS. The
# acceptance gate (1-3 changes per symbol-day, the operator's 20-year prior) is
# what says whether they are right. Do NOT tune them to produce a pleasing
# number — that is fitting, and it is what the old system did.
PERSIST_TREND = 0.62      # travel/range at or above this reads as directional
PERSIST_RANGE = 0.38      # at or below, price is moving without going anywhere
VOL_EXPAND = 1.25         # short-window vol vs its own baseline
VOL_COMPRESS = 0.80

# Hysteresis. From the v3 F7 result: protect-below-hold ALONE landed 3.3
# switches/symbol-day with NO dwell and NO tuning, validated 20.8 -> 4.2 on
# real tape. ⚠️ DWELL IS DELIBERATELY ABSENT — dwell 8+ started deleting real
# genuine state changes, and adding it is fitting.
DISPLACE_MARGIN = 0.10    # a challenger must clear the incumbent's band by this


def persistence(rv_cc: Optional[float],
                rv_parkinson: Optional[float]) -> Optional[float]:
    """Directional persistence in [0, 1]. None when not measurable.

    🔴 THE DISCRIMINATOR THAT WAS UNAVAILABLE UNTIL r61.
      · Parkinson uses the high/low RANGE — how far price travelled in total.
      · Close-to-close uses NET TRAVEL — how far it actually got.
    Range large, net travel small => price is moving without going anywhere,
    which IS ranging, measured rather than asserted. The two converging means
    travel was directional.

    ⚠️ RETURNS None, NEVER 0.5, WHEN EITHER SIDE IS MISSING. A midpoint would
    assert "equally trending and ranging", which is a real reading and a
    completely different claim from "we could not measure".
    """
    if rv_cc is None or rv_parkinson is None:
        return None
    if rv_parkinson <= 0:
        return None
    r = float(rv_cc) / float(rv_parkinson)
    return max(0.0, min(1.0, r))


def volatility_state(rv_now: Optional[float],
                     rv_baseline: Optional[float]) -> Optional[float]:
    """Volatility RELATIVE TO ITS OWN RECENT BASELINE. None if unmeasurable.

    ⚠️ RELATIVE, NOT ABSOLUTE, AND THAT IS THE POINT. TSLA at 45% annualised is
    calm for TSLA; UNH at 45% is a crisis. An absolute threshold would label
    every high-beta name permanently volatile and every index permanently
    compressed, which is a statement about the symbol, not the tape.
    """
    if rv_now is None or rv_baseline is None or rv_baseline <= 0:
        return None
    return float(rv_now) / float(rv_baseline)


def read_character(persist: Optional[float],
                   vol_ratio: Optional[float]) -> Optional[str]:
    """A convenience NAME for the two axes. NEVER the primitive.

    ⚠️ THE AXES ARE THE MEASUREMENT; THIS IS A READING OF THEM. Anything that
    needs nuance reads the axes. The name exists so a human glancing at
    status.py gets one word.

    ⚠️ VOLATILE OUTRANKS THE PERSISTENCE READ, deliberately: a violently
    expanding tape is volatile whether or not it is going anywhere, and that is
    the operator's own usage — "volatile is the character".
    """
    if persist is None and vol_ratio is None:
        return None
    if vol_ratio is not None and vol_ratio >= VOL_EXPAND:
        return "volatile"
    if vol_ratio is not None and vol_ratio <= VOL_COMPRESS:
        return "compressing"
    if persist is None:
        return None
    if persist >= PERSIST_TREND:
        return "trending"
    if persist <= PERSIST_RANGE:
        return "ranging"
    # Between the bands is a real, nameless middle. ⚠️ IT IS NOT FORCED INTO A
    # BUCKET — the old grammar's argmax always produced a winner even when
    # there was nothing to choose between, and that is how a near-random label
    # got traded.
    return None


def qualifies_to_displace(incumbent: Optional[str], challenger: Optional[str],
                          persist: Optional[float],
                          vol_ratio: Optional[float]) -> bool:
    """Hold the incumbent unless the challenger CLEARLY qualifies.

    🔴 THE v3 F7 LESSON, TRANSPLANTED. That engine had a protected branch and
    an UNPROTECTED one: below the hold threshold it took bare argmax every
    tick, no commit, no margin, no dwell — and that path produced **96.9% of
    all label switches**, with the median switch handing off between two
    near-zero beliefs. Applying protect-below-hold in BOTH branches landed
    3.3 switches/symbol-day, inside the operator's stated prior, from REMOVING
    A DEFECT rather than tuning a parameter.

    ⚠️ THE MARGIN IS ON THE AXIS, NOT ON A SCORE. There is no score here to
    compare. A challenger qualifies when the underlying measurement has moved
    clear of the boundary that produced the incumbent — so a value hovering ON
    a boundary cannot flip the state back and forth.
    """
    if challenger is None:
        return False
    if incumbent is None:
        return True
    if challenger == incumbent:
        return False
    if challenger == "volatile":
        return vol_ratio is not None and vol_ratio >= VOL_EXPAND + DISPLACE_MARGIN
    if challenger == "compressing":
        return vol_ratio is not None and vol_ratio <= VOL_COMPRESS - DISPLACE_MARGIN
    if challenger == "trending":
        return persist is not None and persist >= PERSIST_TREND + DISPLACE_MARGIN
    if challenger == "ranging":
        return persist is not None and persist <= PERSIST_RANGE - DISPLACE_MARGIN
    return False
