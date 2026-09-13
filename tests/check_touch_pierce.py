#!/usr/bin/env python3
"""
tests/check_touch_pierce.py  v1.1
v1.1  2026-09-12  r378 — P1 GAINS A CHANNEL AND P2/P4 ARE RE-DERIVED, because
      r378 made a tine event require the contact bar to CLOSE back inside the
      channel and a pool with no opposite rail can no longer produce an event at
      all. P1's tape is unchanged; it is given the far rail it always implied.
      🔴 P2 WAS *"a STATIC pool is unaffected"*, ASSERTED THROUGH `_detect_touch`
      — and that door is now shut by construction: `inside_channel_at` returns
      None for a pool that does not move, the caller emits nothing, so the old P2
      would fail for a reason that has nothing to do with the pierce arithmetic
      it was pinning. Keeping it would be a check red on a PROPERTY OF THE TARGET
      rather than a defect in it, which is the CV.1 shape that teaches a reader
      to skip reds.
      🔑 SO THE PROPERTY MOVES TO WHERE IT ACTUALLY LIVES. The r377 guarantee is
      that `price_at()` returns `price` for a non-moving pool, which makes the
      at-touch and at-now measurements identical BY CONSTRUCTION — P2b asserts
      that directly instead of through a round-trip that no longer exists. And
      the NEW P2 pins the r378 property worth guarding: NO CHANNEL, NO EVENT.
      ⚠️ THE r378 BEHAVIOUR ITSELF IS PINNED IN `check_sweep_event`, not here.
      This file stays r377's control: the pierce is measured where the touch was
      judged.
v1.0  2026-09-12  r377 / LVL.9 — A TOUCH IS JUDGED AND MEASURED AT THE SAME
      INSTANT.

🔴 THE DEFECT. `_detect_touch` tests contact with `pool.price_at(ts)` inside the
per-bar loop — time-aware, and always was. It then measured the DEPTH as
`abs(extreme - pool.price)`: the extreme from whichever bar it printed on,
against the rail's position NOW. For a STATIC pool those are the same number and
the code was correct. For a MOVING tine they differ by slope x elapsed bars, and
the defect arrived with r163 when tines became pools and nothing revisited the
arithmetic — half time-aware is the whole bug.

📊 MEASURED BEFORE IT WAS CHANGED, on 19,997 distinct 1h fork samples across 15
symbols and 5 sessions: at the full 30-bar lookback the error runs a median of
10.3% of the admissible band, p90 27.1%, and **on 57.9% of samples it alone
exceeds `MIN_REJECTION_PCT`** — drift by itself could carry a touch with no real
pierce past the floor. Concentrated rather than diffuse: AMD's median is 78.1%
of the band against QQQ's 1.7%.

WHY THE GATES CARE. `rej` feeds `MIN_REJECTION_PCT` (0.0002) and
`MAX_REJECTION_PCT` (0.0025), and the ceiling exists because the depth genuinely
predicts: shallow <0.10% survived 33%, 0.10-0.25% 34%, 0.25-0.50% 21%, deep
>0.50% 19%.

  P1  a MOVING tine's pierce is measured against the rail where it STOOD when
      the extreme printed, not where it sits now
  P2  a pool with NO opposite rail emits NO event — the channel question is
      unanswerable and an unanswerable test must never read as satisfied (r378)
  P2b a STATIC pool is UNAFFECTED — `price_at()` returns `price`, so the
      at-touch and at-now measurements are identical BY CONSTRUCTION. The r377
      control, asserted where the guarantee lives rather than through
      `_detect_touch`, which a static pool can no longer enter.
  P3  the legacy value is carried, so the correction is measurable on live tape
  P4  ...and for a static pool it EQUALS the live one, which makes a non-zero
      delta by itself evidence that the pool was a tine
  P5  nothing GATES on the legacy value — record-only, or this quietly becomes
      a second opinion competing with the verdict (§31)
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
FAILS = []


def check(n, ok, d=""):
    print("  {:<4} {}  {}".format(n, "PASS" if ok else "FAIL", d))
    if not ok:
        FAILS.append(n)


class _Idx(list):
    pass


class _TS:
    """Minimal stand-in for a pandas timestamp — only .timestamp() is used."""
    def __init__(self, t): self._t = t
    def timestamp(self): return self._t


class _Col(list):
    def astype(self, _): return self
    def tolist(self): return list(self)


class _DF:
    """The two-column frame `_detect_touch` reads, and nothing more."""
    def __init__(self, highs, lows, closes, stamps):
        self._d = {"high": _Col(highs), "low": _Col(lows), "close": _Col(closes)}
        self.index = [_TS(t) for t in stamps]

    def __len__(self): return len(self.index)

    def __getitem__(self, k): return self._d[k]

    def tail(self, _n): return self


def main():
    print("check_touch_pierce — the pierce is measured where the touch was judged")
    try:
        from analysis.liquidity_mapper import LiquidityPool, _detect_touch
    except Exception as exc:                                     # noqa: BLE001
        print("  FAIL  liquidity_mapper did not import: {}".format(exc))
        return 1

    # ── the tape: 10 one-minute bars. The extreme prints on the FIRST bar and
    # nothing reaches the rail afterwards, so "now" is nine bars away from the
    # instant that matters — the shape the defect turns into a wrong number.
    n = 10
    t0 = 1_700_000_000.0
    stamps = [t0 + 60.0 * i for i in range(n)]
    highs = [100.0] + [90.0] * (n - 1)
    lows = [89.0] * n
    closes = [90.0] * n
    df = _DF(highs, lows, closes, stamps)

    # A RISING upper tine: 1.0/min. At the first bar it stood at 100.0 - 9.0 =
    # 91.0 and the bar's high of 100.0 pierced it by 9.0. By the last bar the
    # rail is 100.0, so the old arithmetic reports a pierce of 0.0 — a real
    # 9-point piercing touch measured as no pierce at all.
    # r378 — AND IT IS GIVEN THE FAR RAIL IT ALWAYS IMPLIED. The lower rail sits
    # 20 points under the upper one and rises with it, so at the first bar the
    # channel is [71.0, 91.0] and that bar's close of 90.0 is INSIDE it: the
    # contact is taken back on its own bar, which is the r378 event. The pierce
    # arithmetic under test is untouched by this.
    tine = LiquidityPool(price=100.0, kind="high", name="1h upper tine",
                         timeframe="1h")
    tine.moving = True
    tine.slope_per_min = 1.0
    tine.as_of = stamps[-1]
    tine.opp_price = 80.0
    tine.opp_slope_per_min = 1.0

    sw = _detect_touch(tine, df, stamps[-1])
    if sw is None:
        print("  FAIL  P1 no touch detected on a tape built to contain one")
        return 1

    px = closes[-1]
    want_at_touch = abs(100.0 - 91.0) / px      # judged where the rail stood
    want_at_now = abs(100.0 - 100.0) / px       # what the old code reported
    got = float(sw.rejection_pct)
    check("P1", abs(got - want_at_touch) < 1e-9,
          "moving tine: got {:.6f}, at-touch {:.6f}, at-now {:.6f}".format(
              got, want_at_touch, want_at_now))

    # P3/P4 — the legacy value rides along for measurement.
    legacy = float(getattr(sw, "rejection_pct_legacy", -1.0))
    check("P3", abs(legacy - want_at_now) < 1e-9,
          "legacy carried: {:.6f} (expected the old at-now value)".format(legacy))

    # ── P2 — NO CHANNEL, NO EVENT (r378). A pool that does not move has no
    # far rail, so "did the bar close back inside the channel" has no answer —
    # and an unanswerable test must not fire. This is the guard against the
    # silent-refusal half: `inside_channel_at` returns None, and the detector
    # must treat None as "cannot fire", never as "closed outside".
    stat = LiquidityPool(price=91.0, kind="high", name="PDH", timeframe="1h")
    sw2 = _detect_touch(stat, df, stamps[-1])
    check("P2", sw2 is None,
          "a pool with no channel yields no event (got {})".format(
              "None" if sw2 is None else "an event"))

    # ── P2b — THE r377 CONTROL, at the guarantee itself. A non-moving pool's
    # `price_at()` is its `price` at EVERY instant, so the at-touch rail and the
    # at-now rail are the same number and the pierce correction cannot move a
    # static pool. Asserted here rather than through `_detect_touch`, which
    # static pools no longer enter (P2).
    check("P2b", all(abs(stat.price_at(t) - stat.price) < 1e-12 for t in stamps),
          "static price_at is constant across the window: {:.4f}".format(
              stat.price_at(stamps[0])))

    # ── P4 — and therefore a moving tine is the ONLY way the two can differ, so
    # a non-zero delta is itself evidence the pool moved. Same statement as
    # before, now derived from P2b plus P1's measured delta instead of from a
    # static round-trip.
    check("P4", abs(got - legacy) > 1e-9 and tine.moving,
          "moving tine delta {:.6f} vs static-by-construction 0".format(
              got - legacy))

    # ── P5 — RECORD-ONLY. The legacy value must not reach a verdict.
    # ⚠️ Scoped to a GATE call, not to the token: the strategy has to NAME the
    # field to record it, and r377's own comments name it to explain it, so a
    # string canary would trip on the documentation §5 requires (§20).
    src = open(os.path.join(REPO, "strategy", "sweep_credit_spread.py"),
               encoding="utf-8").read()
    gated = [ln.strip() for ln in src.splitlines()
             if "rejection_pct_legacy" in ln and (".cond(" in ln or "prep.cond" in ln)]
    also = [ln.strip() for ln in src.splitlines()
            if "pierce_legacy" in ln and ".cond(" in ln]
    check("P5", not gated and not also,
          "; ".join((gated + also)[:1]) or "no gate reads the legacy pierce")

    print()
    if FAILS:
        print("FAILED: {}".format(", ".join(FAILS)))
        return 1
    print("ALL PASS ({})".format(6 - len(FAILS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
