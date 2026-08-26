"""
strategy/gex_pin_butterfly.py  v4.3
v4.3  2026-08-26  r147 — UNPARKED, AND IT HAS LEGS. Operator: *"I want it
      active. It already has to clear a high bar to fire. The r-value in
      strict should veto, but allow and record on relaxed. The pin should be
      reachable & the strikes should be relatively narrow but not so narrow
      that it has zero breathing room. Purchased as a debit call butterfly
      for below the pin, and put for [above] the pin."*
      · `ENABLED` now reads config.GEX_BUTTERFLY_ENABLED, default ON.
      · THE LEGS: apex ON the pin; wings at ⟨PRIOR⟩ WING_EM_FRAC (0.25) of
        the expected move, rounded to the strike increment, floor ONE
        increment (breathing room), ceiling the distance to the pin (the
        near wing never crosses spot). Call fly when spot is BELOW the pin,
        put fly when spot is ABOVE it — price travels to the magnet.
      · EXACT STRIKES ONLY. `select_butterfly_strikes` centres on spot and
        falls back to the nearest liquid strike; both would silently move the
        apex off the pin, which is the FOUNDATIONAL condition. Three priced
        contracts at exactly lower/pin/upper, or no trade.
      · net_debit = lower.mark − 2·center.mark + upper.mark; max_profit =
        width − debit; R = (width − debit)/debit through the plan, so STRICT
        vetoes below 1:1 and RELAXED records (`r_muted`). debit/width is
        recorded against BUTTERFLY_MAX_DEBIT_PCT_WIDTH as a check, NOT a
        gate — the R hurdle is the economic gate, one rule fleet-wide.
      · The signal is now VALID: is_butterfly, three contracts, direction,
        net_debit — `is_valid`'s butterfly arm is satisfied and
        entry_engine's `_place_butterfly` runs it unchanged.
v4.2  2026-08-26  r146 — THE PLAN IS WIRED. Every refusal (parked, no GEX,
      not PINNING, pin strength, window, no expected move, pin too near/far)
      goes through `self.planner` (strategy/plan.py) and writes a DECLINE row
      naming the gate; `_gate()` kept as an alias. ⚠️ THE WHAT-IF IS NOT
      PRICED HERE YET, DELIBERATELY: this spec sets `center_strike` and never
      selects the three legs, so the signal cannot be valid (`is_butterfly`
      is never set; the single-leg `is_valid` arm needs a strike and premium
      it does not have) — the same one-writer-zero-readers defect r97 found
      in the sweep and r146 found in the runaway. Building the legs is a
      spec decision (which wing width, how far from the pin) and is NOT made
      here; until it is, R records n/a and the hurdle is not consulted.
      Parked anyway (ENABLED False), so nothing trades on it.
Apex on the GEX pin, OUT OF THE MONEY. Buy the move to the magnet.

v4.0  2026-08-19  First version. **The wrong trade** - see v4.1.
v4.1  2026-08-20  Rewritten to the operator's actual spec.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

════════════════════════════════════════════════════════════════════════════
⚠️ STILL PARKED. THE INPUT IS NOT REAL YET.
════════════════════════════════════════════════════════════════════════════
`OptionContract.open_interest` was a DECLARED FIELD WITH NO PRODUCER - 0 on
every contract for the life of v3 - so `gex_data` fell through to
`oi_proxy = max(1, int(1000 * gamma))` and multiplied by gamma AGAIN:

        **GEX ~ 100,000 * gamma^2 * spot**

Confirmed on the live SPX box 2026-08-19: 542 of 542 contracts in the day's
final snapshot carried `"oi": 0`, while the log showed `pin = call_wall = $7725`
with **spot sitting on it** - gamma peaks at the money, so a gamma-squared
surface always "pins" wherever price already is - and GEX swung
**12.4M -> 0.1M -> 2.0M in three minutes**, flipping PINNING/NEUTRAL inside 90
seconds. OI.1 wires real open interest into both repos; ~2 weeks of collection
are needed before any threshold here can be validated.

⚠️ **AND THAT ALSO HID A DUPLICATE.** v3's `butterfly_strategy` centres on SPOT;
this centres on the PIN. **While GEX was gamma-squared the pin WAS spot, so the
two computed the same centre through different arithmetic and nobody could have
noticed.** They diverge for the first time when real OI lands. One of them
retires then; keeping both is how a codebase grows a second lineage nobody
remembers choosing.

════════════════════════════════════════════════════════════════════════════
WHAT v4.0 GOT WRONG, AND WHY THE CORRECTION MATTERS
════════════════════════════════════════════════════════════════════════════
v4.0 built an AT-THE-MONEY butterfly requiring price to be NEAR the pin already,
and vetoed high ATR because "a butterfly wants price to sit still". **Both
backwards.**

Operator, 2026-08-20: *"the intention of this trade is to place the apex on the
pin, which should be OUT OF THE MONEY ... and the farther away the better as
long as it's within the expected move. That's where the asymmetrical payoff
comes into play."*

**THE ASYMMETRY IS THE ENTIRE TRADE.** A butterfly's apex payoff is fixed at the
wing width, but **the DEBIT falls sharply as the apex moves OTM.** A pin at 80%
of the expected move costs a fraction of one at 20% and pays the same at the
apex. Same maximum payoff, much smaller stake.

So distance is the EDGE, not the risk, and the gate is a BAND:
  · too NEAR  - expensive, poor ratio, and you are paying for a move that has
                already happened
  · too FAR   - beyond the expected move, the chain says price probably cannot
                get there
  · **prefer the far edge of what is reachable**

⚠️ AND THE PIN-STRENGTH CONDITION BECOMES LOAD-BEARING. At 80% of the expected
move the trade relies on the magnet actually PULLING price, not on drift
happening to arrive. **A weak pin far away is the worst cell in the matrix; a
strong pin far away is the best.** `pin_concentration` is what tells them apart
- a strike holding 40% of gross |GEX| is one dominant magnet, one holding 8% is
gamma smeared with nothing pinned, **and both read "PINNING"** past the 0.15
threshold.

⚠️ THE EXPECTED MOVE COMES FROM THE CHAIN, NOT FROM VIX. v3 computed it as
`underlying * VIX/100 * sqrt(hours/6.5) / sqrt(252)` - **VIX is SPX 30-day
implied vol applied to any symbol on any 0DTE horizon.** The chain carries
per-symbol ATM IV directly and that is the right input; the time-scaling from v3
is kept because it is sound.

⚠️ AND NOTE WHAT IS *NOT* HERE: NO ATR GATE. v4.0 vetoed above 0.08% ATR on
short-vol reasoning. This trade needs price to TRAVEL to the pin and then sit -
closer to the runaway's requirement than to a short-vol one. The expected-move
band already encodes reachability using the chain's own volatility estimate,
which is a better instrument than an ATR proxy for the same question.

════════════════════════════════════════════════════════════════════════════
GATE CATEGORIES — required by WA §36. Only SELECTION is ever relaxed.
════════════════════════════════════════════════════════════════════════════
**FOUNDATIONAL — never relaxed.**
  · `gex_environment == PINNING`. Without a pin there is no magnet and this is
    an arbitrary OTM butterfly.
  · the apex sits ON the pin. Centring anywhere else is a different trade -
    v3's `butterfly_strategy` centres on SPOT, and that is the duplicate this
    file exists to replace.
  · the pin is OTM. An ATM apex is v4.0's mistake: it pays for a move that has
    already happened and discards the asymmetry that justifies the structure.

**SELECTION — relaxed.**
  · pin concentration 0.25 -> 0.15 floor 0.10. ⚠️ RELAXED WITH RELUCTANCE: at
    the far edge of the expected move the trade RELIES on the magnet pulling
    price. **A weak pin far away is the worst cell in the matrix.** It is
    selection rather than foundational only because a weak pin still IS a pin.
  · window 11:00-15:00 -> 09:45-15:30.
  · EM ceiling 1.00 -> 1.30.

**FEASIBILITY — never relaxed.**
  · no ATM IV means **no trade**, not a fallback. The whole distance band is
    expressed in expected moves; guessing one would put the trade's central
    gate on a number nobody measured.
  · the EM floor at 0.30. Nearer than that the debit is expensive and the payoff
    ratio poor - **the asymmetry IS the trade**, and without it there is no
    reason to prefer this structure over anything else.

⚠️ AND THIS STRATEGY IS RARE BY DESIGN, WHICH IS AN OPPORTUNITY-COST QUESTION
RATHER THAN A DEFECT. It needs a strong pin far from spot - most likely near
monthly expiration, when real positioning sits at a strike rather than a single
day's worth. **It costs nothing while it waits**: no position slot, no capital,
no competition with the other setups. The only real cost is maintenance
attention, and a strategy that fires rarely is one whose plumbing is rarely
exercised - which is what the relaxed toggle is for.
⚠️ ITS EVIDENCE WILL BE STRUCTURAL, NOT STATISTICAL. A handful of fills a month
will never accumulate what the sweep spread got from 2,169 events. The test is
**"when it fires, does the payoff justify having kept it?"** - answerable on a
small sample in a way a win rate is not. That is a weaker footing than the sweep
spread has and it should be said before it goes live, not after a small sample
looks encouraging.
"""

import logging
import math
from datetime import datetime
from typing import Optional

import config
from strategy import relaxed
from strategy.base_strategy import OptionsSignal as Signal
from strategy.plan import Plan
from utils.math_utils import safe_float

logger = logging.getLogger(__name__)


def _gate(name: str, reason: str) -> None:
    """r73 — report this rung, edge-triggered. NEVER changes the verdict."""
    try:
        from analysis.gate_report import get_gate_reporter
        from config import INSTRUMENT
        r = get_gate_reporter(INSTRUMENT)
        if r is not None:
            r.blocked("GexPinButterfly", name, reason)
    except Exception:                                           # noqa: BLE001
        pass

# ⚠️ EVERY CONSTANT IS A STATED PRIOR AWAITING MEASUREMENT. Nothing here has
# been validated against outcomes, because the data to do it did not exist until
# 2026-08-19. `GEX_PIN_CONCENTRATION = 0.15` in gex_data was tuned against the
# gamma-squared surface and means nothing for real positioning.
ENABLED = getattr(config, "GEX_BUTTERFLY_ENABLED", True)       # v4.3: ON
# ⟨PRIOR⟩ wing width as a fraction of the expected move. Narrow enough that the
# apex payoff is concentrated, wide enough that the pin has a strike of room
# either side. Floor: one increment. Ceiling: the distance to the pin.
WING_EM_FRAC = getattr(config, "GEX_BFLY_WING_EM_FRAC", 0.25)
PIN_CONC_MIN = getattr(config, "GEX_BFLY_PIN_CONC_MIN", 0.25)
EM_MIN_FRAC = getattr(config, "GEX_BFLY_EM_MIN_FRAC", 0.30)
EM_MAX_FRAC = getattr(config, "GEX_BFLY_EM_MAX_FRAC", 1.00)
EARLIEST_ET = getattr(config, "GEX_BFLY_EARLIEST_ET", "11:00")
LATEST_ET = getattr(config, "GEX_BFLY_LATEST_ET", "15:00")

# ── GATE CATEGORIES AS DATA (WA §36) ───────────────────────────────────────
GATES = {
    "EARLIEST_ET":   "SELECTION",
    "LATEST_ET":     "SELECTION",
    "EM_MAX_FRAC":   "SELECTION",
    # ⚠️ SELECTION WITH RELUCTANCE. At the far edge of the expected move the
    # trade RELIES on the magnet pulling price, so a weak pin far away is the
    # worst cell in the matrix. It is selection only because a weak pin is
    # still a pin.
    "PIN_CONC_MIN":  "SELECTION",
    # FEASIBILITY - nearer than this the debit is expensive and the payoff ratio
    # poor. **The asymmetry IS the trade**; without it there is no reason to
    # prefer this structure over anything else.
    "EM_MIN_FRAC":   "FEASIBILITY",
    # v4.3 — SELECTION: a narrower or wider fly is a worse example of the same
    # trade. The floor of one increment is tested inline (no knob).
    "WING_EM_FRAC":  "SELECTION",
    # FOUNDATIONAL: PINNING, the apex ON the pin, and the pin OTM. Tested
    # inline - no knob.
}


def expected_move(underlying: float, atm_iv: float, now=None) -> Optional[float]:
    """1x expected move for the REMAINING session, from the chain's ATM IV.

    ⚠️ ATM IV, NOT VIX. v3 used VIX - SPX 30-day implied vol - for every symbol
    on a 0DTE horizon. The chain publishes the actual implied vol of the actual
    contract; using an index proxy for a single name is a second-order estimate
    where a first-order one is sitting right there.
    The sqrt-of-time scaling is carried from v3 unchanged: it was sound.
    """
    underlying = safe_float(underlying)
    atm_iv = safe_float(atm_iv)
    if not underlying or not atm_iv or atm_iv <= 0 or underlying <= 0:
        return None
    try:
        from utils.time_utils import ET
        now = now or datetime.now(ET)
        close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        hours = max((close - now).total_seconds() / 3600.0, 0.25)
    except Exception:                                          # noqa: BLE001
        hours = 3.0
    return underlying * atm_iv * math.sqrt(hours / 6.5) / math.sqrt(252)


class GEXPinButterflyStrategy:
    """Apex on the pin, OTM, as far out as the expected move allows.

    Four conditions, cheapest first:
      1. GEX IS PINNING          - real GEX, which needs the OI data
      2. THE PIN IS STRONG       - one strike dominates rather than smeared
      3. THE PIN IS OTM AND      - distance is the edge; the band rejects both
         WITHIN THE EXPECTED       "too near to be worth it" and "too far to be
         MOVE                      reachable"
      4. APEX ON THE PIN         - debit, defined risk, cheap because it is away
    """

    name = "GEXPinButterfly"

    PLAN_CHECKS = ("enabled", "gex", "pinning", "pin_concentration",
                   "entry_window", "expected_move", "pin_em_fraction",
                   "wing_width", "legs", "debit", "debit_pct_width", "width", "r")

    def __init__(self):
        self.planner = Plan(self.name, self.PLAN_CHECKS)

    def generate_signal(self, *, gex, price_now: float, now_et: str,
                        atm_iv: float = None, chain=None,
                        **_ignored) -> Optional[Signal]:
        t = self.planner.tick(price_now)
        # ⚠️ PARKED. Complete code, not a stub. It is OFF because its INPUT is
        # not trustworthy - enabling it now would trade a gamma-squared artifact.
        if not ENABLED:
            return t.refuse("enabled", "PARKED — GEX_BUTTERFLY_ENABLED is False "
                                       "(open interest not yet trustworthy)")
        price_now = safe_float(price_now)
        if not price_now or price_now <= 0:
            return t.refuse("price", f"price unusable ({price_now})")
        if not gex:
            return t.starved("gex")

        env = str(getattr(gex, "gex_environment", "") or "")
        conc = float(getattr(gex, "pin_concentration", 0.0) or 0.0)
        pin = float(getattr(gex, "pin_strike", 0.0) or 0.0)
        if env != "PINNING" or pin <= 0:
            return t.refuse("pinning", f"GEX environment is {env or 'unknown'} "
                                       f"(pin {pin:g}) — not PINNING")
        t.check("pinning", pin, True)
        t.anchor(trigger=pin)

        # ── 2. the pin must be STRONG, and it matters more the further out ──
        _conc_min = relaxed.widen(PIN_CONC_MIN, 0.6, floor=0.10, name="pin_conc_min")
        t.check("pin_concentration", conc, conc >= _conc_min)
        if conc < _conc_min:
            logger.debug("[gex_bfly] no trade: pin concentration %.3f < %.2f - "
                         "PINNING without a dominant strike", conc, PIN_CONC_MIN)
            return t.refuse("pin_concentration",
                            f"pin concentration {conc:.3f} < {_conc_min:.2f} — "
                            f"PINNING without a dominant strike")

        _early, _late = relaxed.window(EARLIEST_ET, LATEST_ET)
        if now_et and not (_early <= now_et <= _late):
            return t.refuse("entry_window", f"{now_et} ET is outside the "
                                            f"butterfly window {_early}-{_late}")
        t.check("entry_window", None, True)

        # ── 3. OTM, and inside the expected move ────────────────────────────
        em = expected_move(price_now, atm_iv)
        if not em or em <= 0:
            # ⚠️ NO EXPECTED MOVE MEANS NO TRADE, not a fallback. Guessing one
            # would put the whole distance band on a number nobody measured.
            logger.debug("[gex_bfly] no trade: no ATM IV, so no expected move")
            return t.refuse("expected_move", "no ATM IV, so no expected move — "
                                             "not a fallback")
        t.check("expected_move", em, True)

        dist = abs(pin - price_now)
        frac = dist / em
        _em_max = relaxed.widen(EM_MAX_FRAC, 1.3, name="em_max_frac")
        t.check("pin_em_fraction", frac, EM_MIN_FRAC <= frac <= _em_max)
        if frac < EM_MIN_FRAC:
            logger.debug("[gex_bfly] no trade: pin is %.0f%% of the expected "
                         "move away - too near, the debit is expensive and the "
                         "payoff ratio poor", frac * 100)
            return t.refuse("pin_em_fraction",
                            f"pin is {frac*100:.0f}% of expected move (floor "
                            f"{EM_MIN_FRAC*100:.0f}%) - debit expensive, payoff poor")
        if frac > _em_max:
            logger.debug("[gex_bfly] no trade: pin is %.0f%% of the expected "
                         "move away - the chain says price probably cannot get "
                         "there", frac * 100)
            return t.refuse("pin_em_fraction",
                            f"pin is {frac*100:.0f}% of expected move (ceiling "
                            f"{_em_max*100:.0f}%) - the chain says price probably "
                            f"cannot get there")

        side = "call" if pin > price_now else "put"
        t.direction = side

        # ── 4. THE LEGS (v4.3) — apex on the pin, wings by the expected move ─
        if chain is None:
            return t.starved("chain")
        inc = float(getattr(config, "STRIKE_INCREMENT", 1) or 1)
        from utils.math_utils import round_to_strike
        wing = float(round_to_strike(WING_EM_FRAC * em, inc) or 0.0)
        wing = max(inc, min(wing, float(round_to_strike(dist, inc) or inc)))
        t.check("wing_width", wing, wing >= inc)
        contracts = chain.calls if side == "call" else chain.puts
        lo_k, hi_k = pin - wing, pin + wing

        def _exact(k):
            for c in contracts or []:
                try:
                    if abs(float(c.strike) - k) < 1e-9 and float(c.mark or 0) > 0:
                        return c
                except (TypeError, ValueError, AttributeError):
                    continue
            return None
        lower, center, upper = _exact(lo_k), _exact(pin), _exact(hi_k)
        missing = [f"{k:g}" for k, c in ((lo_k, lower), (pin, center), (hi_k, upper)) if c is None]
        t.check("legs", 3 - len(missing), not missing)
        if missing:
            return t.refuse("legs", f"no priced {side} contract at strike(s) "
                                    f"{', '.join(missing)} — the apex is the trade; "
                                    f"a nearest-strike substitute is a different one")
        debit = float(lower.mark) - 2.0 * float(center.mark) + float(upper.mark)
        width = float(upper.strike) - float(center.strike)
        t.butterfly(debit, width, trigger=pin)
        if debit <= 0:
            return t.refuse("debit", f"{side} fly {lo_k:g}/{pin:g}/{hi_k:g} prices at "
                                     f"{debit:.2f} — no debit, marks are stale or crossed")
        _pct = debit / width if width else None
        _cap = float(getattr(config, "BUTTERFLY_MAX_DEBIT_PCT_WIDTH", 0.33))
        t.check("debit_pct_width", _pct, None if _pct is None else _pct <= _cap)
        ok, why = t.executable()
        if not ok:
            logger.info("[gex_bfly] R %s refused: %s", f"{t.r:.2f}" if t.r is not None else "n/a", why)
            return t.refuse("r", why)
        t.note(why)

        sig = Signal(
            strategy_name=self.name,
            setup_type="gex_pin_butterfly",
            direction="neutral",
            option_side=side,
            underlying_entry=price_now,
            underlying_target=pin,
            is_butterfly=True,
            lower_contract=lower,
            center_contract=center,
            upper_contract=upper,
            butterfly_direction=side,
            net_debit=round(debit, 4),
            max_profit=round(width - debit, 4),
            strike=float(center.strike),
            expiry=getattr(center, "expiry", ""),
            entry_premium=round(debit, 4),
            contract=center,
            stop_loss_pct=float(getattr(config, "BUTTERFLY_STOP_LOSS_PCT", 0.25)),
        )
        sig.center_strike = pin              # the APEX sits on the pin
        sig.pin_concentration = conc
        sig.expected_move = round(em, 4)
        sig.pin_em_fraction = round(frac, 4)
        sig.pin_distance = round(dist, 4)
        relaxed.tag(sig)

        logger.info("[gex_bfly] FIRE  %s fly %g/%g/%g  debit %.2f  width %.2f  R %s  "
                    "apex %.2f (%.0f%% of a %.2f expected move)  pin conc %.2f  spot %.2f",
                    side.upper(), lo_k, pin, hi_k, debit, width,
                    f"{t.r:.2f}" if t.r is not None else "n/a",
                    pin, frac * 100, em, conc, price_now)
        return t.take(sig)
