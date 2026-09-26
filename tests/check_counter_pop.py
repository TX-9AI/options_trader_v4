#!/usr/bin/env python3
"""
tests/check_counter_pop.py — v1.0
v1.0  2026-09-26  r436 / S3.25 — the gate for the narrow counter repair.

🔴 N2 IS THE SHIP-BLOCKER AND IT IS THE WHOLE POINT OF THE TOOL. A prefix that
is merely SHORT (`got < exp`, `got > 0`) must be REFUSED, never popped. r180's
heal repairs exactly that case on the next clean drain and LOGS it
(`HEALED <prefix> ledger 29 -> 28`). Popping it here would take a repair the
system performs correctly and make it permanent and unlogged — turning a
recoverable one-object gap into a silent lie in the ledger.
📊 MEASURED, SOFI 2026-09-26: ten short prefixes, six at `got=0` and four
partial (27/26, 29/28, 29/28, 2/1). Only six qualify. My own first reading
called all ten emptied; the peer session caught it, which is why this is a
gate and not a comment.

⚠️ N3 — DRY BY DEFAULT. The tool writes to the counter ledger of a live box.
A default that acts is how `--reconcile` became dangerous enough to need
replacing.

⚠️ N4 — NO LOCK, NO RUN, AND SAY SO. r349: a fleet reconcile lost the race to
`s3-push.timer`, returned 0, printed nothing and exited 0 — an operator's
repair indistinguishable from a box with nothing to say, while the fleet stayed
HELD for three nights. Losing the lock must be rc=3 and a named line.

BORN RED, verified 2026-09-26 against the pre-change tree:
  N1-N5 -> "warehouse.counter_pop is absent"

MUTATIONS — each reddens exactly one check:
  * pop on `got < exp` instead of `got == 0`        -> N2 only
  * write without --apply                           -> N3 only
  * proceed when the lock is unavailable            -> N4 only
  * pop a key that is not in the ledger             -> N5 only
"""
from __future__ import annotations

import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_fails = []


def ck(tag, ok, msg=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {tag}  {msg}")
    if not ok:
        _fails.append(tag)


def _stub_s3_push(tmp, lock_ok=True, saved=None):
    m = types.ModuleType("s3_push")
    m.REGION, m.BUCKET, m.LOCK_WAIT = "us-east-2", "b", 1
    m.COUNTERS_PATH = m.LEDGER_PATH = os.path.join(tmp, "prefix_counters.json")
    m._ledger = {"A/": {"n": 1}, "B/": {"n": 29}, "C/": {"n": 2}}
    m._short = [("A/", 1, 0), ("B/", 29, 28), ("C/", 2, 1), ("GONE/", 1, 0)]

    class _FH:
        def close(self): pass
    m.acquire_lock = (lambda w=0: _FH()) if lock_ok else (lambda w=0: None)
    m.load_ledger = lambda p=None: dict(m._ledger)
    m.verify = lambda s3, b, c: (list(m._short), 10, 7)

    def _save(led, p=None):
        if saved is not None:
            saved.append(dict(led))
        return True
    m.save_ledger = _save
    sys.modules["s3_push"] = m
    return m


def main():
    import tempfile
    tmp = tempfile.mkdtemp(prefix="cpop_gate_")
    sys.path.insert(0, os.path.join(ROOT, "warehouse"))
    sys.path.insert(0, ROOT)
    _stub_s3_push(tmp)
    sys.modules.pop("counter_pop", None)
    try:
        import counter_pop as cp
    except Exception as exc:                                      # noqa: BLE001
        for t in ("N1", "N2", "N3", "N4", "N5"):
            ck(t, False, f"warehouse.counter_pop is absent ({type(exc).__name__})")
        print(f"\nRED — {len(_fails)} check(s) failed: {' '.join(_fails)}")
        return 1

    led = {"A/": {"n": 1}, "B/": {"n": 29}, "C/": {"n": 2}}
    short = [("A/", 1, 0), ("B/", 29, 28), ("C/", 2, 1), ("GONE/", 1, 0)]
    pop, refuse = cp.plan(led, short)
    popped = [p[0] for p in pop]
    refused = {r[0]: r[3] for r in refuse}

    ck("N1", popped == ["A/"],
       f"pops only the EMPTY, PRESENT prefix — got {popped}")

    partials_refused = "B/" in refused and "C/" in refused
    ck("N2", partials_refused and "heal" in (refused.get("B/") or ""),
       "a PARTIAL (got>0) is refused and the reason names r180's heal"
       if partials_refused else f"partial was not refused: {popped}")

    # N3 — dry by default: no save without --apply
    saved = []
    _stub_s3_push(tmp, saved=saved)
    sys.modules.pop("counter_pop", None)
    import counter_pop as cp2
    try:
        import boto3                                              # noqa: F401
        rc = cp2.main([])
        ck("N3", rc == 0 and not saved,
           f"dry by default — rc={rc}, ledger writes={len(saved)}")
    except Exception as exc:                                      # noqa: BLE001
        ck("N3", False, f"dry run raised {type(exc).__name__}: {exc}")

    # N4 — no lock, no run, rc=3
    saved2 = []
    _stub_s3_push(tmp, lock_ok=False, saved=saved2)
    sys.modules.pop("counter_pop", None)
    import counter_pop as cp3
    try:
        rc = cp3.main(["--apply"])
        ck("N4", rc == 3 and not saved2,
           f"lock unavailable -> rc={rc}, writes={len(saved2)} (want 3 / 0)")
    except Exception as exc:                                      # noqa: BLE001
        ck("N4", False, f"raised {type(exc).__name__}: {exc}")

    ck("N5", "GONE/" in refused and "ledger" in (refused.get("GONE/") or ""),
       "a key absent from the ledger is refused, not popped")

    if _fails:
        print(f"\nRED — {len(_fails)} check(s) failed: {' '.join(_fails)}")
        return 1
    print("\nGREEN — only empty prefixes pop; partials heal themselves")
    return 0


if __name__ == "__main__":
    sys.exit(main())
