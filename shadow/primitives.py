"""
shadow/primitives.py  v4.1
v4.1  2026-09-05  r268 — VELOCITY SURVIVES A RESTART, AND SAYS WHERE IT CAME
      FROM. `TickAccumulator` is LIVE-ONLY: `add()` runs from inside
      `one_tick`, so every tick before the process existed is gone. With
      `Restart=always` / `RestartSec=30`, a reboot at 10:00 or the fourth pass
      of a crash loop entered RTH with an empty deque and emitted
      `typical_roc: null` for the next five minutes — MIN_TYPICAL_SAMPLES=20 at
      the fleet's poll interval.
      🔴 AND A NULL VELOCITY IS INDISTINGUISHABLE FROM A QUIET TAPE, in the
      corpus the operator intends to fit triggers on. Same silent-empty shape
      that let seven weeks of stage-1 data look like data.
      🔑 `seed_from_closes()` rebuilds the ROC history from 1m closes the
      caller already holds — backfilled from the session open — so recovery is
      independent of WHEN the process started: no timer, and the first tick of
      the day and the fourth restart of a crash loop take the same path.
      ⚠️ `velocity_state()` reports `warming` | `seeded` | `live` on every
      record, because a seeded baseline is a median of MINUTE-to-minute moves
      while live samples are poll-interval moves — different scales, and the
      record must say which rather than pretend they are interchangeable. It
      stays `seeded` while any seeded sample is still inside
      TYPICAL_LOOKBACK_S, since the median is taken over that window.
Velocity and tick-stream primitives for the observer.

v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

shadow/primitives.py — shared, pattern-agnostic primitives (velocity / magnitude / position).
initial release.
Computed ONCE per symbol per tick by the observer and handed to every scorer.
Everything here is a pure read over the tick stream and the engine state
objects (VolatilityState, LiquidityMap) — no side effects, no engine calls.
THE THREE PRIMITIVES
  velocity  — the genuinely new one: NORMALIZED rate-of-change.
              raw ROC over VELOCITY_WINDOW_S, divided by this symbol's own
              recent-typical |ROC| (median over the trailing sample buffer).
              Dimensionless => comparable across the whole fleet with no
              per-name tuning. Hypothesis preserved for the scorers: velocity's
              SIGN BEHAVIOR AT A LEVEL is an early accept/reject discriminator
              (a breakout accelerates THROUGH a level; a sweep decelerates and
              reverses AT it).
  magnitude — range/ATR context, mostly lifted read-only from VolatilityState.
  position  — where price is relative to the mapped landscape: nearest NAMED
              liquidity level above/below (PDH/PDL/session H/L), VWAP, bands,
              plus intrabar position within the FORMING 1-minute bar.
TICK MEMORY
  TickAccumulator gives the primitives memory across ticks: it maintains a
  "forming bar" (the current 1-minute OHLC assembled from tick samples) so the
  low timeframe informs the higher one continuously, not only at bar close.
"""

from collections import deque
from dataclasses import dataclass, field
from statistics import median
from typing import Deque, Dict, List, Optional, Tuple

# ── Calibration knobs (placeholders — tighten from shadow sessions) ──────────
VELOCITY_WINDOW_S   = 60      # ROC lookback window
TYPICAL_LOOKBACK_S  = 1800    # trailing window that defines "recent-typical" ROC
MIN_TYPICAL_SAMPLES = 20      # need this many trailing ROCs before velocity is trusted
TYPICAL_ROC_FLOOR   = 5e-5    # dead-tape guard: floor on typical |ROC| so the
                              # normalization can't divide by ~0 and explode
VELOCITY_CAP        = 25.0    # soft cap (signed) — clips pathological tails,
                              # keeps the dimensionless scale comparable fleet-wide
SAMPLE_MAXLEN       = 400     # tick samples kept (~100 min at 15s polling)
FORMING_BAR_HISTORY = 30      # completed forming bars retained


@dataclass
class FormingBar:
    """The current 1-minute bar, assembled live from tick samples."""
    minute_key: str = ""          # 'YYYY-MM-DDTHH:MM' ET
    open:  float = 0.0
    high:  float = 0.0
    low:   float = 0.0
    close: float = 0.0
    ticks: int = 0


@dataclass
class LevelRef:
    """A named liquidity level and where price sits relative to it."""
    name: str = ""                # 'PDH', 'PDL', 'NY High', ...
    price: float = 0.0
    side: str = ""                # 'above' or 'below' current price
    dist_pct: float = 0.0         # |price - level| / price
    dist_atr: float = 0.0         # |price - level| / ATR (0 if ATR unknown)


@dataclass
class Primitives:
    """One tick's primitive snapshot for one symbol."""
    ts_et: str = ""
    price: float = 0.0

    # velocity
    roc_raw: Optional[float] = None        # signed fractional ROC over window
    roc_typical: Optional[float] = None    # median |ROC| over trailing buffer
    velocity: Optional[float] = None       # roc_raw / roc_typical (signed, dimensionless)
    velocity_prev: Optional[float] = None  # previous tick's velocity (for contraction/flip checks)

    # magnitude
    atr: float = 0.0
    atr_normalized: float = 0.0
    forming_range_atr: Optional[float] = None   # forming bar range / ATR
    is_expanding: bool = False
    bb_width_pct: float = 0.5

    # position
    vwap_dist_pct: Optional[float] = None       # signed (price - vwap)/vwap
    price_vs_bb: str = "INSIDE"
    intrabar_pos: Optional[float] = None        # 0 = at forming-bar low, 1 = at high
    nearest_named_above: Optional[LevelRef] = None
    nearest_named_below: Optional[LevelRef] = None
    named_levels: List[LevelRef] = field(default_factory=list)


class TickAccumulator:
    """Per-symbol tick memory. add() every tick; read-only otherwise."""

    def __init__(self):
        self.samples: Deque[Tuple[float, float]] = deque(maxlen=SAMPLE_MAXLEN)  # (epoch_s, price)
        self.rocs: Deque[Tuple[float, float]] = deque(maxlen=SAMPLE_MAXLEN)     # (epoch_s, roc)
        self.forming: FormingBar = FormingBar()
        self.completed: Deque[FormingBar] = deque(maxlen=FORMING_BAR_HISTORY)
        self.last_velocity: Optional[float] = None
        # r268 — newest seeded sample's epoch, or 0.0. Drives `velocity_state`.
        self.seeded_until: float = 0.0

    def add(self, epoch_s: float, price: float, minute_key: str):
        # rolling ROC over VELOCITY_WINDOW_S, computed against the oldest sample
        # still inside the window (graceful with jittery poll intervals)
        anchor = None
        for ts, p in self.samples:
            if epoch_s - ts <= VELOCITY_WINDOW_S:
                anchor = (ts, p)
                break
        if anchor and anchor[1] > 0 and epoch_s > anchor[0]:
            self.rocs.append((epoch_s, (price - anchor[1]) / anchor[1]))
        self.samples.append((epoch_s, price))

        # forming 1-minute bar
        fb = self.forming
        if fb.minute_key != minute_key:
            if fb.ticks > 0:
                self.completed.append(fb)
            self.forming = FormingBar(minute_key=minute_key, open=price, high=price,
                                      low=price, close=price, ticks=1)
        else:
            fb.high = max(fb.high, price)
            fb.low = min(fb.low, price)
            fb.close = price
            fb.ticks += 1

    def seed_from_closes(self, bars) -> int:
        """Rebuild ROC history from 1-minute closes. -> samples seeded.

        🔴 THIS IS THE RESTART PATH, AND IT IS THE WHOLE POINT (r268). The
        accumulator is LIVE-ONLY: `add()` runs from inside `one_tick`, so every
        tick before the process existed is gone. A reboot at 10:00, or the
        third pass of a `Restart=always` crash loop, would otherwise enter RTH
        with an empty deque and emit `typical_roc: null` for the next five
        minutes — a record indistinguishable from a quiet tape, which is the
        same silent-empty failure that made seven weeks of stage-1 data look
        like data.
        ⚠️ THE 1m CLOSES ARE ALREADY BACKFILLED by `candle_feed` from the
        session open, and `one_tick` already holds them, so recovery costs a
        loop over a list the caller has in hand — no new fetch, no timer, and
        nothing that depends on WHEN the process started.
        ⚠️ SEEDED ROCs ARE NOT LIVE ROCs. These are minute-to-minute moves;
        live samples are poll-interval moves. The magnitudes are on different
        scales, so `typical_roc` computed over a seeded deque means something
        different from one computed over ticks — and the CALLER is told which,
        rather than this class pretending they are interchangeable.
        """
        n = 0
        prev_ts = prev_px = None
        for ts, px in bars:
            try:
                ts = float(ts)
                px = float(px)
            except (TypeError, ValueError):
                continue
            if px <= 0:
                continue
            if prev_px and prev_px > 0 and ts > prev_ts:
                self.rocs.append((ts, (px - prev_px) / prev_px))
                self.seeded_until = max(getattr(self, "seeded_until", 0.0), ts)
                n += 1
            self.samples.append((ts, px))
            prev_ts, prev_px = ts, px
        return n

    def velocity_state(self, epoch_s: float) -> str:
        """`live` | `seeded` | `warming` — provenance for the record.

        🔑 A NULL VELOCITY AND A QUIET TAPE MUST NOT RENDER ALIKE. Without this
        the first five minutes of every session, every mid-session restart and
        every crash loop all read as a flat market in the fitting corpus. The
        record says which it is; the fit decides what to do about it.
        """
        vals = [ts for ts, _ in self.rocs if epoch_s - ts <= TYPICAL_LOOKBACK_S]
        if len(vals) < MIN_TYPICAL_SAMPLES:
            return "warming"
        # ⚠️ SEEDED WHILE ANY SEEDED SAMPLE IS STILL INSIDE THE LOOKBACK —
        # `typical_roc` is a median over that window, so one seeded sample in
        # it still shifts the denominator. It stops being "seeded" when the
        # window has rolled clear of them, not when the next live tick lands.
        cut = getattr(self, "seeded_until", 0.0)
        if cut and epoch_s - cut <= TYPICAL_LOOKBACK_S:
            return "seeded"
        return "live"

    def current_roc(self, epoch_s: float) -> Optional[float]:
        if not self.rocs:
            return None
        ts, roc = self.rocs[-1]
        return roc if epoch_s - ts <= 2 * VELOCITY_WINDOW_S else None

    def typical_roc(self, epoch_s: float) -> Optional[float]:
        vals = [abs(r) for ts, r in self.rocs if epoch_s - ts <= TYPICAL_LOOKBACK_S]
        if len(vals) < MIN_TYPICAL_SAMPLES:
            return None
        m = median(vals)
        return max(m, TYPICAL_ROC_FLOOR) if m >= 0 else None


def _named_levels_from_map(liq_map, price: float, atr: float) -> List[LevelRef]:
    """Read-only extraction of the named landscape from LiquidityMap."""
    raw = [
        ("PDH", getattr(liq_map, "prev_day_high", None)),
        ("PDL", getattr(liq_map, "prev_day_low", None)),
        ("Asia High", getattr(liq_map, "asia_session_high", None)),
        ("Asia Low", getattr(liq_map, "asia_session_low", None)),
        ("London High", getattr(liq_map, "london_session_high", None)),
        ("London Low", getattr(liq_map, "london_session_low", None)),
        ("NY High", getattr(liq_map, "ny_session_high", None)),
        ("NY Low", getattr(liq_map, "ny_session_low", None)),
    ]
    # named pools carry names too — include any pool flagged is_named
    for p in getattr(liq_map, "pools", []) or []:
        if getattr(p, "is_named", False) and getattr(p, "name", ""):
            raw.append((p.name, p.price))
    out: Dict[str, LevelRef] = {}
    for name, lvl in raw:
        if lvl is None or lvl <= 0 or price <= 0:
            continue
        dist = abs(price - lvl)
        ref = LevelRef(
            name=name, price=float(lvl),
            side="above" if lvl >= price else "below",
            dist_pct=dist / price,
            dist_atr=(dist / atr) if atr > 0 else 0.0,
        )
        key = f"{name}:{lvl:.4f}"
        out.setdefault(key, ref)   # collapse duplicates
    return list(out.values())


def compute_primitives(acc: TickAccumulator, epoch_s: float, ts_et: str,
                       minute_key: str, price: float,
                       vol_state, liq_map) -> Primitives:
    """One tick: update memory, then produce the primitive snapshot."""
    acc.add(epoch_s, price, minute_key)

    prim = Primitives(ts_et=ts_et, price=price)

    # ── velocity ──────────────────────────────────────────────────────────────
    prim.roc_raw = acc.current_roc(epoch_s)
    prim.roc_typical = acc.typical_roc(epoch_s)
    if prim.roc_raw is not None and prim.roc_typical:
        v = prim.roc_raw / prim.roc_typical
        prim.velocity = max(-VELOCITY_CAP, min(VELOCITY_CAP, v))
    prim.velocity_prev = acc.last_velocity
    acc.last_velocity = prim.velocity

    # ── magnitude (read-only off VolatilityState) ────────────────────────────
    prim.atr = float(getattr(vol_state, "atr_current", 0.0) or 0.0)
    prim.atr_normalized = float(getattr(vol_state, "atr_normalized", 0.0) or 0.0)
    prim.is_expanding = bool(getattr(vol_state, "is_expanding", False))
    prim.bb_width_pct = float(getattr(vol_state, "bb_width_pct", 0.5) or 0.5)
    fb = acc.forming
    if fb.ticks >= 2 and prim.atr > 0:
        prim.forming_range_atr = (fb.high - fb.low) / prim.atr

    # ── position ──────────────────────────────────────────────────────────────
    vwap = float(getattr(vol_state, "vwap", 0.0) or 0.0)
    if vwap > 0:
        prim.vwap_dist_pct = (price - vwap) / vwap
    prim.price_vs_bb = str(getattr(vol_state, "price_vs_bb", "INSIDE"))
    if fb.ticks >= 2 and fb.high > fb.low:
        prim.intrabar_pos = (price - fb.low) / (fb.high - fb.low)

    prim.named_levels = _named_levels_from_map(liq_map, price, prim.atr)
    above = [l for l in prim.named_levels if l.side == "above"]
    below = [l for l in prim.named_levels if l.side == "below"]
    prim.nearest_named_above = min(above, key=lambda l: l.dist_pct) if above else None
    prim.nearest_named_below = min(below, key=lambda l: l.dist_pct) if below else None
    return prim
