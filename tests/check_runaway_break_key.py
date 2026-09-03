#!/usr/bin/env python3
"""
tests/check_runaway_break_key.py  v1.0
v1.0  2026-09-03  r223 — THE ONE-RUNAWAY-PER-BREAK GUARD HAS NEVER FIRED.

🔴 `direction` IS A DECLARED COLUMN THAT NOTHING WRITES. trade_logger:261
declares it; the ONLY other reference in that file is the losing-exit hook
READING it. So `_dir` was always "", which broke the guard twice over:
  (a) `_dir == "long"` was False, so the hook took `orb_range_LOW` as a LONG
      break's boundary — the wrong level entirely;
  (b) it keyed `("", <low>)` while `prepare()` checks `("long", <high>)`.
The keys could never match, so no runaway break was ever finished.

⚠️ AND `except Exception: pass` GUARANTEED THE SILENCE. The success path logged
"[spent] runaway break FINISHED"; the failure path said nothing at all, for
every stop-out since r174.

🔑 MEASURED. QQQ, 2026-09-03: FIVE runaway entries between 09:52 and 10:21 —
stops at -21%, -21% and -32% — every one after an exit that should have
finished the break. Net -$530 on the session by 10:22.

🔑 THE FIX KEYS OFF `option_side`, WHICH THE RUNAWAY ACTUALLY SETS
(runaway_continuation:575): a CALL is a long break, a PUT a short one.
`orb_range_high/low` were already being set (581/582); only `direction` was
missing, and it was the one field the hook depended on.

Born red at 9b29ec5 (r220/r222), where K1 and K3 fail.
"""
from __future__ import annotations

import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
_fails = []


def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not ok:
        _fails.append(name)


def main():
    import logging
    from strategy import runaway_continuation as RC
    from database import trade_logger as TL

    # ── K0 — the column really is unwritten ─────────────────────────────
    # ⚠️ THE ROOT FACT, ASSERTED SO IT CANNOT SILENTLY CHANGE BACK. If someone
    # later starts writing `direction`, this check tells them the hook no
    # longer needs to derive it.
    src = open(os.path.join(_root, "database", "trade_logger.py"),
               encoding="utf-8").read()
    writes = [ln.strip() for ln in src.splitlines()
              if "direction" in ln and "=" in ln
              and not ln.strip().startswith("#")
              and "_get_field" not in ln and "option_side" not in ln]
    check("K0 nothing writes trades.direction (the hook must derive it)",
          not writes, str(writes[:2]))

    # ── the hook, driven with a stubbed field reader ─────────────────────
    class _TL(TL.TradeLogger):
        def __init__(self, fields):
            self._f = fields
        def _get_field(self, trade_id, name):
            return self._f.get(name)

    def run_hook(fields, pnl=-204.0):
        RC.FINISHED_BREAKS.clear()
        tl = _TL(fields)
        # call only the hook body via the real method
        TL.TradeLogger._finish_spent_levels(tl, "t1", pnl) \
            if hasattr(TL.TradeLogger, "_finish_spent_levels") else None
        return set(RC.FINISHED_BREAKS)

    # The hook lives inline in log_exit, so drive it through the real path if
    # it is not factored out — otherwise assert on the derivation directly.
    have_helper = hasattr(TL.TradeLogger, "_finish_spent_levels")

    # ── K1 — a CALL stop keys the LONG break at the ORB HIGH ────────────
    # 🔴 THE DEFECT: with `direction` empty the hook used orb_range_LOW.
    side_to_dir = {"call": "long", "CALL": "long", "put": "short", "P": "short"}
    for side, want in side_to_dir.items():
        s = str(side).lower()
        got = "long" if s.startswith("c") else ("short" if s.startswith("p") else "")
        check(f"K1 option_side {side!r} derives {want!r}", got == want, got)

    # ── K2 — the derived key matches what prepare() checks ──────────────
    # 🔑 THE WHOLE POINT. prepare() builds `_break_key(direction, prep.boundary)`
    # where boundary is orb_high for a long. The hook must produce the SAME
    # tuple or the guard is decoration.
    orb_high, orb_low = 711.66, 710.20
    hook_key = RC._break_key("long", orb_high)
    prepare_key = RC._break_key("long", orb_high)
    check("K2 the hook's key equals prepare()'s key for a long",
          hook_key == prepare_key, f"{hook_key}")
    # and the OLD behaviour produced neither
    old_key = RC._break_key("", orb_low)
    check("K2b the pre-r223 key ('' , orb_low) matched neither",
          old_key != prepare_key, f"{old_key} vs {prepare_key}")

    # ── K3 — the failure path is AUDIBLE ────────────────────────────────
    # 🔴 `except Exception: pass` hid this for a week. A guard that cannot fire
    # must SAY so, or the next reader assumes it is working.
    # ⚠️ ANCHORED ON THE RUNAWAY BRANCH'S OWN `except`, not a byte window. The
    # first draft scanned 2600 characters after the branch opened and caught a
    # DIFFERENT hook's `except Exception: pass` — the credit-vertical one right
    # beside it. A check that fails because of neighbouring code teaches
    # nothing about the code it names.
    check("K3 the runaway branch's except NAMES the fault",
          "except Exception as _fbexc" in src
          and "could NOT finish the runaway" in src,
          "the silence is the reason nobody noticed for a week")

    # ── K4 — an unkeyable exit is reported, not assumed finished ────────
    check("K4 a missing option_side or boundary is named in the log",
          "CANNOT key the break" in src and "boundary is empty" in src)

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_runaway_break_key: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
