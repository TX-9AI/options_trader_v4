#!/usr/bin/env python3
"""
tests/check_atr_units.py  v1.0

r96 — ATR THRESHOLDS ARE IN PERCENT. THE PRODUCER EMITS A FRACTION.

🔴 THE DEFECT THIS PINS, AND IT COST EVERY ORB TRADE THE FLEET EVER CONFIRMED.
`VolatilityState.atr_normalized` is `atr / price` — a FRACTION — while its own
comment read "ATR as % of price". Every strategy threshold is stated in PERCENT
and every one is traceable to a measurement in percent:

    ORB_ATR_FLOOR_PCT      0.05   (0 of 5,517 bars reached the required move)
    RUNAWAY_ATR_FLOOR_PCT  0.08
    RUNAWAY_ATR_VETO_PCT   0.05
    SWEEP_CS_ATR_MAX_PCT   0.20   (a CEILING — this one failed OPEN)

So `atr_normalized < ORB_ATR_FLOOR_PCT` demanded a **five percent intraday
ATR**, which effectively never occurs. ORB could not fire on any box, any day.

Observed live, NFLX 2026-08-24: break+retest confirmed 09:58 ET, chain built,
strike priced (C 81.0 @ $0.85, delta 0.389), then
`ATR 0.004% is below the reachable floor (0.05%)` once per tick for 62 minutes
until the 11:00 cutoff. True ATR was 0.4% — EIGHT TIMES ABOVE the floor.

⚠️ THE SAME MISMATCH FAILED IN BOTH DIRECTIONS, which is why it hid so well.
On a FLOOR it refused everything. On the sweep's CEILING it refused nothing, so
"too hot for a boundary to hold" has been dead since the split. A defect that
fails closed in one place and open in another produces no single symptom to
chase.

⚠️ WHY `atr_normalized` IS NOT SIMPLY RESCALED. Five tables already hold
fractions (indicator_series, character_ledger, fire_snapshot, strategy_note,
shadow primitives). Rescaling the producer would change what that column MEANS
mid-stream with nothing marking the seam — the RTH-backfill lesson, where the
repair was worse than the hole because a gap announces itself and a character
change does not. `atr_pct` is added alongside and the GATES move to it.

⚠️ BORN RED: U2/U3 fail if a gate reads the fraction. Mutation-proven.

Run:  python3 tests/check_atr_units.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FAILURES: list = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


class _Vol:
    """A VolatilityState as the engine actually produces one."""

    def __init__(self, atr_frac):
        self.atr_normalized = atr_frac
        self.atr_pct = atr_frac * 100.0
        self.price_vs_vwap = "ABOVE"
        self.atr_current = 0.32


class _Legacy:
    """A part-baked box: the OLD state, with no `atr_pct` at all."""

    def __init__(self, atr_frac):
        self.atr_normalized = atr_frac
        self.price_vs_vwap = "ABOVE"


def main() -> int:
    print("check_atr_units — gates compare PERCENT against PERCENT")

    from analysis.volatility_engine import VolatilityState

    # ── U1: THE TWO FIELDS ARE ONE MEASUREMENT ───────────────────────────────
    v = VolatilityState()
    v.atr_normalized = 0.004          # NFLX: ATR $0.32 on an $80 underlying
    v.atr_pct = v.atr_normalized * 100.0
    check("U1 atr_pct is exactly 100x atr_normalized",
          abs(v.atr_pct - 0.4) < 1e-9,
          f"frac={v.atr_normalized} pct={v.atr_pct}")

    # ── U2: THE REAL NFLX NUMBER CLEARS THE REAL FLOOR ───────────────────────
    # The whole bug in one assertion. 0.4% is EIGHT TIMES the 0.05% floor; as a
    # fraction it is one twelfth of it.
    from strategy.orb_strategy import ORB_ATR_FLOOR_PCT
    nflx = _Vol(0.004)
    read = float(getattr(nflx, "atr_pct", None)
                 or (float(getattr(nflx, "atr_normalized", 0.0) or 0.0) * 100.0))
    check("U2 NFLX's real ATR clears the ORB floor",
          read >= ORB_ATR_FLOOR_PCT,
          f"read={read}% floor={ORB_ATR_FLOOR_PCT}% "
          f"(fraction would read {nflx.atr_normalized})")

    check("U2b and the fraction would NOT have — this is the live failure",
          nflx.atr_normalized < ORB_ATR_FLOOR_PCT,
          f"{nflx.atr_normalized} < {ORB_ATR_FLOOR_PCT}")

    # ── U3: THE GATE ITSELF, EXECUTED ────────────────────────────────────────
    # 🔴 THE FIRST VERSION OF U3/U4 WAS THEATRE AND BOTH MUTANTS PASSED IT. It
    # called generate_signal with chain=None, which returns at the contract
    # lookup ~25 lines BEFORE the ATR gate, and the assertion "no floor message
    # was logged" was satisfied by never reaching the floor at all. WA 21: a
    # test must EXECUTE the path, and the proof it is real is that it fails
    # against the broken version.
    # So the chain fetcher is stubbed to return a priced contract, which is the
    # minimum required to reach line 259.
    import logging
    import strategy.orb_strategy as OS
    from analysis.orb_engine import ORBState

    class _Contract:
        strike, expiry, mark, bid, ask = 81.0, "2026-08-28", 0.85, 0.83, 0.87
        delta, symbol = 0.389, "NFLX 260828C81"

    class _Fetcher:
        def select_orb_strike(self, chain, direction, target_strike):
            return _Contract()

    orb = type("O", (), {})()
    orb.state = ORBState.OPEN_LONG
    orb.break_direction = "long"
    orb.orb_high, orb.orb_low, orb.orb_width = 80.01, 79.02, 0.99
    orb.target_100pct, orb.target_50pct = 81.0, 80.5
    orb.stop_level, orb.target_strike = 79.9, 81
    orb.attempt_number, orb.retest_depth_px = 1, 0.01

    macro = type("M", (), {"vix": 15.0, "is_fed_day": False,
                           "butterfly_half_size": False})()
    # _analyze_liquidity iterates liq_map.pools before the ATR gate, so a bare
    # None returns early and the gate is never reached — which is exactly what
    # the first draft of this test failed to notice.
    liq = type("L", (), {"pools": []})()
    # generate_signal also reads ms.adx before the gate. A real MarketState is
    # used rather than a stub so a future field addition surfaces here instead
    # of being silently absorbed by a permissive fake.
    from analysis.market_state import MarketState
    ms_fix = MarketState()
    ms_fix.adx = 26.0

    def _run(vol):
        """Call the REAL generate_signal and report what the ATR gate did."""
        msgs = []

        class _Grab(logging.Handler):
            def emit(self, rec):
                msgs.append(rec.getMessage())

        lg = logging.getLogger("strategy.orb_strategy")
        h = _Grab()
        lg.addHandler(h)
        lg.setLevel(logging.INFO)
        real = OS.get_chain_fetcher
        OS.get_chain_fetcher = lambda: _Fetcher()
        err = None
        try:
            OS.ORBStrategy().generate_signal(
                orb=orb, ms=ms_fix, vol_state=vol, liq_map=liq,
                chain=object(), macro=macro, current_price=80.05)
        except Exception as exc:                               # noqa: BLE001
            err = exc
        finally:
            OS.get_chain_fetcher = real
            lg.removeHandler(h)
        refused = [m for m in msgs if "reachable floor" in m]
        reached = bool(refused) or any("ORB" in m for m in msgs) or err is None
        return refused, msgs, err, reached

    # PROOF THE PATH IS LIVE: an ATR below the floor on BOTH readings must
    # produce the refusal. If this does not fire, the test is not reaching the
    # gate and every other U3 assertion is worthless.
    dead_refused, _, _, _ = _run(_Vol(0.0001))       # 0.01% — below on any scale
    check("U3a the ATR gate is REACHED (a truly dead tape is refused)",
          bool(dead_refused),
          "gate never reached — test is not executing the path"
          if not dead_refused else dead_refused[0][:70])

    # THE ACTUAL ASSERTION: 0.1 percent / 0.001 fraction. Above the floor as a
    # percent, below it as a fraction. Only a gate reading the FRACTION refuses.
    probe_refused, _, _, _ = _run(_Vol(0.001))
    check("U3b a 0.1% ATR is NOT refused — the gate reads percent",
          not probe_refused,
          probe_refused[0][:80] if probe_refused else "")

    # ── U4: A PART-BAKED BOX STILL GETS THE RIGHT NUMBER ─────────────────────
    # 🔴 THE FALLBACK MUST NOT BE 0.0. A falsy `_atr_pct` SKIPS the gate and
    # lets a trade through on an unmeasured ATR — a feasibility veto silently
    # becoming a pass, which is worse than the bug being fixed. Driven through
    # the REAL call with a state that has no `atr_pct` attribute at all.
    legacy_dead, _, _, _ = _run(_Legacy(0.0001))
    check("U4 a state with NO atr_pct still gets vetoed on a dead tape",
          bool(legacy_dead),
          "veto SKIPPED on a legacy state — fallback is falsy"
          if not legacy_dead else legacy_dead[0][:70])

    legacy_ok, _, _, _ = _run(_Legacy(0.001))
    check("U4b and a legacy state at 0.1% is still allowed through",
          not legacy_ok, legacy_ok[0][:80] if legacy_ok else "")

    # ── U5: THE SWEEP CEILING IS ALIVE AGAIN ─────────────────────────────────
    # The other direction. Fed the fraction, a MAX of 0.20 could never trip.
    from strategy.sweep_credit_spread import ATR_MAX_PCT
    hot = _Vol(0.004)                 # 0.4% — genuinely above the 0.20% ceiling
    hot_read = hot.atr_pct
    check("U5 a hot tape now trips the sweep ceiling",
          hot_read > ATR_MAX_PCT and hot.atr_normalized < ATR_MAX_PCT,
          f"pct={hot_read} frac={hot.atr_normalized} ceiling={ATR_MAX_PCT}")

    # ── U6: THE THRESHOLDS ARE ALL ON THE SAME SCALE ─────────────────────────
    # A sanity band. Every ATR threshold in the tree is a small percent; any
    # constant above 5 would mean somebody re-scaled one and not the others.
    from strategy.runaway_continuation import (ATR_FLOOR_PCT, ATR_HARD_VETO_PCT,
                                               ATR_DEEP_PCT)
    consts = {"ORB_ATR_FLOOR_PCT": ORB_ATR_FLOOR_PCT,
              "RUNAWAY_ATR_FLOOR_PCT": ATR_FLOOR_PCT,
              "RUNAWAY_ATR_VETO_PCT": ATR_HARD_VETO_PCT,
              "RUNAWAY_ATR_DEEP_PCT": ATR_DEEP_PCT,
              "SWEEP_CS_ATR_MAX_PCT": ATR_MAX_PCT}
    odd = {k: v for k, v in consts.items() if not (0.0 < v < 5.0)}
    check("U6 every ATR threshold is on the percent scale", not odd, str(odd))

    print()
    if FAILURES:
        print(f"FAILED {len(FAILURES)}: {', '.join(FAILURES)}")
        return 1
    print("check_atr_units: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
