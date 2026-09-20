#!/usr/bin/env python3
"""
tests/check_map_accuracy.py  v1.0
v1.0  2026-09-20  r400 / DOC.25 — THE WRITE MAP'S DEAD-WEIGHT LIST WAS NAMING
      EIGHT LIVE STREAMS, AND `--check` WAS GREEN OVER ALL OF IT.

🔴 WHAT IT PROTECTS, AND IT IS NOT AN ACCURACY QUESTION.
`docs/WRITE_MAP.md` publishes a line headed **"No external reader"**, and says
of it in its own words: *"A table nobody reads is dead weight … It IS a defect
when nobody ever intends to read it, and this list is where that question gets
asked."* **It is a deletion-candidate list.** Measured at 196d27c, 8 of its 9
entries were read by `warehouse/s3_push.py` every single session and pushed to
S3 — the generator was pure regex and could not see `"SELECT * FROM %s" % table`
inside `for table in SERIES_TABLES:`, so it credited s3_push with the TWO
tables it names literally against the TWENTY it reads.

⚠️ **THIS PROJECT HAS ALREADY ACTED ON EXACTLY THAT REASONING ONCE.** [[S3.13]]:
*"THE 2026-08-25 PURGE DELETED 492,945 `raw/shadow` OBJECTS AS A DEAD STREAM.
IT WAS NOT DEAD."*

🔑 **AND `gen_write_map.py --check` WAS GREEN THROUGHOUT**, because it asserts
the map matches what the generator produces. Generator and map agreed with each
other; both were wrong. A check that compares a tool to itself cannot see this,
which is why this file compares the map to an INDEPENDENT source of truth.

  R1   every table s3_push pushes AT RUNTIME is credited to it as a reader
  R1b  CONTROL — a table it does NOT push is not credited to it (over-attribution)
  R1c  an AMBIGUOUS multi-`%s` template resolves to NOTHING, never to a guess
  R2   the "No external reader" line agrees with the map's own rendered rows.

🔴 **AND R2 IS GREEN AT 196d27c WITH NINE TABLES ON THE LIST — MEASURED, AND IT
CORRECTS THE FORK'S DESCRIPTION OF THEIR OWN CHECK.** They offered R2 as the
one that "speaks to the blast radius directly … independent of whether the
resolver works." It does not. **The generator's blind spot is UNIFORM**: it
hides the `FROM %s` read from the flagged LIST and from the table's ROW alike,
so the document stays perfectly self-consistent while being wrong about eight
live streams. R2 can only catch a RENDERING disagreement, never a RESOLUTION
one.
🔑 **THE GENERAL LESSON, WHICH IS WORTH MORE THAN THIS CHECK: A CONSISTENCY
CHECK CANNOT DETECT A UNIFORM BLIND SPOT.** It is the same shape as
`gen_write_map --check` being green throughout — that compares the map to the
generator, and both held the same error. **The only thing that caught this was
R1, which compares the map to `s3_push`'s RUNTIME TUPLES — a source that does
not share the blind spot.** R2 is kept because a rendering divergence is a real
failure mode too, but it is NOT the guard on the deletion list and must not be
read as one.

⚠️ **THE EXPECTATION IS s3_push's RUNTIME TUPLES, IMPORTED — NEVER RE-DERIVED
FROM ITS SOURCE.** Re-deriving would reproduce whatever blind spot the
generator has and the check would agree with the mistake it exists to catch.
That is the OTV4TEST fork's instruction (their r67) and it is the reason this
file imports rather than parses.
⚠️ **AND IT IS INTERPRETER-SAFE:** `s3_push` is stdlib-only at module level,
verified importable under `/usr/bin/python3`, which [[CHK.9]] records is what
the land gate actually runs.
"""
import ast
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

FAILS, RAN = [], []


def check(name, ok, detail=""):
    RAN.append(name)
    print("  {:<5} {}  {}".format(name, "PASS" if ok else "FAIL", detail))
    if not ok:
        FAILS.append(name)


def _load(rel, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    try:
        import gen_write_map as G
    except Exception as exc:                                    # noqa: BLE001
        print("  FAIL  gen_write_map did not import: {}".format(exc))
        return 1
    try:
        sp = _load("warehouse/s3_push.py", "_sp_under_check")
    except Exception as exc:                                    # noqa: BLE001
        print("  FAIL  warehouse/s3_push.py did not import: {}".format(exc))
        return 1

    pushed = (set(sp.SERIES_TABLES) | set(sp.DERIVED_SERIES_TABLES)
              | set(sp.DERIVED_TABLES))
    creates, writes, reads, _dbs = G.scan()
    known = set(creates) | set(writes)
    SELF = "warehouse/s3_push.py"

    missing = sorted(t for t in pushed & known
                     if SELF not in reads.get(t, set()))
    check("R1", not missing,
          "every table s3_push pushes at runtime is credited to it as a "
          "reader ({} of {} in-tree): {}".format(
              len(pushed & known), len(pushed),
              "none missing" if not missing else "MISSING " + str(missing)))

    # ⚠️ CONTROL. Without it the resolver could credit s3_push with EVERY
    # table and R1 would still be green — which is exactly how the fork's
    # first mutation slipped through, because the union it injected was a
    # SUBSET of what s3_push genuinely reads.
    over = sorted(t for t in known - pushed
                  if SELF in reads.get(t, set())
                  and t not in ("candles", "trades"))
    check("R1b", not over,
          "CONTROL — a table s3_push does NOT push is not credited to it "
          "(`candles`/`trades` excluded, it reads those literally): {}".format(
              "no over-attribution" if not over else "OVER-ATTRIBUTED " + str(over)))

    # 🔑 A TUPLE ON THE RIGHT MEANS THE TABLE'S POSITION IS NOT KNOWABLE.
    # `s3_push` really carries `"%s/derived_%s/dt=%s/..." % (PREFIX, table, ...)`
    # in the same functions as the real reads, so resolving it to the FIRST
    # slot would invent a table name out of a path fragment.
    # ⚠️ GUARDED ON hasattr, AND THE REASON IS A MISTAKE MADE WRITING THIS
    # FILE. The first cut called `G._sql_template` directly; against the
    # pre-r400 generator that raised AttributeError, the whole checker DIED,
    # and R1/R1b/R2 never ran at all. **A crash reports breakage; a failure
    # reports a finding, and the two are triaged differently.** Caught by
    # running the born-red pass rather than trusting it.
    _tpl = getattr(G, "_sql_template", None)
    if _tpl is None:
        check("R1c", False,
              "gen_write_map has no `_sql_template` — dynamic SQL is not "
              "resolved at all, so every `FROM %s` read is invisible")
    else:
        amb = ast.parse('x = "%s/derived_%s/dt=%s" % (PREFIX, table, day)'
                        ).body[0].value
        ok1 = _tpl(amb, "table") is None
        good = ast.parse('x = "SELECT * FROM %s" % table').body[0].value
        ok2 = _tpl(good, "table") == "SELECT * FROM \0"
        check("R1c", ok1 and ok2,
              "an AMBIGUOUS multi-%s template resolves to NOTHING while a "
              "single one resolves: ambiguous={} single={}".format(ok1, ok2))

    # ══ R2 — THE BLAST-RADIUS CHECK ═══════════════════════════════════════
    # Read off the RENDERED document, so it holds even if every resolution
    # shape above is broken. This is the one that speaks to the deletion.
    doc = G.render()
    flagged, rows = [], {}
    for line in doc.splitlines():
        if line.startswith("- **No external reader**"):
            flagged = [w.strip(" `") for w in line.split(":", 1)[1].split(",")]
        elif line.startswith("| `") and line.count("|") >= 5:
            cols = [c.strip() for c in line.split("|")]
            rows[cols[1].strip(" `")] = cols[4]
    contradict = sorted(t for t in flagged
                        if t in rows and rows[t] not in ("—", ""))
    check("R2", not contradict,
          "nothing on the DELETION-CANDIDATE line has a reader in its own row "
          "({} flagged): {}".format(
              len(flagged),
              "consistent" if not contradict else
              "🔴 CONTRADICTED " + str(contradict)))

    print("")
    if FAILS:
        print("FAILED: {}".format(", ".join(FAILS)))
        return 1
    print("ALL PASS ({})".format(len(RAN)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
