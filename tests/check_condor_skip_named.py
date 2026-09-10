#!/usr/bin/env python3
"""
tests/check_condor_skip_named.py  v1.0
v1.0  2026-09-10  r341 / PLN.1 — on a FLAT box, no plan may fall to the
      generic dispatch-gap default.

🔴 WHY. r213 made every skip name itself, and its fallback deliberately reads
as a defect report: *"no reason recorded — main.py reached a return path that
does not name this strategy. That is a dispatch gap, not a market condition."*
`IronCondorStrategy` was outside r213's three shapes, so on every flat tick of
every session it printed that accusation — **confident, specific, and wrong**.
It is management-driven (`authorize` hands a side to the sweep; the condor
opens nothing) and its call site sits inside `has_open_position()`, so on a
flat box it is never reached at all.

  P1  `IronCondorStrategy` is covered by `skipped_management`
  P2  its neighbours still are — r213's three shapes are not disturbed
  P3  a plan that already has a SPECIFIC reason keeps it (setdefault, r213 N3)
  P4  membership is by registration, not a name list in main.py — the r35
      allow-list rot r213 called out by name
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
        from strategy import plan as P
    except Exception as exc:                                    # noqa: BLE001
        print("  FAIL  strategy.plan did not import: {}".format(exc))
        return 1

    REASON = "no open position — nothing to manage"
    P._SKIPPED.clear()
    for n in ("IronCondorStrategy", "CondorManagement", "CreditRoll",
              "ORBStrategy", "ORBStrategy/manage"):
        P.REGISTRY.setdefault(n, object())
    # a plan already skipped for a SPECIFIC cause, before the sweep runs
    P._SKIPPED["CreditRoll"] = "one vertical open — awaiting its complement"

    P.skipped_management(REASON)

    check("P1", P._SKIPPED.get("IronCondorStrategy") == REASON,
          "condor -> {!r}".format(P._SKIPPED.get("IronCondorStrategy")))
    check("P2", P._SKIPPED.get("CondorManagement") == REASON
          and P._SKIPPED.get("ORBStrategy/manage") == REASON,
          "CondorManagement and /manage rows still named")
    check("P3", P._SKIPPED.get("CreditRoll") ==
          "one vertical open — awaiting its complement",
          "specific cause survived: {!r}".format(P._SKIPPED.get("CreditRoll")))
    # an ENTRY strategy must NOT be swept up by the management skip
    check("P4", "ORBStrategy" not in P._SKIPPED
          and "IronCondorStrategy" in P._MANAGEMENT_PLANS,
          "ORB untouched; membership by registration set")

    print("")
    if FAILS:
        print("FAILED: {}".format(", ".join(FAILS)))
        return 1
    print("ALL PASS (4)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
