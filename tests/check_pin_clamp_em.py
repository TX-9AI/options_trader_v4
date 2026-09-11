#!/usr/bin/env python3
"""
tests/check_pin_clamp_em.py  v1.0
v1.0  2026-09-10  r352 / BFLY.1 — the pin must be selected in the unit the
      strategy judges it in.

🔴 THE DEFECT. `compute_gex` clamped `pin_strike` to within 3% OF SPOT while
`gex_pin_butterfly` judges it in EXPECTED MOVES (`pin_em_fraction`, window
0.30-1.00). Two scales with no relationship: on SPX an expected move is about
0.35% of price, so a 3% clamp admits pins up to ~8.5 EM away — candidates the
strategy can only refuse.

⚠️ AND THE DATA SAYS EXACTLY THAT. Over 2026-09-05..09-10 `pin_em_fraction`
was the ONLY failing rung on 2,412 butterfly ticks — 52% of every "exactly one
gate short" — with fail percentiles p25 1.10, MEDIAN 1.55, p75 1.94 against a
ceiling of 1.00. Not near misses under a strict rule: pins that were never
reachable.

🔑 THE EM WINDOW IS NOT LOOSENED. The trade's premise is that price TRAVELS to
the pin and sits; the ceiling states it. Selecting in the same unit makes the
candidate reachable by construction.

  P1  with an EM, a pin beyond 1.00 EM is NOT selected
  P2  with an EM, a pin inside 1.00 EM IS selected
  P3  the percent clamp still applies when no EM is given — a missing ATM IV
      degrades to the old rule, it does not remove the clamp
  P4  the basis is RECORDED ("em" / "pct"), because the two can differ by an
      order of magnitude and a reader must not have to guess
  P5  the unbounded argmax is still recorded — the clamp narrows the choice,
      it never hides what the chain actually published
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
FAILS = []


def check(name, ok, detail=""):
    print("  {:<4} {}  {}".format(name, "PASS" if ok else "FAIL", detail))
    if not ok:
        FAILS.append(name)


class _C:
    def __init__(self, strike, oi=100, gamma=0.01, opt="call"):
        self.strike = strike
        self.open_interest = oi
        self.gamma = gamma
        self.option_type = opt
        self.mark = 1.0
        self.bid = 0.9
        self.ask = 1.1
        self.iv = 0.2


class _Chain:
    def __init__(self, cs):
        self.calls = [c for c in cs if c.option_type == "call"]
        self.puts = [c for c in cs if c.option_type == "put"]
        self.contracts = cs


def main():
    # ⚠️ THE BROKER SDK IS STUBBED, NOT REQUIRED. `gex_data` imports
    # `tastytrade` for a type annotation; that package lives on the BOXES while
    # this gate runs on CONTROL at land time, and a red meaning "wrong host" is
    # a red the reader learns to skip (r340). The arithmetic under test touches
    # none of it.
    import types

    class _Any:
        def __init__(self, *a, **k):
            pass

        def __getattr__(self, _n):
            return _Any()

        def __call__(self, *a, **k):
            return _Any()

    class _Mod(types.ModuleType):
        def __getattr__(self, _n):
            return _Any()

    for _m in ("tastytrade", "tastytrade.instruments", "tastytrade.order",
               "tastytrade.session", "tastytrade.dxfeed"):
        sys.modules.setdefault(_m, _Mod(_m))
    try:
        from data.gex_data import compute_gex, PIN_MAX_DIST_EM
    except Exception as exc:                                    # noqa: BLE001
        print("  FAIL  gex_data lacks the EM clamp: {}".format(exc))
        return 1

    spot = 7600.0
    em = 26.0                      # ~0.34% of spot, an SPX-shaped expected move
    # a huge-gamma strike 200 points out: 7.7 EM away, but only 2.6% of spot,
    # so the OLD clamp admitted it and the strategy could only refuse it.
    far = _C(7800.0, oi=100000, gamma=0.05)
    near = _C(7615.0, oi=500, gamma=0.02)
    chain = _Chain([far, near, _C(7590.0, opt="put"), _C(7810.0, opt="put")])

    snap = compute_gex(chain, spot, em=em)
    check("P1", snap.pin_strike != far.strike,
          "far pin ({:.0f}, {:.1f} EM) not selected -> pin {:.0f}".format(
              far.strike, abs(far.strike - spot) / em, snap.pin_strike))
    check("P2", snap.pin_strike == near.strike,
          "pin = {:.0f} ({:.2f} EM)".format(
              snap.pin_strike, abs(snap.pin_strike - spot) / em))

    snap2 = compute_gex(chain, spot)          # no EM -> percent clamp
    check("P3", snap2.pin_strike == far.strike
          and getattr(snap2, "pin_clamp_basis", "") == "pct",
          "no EM -> basis {!r}, pin {:.0f} (the old 3% rule)".format(
              getattr(snap2, "pin_clamp_basis", ""), snap2.pin_strike))

    check("P4", getattr(snap, "pin_clamp_basis", "") == "em"
          and getattr(snap, "pin_clamp_limit", 0) > 0,
          "basis={!r} limit={}".format(getattr(snap, "pin_clamp_basis", ""),
                                       getattr(snap, "pin_clamp_limit", 0)))

    check("P5", snap.pin_strike_raw == far.strike and snap.pin_dist_pct > 0,
          "raw argmax {:.0f} still recorded".format(snap.pin_strike_raw))

    print("")
    if FAILS:
        print("FAILED: {}".format(", ".join(FAILS)))
        return 1
    print("ALL PASS (5)   PIN_MAX_DIST_EM={}".format(PIN_MAX_DIST_EM))
    return 0


if __name__ == "__main__":
    sys.exit(main())
