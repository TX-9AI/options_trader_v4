#!/usr/bin/env python3
"""check_runaway_handoff.py — v1.0

🔴 AN ORB INVALIDATED *BY RUNAWAY* IS RunawayContinuation'S TRIGGER, NOT A
DISQUALIFIER.

Measured live, NFLX 2026-08-27: price broke the ORB low 80.08 at 09:41 and ran
to the 50% TP at 79.52 with no retest — the textbook runaway. `orb_engine`
classified it exactly right (`state = INVALIDATED`, `invalidation_reason =
"runaway"`, `break_direction = "short"`). The strategy named after that setup
refused it with *"ORB state 'INVALIDATED' carries no direction."*

⚠️ THE CAUSE: direction was read by string-matching "LONG"/"SHORT" inside
`orb.state`. "INVALIDATED" contains neither, so the function returned at step 3
of its own checklist and never reached step 4, where `runaway_confirmed()`
would have confirmed the setup. The engine had already recorded the direction
in `break_direction` — a field the strategy never read.

⚠️ SAME CLASS AS `all()` vs `all_rails()` AND `oi` vs `open_interest`: reading a
plausible attribute instead of the one carrying the information. It costs more
here because it silently disables an entire strategy on exactly its own setup.

⚠️ `close_inside` MUST STILL REFUSE. That is the opposite tape — price came
back into the range — and is not a handoff.
"""
import ast
import os
import sys
import textwrap

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


class _Refuse(Exception):
    pass


class _ORB:
    def __init__(self, state, reason="", brk=""):
        self.state = state
        self.invalidation_reason = reason
        self.break_direction = brk


def _direction_for(orb):
    """Run the strategy's REAL direction block against an ORB shape.

    ⚠️ Extracted from the source rather than reimplemented — a copy of the
    logic here would be the very mistake this repo spent 2026-08-26 undoing.
    """
    import logging
    src = open(os.path.join(_root, "strategy", "runaway_continuation.py"),
               encoding="utf-8").read()
    i = src.index("        state = str(getattr(orb,")
    j = src.index("        t.direction = direction", i)
    block = textwrap.dedent(
        src[i:j].replace("            return t.refuse(", "            raise _Refuse("))
    ns = {"orb": orb, "logger": logging.getLogger("t"), "_Refuse": _Refuse}
    exec(block, ns)
    return ns["direction"], ns["side"]


def main():
    # ── the retest states still work ─────────────────────────────────────
    try:
        check("RW1 OPEN_SHORT gives short/put",
              _direction_for(_ORB("OPEN_SHORT")) == ("short", "put"))
        check("RW2 OPEN_LONG gives long/call",
              _direction_for(_ORB("OPEN_LONG")) == ("long", "call"))
    except _Refuse:
        check("RW1/RW2 the retest states still resolve", False, "refused")

    # ── 🔴 THE HANDOFF — the case that was broken ────────────────────────
    try:
        got = _direction_for(_ORB("INVALIDATED", "runaway", "short"))
        check("RW3 INVALIDATED by runaway (short) resolves — the NFLX case",
              got == ("short", "put"), str(got))
    except _Refuse:
        check("RW3 INVALIDATED by runaway (short) resolves — the NFLX case",
              False, "REFUSED — the strategy is still blind to its own setup")

    try:
        got = _direction_for(_ORB("INVALIDATED", "runaway", "long"))
        check("RW4 INVALIDATED by runaway (long) resolves",
              got == ("long", "call"), str(got))
    except _Refuse:
        check("RW4 INVALIDATED by runaway (long) resolves", False, "REFUSED")

    # ── and the cases that must KEEP refusing ────────────────────────────
    # ⚠️ close_inside is price returning INTO the range — the opposite tape.
    for state, reason, brk, label in (
            ("INVALIDATED", "close_inside", "short",
             "RW5 INVALIDATED by close_inside still refuses"),
            ("INVALIDATED", "runaway", "",
             "RW6 runaway with NO break_direction refuses, never guesses"),
            ("EXPIRED", "", "", "RW7 EXPIRED refuses"),
            ("AWAITING_RETEST", "", "", "RW8 AWAITING_RETEST refuses")):
        try:
            got = _direction_for(_ORB(state, reason, brk))
            check(label, False, f"resolved to {got} — should have refused")
        except _Refuse:
            check(label, True)

    # ⚠️ THE REFUSAL MUST NAME THE REASON. "carries no direction" alone sent
    # the operator hunting; the invalidation reason is what distinguishes a
    # handoff from a disarm.
    src = open(os.path.join(_root, "strategy", "runaway_continuation.py"),
               encoding="utf-8").read()
    check("RW9 the refusal message names the invalidation reason",
          "invalidated: {_inval_reason}" in src or "_inval_reason}" in src)

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_runaway_handoff: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
