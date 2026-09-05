#!/usr/bin/env python3
"""
tests/check_cascade_constants.py  v1.0
v1.0  2026-09-04  r246 — TCS.9: THE CASCADE HARNESSES' LOCAL CONSTANTS MUST
      MATCH CONFIG.

🔴 `cascade_harness.py` and `cascade_real.py` each keep their own copy of the
session constants so the cascade can be reasoned about without importing
config. That is deliberate. What was missing is the COMPARISON — r238 set
`TCS_ENTRY_END_ET` to (0,0) to park TCS and both harnesses still read (14,0),
so for a day they modelled a TCS that traded. r241 restored (14,0) and made
them correct BY ACCIDENT, which is not the same as correct.

🔑 A COPY IS FINE. A COPY NOBODY COMPARES IS DRIFT WAITING TO HAPPEN. This is
the same treatment `ORB_NO_ENTRY_AFTER_ET` already has, and the harness comment
already promised it.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name)


# harness name -> config name. Only constants the harness claims to mirror.
MIRRORED = {
    "DEBIT_DIRECTIONAL_CUTOFF_ET": "DEBIT_DIRECTIONAL_CUTOFF_ET",
    "TCS_START_ET":                "TCS_START_ET",
    "TCS_ENTRY_END_ET":            "TCS_ENTRY_END_ET",
    "HARD_CLOSE_ET":               "HARD_CLOSE_ET",
}


def main():
    import config as C
    root = os.path.dirname(os.path.abspath(__file__))
    seen = 0
    for mod in ("cascade_harness", "cascade_real"):
        path = os.path.join(root, mod + ".py")
        if not os.path.exists(path):
            # ⚠️ ABSENT IS NOT PASSING. A harness that has been deleted or
            # renamed must be noticed, not silently skipped.
            check(f"C0 {mod}.py exists", False, "harness missing")
            continue
        ns = {}
        src = open(path, encoding="utf-8").read()
        for line in src.split("\n"):
            for name in MIRRORED:
                if line.startswith(name) and "=" in line:
                    try:
                        ns[name] = eval(line.split("=", 1)[1].split("#")[0].strip())
                    except Exception:                          # noqa: BLE001
                        pass
        for name, cfg_name in MIRRORED.items():
            if name not in ns:
                continue
            want = getattr(C, cfg_name, None)
            if want is None:
                continue
            seen += 1
            got = tuple(ns[name]) if isinstance(ns[name], (list, tuple)) else ns[name]
            check(f"C1 {mod}.{name} matches config",
                  got == tuple(want) if isinstance(want, (list, tuple)) else got == want,
                  f"harness {got} vs config {tuple(want)}")

    # ⚠️ A CHECKER THAT COMPARED NOTHING MUST FAIL. If the parse stops finding
    # the constants — renamed, reformatted, moved — this would otherwise report
    # a cheerful green having verified nothing at all.
    check("C2 the checker actually compared something", seen >= 4, f"{seen} compared")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print(f"GREEN — {seen + 1} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
