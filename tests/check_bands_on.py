#!/usr/bin/env python3
"""
tests/check_bands_on.py  v1.0
v1.0  2026-09-11  r356 / CHR.1 — the engine is ON, the persistence bands are
      MEASURED, and a later re-fit cannot be contaminated by this one.

🔴 WHY IT WAS OFF FOR THREE WEEKS AND WHY THAT WAS WRONG. r85 set
`BANDS_SET = False` because the old numbers were fitted to an intrabar wick
ratio. Right for a number that GATES. But NOTHING GATES ON CHARACTER — every
reference outside the module and its engine is a warehouse push, a retention
rule or a comment — so the rule bought nothing and cost an engine nobody could
watch. Operator, 2026-09-11: *"I can't see what it's doing if it's not on & it
informs nothing."*

  N1  BANDS_SET is True and the persistence bands are the MEASURED p70/p30
      (0.183 / 0.072), not the retired 0.62 / 0.38
  N2  the bands actually partition: above p70 trending, below p30 ranging, and
      the middle stays NAMELESS — the v3 argmax always produced a winner even
      when there was nothing to choose between, and that is how a near-random
      label got traded
  N3  the vol pair is still PROVISIONAL and labelled as such, because
      `vol_ratio` had no producer until r355 and there is nothing to cut yet
  N4  every ledger row carries `bands`, so transitions from different band
      regimes can be told apart — the `ruleset` lesson
  N5  THE FUTURE RE-FIT CANNOT BE CIRCULAR: the band study reads
      `character_axis_sample` (raw axes, written regardless of BANDS_SET) and
      NEVER `character_ledger` (labels produced BY the bands)
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


def main():
    try:
        from analysis.character import (BANDS_SET, PERSIST_TREND, PERSIST_RANGE,
                                        VOL_EXPAND, VOL_COMPRESS,
                                        read_character, bands_fingerprint)
    except Exception as exc:                                    # noqa: BLE001
        print("  FAIL  character module: {}".format(exc))
        return 1

    check("N1", BANDS_SET is True and abs(PERSIST_TREND - 0.183) < 1e-9
          and abs(PERSIST_RANGE - 0.072) < 1e-9,
          "ON, trend {} / range {}".format(PERSIST_TREND, PERSIST_RANGE))

    hi = read_character(PERSIST_TREND + 0.05, None)
    mid = read_character((PERSIST_TREND + PERSIST_RANGE) / 2, None)
    lo = read_character(PERSIST_RANGE - 0.02, None)
    check("N2", hi == "trending" and lo == "ranging" and mid is None,
          "{} / {} / {} — the middle stays nameless".format(hi, mid, lo))

    src = open(os.path.join(REPO, "analysis", "character.py"),
               encoding="utf-8").read()
    vol_line = [l for l in src.splitlines() if l.startswith("VOL_EXPAND")]
    check("N3", vol_line and "PROVISIONAL" in vol_line[0]
          and VOL_EXPAND == 1.25 and VOL_COMPRESS == 0.80,
          "vol pair untouched and labelled PROVISIONAL")

    eng = open(os.path.join(REPO, "derived", "character_engine.py"),
               encoding="utf-8").read()
    check("N4", "bands       TEXT" in eng and "bands_fingerprint()" in eng
          and "price, bands) VALUES" in eng,
          "ledger column + populated: {}".format(bands_fingerprint()))

    study = open(os.path.join(REPO, "tests", "character_band_study.py"),
                 encoding="utf-8").read()
    code = "\n".join(l for l in study.splitlines()
                     if not l.lstrip().startswith("#"))
    check("N5", "character_axis_sample" in code
          and "character_ledger" not in code,
          "study reads the SAMPLE, never the ledger — no circularity")

    print("")
    if FAILS:
        print("FAILED: {}".format(", ".join(FAILS)))
        return 1
    print("ALL PASS (5)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
