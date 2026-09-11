#!/usr/bin/env python3
"""
tests/check_realised_vol.py  v1.0
v1.0  2026-09-11  r355 / CHR.2 — the realised-vol ports must have a producer.

🔴 WHAT WAS WRONG. `main.py` declared `realised_vol_cc` and
`realised_vol_parkinson` with `setdefault(..., None)` and NOTHING IN THE TREE
EVER COMPUTED THEM. So the character engine's `cc` was None on every tick:
`_vol_hist` never appended, `base` never formed, `volatility_state` returned
None, and **vol_ratio was null on all 22,562 sample rows over
2026-09-05..09-10 across fifteen symbols.** That is HALF the engine —
`vol_ratio` produces `volatile` and `compressing` and `read_character` checks
it FIRST — plus `close_capture`, whose inputs are the same two keys.

  R1  a moving tape produces a POSITIVE cc; a flat one produces 0.0, and an
      unmeasurable one produces None — three distinct answers, never merged
  R2  Parkinson is positive on a ranging tape and 0.0 when every bar has no
      range; a crossed bar (high < low) is SKIPPED, not clamped
  R3  the two are on the SAME per-bar scale, so `close_capture` compares like
      with like — a tape that travels but closes flat reads LOW cc / HIGH pk
  R4  neither is annualised: scaling the window's prices leaves both unchanged
      in ratio terms, which is all `volatility_state` consumes
  R5  main.py actually ASSIGNS both keys — the defect was a declared port with
      no writer, so the gate checks the write, not the declaration
"""
import ast
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
FAILS = []


def check(name, ok, detail=""):
    print("  {:<4} {}  {}".format(name, "PASS" if ok else "FAIL", detail))
    if not ok:
        FAILS.append(name)


def main():
    try:
        from analysis.character import (realised_vol_cc, realised_vol_parkinson,
                                        close_capture)
    except Exception as exc:                                    # noqa: BLE001
        print("  FAIL  estimators missing: {}".format(exc))
        return 1

    moving = [100.0, 101.0, 100.5, 102.0, 101.0, 103.0, 102.5, 104.0]
    flat = [100.0] * 8
    cc_m, cc_f = realised_vol_cc(moving), realised_vol_cc(flat)
    check("R1", cc_m and cc_m > 0 and cc_f == 0.0
          and realised_vol_cc([100.0]) is None
          and realised_vol_cc(None) is None,
          "moving {:.5f} · flat {} · short None".format(cc_m, cc_f))

    hs = [101.0, 102.0, 101.5, 103.0, 102.0, 104.0]
    ls = [99.0, 100.0, 99.5, 101.0, 100.0, 102.0]
    pk = realised_vol_parkinson(hs, ls)
    pk_flat = realised_vol_parkinson([100.0] * 6, [100.0] * 6)
    # a crossed bar must be skipped: with 3 good bars left it still measures
    pk_crossed = realised_vol_parkinson(hs[:3] + [90.0], ls[:3] + [95.0])
    check("R2", pk and pk > 0 and pk_flat == 0.0 and pk_crossed is not None,
          "ranging {:.5f} · flat {} · crossed-bar skipped".format(pk, pk_flat))

    # R3 — travels but closes flat: cc near zero, pk clearly positive
    closes = [100.0] * 6
    hi = [102.0] * 6
    lo = [98.0] * 6
    cc_t, pk_t = realised_vol_cc(closes), realised_vol_parkinson(hi, lo)
    check("R3", cc_t == 0.0 and pk_t > 0 and close_capture(cc_t, pk_t) is not None,
          "closes flat cc={} but pk={:.5f} — the gap is the signal".format(
              cc_t, pk_t))

    # R4 — scale invariance of the ratio the consumer uses
    scaled = [p * 7.0 for p in moving]
    check("R4", abs(realised_vol_cc(scaled) - cc_m) < 1e-12,
          "price scale x7 leaves cc unchanged (log returns)")

    src = open(os.path.join(REPO, "main.py"), encoding="utf-8").read()
    code = "\n".join(l for l in src.splitlines()
                     if not l.lstrip().startswith("#"))
    writes = ('ctx["realised_vol_cc"] =' in code
              and 'ctx["realised_vol_parkinson"] =' in code)
    check("R5", writes, "main.py assigns both keys, not only setdefault")

    print("")
    if FAILS:
        print("FAILED: {}".format(", ".join(FAILS)))
        return 1
    print("ALL PASS (5)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
