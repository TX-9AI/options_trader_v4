#!/usr/bin/env python3
"""
tests/check_snapshot_pin.py  v1.0
v1.0  2026-09-04  r243 — THE PIN AND ITS EM FRACTION REACH THE SNAPSHOT.

🔴 WHY. Operator, 2026-09-04, after the stop-removal and window cases both
failed on evidence: *"then that leaves the EM variable as our last hope of
raising our win rate. What is the furthest EM that this trade will fire on?"*
The band is 0.30–1.00 and hard-capped — but whether the SEVEN winners sat lower
in it than the THIRTEEN losers was UNANSWERABLE: `plan_check` carries
`pin_em_fraction` on every tick and has NO trade_id, and `fire_snapshot` is
keyed BY trade_id and carried no pin and no EM.

🔑 SAME SHAPE AS r240 — a field computed, used for a DECISION, and never
written where the OUTCOME could be joined to it. The bridge existed; it just
did not carry the field.

⚠️ NOTHING ACCRUES RETROACTIVELY. The 20 butterflies already banked stay
unmeasurable. This starts the collection.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name)


class _Gex:
    def __init__(self, pin):
        self.pin_strike = pin


def main():
    from derived.snapshot import SnapshotEngine
    from strategy.gex_pin_butterfly import expected_move, EM_MIN_FRAC, EM_MAX_FRAC

    e = SnapshotEngine.__new__(SnapshotEngine)
    e.symbol = "TEST"

    # ══ S1 — THE KEYS ARE ALWAYS PRESENT ══════════════════════════════════
    # ⚠️ This file's own contract: every key is emitted even when null, so a
    # study can tell "measured as absent" from "did not exist in that era".
    p = e.build_payload({"price": 100.0, "atm_iv": 0.30})
    check("S1 pin_strike and pin_em_fraction are always emitted",
          "pin_strike" in p and "pin_em_fraction" in p)
    check("S1b unmeasurable reads None, NEVER 0.0",
          p["pin_strike"] is None and p["pin_em_fraction"] is None,
          f"{p['pin_strike']!r} {p['pin_em_fraction']!r}")

    # ══ S2 — THE FRACTION MATCHES THE GATE'S OWN ARITHMETIC ═══════════════
    # 🔴 THE POINT OF THE WHOLE REVISION. If this reproduced the fraction with
    # a second definition, the study would compare a number the gate never saw
    # against an outcome the gate decided — worse than no field at all.
    price, iv, pin = 100.0, 0.30, 103.0
    got = e.build_payload({"price": price, "atm_iv": iv, "gex": _Gex(pin)})
    want = abs(pin - price) / expected_move(price, iv)
    check("S2 the fraction equals |pin - spot| / expected_move()",
          abs(got["pin_em_fraction"] - want) < 1e-9,
          f"{got['pin_em_fraction']:.6f} vs {want:.6f}")
    check("S2b and the pin itself round-trips", got["pin_strike"] == pin)

    # ══ S3 — A PIN AT THE MONEY IS 0.0, NOT None ══════════════════════════
    # ⚠️ The opposite fact from S1b and it must not collapse into it: a pin
    # exactly at spot is a MEASURED zero and belongs in the sample.
    atm = e.build_payload({"price": price, "atm_iv": iv, "gex": _Gex(price)})
    check("S3 a pin AT spot reads 0.0, distinct from unmeasurable",
          atm["pin_em_fraction"] == 0.0, repr(atm["pin_em_fraction"]))

    # ══ S4 — IT NEVER RAISES INTO THE FIRE PATH ═══════════════════════════
    # 🔴 `capture()` runs on every fill. A study field that can throw would
    # cost a trade its snapshot — or worse — for a number nobody needs live.
    for bad in ({"price": None, "atm_iv": 0.3, "gex": _Gex(100.0)},
                {"price": 100.0, "atm_iv": None, "gex": _Gex(100.0)},
                {"price": 100.0, "atm_iv": 0.3, "gex": object()},
                {}):
        try:
            e.build_payload(bad)
        except Exception as exc:                               # noqa: BLE001
            check("S4 build_payload never raises on a degenerate ctx", False,
                  f"{type(exc).__name__}: {exc}")
            break
    else:
        check("S4 build_payload never raises on a degenerate ctx", True)

    # ══ S5 — THE BAND IS STILL HARD-CAPPED ════════════════════════════════
    # ⚠️ r208: `cap=EM_MAX_FRAC` makes the relaxed value equal the base, so the
    # ceiling cannot widen. Recording the fraction must not become a reason to
    # loosen the gate that made it worth recording.
    check("S5 the EM band is unchanged at 0.30-1.00",
          EM_MIN_FRAC == 0.30 and EM_MAX_FRAC == 1.00,
          f"{EM_MIN_FRAC}-{EM_MAX_FRAC}")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — 7 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
