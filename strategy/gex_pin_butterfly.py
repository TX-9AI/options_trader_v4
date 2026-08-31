"""
strategy/gex_pin_butterfly.py  v4.6
v4.6  2026-08-31  r196 — THE NOON FLOOR IS HARD. Operator, on the first live
      open, seeing butterflies fire at 09:45: "the noon floor is
      non-negotiable." 🔴 That 09:45 is `relaxed.window()`'s relaxed_earliest
      default EXACTLY — the fires were the relaxed floor, not a pin forming
      early. EARLIEST_ET moves SELECTION -> FOUNDATIONAL and is passed as its
      own relaxed value so it cannot widen. LATEST_ET stays relaxable.
      🔑 THE RULE THIS TEACHES: relax DIALS, never STRUCTURAL gates. A dial's
      near-misses tell you whether the line is right; a structural gate's
      "near-misses" are a different trade entirely. And think twice before
      relaxing anything on a strategy with a SESSION CAP — there, a relaxed
      gate does not collect a sample, it SPENDS the sample.
v4.5  2026-08-29  r178 — 🔴 ONE BUTTERFLY PER PIN PER SESSION. The hour
      r177 unblocked the starved atm_iv, the strategy fired the SAME UNH
      397.5 fly five times in ninety seconds: the additive exemption (r161)
      let it stack ITSELF and it had no self-lock — it had never once fired
      to need one. PLAYED_PINS registry: a fire marks the pin played (from
      the dispatch, on the signal's pin); prepare() declines a played pin
      STRUCTURALLY (relaxed does not waive it), checked before the
      conditions. A NEW pin is a new trade. In-process; a restart clears it.
v4.4  2026-08-27  r161 — THE PLAN PREPARES, THE STRATEGY EXECUTES; EXEMPT FROM
      THE SINGLE-POSITION RULE. Operator, 2026-08-27: *"I want it to be able
      to fire regardless if any other open trades are found. Reason: it has
      such a high hurdle to clear. GEX pinning, pin reachable, economic
      feasibility. If it can achieve all that, it's earned an entry."*
      `prepare()` is the plan (the sweep's v4.6 shape): DORMANT outside the
      slot; each declared CONDITION with its current reading; the three legs
      SELECTED (apex on the pin, wing from the expected move, exact strikes);
      R = (width-debit)/debit against R_FLOOR as a STRUCTURAL check — the
      operator's third hurdle, so relaxed does not waive it (v4.3 routed it
      through the muteable hurdle; that was wrong for a trade whose entry
      is EARNED by feasibility). `generate_signal()` executes the prepared
      legs. main.py v4.19 asks it every tick of its slot whether or not a
      position is open, and appends its record (position_manager v4.4).
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
from strategy.criteria import R_FLOOR
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
    # 🔴 r196 — FOUNDATIONAL, NOT SELECTION. Operator, 2026-08-31, watching
    # butterflies open at 09:45 on the first live open: "the noon floor is
    # non-negotiable."
    # The 09:45 was not a marginal call and not GEX pinning early — it is
    # `relaxed.window()`'s `relaxed_earliest` default EXACTLY, so the fires
    # were the relaxed floor, not the market.
    # ⚠️ WHY THE CATEGORY WAS WRONG, WHICH IS THE PART WORTH KEEPING:
    # relaxation only informs a gate that is a DIAL ALONG A CONTINUUM. Widen a
    # dial and you collect the near-misses, whose outcomes tell you whether the
    # line sits in the right place. `PIN_CONC_MIN` and `EM_MAX_FRAC` are dials
    # and are relaxed correctly. This is not a dial. The operator's rule is
    # "any sooner than noon to reach a pin is unlikely to hold all the way to
    # the closing bell" — a claim about TIME TO EXPIRY, not about pin quality.
    # A 09:45 butterfly is not a marginally worse butterfly; it is a different
    # trade with six and a half hours of gamma ahead of it instead of four, and
    # its outcome says nothing about whether noon is the right hour.
    # ⚠️ AND THE WIDENING CAME FROM UNRELATED REASONING. `relaxed.window`'s
    # 09:45 floor is documented as avoiding the opening auction's residue — a
    # QUOTE-QUALITY argument. It silently overrode a TIME-TO-PIN argument. Two
    # different concerns sharing one default.
    # ⚠️ AND THE COST IS WORST HERE BECAUSE THE BUTTERFLY IS ONE PER SESSION.
    # Relaxing a dial spends a marginal trade. Relaxing this spent the day's
    # ONLY attempt, three hours before the thesis is valid.
    "EARLIEST_ET":   "FOUNDATIONAL",
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


class ButterflyPreparation:
    """What the plan hands the strategy each tick of the slot — never executable."""
    __slots__ = ("tick", "pin", "side", "conc", "em", "frac", "wing", "lower", "center",
                 "upper", "debit", "width", "r", "r_min", "conditions", "unmet",
                 "structural", "starved", "ready")

    def __init__(self, tick):
        self.tick = tick
        self.pin = self.conc = self.em = self.frac = self.wing = 0.0
        self.side = ""
        self.lower = self.center = self.upper = None
        self.debit = self.width = self.r = None
        self.r_min = R_FLOOR
        self.conditions, self.unmet, self.structural, self.starved = {}, [], [], []
        self.ready = False

    def cond(self, name, current, required, met):
        self.conditions[name] = (current, required, bool(met))
        if not met:
            self.unmet.append(name)
        self.tick.check(name, current if isinstance(current, (int, float)) else None, bool(met))

    def trade_line(self):
        if not self.ready:
            return "no trade prepared"
        return (f"buy {self.lower.strike:g}/{self.center.strike:g}/{self.upper.strike:g} "
                f"{self.side} fly  debit {self.debit:.2f}  width {self.width:.2f}  "
                f"R {self.r:.2f} (min {self.r_min:.2f})")


class GEXPinButterflyStrategy:
    """THE SPEC. Declares its conditions; executes with the plan's legs.

    🔴 EXEMPT FROM THE SINGLE-POSITION RULE. Operator, 2026-08-27: *"I want it
    to be able to fire regardless if any other open trades are found. Reason:
    it has such a high hurdle to clear. GEX pinning, pin reachable, economic
    feasibility. If it can achieve all that, it's earned an entry."* TRADES.md
    §3 said the same from the start: *"no position slot, no capital, no
    competition."* main.py asks it every tick of its slot, position open or
    not, and appends its record rather than replacing.
    """
    name = "GEXPinButterfly"

    CONDITIONS = {
        "enabled":           "GEX_BUTTERFLY_ENABLED is on",
        "pinning":           "GEX environment is PINNING with a pin strike",
        "pin_concentration": f"pin concentration >= {PIN_CONC_MIN:.2f} (relaxed 0.6x, floor 0.10)",
        "entry_window":      f"{EARLIEST_ET}-{LATEST_ET} ET",
        "expected_move":     "an expected move from the chain's ATM IV (no fallback)",
        "pin_em_fraction":   f"pin at {EM_MIN_FRAC:.0%}-{EM_MAX_FRAC:.0%} of the expected move (relaxed x1.3)",
    }
    STRUCTURAL = ("legs", "debit", "r", "pin_played")
    PLAN_CHECKS = tuple(CONDITIONS) + STRUCTURAL + ("gex", "wing_width", "width", "debit_pct_width")

    def __init__(self):
        self.planner = Plan(self.name, self.PLAN_CHECKS)

    # ══════════════════════════════════════════════════════════════════════
    # THE PLAN — evaluates the declared conditions, SELECTS the three legs.
    # ══════════════════════════════════════════════════════════════════════
    # ── ONE BUTTERFLY PER PIN PER SESSION (r178) ──────────────────────────
    # 2026-08-28 15:00-15:01: r177 unblocked the starved atm_iv, every
    # condition was genuinely true on UNH's pin, and the strategy fired the
    # SAME 397.5 fly five times in ninety seconds — the additive exemption
    # (r161) let it stack ITSELF, and it had no self-lock because it had
    # never once fired to need one. Same failure class as the runaway
    # re-arm; same doctrine as the fix: a fired pin is PLAYED for the
    # session. A NEW pin (GEX migrates the magnet) is a new trade.
    # In-process registry; a restart clears it, recorded as acceptable.
    PLAYED_PINS: set = set()

    @classmethod
    def mark_pin_played(cls, pin) -> None:
        try:
            cls.PLAYED_PINS.add(round(float(pin), 2))
        except (TypeError, ValueError):
            pass

    def prepare(self, *, gex, price_now, now_et, atm_iv=None, chain=None,
                **_ignored) -> ButterflyPreparation:
        t = self.planner.tick(price_now)
        prep = ButterflyPreparation(t)
        # r196 — the floor is passed as its OWN relaxed value, so
        # `min(earliest, relaxed_earliest)` can only ever return EARLIEST_ET.
        # LATEST_ET stays relaxable: staying LATER is a dial (a pin that forms
        # at 15:10 is a marginally worse version of the same trade), whereas
        # starting EARLIER is a different trade.
        _early, _late = relaxed.window(EARLIEST_ET, LATEST_ET,
                                       relaxed_earliest=EARLIEST_ET)
        if now_et and not (_early <= now_et <= _late):
            # ⚠️ TIME-INVARIANT reason (check_plan_signal PS7): the dormant row
            # is edge-triggered on its text; a clock in it defeats the dedupe.
            t.dormant("entry_window", f"outside the butterfly slot {_early}-{_late}")
            return prep
        prep.cond("entry_window", None, self.CONDITIONS["entry_window"], True)
        prep.cond("enabled", 1.0 if ENABLED else 0.0, self.CONDITIONS["enabled"], ENABLED)
        price_now = safe_float(price_now)
        if not price_now or price_now <= 0:
            prep.starved.append("price_now")
            t.starved("price_now")
            return prep
        if not gex:
            prep.starved.append("gex")
            t.starved("gex")
            return prep
        t.check("gex", 1.0, True)

        env = str(getattr(gex, "gex_environment", "") or "")
        conc = float(getattr(gex, "pin_concentration", 0.0) or 0.0)
        pin = float(getattr(gex, "pin_strike", 0.0) or 0.0)
        prep.pin, prep.conc = pin, conc
        # r178 — a played pin is a structural DECLINE; relaxed does not waive
        # it, and it is checked BEFORE the conditions so the row names it
        # first (a stacked structure corrupts the sample worse than a missed
        # one). The magnet moving to a new strike is a new trade.
        if pin and round(pin, 2) in self.PLAYED_PINS:
            prep.structural.append(("pin_played",
                f"pin {pin:g} already has a butterfly this session — one "
                f"structure per pin; a NEW pin is a new trade"))
            t.check("pin_played", pin, False)
        pinning = env == "PINNING" and pin > 0
        prep.cond("pinning", pin or None, f"PINNING (now {env or 'unknown'})", pinning)
        _conc_min = relaxed.widen(PIN_CONC_MIN, 0.6, floor=0.10, name="pin_conc_min")
        prep.cond("pin_concentration", conc, f">= {_conc_min:.2f}", conc >= _conc_min)
        em = expected_move(price_now, atm_iv)
        prep.em = em or 0.0
        prep.cond("expected_move", em or None, self.CONDITIONS["expected_move"], bool(em and em > 0))
        if pin > 0 and em and em > 0:
            dist = abs(pin - price_now)
            frac = dist / em
            prep.frac = frac
            _em_max = relaxed.widen(EM_MAX_FRAC, 1.3, name="em_max_frac")
            prep.cond("pin_em_fraction", frac, f"{EM_MIN_FRAC:.2f}-{_em_max:.2f}",
                      EM_MIN_FRAC <= frac <= _em_max)
            t.anchor(trigger=pin)
        else:
            prep.cond("pin_em_fraction", None, self.CONDITIONS["pin_em_fraction"], False)

        # ── SELECTION — the three legs, if the conditions hold next tick ────
        if pin > 0 and em and em > 0:
            side = "call" if pin > price_now else "put"
            prep.side = side
            t.direction = side
            if chain is None:
                prep.starved.append("chain")
            else:
                inc = float(getattr(config, "STRIKE_INCREMENT", 1) or 1)
                from utils.math_utils import round_to_strike
                wing = float(round_to_strike(WING_EM_FRAC * em, inc) or 0.0)
                wing = max(inc, min(wing, float(round_to_strike(abs(pin - price_now), inc) or inc)))
                prep.wing = wing
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
                    prep.structural.append(("legs",
                        f"no priced {side} contract at strike(s) {', '.join(missing)} — the "
                        f"apex is the trade; a nearest-strike substitute is a different one"))
                else:
                    debit = float(lower.mark) - 2.0 * float(center.mark) + float(upper.mark)
                    width = float(upper.strike) - float(center.strike)
                    t.butterfly(debit, width, trigger=pin)
                    if debit <= 0:
                        prep.structural.append(("debit",
                            f"{side} fly {lo_k:g}/{pin:g}/{hi_k:g} prices at {debit:.2f} — "
                            f"no debit, marks stale or crossed"))
                    else:
                        _pct = debit / width if width else None
                        _cap = float(getattr(config, "BUTTERFLY_MAX_DEBIT_PCT_WIDTH", 0.33))
                        t.check("debit_pct_width", _pct, None if _pct is None else _pct <= _cap)
                        r = (width - debit) / debit if width > debit else None
                        # ⚠️ STRUCTURAL: R >= 1 is economic feasibility, the third
                        # of the operator's three hurdles. Relaxed does not waive it.
                        t.check("r", r, None if r is None else r >= R_FLOOR)
                        if r is None or r < R_FLOOR:
                            prep.structural.append(("r",
                                f"{side} fly {lo_k:g}/{pin:g}/{hi_k:g} debit {debit:.2f} on "
                                f"width {width:.2f} is R {_nr(r)} — below the {R_FLOOR:.2f} "
                                f"floor; economic feasibility is structure, not selection"))
                        else:
                            prep.lower, prep.center, prep.upper = lower, center, upper
                            prep.debit, prep.width, prep.r = debit, width, r
                            prep.ready = True

        head = f"pin {pin:g} ({env or 'no env'}, conc {conc:.2f}, {prep.frac:.0%} of EM {prep.em:.2f})"
        if prep.starved:
            t.starved(*prep.starved)
            return prep
        if prep.structural:
            gate, why = prep.structural[0]
            t.refuse(gate, f"{head}: {why}")
            return prep
        if prep.unmet:
            cur = "; ".join(f"{n}={_nr(prep.conditions[n][0]) if isinstance(prep.conditions[n][0], (int, float)) else 'no'}"
                            f" (need {prep.conditions[n][1]})" for n in prep.unmet)
            t.hold(f"{head}: PREPARED — {prep.trade_line()}. Waiting on: {cur}")
            return prep
        t.note(f"{head}: all {len(self.CONDITIONS)} conditions true — {prep.trade_line()}")
        return prep

    # ══════════════════════════════════════════════════════════════════════
    # THE STRATEGY — conditions true -> execute the plan's legs.
    # ══════════════════════════════════════════════════════════════════════
    def generate_signal(self, *, gex, price_now: float, now_et: str,
                        atm_iv: float = None, chain=None,
                        **_ignored) -> Optional[Signal]:
        prep = self.prepare(gex=gex, price_now=price_now, now_et=now_et,
                            atm_iv=atm_iv, chain=chain)
        if not prep.ready or prep.unmet or prep.structural or prep.starved:
            return prep.tick.already()
        sig = Signal(
            strategy_name=self.name,
            setup_type="gex_pin_butterfly",
            direction="neutral",
            option_side=prep.side,
            underlying_entry=float(price_now),
            underlying_target=prep.pin,
            is_butterfly=True,
            lower_contract=prep.lower,
            center_contract=prep.center,
            upper_contract=prep.upper,
            butterfly_direction=prep.side,
            net_debit=round(prep.debit, 4),
            max_profit=round(prep.width - prep.debit, 4),
            strike=float(prep.center.strike),
            # r178: the pin rides the signal so the fire can mark it PLAYED
            # by the same key prepare() checks

            expiry=getattr(prep.center, "expiry", ""),
            entry_premium=round(prep.debit, 4),
            contract=prep.center,
            stop_loss_pct=float(getattr(config, "BUTTERFLY_STOP_LOSS_PCT", 0.25)),
        )
        sig.center_strike = prep.pin
        sig.pin_concentration = prep.conc
        sig.expected_move = round(prep.em, 4)
        sig.pin_em_fraction = round(prep.frac, 4)
        sig.pin_distance = round(abs(prep.pin - float(price_now)), 4)
        sig.pin_strike = prep.pin          # r178: the mark's key == the plan's key
        relaxed.tag(sig)
        logger.info("[gex_bfly] FIRE  %s  pin conc %.2f  spot %.2f",
                    prep.trade_line(), prep.conc, float(price_now))
        return prep.tick.take(sig)


def _nr(v):
    return "n/a" if v is None else f"{v:.2f}"
