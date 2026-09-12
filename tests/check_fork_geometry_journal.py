#!/usr/bin/env python3
"""
tests/check_fork_geometry_journal.py  v1.0

v1.0  2026-09-12  r367 — THE LOG-ONLY MONTH CAN ONLY STUDY WHAT IT RECORDED.

🔴 WHAT THIS PINS AND WHY IT IS NOT COSMETIC. LVL.6: two builders construct a
1h fork from the same bars with different ATRs — `ForkEngine` (20-bar
high-minus-low) and `pitchfork_observer` (14-bar true range). Measured over
2026-09-10/11 they TIE on presence: 57% of minutes each across 9,753
symbol-minutes, disagreeing 1% of the time. So the open question is whether
they select the same GEOMETRY, and presence cannot answer it.

`fork_series` already stores `origin_idx` and `slope` for the ForkEngine side.
The observer's journal stored NEITHER — `_state()` recorded rails and position
only, on the reasoning that "the journal records a POSITION, not a trajectory".
That was right for a journal nobody compared, and wrong the moment the other
half of a study existed.

⚠️ THE GATE EXISTS BECAUSE THE FAILURE IS INVISIBLE FOR A MONTH. A missing
field costs nothing today and costs the entire study on ~2026-10-12, by which
time the tape it needed is gone. That is SHD.5's lesson verbatim: shadow
collected for three weeks against a question its record could not answer.

G3 IS THE ONE THAT MATTERS: the fields must be RECORDS, not inputs. If anything
ever reads them, this stops being log-only and becomes a second opinion about
fork geometry (WORKING_AGREEMENT §31, §35).
"""
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

_fails = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        _fails.append(name)


def main():
    print("check_fork_geometry_journal — the observer records its TRAJECTORY")

    src = open(os.path.join(_root, "analysis", "pitchfork_observer.py"),
               encoding="utf-8").read()

    # G1/G2 — anchored on the DICT KEY being assigned, not on a mention. The
    # changelog above necessarily names both fields while describing them, so a
    # bare word match would go red on its own documentation (§20).
    check("G1 _state records origin_idx as a journal field",
          '"origin_idx": (' in src)
    check("G2 _state records slope as a journal field",
          '"slope": (' in src)

    # G3 — RECORD-ONLY. `rails_for` computes its own slope for the condor and
    # always has; that is a live consumer of a DIFFERENT expression and is not
    # what this forbids. What is forbidden is anything READING the journalled
    # dict's new keys.
    bad = [ln.strip() for ln in src.splitlines()
           if ('["origin_idx"]' in ln or '.get("origin_idx"' in ln
               or "['origin_idx']" in ln)
           and '"origin_idx": (' not in ln]
    check("G3 nothing reads origin_idx back — it is a RECORD, not an input",
          not bad, "; ".join(bad[:2]))

    # G4 — the fields must survive into the journalled record, so they belong to
    # the dict `_state` RETURNS. Proven by driving the real function against a
    # stub fork rather than by reading the source (§21).
    import analysis.pitchfork_observer as PO

    class _F:
        direction = "bullish"
        variant = "modified_schiff"
        filters_passed = ("CONTAINMENT_0.95", "SPAN_42")
        born_idx = 10
        origin_idx = 56.0
        slope = 2.023871

        def is_born_by(self, idx):
            return True

        def rails_at(self, idx):
            return {"upper": 110.0, "median": 100.0, "lower": 90.0}

    st = PO._state({"contained": _F(), "bars": 60, "atr": 2.0}, 105.0)
    check("G4 the returned record carries both fields",
          isinstance(st, dict) and st.get("origin_idx") == 56.0
          and st.get("slope") == 2.023871,
          f"origin_idx={None if st is None else st.get('origin_idx')} "
          f"slope={None if st is None else st.get('slope')}")

    # G5 — a control. The fields that were already there must not have been
    # displaced by the addition.
    check("G5 the existing position fields are untouched",
          isinstance(st, dict) and st.get("upper") == 110.0
          and st.get("lower") == 90.0 and st.get("pos_pct") == 75.0,
          f"pos_pct={None if st is None else st.get('pos_pct')}")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: {', '.join(_fails)}")
        return 1
    print("check_fork_geometry_journal: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
