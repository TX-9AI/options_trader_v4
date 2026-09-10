#!/usr/bin/env python3
"""
tests/check_backlog_ids.py  v1.0
v1.0  2026-09-09  r328 / DOC.22 — every PART 1 row owns its ID, alone.

🔴 WHY THIS EXISTS. r326 filed RPT.17 and RPT.18, r327 filed RPT.19, and all
three IDs were already taken (r298's widened default, r299's relaxed filter,
and the open row on refitting the relaxed question). Both deliveries LANDED.
Six rows, three identities, two meanings each.

🔑 NOTHING COULD HAVE SEEN IT. `check_land_discipline` asserts a file agrees
with ITSELF — title version against newest changelog entry — and the content
gate greps for strings the spec names. Neither can notice that a table holds
two rows claiming one identity. And an ID is the ONLY handle a backlog row
has: once duplicated, "see RPT.19" is ambiguous forever, silently.

  D1  no NEW duplicate row ID — the four legacy ones are named below
  D2  every row ID is well-formed (AREA.n)
  D3  the NEWEST PART 4 entry cites only rows that exist

🔴 D1 IS SCOPED, AND THE SCOPE IS THE HONEST PART. Four IDs were ALREADY
duplicated before any of this — DOC.17 (r278/r317), ORB.1 (r192, three
rows), S3.4 (r189), SHD.2 (r268/dtp r299) — some of them cited in PART 4
prose that would break on a renumber. Untangling other authors' history is
not this delivery's job, and a gate that lands RED is a gate nobody adopts.
So they are named, once, with their revisions.

⚠️ ADDING TO `LEGACY` IS NOT HOW YOU FIX A FAILURE. It is the same move as
refreshing a drift baseline without reading the diff — the tool stops being
a proof and becomes a rubber stamp. A new collision means pick a free ID.

⚠️ D3 IS DELIBERATELY NARROW. Fourteen older PART 4 entries cite rows that
have since been closed and removed from PART 1; that is the document working
as intended, and failing on it would fire on the normal case (§18). Only the
entry being written now is checked, which is the one an author can still fix.
"""
import os
import re
import sys
from collections import Counter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "BACKLOG.md")
ROW = re.compile(r"^\|\s*\*\*([A-Z][A-Z0-9]*\.\d+)\*\*\s*\|")
CITE = re.compile(r"\b([A-Z][A-Z0-9]{1,9}\.\d+)\b")
# Duplicated before r326 and left alone deliberately — see the header.
LEGACY = {"DOC.17", "ORB.1", "S3.4", "SHD.2"}

FAILS = []


def check(name, ok, detail=""):
    print("  {:<4} {}  {}".format(name, "PASS" if ok else "FAIL", detail))
    if not ok:
        FAILS.append(name)


def main():
    if not os.path.exists(DOC):
        print("  FAIL  docs/BACKLOG.md not found at {}".format(DOC))
        return 1
    text = open(DOC, encoding="utf-8").read()
    lines = text.split("\n")
    try:
        p4 = next(i for i, l in enumerate(lines) if l.startswith("## PART 4"))
    except StopIteration:
        p4 = len(lines)

    ids = [m.group(1) for m in (ROW.match(l) for l in lines[:p4]) if m]
    dupes = sorted(k for k, v in Counter(ids).items() if v > 1)
    new = [d for d in dupes if d not in LEGACY]
    check("D1", not new and bool(ids),
          "{} row(s); new duplicates: {}; legacy still present: {}".format(
              len(ids), ", ".join(new) or "none",
              ", ".join(d for d in dupes if d in LEGACY) or "none"))

    bad = [i for i in ids if not re.fullmatch(r"[A-Z][A-Z0-9]*\.\d+", i)]
    check("D2", not bad, "malformed: {}".format(bad) if bad else "all well-formed")

    known = set(ids)
    prefixes = {i.split(".")[0] for i in ids}
    tail = lines[p4:]
    heads = [i for i, l in enumerate(tail) if l.startswith("**v")]
    newest = "\n".join(tail[heads[0]:heads[1]] if len(heads) > 1 else tail)
    cited = {c for c in CITE.findall(newest) if c.split(".")[0] in prefixes}
    missing = sorted(cited - known)
    check("D3", not missing,
          "newest entry cites {} row(s) that do not exist: {}".format(
              len(missing), ", ".join(missing)) if missing
          else "newest entry: {} citation(s) resolve".format(len(cited)))

    print("")
    if FAILS:
        print("FAILED: {}".format(", ".join(FAILS)))
        return 1
    print("ALL PASS (3)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
