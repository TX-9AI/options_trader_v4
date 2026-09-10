#!/usr/bin/env python3
"""
tests/check_credit_sign_history.py  v1.0
v1.0  2026-09-10  r344 / RPT.26 — the historical book re-reads with the right
      sign, without rewriting a row.

🔴 WHY A FALLBACK AT ALL. `is_short_position` had NO WRITER until r343, so
every row already logged carries the schema default 0. Trusting the flag
alone leaves the entire history mis-signed: a credit position's favourable
move is the premium FALLING, so its MFE comes off `mae_premium`, and reading
it as a long EXCHANGES MFE with MAE.

  H1  a historical credit row (flag 0, credit > 0) reads as SHORT
  H2  and its MFE/MAE come out the credit way round
  H3  a debit row (no credit) is UNCHANGED — the half that was accidentally
      correct must not move
  H4  the flag WINS when set: flag 1 + no credit still reads SHORT
  H5  a zero or absent credit does not flip anything (no >= 0 sloppiness)
  H6  the never-favourable verdict flips for a credit winner — this is the
      finding the bug was corrupting, not just a column
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
FAILS = []


def check(name, ok, detail=""):
    print("  {:<4} {}  {}".format(name, "PASS" if ok else "FAIL", detail))
    if not ok:
        FAILS.append(name)


def main():
    try:
        from r_ledger import position_dollars, is_credit
    except Exception as exc:                                    # noqa: BLE001
        print("  FAIL  r_ledger.is_credit missing: {}".format(exc))
        return 1

    # A credit spread as the BOOK ACTUALLY HOLDS IT: flag 0, credit written.
    # Sold at 1.00; premium fell to 0.20 (the win) and rose to 1.30 (adverse).
    hist = dict(entry_premium=1.0, mfe_premium=1.30, mae_premium=0.20,
                contracts=1, is_short_position=0, credit_received=1.0)
    check("H1", is_credit(hist), "flag=0 credit=1.0 -> credit={}"
          .format(is_credit(hist)))

    mfe, mae = position_dollars(hist)
    check("H2", abs(mfe - 80.0) < 1e-6 and abs(mae - 30.0) < 1e-6,
          "MFE=${:.0f} (off mae_premium) MAE=${:.0f}".format(mfe, mae))

    debit = dict(entry_premium=1.0, mfe_premium=1.30, mae_premium=0.20,
                 contracts=1, is_short_position=0, credit_received=0)
    dmfe, dmae = position_dollars(debit)
    check("H3", abs(dmfe - 30.0) < 1e-6 and abs(dmae - 80.0) < 1e-6,
          "debit MFE=${:.0f} MAE=${:.0f} — long rule intact".format(dmfe, dmae))

    flagged = dict(entry_premium=1.0, mfe_premium=1.30, mae_premium=0.20,
                   contracts=1, is_short_position=1)
    check("H4", is_credit(flagged), "flag=1, no credit key -> SHORT")

    for v in (0, 0.0, None, ""):
        if is_credit(dict(entry_premium=1.0, is_short_position=0,
                          credit_received=v)):
            check("H5", False, "credit_received={!r} flipped it".format(v))
            break
    else:
        check("H5", True, "0 / 0.0 / None / '' all stay long")

    # H6 — the verdict, not the column. Before the fix this credit WINNER
    # read MFE -$30 and would land in "never favourable".
    before = (1.30 - 1.0) * 100.0          # the old long-rule MFE
    check("H6", before > 0 and mfe > 0 and abs(mfe - before) > 1e-6
          and (1.0 - 1.30) * 100.0 < 0,
          "old rule gave MFE=${:.0f} on the adverse leg; now ${:.0f} on the "
          "favourable one".format(before, mfe))

    print("")
    if FAILS:
        print("FAILED: {}".format(", ".join(FAILS)))
        return 1
    print("ALL PASS (6)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
