#!/usr/bin/env python3
"""
tests/check_character_band_study.py  v1.0
v1.0  2026-09-11  r354 / CHR.1 — the band study must read the sample honestly.

🔴 WHAT IT PROTECTS. The whole reason `BANDS_SET` is False is that the old
numbers were calibrated against the WRONG QUANTITY (an intrabar wick ratio,
not directional persistence). Replacing them with numbers derived carelessly
from the right quantity would be the same error with a fresh coat.

  C1  a NULL axis is excluded and COUNTED — never read as 0.0, which would
      drag every percentile toward the ranging band
  C2  percentiles are cut points on the observed data, not constants
  C3  per-symbol output exists, because one global pair of bands can label
      two symbols wrongly in OPPOSITE directions
  C4  an empty window says so rather than deriving bands from nothing
  C5  the report states it is descriptive and that BANDS_SET is the
      operator's call in the SAME commit as the numbers
"""
import io
import os
import sys
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
FAILS = []


def check(name, ok, detail=""):
    print("  {:<4} {}  {}".format(name, "PASS" if ok else "FAIL", detail))
    if not ok:
        FAILS.append(name)


def main():
    try:
        import character_band_study as C
    except Exception as exc:                                    # noqa: BLE001
        print("  FAIL  character_band_study did not import: {}".format(exc))
        return 1

    rows = [{"symbol": "A", "efficiency": 0.9, "vol_ratio": 1.1},
            {"symbol": "A", "efficiency": None, "vol_ratio": 1.0},
            {"symbol": "B", "efficiency": 0.1, "vol_ratio": None}]
    eff, vr, nulls = C.coverage(rows)
    check("C1", nulls["efficiency"] == 1 and nulls["vol_ratio"] == 1
          and 0.0 not in eff["A"] and len(eff["A"]) == 1,
          "nulls counted {} and excluded".format(dict(nulls)))

    vals = [0.0, 0.25, 0.5, 0.75, 1.0]
    check("C2", C.pct(vals, .50) == 0.5 and C.pct(vals, .90) == 1.0,
          "median {} p90 {}".format(C.pct(vals, .50), C.pct(vals, .90)))

    buf = io.StringIO()
    with redirect_stdout(buf):
        C.render({"A": [0.8] * 30, "B": [0.2] * 30},
                 {"A": [1.0] * 30, "B": [1.0] * 30}, {}, "w")
    out = buf.getvalue()
    check("C3", "PER SYMBOL" in out and "OPPOSITE" in out,
          "per-symbol section and the divergence warning are present")

    buf2 = io.StringIO()
    with redirect_stdout(buf2):
        C.render({}, {}, {}, "w")
    check("C4", "nothing to derive from" in buf2.getvalue(),
          "empty window named")

    check("C5", "descriptive" in out.lower() and "BANDS_SET" in out
          and "SAME commit" in out,
          "descriptive + same-commit rule stated")

    print("")
    if FAILS:
        print("FAILED: {}".format(", ".join(FAILS)))
        return 1
    print("ALL PASS (5)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
