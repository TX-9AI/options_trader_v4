"""
analysis/market_state.py  v4.0
Structural market state and the regime vocabulary. No scoring, no gating.

v4.0  2026-08-19  Built at the OTV4 split, replacing analysis/regime_classifier.py.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

WHY THIS MODULE EXISTS.
`regime_classifier.py` had fan-in 12 - third highest in the whole codebase,
behind only config.py and time_utils. It could not simply be deleted. But the
file map showed the shape of the dependency: EIGHT OF ITS NINE IMPORTERS WANTED
ONLY `RegimeState` AND `Regime` - the dataclass and the enum. Two called the
classifier.

So the cut is: KEEP THE TYPES, DROP THE SCORING.

WHAT WAS MEASURED, AND WHY THE SCORING IS GONE.
`tests/direction_skill.py`, 2026-08-19, 715 closed directional trades over 16
sessions with ORB and neutral structures excluded: the classifier picked the
correct SIDE on 44.9% of them, 95% CI [41.3%, 48.6%] - the interval sits
ENTIRELY BELOW A COIN FLIP. Calls 48.7%; puts 34.2%, CI [28%, 41%]. The strategy
most dependent on it lost $5,872 across 660 trades.
A blind read of six random tapes agreed: two of six were directionally BACKWARDS
on the largest moves in the sample.

WHAT SURVIVES AND WHY.
Most of `RegimeState` was never a regime at all - it was a CARRIER for
structural facts computed elsewhere: adx, atr_normalized, bb_width_pct,
trend_direction, structure_sequence, sweep_recent, flat_angle_deg,
sweep_age_bars, vix_regime, timeframe_alignment. Those are exactly the inputs
v4 is built on and they pass through untouched.

`Regime` - the six-label vocabulary - survives DELIBERATELY. Operator, 2026-08-19:
labels "must be predicated on structure above all else & shaped by the other
available cues", and they INFORM rather than authorise. A setup may read one.
NO SETUP MAY REQUIRE ONE. The labels themselves are rebuilt from structure in
ROADMAP Phase 4.1; this module only holds the vocabulary and the slot.

⚠️ `conviction` IS RETAINED FOR NOW AND IS ON ITS WAY OUT. 49 live reads across
8 files. Removing the field outright would mean one large blind edit with
nothing importable until every site was fixed - and no way to test any of it
until all of it compiled. It stays, defaulted and unused by anything in this
module, so the reads can be removed FILE BY FILE with tests passing at each
step. **It must not be reintroduced as a gate.** See ROADMAP Phase 0.3.
"""

from dataclasses import dataclass, field
from typing import Dict


class Regime:
    """The vocabulary. Descriptive labels, never an authorisation.

    ⚠️ These names are carried from v3 unchanged so that historical journals,
    trade rows and replay logs remain readable against v4 code. **The names
    survive; the way they were COMPUTED does not** - v3 derived them from a
    damper x corroborator confluence score whose every scoring defect is
    catalogued in docs/INHERITED_FINDINGS.md. v4 derives them from structure
    (ROADMAP Phase 4.1).
    """
    TRENDING_BULL = "TRENDING_BULL"
    TRENDING_BEAR = "TRENDING_BEAR"
    RANGING = "RANGING"
    BREAKOUT_VOLATILE = "BREAKOUT_VOLATILE"
    COMPRESSION = "COMPRESSION"
    SWEEP_REVERSAL = "SWEEP_REVERSAL"
    UNKNOWN = "UNKNOWN"

    ALL = (TRENDING_BULL, TRENDING_BEAR, RANGING, BREAKOUT_VOLATILE,
           COMPRESSION, SWEEP_REVERSAL, UNKNOWN)


@dataclass
class MarketState:
    """Structural facts about the tape, plus a descriptive label slot.

    ⚠️ THIS IS A CARRIER, NOT A CLASSIFIER. Nothing in this module computes a
    label or a score. The fields below are produced by the engines that own them
    - volatility_engine (atr, bb), trend_engine (adx, direction),
    structure_analyzer (sequence), liquidity_mapper (sweep) - and gathered here
    so a consumer has one object to read.
    """

    # ── the descriptive label ────────────────────────────────────────────────
    # ⚠️ INFORMS, NEVER AUTHORISES. A setup may read this. No setup may require
    # it. In v3 this label gated entries and picked the wrong side 55% of the
    # time.
    primary_regime: str = Regime.UNKNOWN

    # ⚠️ ON ITS WAY OUT - DO NOT ADD NEW READS. Retained only so the 49 existing
    # reads can be removed file by file with tests passing at each step. It was
    # confirmatory by construction: a leaky integrator over argmax agreement is
    # only confident once winning has already persisted.
    conviction: float = 0.0
    trend_conviction: float = 0.0

    # ── structural facts, computed elsewhere and carried here ────────────────
    macro_context: str = "NEUTRAL"
    adx: float = 0.0
    atr_normalized: float = 0.0
    bb_width_pct: float = 0.5
    trend_direction: str = "NEUTRAL"
    structure_sequence: str = "NEUTRAL"
    sweep_recent: bool = False
    sweep_age_bars: int = 999
    vix_regime: str = "UNKNOWN"
    timeframe_alignment: Dict[str, str] = field(default_factory=dict)

    # ⚠️ NEGATIVE MEANS "NOT COMPUTED", NOT "FLAT". Zero degrees IS the flattest
    # possible reading, so a 0.0 default is indistinguishable from a genuinely
    # flat tape - the exact confusion that made this column read as 100% ties on
    # ONE unique value in v3 and be scored as a measured null when it was simply
    # never written. See INHERITED_FINDINGS 3.
    flat_angle_deg: float = -1.0

    # ── provenance ───────────────────────────────────────────────────────────
    classified_at: str = ""
    trigger: str = "scheduled"
    notes: str = ""


# ⚠️ BACK-COMPAT ALIAS, DELIBERATE AND TEMPORARY. Eight modules import
# `RegimeState` by name. Aliasing here lets the repo import while those call
# sites are updated one at a time; renaming all of them in a single edit would
# be a large blind change with nothing testable until every file compiled.
# Remove once the last importer reads `MarketState` directly.
RegimeState = MarketState
