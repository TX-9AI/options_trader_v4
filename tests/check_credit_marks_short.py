#!/usr/bin/env python3
"""
tests/check_credit_marks_short.py  v1.0
v1.0  2026-09-10  r343 / RPT.26 — a record that takes a CREDIT must mark
      itself SHORT.

🔴 THE DEFECT. `is_short_position` was READ by `exit_engine`,
`position_manager` and the adopted-position alert, and WRITTEN by nothing on
any entry path. Every trade ever logged took the schema default of 0 —
including every credit spread. `r_ledger.position_dollars` keys the excursion
sign on that flag, so for credit trades MFE and MAE have been SWAPPED in
EXCURSIONS, in the R ledger's capture/giveback, in the never-favourable split
and in stop_sweep. The debit strategies were accidentally correct (0 is right
for them), which is why nothing ever looked wrong.

  C1  every record construction that passes `credit_received` also passes
      `is_short_position` — checked by AST over the call's keywords, so a new
      credit site cannot be added without the flag
  C2  and the value written there is 1, not a variable that might be 0
  C3  the flag actually changes the sign: `position_dollars` maps a credit
      position's MFE off `mae_premium`, the long rule off `mfe_premium`

⚠️ C1/C2 ARE AST, NOT GREP. The failure mode is a NEW call site added later
without the keyword; only walking the calls can see that.
"""
import ast
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tests"))
FILES = ("main.py", os.path.join("strategy", "condor_roll.py"))
FAILS = []


def check(name, ok, detail=""):
    print("  {:<4} {}  {}".format(name, "PASS" if ok else "FAIL", detail))
    if not ok:
        FAILS.append(name)


def credit_calls():
    """Every call passing `credit_received=`, with its keyword set."""
    out = []
    for rel in FILES:
        path = os.path.join(REPO, rel)
        tree = ast.parse(open(path, encoding="utf-8").read())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            kw = {k.arg: k.value for k in node.keywords if k.arg}
            if "credit_received" in kw:
                out.append((rel, node.lineno, kw))
    return out


def main():
    calls = credit_calls()
    if not calls:
        print("  FAIL  no call passing credit_received found — the sweep "
              "found nothing, which is not a pass")
        return 1

    missing = [(r, ln) for r, ln, kw in calls if "is_short_position" not in kw]
    check("C1", not missing,
          "{} credit record site(s); missing the flag at {}".format(
              len(calls), missing) if missing
          else "{} credit record site(s), all mark short".format(len(calls)))

    notone = []
    for r, ln, kw in calls:
        v = kw.get("is_short_position")
        if v is None or not (isinstance(v, ast.Constant) and v.value == 1):
            notone.append((r, ln))
    check("C2", not notone,
          "not a literal 1 at {}".format(notone) if notone
          else "every site writes a literal 1")

    try:
        from r_ledger import position_dollars
    except Exception as exc:                                    # noqa: BLE001
        check("C3", False, "r_ledger did not import: {}".format(exc))
    else:
        # entry 1.00; premium fell to 0.60 (a credit WIN) and rose to 1.40.
        row = dict(entry_premium=1.0, mfe_premium=1.40, mae_premium=0.60,
                   contracts=1, is_short_position=1)
        mfe, mae = position_dollars(row)
        longrow = dict(row, is_short_position=0)
        lmfe, lmae = position_dollars(longrow)
        ok = (abs(mfe - 40.0) < 1e-6 and abs(mae - 40.0) < 1e-6
              and abs(lmfe - 40.0) < 1e-6 and abs(lmae - 40.0) < 1e-6
              and mfe is not None)
        # the sign RULE differs even where the magnitudes coincide: prove it
        # with an asymmetric row.
        row2 = dict(entry_premium=1.0, mfe_premium=2.00, mae_premium=0.90,
                    contracts=1, is_short_position=1)
        cmfe, _ = position_dollars(row2)
        lmfe2, _ = position_dollars(dict(row2, is_short_position=0))
        ok = abs(cmfe - 10.0) < 1e-6 and abs(lmfe2 - 100.0) < 1e-6
        check("C3", ok,
              "credit MFE={:.0f} (off mae_premium) vs long MFE={:.0f} "
              "(off mfe_premium)".format(cmfe, lmfe2))

    print("")
    if FAILS:
        print("FAILED: {}".format(", ".join(FAILS)))
        return 1
    print("ALL PASS (3)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
