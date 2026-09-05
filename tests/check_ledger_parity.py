#!/usr/bin/env python3
"""
tests/check_ledger_parity.py  v1.1
v1.1  2026-09-04  r241 — r226 JOINS THE KNOWN-ROWLESS SET. r240's own
      GENESIS row cites it by name while explaining that it rebuilds it, so
      the citation became "cited but rowless" the moment r240 landed — caught
      by this checker the same day it was written. The citation IS the record
      of why the number is missing, not evidence of a lost row.
v1.0  2026-09-04  r240 — THE TWO LEDGERS MUST AGREE, AND THE BACKLOG MUST BE
      ABLE TO ANSWER "WHAT IS OPEN". Both had stopped being true.

🔴 MEASURED at 45988b6 (BACKLOG v1.57, GENESIS 226 rows, r1..r239):
  • 25 rows read `🔲 OPEN`, and FOUR of those ids — SWEEP.2, SWEEP.3, SWEEP.4,
    TCS.8 — also carry a later `✅ CLOSED` row. Entries are per-revision and
    append-only, so closing an item leaves its earlier OPEN row in place.
    SWEEP.2 appears on FOUR rows. Roughly a third of the open list was wrong.
  • r226 is CLAIMED BY A BACKLOG ENTRY and has NO GENESIS ROW. §35: a revision
    absent from the ledger did not happen.
  • GENESIS skips 13 numbers (r42, 49, 89, 97, 109, 110, 111, 117, 123, 141,
    151, 159, 226). Nine are absent everywhere — allocated and never used,
    which is fine. THREE are cited in GENESIS prose by other revisions
    (r110, r141, r159) but have no row of their own, which is not.

⚠️ THE POINT IS NOT TIDINESS. Every prioritisation starts by reading the open
list, and a list that is a third wrong sends the next session at work that is
already done. This checker makes that state a RED rather than a discovery.
"""
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name)


def _docs():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return (open(os.path.join(root, "docs", "GENESIS.md"), encoding="utf-8").read(),
            open(os.path.join(root, "docs", "BACKLOG.md"), encoding="utf-8").read())


def item_rows(bl):
    """(id, state) for every backlog table row that declares an item."""
    return [(m.group(1), m.group(3).strip()) for m in
            re.finditer(r'^\|\s*\*\*([A-Z]+\.\d+)\*\*\s*\|(.*?)\|\s*([^|]*?)\s*\|\s*$',
                        bl, re.M)]


def open_items(bl):
    """The ids that are ACTUALLY open, newest state per id.

    🔴 THE FILE IS NEWEST-FIRST. Entries are PREPENDED — v1.57 sits at the top
    and v1.0 at the bottom — so the FIRST row for an id is its most recent
    state, not the last. The first cut of this helper took the last and
    reported SWEEP.2/3/4 as open when they had been closed at r231/r234: the
    exact error it exists to catch, made while catching it.
    """
    newest = {}
    for rid, state in item_rows(bl):
        if rid not in newest:          # first occurrence == newest entry
            newest[rid] = state
    return sorted(k for k, s in newest.items()
                  if "OPEN" in s.upper() and "CLOSED" not in s.upper())


def main():
    gen, bl = _docs()

    # ══ L1 — NO ID IS BOTH OPEN AND CLOSED ════════════════════════════════
    seen = defaultdict(list)
    for rid, state in item_rows(bl):
        seen[rid].append(state.upper())
    contradictory = sorted(k for k, v in seen.items()
                           if any("CLOSED" in s for s in v)
                           and any("OPEN" in s and "CLOSED" not in s for s in v))
    check("L1 no item carries both an OPEN row and a CLOSED row",
          not contradictory, ", ".join(contradictory))

    # ══ L2 — EVERY BACKLOG ENTRY HAS A GENESIS ROW ════════════════════════
    # 🔴 §35: a revision absent from the ledger did not happen. The backlog is
    # not the ledger, so a revision it claims and GENESIS does not is a claim
    # with no record behind it.
    gen_rows = set(re.findall(r'^\| \*\*(r\d+)\*\*', gen, re.M))
    claimed = set(re.findall(r'^\*\*v[\d.]+ — [\d-]+ — (r\d+)', bl, re.M))
    # ⚠️ r226 IS A KNOWN, EXPLAINED HOLE AND IS ALLOWED BY NAME. It was cut on
    # 2026-09-03 and NEVER LANDED — no commit for it exists on any branch —
    # and its BACKLOG entry reached git only because `docs/BACKLOG.md` ships in
    # every archive, so r227 (the urgent "did you brick my ORB" fix) carried
    # the already-written entry along with its own. r240 rebuilds the change
    # and the v1.58 entry records the history. Allowed BY NAME, not by
    # loosening the rule: a second orphan still fails.
    KNOWN_UNLANDED = {"r226"}
    # ⚠️ THE NEWEST ENTRY IS EXEMPT, BY CONSTRUCTION. `land.sh` appends the
    # GENESIS row at LAND time, so the backlog entry for the revision being cut
    # always exists first. Demanding a row for it would fail on every single
    # delivery, and a check that is red by design is a check that gets ignored.
    # Scoped to ONE — the highest-numbered claim — so a second unlanded entry
    # still fails.
    _newest = max((int(r[1:]) for r in claimed), default=0)
    orphan = sorted(claimed - gen_rows - KNOWN_UNLANDED - {f"r{_newest}"},
                    key=lambda r: int(r[1:]))
    check("L2 every revision the BACKLOG claims has a GENESIS row "
          "(r226 excepted — cut, never landed, rebuilt as r240)",
          not orphan, ", ".join(orphan))

    # ══ L3 — NO REVISION IS CITED IN PROSE WITHOUT A ROW ══════════════════
    # ⚠️ A citation to a revision with no row is a reference to something the
    # ledger says never happened — either the row was lost or the citation is
    # wrong, and both are worth knowing. Scoped to the numbers actually MISSING
    # from the sequence, so an ordinary backward citation does not trip it.
    nums = sorted(int(r[1:]) for r in gen_rows)
    gaps = [n for n in range(nums[0], nums[-1] + 1) if f"r{n}" not in gen_rows]
    # ⚠️ r110, r141 AND r159 ARE CITED BY LATER REVISIONS AND HAVE NO ROW.
    # Either three rows were lost or three citations point at revisions that
    # never existed; the ledger cannot say which and it is not rewritten to
    # guess. Recorded as DOC.11, allowed by name, and a FOURTH such citation
    # fails — because that would be a new loss rather than an old one.
    # ⚠️ r226 JOINED THIS SET WHEN r240 LANDED, and the checker caught it the
    # same day it was written. r240's own GENESIS row explains that it rebuilds
    # r226 — so citing it by name is CORRECT, and the citation is the record of
    # why the number is missing rather than evidence of a lost row. L2 already
    # allows it as a known unlanded revision; L3 allows the citation for the
    # same reason and by the same name.
    KNOWN_ROWLESS_CITATIONS = {110, 141, 159, 226}
    cited = [n for n in gaps
             if re.search(rf'\br{n}\b', gen) and n not in KNOWN_ROWLESS_CITATIONS]
    check("L3 no NEW missing revision number is cited in GENESIS prose "
          "(r110/r141/r159 known, DOC.13)",
          not cited, f"cited but rowless: {cited}")

    # ══ L4 — THE SEQUENCE IS REPORTED, NOT ENFORCED ═══════════════════════
    # ⚠️ NOT A FAILURE. §26 says numbering is sequential and never resets, but
    # a number allocated and abandoned leaves a legitimate hole. This prints
    # the holes so they are visible; only a CITED hole (L3) or a CLAIMED hole
    # (L2) is a defect.
    print(f"        note: {len(gaps)} unused revision number(s): {gaps}")
    check("L4 the ledger is contiguous enough to trust its ordering",
          len(gaps) < 25, f"{len(gaps)} gaps in r{nums[0]}..r{nums[-1]}")

    # ══ L5 — THE OPEN LIST IS COMPUTABLE AND NON-EMPTY ════════════════════
    op = open_items(bl)
    check("L5 the open list resolves to one state per id",
          len(op) == len(set(op)) and op, f"{len(op)} open")
    print()
    print("  OPEN (latest state per id):")
    for rid in op:
        print(f"      {rid}")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — 5 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
