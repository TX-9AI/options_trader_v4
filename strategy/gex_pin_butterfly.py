"""
strategy/gex_pin_butterfly.py  v4.0
Butterfly centred on the GEX pin. PARKED - the signal it needs does not exist
in any archive yet.

v4.0  2026-08-19  Written at the OTV4 split. NOT ENABLED. See PARKED below.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

════════════════════════════════════════════════════════════════════════════
⚠️ PARKED 2026-08-19. DO NOT ENABLE THIS UNTIL THE GEX DATA IS REAL.
════════════════════════════════════════════════════════════════════════════
`OptionContract.open_interest` was a DECLARED FIELD WITH NO PRODUCER - 0 on
every contract for the life of v3. `gex_data` therefore fell through to
`oi_proxy = max(1, int(1000 * gamma))` and multiplied by gamma AGAIN, so:

        **GEX ~ 100,000 * gamma^2 * spot**

**Every GEX number this project has ever produced is a gamma-SQUARED surface,
not dealer positioning.** Confirmed on the live SPX box, 2026-08-19:
  · 542 of 542 contracts in the day's final chain snapshot carried `"oi": 0`
  · the bot log showed `pin = call_wall = $7725` with SPOT SITTING ON IT -
    gamma peaks at the money, so a gamma-squared surface always "pins" wherever
    price already is. It was not finding a magnet; it was reporting the price.
  · GEX ran **12.4M -> 0.1M -> 2.0M in three minutes**, flipping PINNING to
    NEUTRAL and back inside 90 seconds. A pin with a 90-second half-life is not
    a pin.

OI.1 (2026-08-19) wires real open interest over REST into BOTH repos, and
`pin_concentration` is now recorded in the chain snapshot. **Roughly two weeks
of collection are needed before any threshold below can be validated**, because
the archive cannot be reconstructed - the zeros are already written.

⚠️ AND THE THRESHOLDS BELOW WILL BE WRONG. `GEX_PIN_CONCENTRATION = 0.15` was
tuned against the gamma-squared surface. Real OI is orders of magnitude larger
and differently distributed, so the number that meant "concentrated" for
gamma^2 means nothing for actual positioning. **Every constant here is a STATED
PRIOR awaiting measurement, not a calibration.**

════════════════════════════════════════════════════════════════════════════
WHY THE SETUP IS WORTH WRITING ANYWAY
════════════════════════════════════════════════════════════════════════════
It is the one entry in the book where **the chain names the target**. Every
other setup has to infer where price is going; a gamma pin is a claim about
where dealers must hedge, which is positional rather than predictive. That
matters because four independent searches failed to find ANY directional
predictor in this data - entry conditions (all ambient), recorded columns
(gates or empty), opening bias (a coin, forward-only, 797 sessions), and the
tape harness (every surviving condition helped UP *and* DOWN). **A butterfly
needs no direction at all.**

⚠️ AND THE ATR LOGIC INVERTS HERE. `RunawayContinuation` needs ATR HIGH enough
that price can reach a strike. **A butterfly is SHORT volatility: it needs ATR
LOW enough that price STAYS.** The same reachability table read backwards -
from `tests/magnitude_estimator.py`, 52,949 bars:

    ATR%        0.5% move within 90 bars        butterfly reading
    < 0.05           ~0%                        ideal - price cannot leave
    0.05-0.08        11%                        good
    0.08-0.12        30%                        marginal
    0.12-0.20        60%                        hostile
    > 0.20           92%                        do not trade

That is the SAME measurement that vetoes the runaway trade below 0.08%, used in
the opposite direction. The tape harness agrees from a different angle: the base
rate for a 0.5% move in 90 minutes is **24-35%**, so roughly two thirds of
windows stay inside it. **The butterfly sells the side that is usually right.**

⚠️ THE RISK IS THE OTHER THIRD, AND IT IS NOT SYMMETRIC. A butterfly's loss is
capped at the debit, which is why it is written here rather than a short
straddle - v3's condor doctrine records that a leg must never be closed on a
profit target because the backtest showed TP was WORSE at every level (18 legs:
TP@25% turned -$242.77 into -$8.43; on 28 condor legs a TP was worse at every
level). **Defined risk is the whole reason this structure is acceptable and a
short strangle is not.**
"""

import logging
from typing import Optional

import config
from strategy.base_strategy import OptionsSignal as Signal

logger = logging.getLogger(__name__)

# ⚠️ EVERY CONSTANT BELOW IS A STATED PRIOR AWAITING MEASUREMENT. None has been
# validated against outcomes, because the data to validate it did not exist
# until 2026-08-19. Config-overridable so retuning needs no code change.
ENABLED = getattr(config, "GEX_BUTTERFLY_ENABLED", False)      # PARKED
PIN_CONC_MIN = getattr(config, "GEX_BFLY_PIN_CONC_MIN", 0.25)
ATR_MAX_PCT = getattr(config, "GEX_BFLY_ATR_MAX_PCT", 0.08)
PIN_DIST_MAX_PCT = getattr(config, "GEX_BFLY_PIN_DIST_MAX_PCT", 0.30)
EARLIEST_ET = getattr(config, "GEX_BFLY_EARLIEST_ET", "13:00")
LATEST_ET = getattr(config, "GEX_BFLY_LATEST_ET", "15:00")


def _reachable_pct(atr_pct: float) -> float:
    """Roughly how far price can travel, from the measured ATR->excursion map.

    Medians from `tests/magnitude_estimator.py` (52,949 bars, 90-bar horizon):
    ATR 0.03 -> 0.19% · 0.05 -> 0.28% · 0.08 -> 0.43% · 0.12 -> 0.60% ·
    0.20+ -> 1.07%. Interpolated coarsely on purpose - a precise curve fitted to
    28 sessions in ONE market regime would be false precision.
    """
    pts = [(0.03, 0.19), (0.05, 0.28), (0.08, 0.43), (0.12, 0.60), (0.20, 1.07)]
    if atr_pct <= pts[0][0]:
        return pts[0][1]
    if atr_pct >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= atr_pct <= x1:
            f = (atr_pct - x0) / max(x1 - x0, 1e-9)
            return y0 + f * (y1 - y0)
    return pts[-1][1]


class GEXPinButterflyStrategy:
    """Centre a butterfly on the gamma pin when price can reach it and stay.

    Three questions, in order, and the order matters - each is cheaper than the
    one after it:
      1. IS THERE A PIN?      environment PINNING *and* concentration high
                              enough that ONE strike dominates. A strike holding
                              40% of gross |GEX| is a magnet; one holding 8% is
                              gamma smeared across the chain with nothing
                              actually pinned - **and both read "PINNING"**.
      2. CAN PRICE REACH IT?  distance to the pin against the ATR-implied
                              reachable move. A pin price cannot reach is not a
                              target.
      3. WILL PRICE STAY?     ATR low enough that the wings are not breached.
                              This is the SHORT-VOL condition and it is the one
                              the runaway trade inverts.
    """

    name = "GEXPinButterfly"

    def generate_signal(self, *, gex, atr_pct: float, price_now: float,
                        now_et: str, chain=None, **_ignored) -> Optional[Signal]:
        # ── 0. PARKED ────────────────────────────────────────────────────────
        # ⚠️ Not a placeholder and not a stub: the code below is complete. It is
        # OFF because its INPUT is not yet trustworthy. Enabling it before the
        # OI data accumulates would trade a gamma-squared artifact.
        if not ENABLED:
            return None

        if not gex or not price_now:
            return None

        # ── 1. is there actually a pin? ──────────────────────────────────────
        env = str(getattr(gex, "gex_environment", "") or "")
        conc = float(getattr(gex, "pin_concentration", 0.0) or 0.0)
        pin = float(getattr(gex, "pin_strike", 0.0) or 0.0)
        if env != "PINNING" or pin <= 0:
            return None
        if conc < PIN_CONC_MIN:
            logger.debug("[gex_bfly] no trade: pin concentration %.3f < %.2f - "
                         "PINNING label without a dominant strike", conc,
                         PIN_CONC_MIN)
            return None

        # ── 2. window ────────────────────────────────────────────────────────
        # ⚠️ AFTERNOON ONLY, AND THIS IS THE WEAKEST ASSUMPTION IN THE FILE.
        # 0DTE gamma sharpens toward expiry, so a pin should hold harder late -
        # but that is REASONING, not measurement. `tests/pin_strength.py` exists
        # to test it by time-of-day and COULD NOT RUN: the archive has no OI.
        if now_et and not (EARLIEST_ET <= now_et <= LATEST_ET):
            return None

        # ── 3. can price reach the pin? ──────────────────────────────────────
        dist_pct = abs(price_now - pin) / price_now * 100.0
        reach = _reachable_pct(atr_pct or 0.0)
        if dist_pct > min(PIN_DIST_MAX_PCT, reach):
            logger.debug("[gex_bfly] no trade: pin %.2f is %.2f%% away, tape "
                         "reaches ~%.2f%%", pin, dist_pct, reach)
            return None

        # ── 4. will price STAY? the short-vol condition ──────────────────────
        # ⚠️ THIS IS THE INVERSE OF THE RUNAWAY GATE, deliberately. Above 0.12%
        # ATR the tape produced a 0.5% move on 60% of 90-bar windows and on 92%
        # above 0.20% - a butterfly's wings do not survive that.
        if atr_pct is None or atr_pct > ATR_MAX_PCT:
            logger.debug("[gex_bfly] no trade: ATR %.3f%% too hot for a pin "
                         "(wings breach). Measured: >0.12%% ATR moved 0.5%% on "
                         "60%% of windows.", atr_pct or 0.0)
            return None

        sig = Signal(
            strategy_name=self.name,
            setup_type="gex_pin_butterfly",
            direction="neutral",
            underlying_entry=price_now,
        )
        sig.center_strike = pin
        sig.pin_concentration = conc
        sig.atr_pct_at_entry = atr_pct
        sig.pin_distance_pct = dist_pct

        logger.info("[gex_bfly] FIRE  pin=%.2f conc=%.2f dist=%.2f%% "
                    "ATR=%.3f%%  (neutral - no direction required)",
                    pin, conc, dist_pct, atr_pct)
        return sig
