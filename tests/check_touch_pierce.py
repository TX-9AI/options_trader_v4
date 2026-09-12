#!/usr/bin/env python3
"""
tests/check_touch_pierce.py  v1.0
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
  P2  a STATIC pool is UNAFFECTED — `price_at()` returns `price`, so the two
      measurements are identical by construction. This is the control: a fix
      that changed static pools too would be a different, larger change than
      the one that was measured and approved.
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
    tine = LiquidityPool(price=100.0, kind="high", name="1h upper tine",
                         timeframe="1h")
    tine.moving = True
    tine.slope_per_min = 1.0
    tine.as_of = stamps[-1]

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

    # ── P2 — THE CONTROL. A static pool must be untouched by this change.
    # `price_at()` returns `price` when the pool does not move, so both
    # measurements are identical by construction — and a fix that moved static
    # pools too would be a larger change than the one that was measured.
    stat = LiquidityPool(price=91.0, kind="high", name="PDH", timeframe="1h")
    sw2 = _detect_touch(stat, df, stamps[-1])
    if sw2 is None:
        print("  FAIL  P2 no touch detected against the static pool")
        return 1
    want_static = abs(100.0 - 91.0) / px
    check("P2", abs(float(sw2.rejection_pct) - want_static) < 1e-9,
          "static pool unaffected: {:.6f}".format(float(sw2.rejection_pct)))
    check("P4", abs(float(getattr(sw2, "rejection_pct_legacy", -1.0))
                    - float(sw2.rejection_pct)) < 1e-9,
          "static: legacy == live, so a non-zero delta means the pool moved")

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
    print("ALL PASS ({})".format(5 - len(FAILS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
