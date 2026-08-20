#!/usr/bin/env python3
"""
tests/gen_file_map.py  v4.0
Generates docs/FILE_MAP.md from the real import graph; fails on drift.

v4.0  2026-08-19  Built at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

WHY THIS IS GENERATED AND NOT WRITTEN.
OTV3's FILE_MAP.md was maintained BY HAND and its own header admitted the
consequence: "Regenerate after structural changes - it is a snapshot, and it
will drift." It did. A map that looks current and is not is worse than no map:
on 2026-08-19 an entire module was nearly excised on a reading of its imports
while the map recorded its fan-in as 12 - third highest in the codebase, behind
only config.py and time_utils.

WHY IT PARSES INSTEAD OF IMPORTING.
`ast` reads the import statements without executing the module. A file that
crashes on import - and at the v4 split there were eight of them - still maps
correctly. An importing mapper would have gone blind exactly when the map was
most needed.

THE THREE FAILURES IT CATCHES, all seen for real during the v3 -> v4 port:
  1. DRIFT. The committed map disagrees with the code. Fails.
  2. BROKEN LOCAL IMPORT. A module imports something that is not there. Eight
     files did after the deliberate regime-engine drop, and it was found by
     running imports BY HAND rather than by any check.
  3. ORPHANS. A module nothing imports and that is not an entry point. Twenty
     files were silently omitted from the port manifest; nothing errored,
     because a file that is simply absent breaks nothing until it is needed.

DELIBERATE ABSENCES ARE PRESERVED, NOT REGENERATED. The "REMOVED ON PURPOSE"
block is hand-written and carried across every regeneration: a parser cannot
know that regime_confluence was dropped because its output measured
anti-predictive, and without that line someone re-adds it in six months because
a strategy appears to want it.
"""

import argparse
import ast
import os
import sys

SKIP_DIRS = {".git", "__pycache__", "deploy", "reports", "blind_tapes", "venv"}
# ⚠️ AN ENTRY POINT IS NOT AN ORPHAN. A systemd service or a CLI helper SHOULD
# have no importers - that is what being an entry point means. Listing them here
# is not suppression: an orphan report that flags every service teaches the
# operator to skim it, and then a genuinely unwired module hides in the noise.
# Each of these was verified to be launched by a unit file or run by hand.
ENTRY_POINTS = {
    # operator / CLI
    "main.py", "query.py", "status.py", "debug_status.py",
    "eod_summary.py", "stress_theta_bleed.py",
    # systemd-launched services
    "shadow/observer.py",          # shadow-observer.service
    "shadow/trading_day.py",       # shadow-start.service ExecCondition
    "data/candle_logger.py",       # candle-logger.service
    "warehouse/s3_push.py",        # s3-push.service
    "data/candle_feed.py",         # candle-feed.service
    # CLI helpers, run by hand or by a script
    "analysis/get_orb_range.py",
    "utils/check_sdk.py",
}
ABSENT_MARK = "<!-- REMOVED-ON-PURPOSE -->"


def _walk(root):
    for r, d, f in os.walk(root):
        d[:] = [x for x in d if x not in SKIP_DIRS and not x.startswith(".")]
        for x in f:
            if x.endswith(".py"):
                yield os.path.relpath(os.path.join(r, x), root)


def _local_imports(path, root, known_files):
    """Local modules this file imports. Parsed, never executed."""
    try:
        tree = ast.parse(open(os.path.join(root, path), encoding="utf-8").read())
    except Exception:                                          # noqa: BLE001
        return set(), True                                     # unparseable
    out = set()
    for node in ast.walk(tree):
        mods = []
        if isinstance(node, ast.Import):
            mods = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            mods = [node.module]
            # ⚠️ `from <package> import <module>` - the MODULE is the imported
            # NAME, not `node.module`. Reading only `node.module` resolves the
            # PACKAGE and misses the dependency entirely, so a file imported
            # this way reports as an ORPHAN.
            # Found 2026-08-19: `from strategy import credit_vertical as cv`
            # in BOTH trend_credit_spread.py and iron_condor_strategy.py. The
            # module is live - `cv.pop`, `cv.bars_left` - and TC.6 traded with
            # it four times on 08-17. The checker called it unwired, and an
            # orphan report that accuses live modules is one nobody reads.
            mods += [node.module + "." + a.name for a in node.names]
        for m in mods:
            # ⚠️ RESOLVE TO A REAL FILE OR DROP IT. A first pass turned a bare
            # `import analysis` into "analysis.py" and reported it as a broken
            # import - a PACKAGE is not a module, and a checker that invents
            # missing files teaches the operator to ignore its own output.
            cand = m.replace(".", "/") + ".py"
            if cand in known_files:
                out.add(cand)
                continue
            pkg_init = m.replace(".", "/") + "/__init__.py"
            if pkg_init in known_files:
                out.add(pkg_init)
    return out, False


def build(root):
    files = sorted(_walk(root))
    pkgs = {p.split("/")[0] for p in files if "/" in p}
    pkgs |= {p for p in files if "/" not in p}
    calls, unparsed = {}, []
    for p in files:
        c, bad = _local_imports(p, root, set(files))
        calls[p] = {x for x in c if x != p}
        if bad:
            unparsed.append(p)
    called_by = {p: set() for p in files}
    broken = []
    for p, cs in calls.items():
        for c in cs:
            if c in called_by:
                called_by[c].add(p)
            else:
                broken.append((p, c))
    return files, calls, called_by, broken, unparsed


def render(root, files, calls, called_by, broken, unparsed, absent_block):
    L = []
    L.append("# FILE_MAP - every module, what it calls, and what calls it")
    L.append("")
    L.append("**GENERATED by `tests/gen_file_map.py` from the real import graph.**")
    L.append("Do not edit by hand: the generator runs inside the land command and")
    L.append("the canary fails on drift (WORKING_AGREEMENT 33).")
    L.append("")
    L.append(f"{len(files)} Python modules across {len({p.split('/')[0] for p in files if '/' in p})} local packages.")
    L.append("")
    # ── orientation, emitted every run (v4.1, 2026-08-20) ──────────────────
    # ⚠️ THIS BELONGS IN THE GENERATOR, NOT THE OUTPUT. A hand-edit to
    # docs/FILE_MAP.md vanishes on the next run - correct behaviour for a
    # generated file, and the reason this text lives here instead.
    L.append("## How to read this repo - orientation")
    L.append("")
    L.append("**The one-way flow:** `data/` fetches -> `analysis/` describes ->")
    L.append("`strategy/` decides -> `execution/` acts -> `database/` records.")
    L.append("**Nothing flows backwards**, and that is what let v3's defects be")
    L.append("isolated rather than being everywhere at once.")
    L.append("")
    L.append("**Where the decisions live:**")
    L.append("")
    L.append("- `main.py::attempt_new_entry` - the dispatch chain. ORB, then")
    L.append("  runaway (it reads ORB's own state, and firing DISARMS the")
    L.append("  retest), then sweep, then the parked butterfly. **Order is")
    L.append("  load-bearing.**")
    L.append("- `strategy/<name>.py` - one file per setup, each with a `GATES`")
    L.append("  dict naming every constant SELECTION / FOUNDATIONAL /")
    L.append("  FEASIBILITY. **Foundational conditions are tested inline")
    L.append("  against no constant** - the safest form, since there is nothing")
    L.append("  to relax even by mistake.")
    L.append("- `execution/exit_engine.py` - 37 methods on `ExitEngine`.")
    L.append("  ⚠️ **F0: a function inserted at column 0 above a method bisected")
    L.append("  this class and every intraday exit became dead code for seven")
    L.append("  revisions behind a green board.** `check_exit_executes.py`")
    L.append("  exists so it cannot happen silently again.")
    L.append("- `analysis/market_state.py` - replaced `regime_classifier`.")
    L.append("  **Carries the vocabulary, classifies nothing.**")
    L.append("")
    L.append("**Where the evidence lives:** `tests/` holds the eight standing")
    L.append("checks plus the studies that produced every threshold in")
    L.append("`docs/TRADES.md`. **A number in a strategy file should be")
    L.append("traceable to a tool in here.**")
    L.append("")
    L.append("## Fan-in leaderboard - widest blast radius")
    L.append("")
    L.append("Change these with the most care; a break here reaches everything downstream.")
    L.append("")
    L.append("| module | imported by | some of the importers |")
    L.append("|---|---|---|")
    for p in sorted(files, key=lambda x: -len(called_by[x]))[:12]:
        n = len(called_by[p])
        if not n:
            continue
        some = ", ".join(sorted(os.path.basename(x) for x in called_by[p])[:4])
        L.append(f"| `{p}` | {n} | {some} |")
    L.append("")
    L.append("## Every module")
    L.append("")
    for p in files:
        L.append(f"### `{p}`")
        c = sorted(calls[p])
        b = sorted(called_by[p])
        L.append(f"- **calls:** {', '.join('`'+x+'`' for x in c) if c else '(none)'}")
        if b:
            L.append(f"- **called by:** {', '.join('`'+x+'`' for x in b)}")
        elif p in ENTRY_POINTS or os.path.basename(p) in ENTRY_POINTS:
            L.append("- **called by:** (entry point)")
        else:
            L.append("- **called by:** (nothing - orphan or leaf)")
        L.append("")
    L.append(absent_block.rstrip())
    # ⚠️ NORMALISE THE TAIL OR THE MAP DRIFTS FROM ITSELF. `render` appended a
    # newline to a block that already ended with one, and `_absent_block`
    # re-read that grown tail on the next run - so the file gained a blank line
    # EVERY regeneration and `--check` reported drift immediately after a
    # successful write. The checker was right and the writer was wrong.
    return "\n".join(L).rstrip() + "\n"


def _absent_block(dst):
    """Carry the hand-written REMOVED-ON-PURPOSE section across regenerations."""
    default = (ABSENT_MARK + "\n"
               "## Removed on purpose\n\n"
               "Hand-written. **Preserved across regenerations** - a parser cannot\n"
               "know WHY something is absent, and without that a dropped module gets\n"
               "re-added by someone who finds a strategy that appears to want it.\n\n"
               "| module | removed | why |\n|---|---|---|\n"
               "| `analysis/regime_confluence.py` | v4 split | The damper x corroborator grammar. Every scoring defect found in the final week lived in it. |\n"
               "| `analysis/conviction_integrator.py` | v4 split | Confirmatory by construction: a leaky integrator over argmax agreement is only confident once winning has persisted. |\n"
               "| `analysis/regime_axes.py` | v4 split | `direction_conf` measured Cliff's delta **+0.09** at 28% ties - a median artifact, not separation. |\n"
               "| `utils/regime_labels.py` | v4 split | Vocabulary is redefined in v4's own structural terms. |\n\n"
               "⚠️ `analysis/volatility_engine.py` and `analysis/trend_engine.py` were\n"
               "dropped at first and **RESTORED**: they are structure providers, not\n"
               "regime engines. ATR, Bollinger bands, VWAP, price-vs-band, ADX, the EMA\n"
               "stack. They were cut on location and name rather than on what they\n"
               "compute. See `docs/INHERITED_FINDINGS.md`.\n")
    if not os.path.exists(dst):
        return default
    txt = open(dst, encoding="utf-8").read()
    return txt[txt.index(ABSENT_MARK):] if ABSENT_MARK in txt else default


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="docs/FILE_MAP.md")
    ap.add_argument("--check", action="store_true",
                    help="fail on drift instead of writing")
    a = ap.parse_args(argv[1:])

    files, calls, called_by, broken, unparsed = build(a.root)
    dst = os.path.join(a.root, a.out)
    text = render(a.root, files, calls, called_by, broken, unparsed,
                  _absent_block(dst))

    fail = False
    if broken:
        print(f"  BROKEN LOCAL IMPORTS: {len(broken)}")
        for p, c in broken[:10]:
            print(f"    {p} imports {c} - which does not exist")
        fail = True
    if unparsed:
        print(f"  UNPARSEABLE: {len(unparsed)}")
        for p in unparsed[:6]:
            print(f"    {p}")
        fail = True
    orphans = [p for p in files if not called_by[p]
               and p not in ENTRY_POINTS
               and os.path.basename(p) not in ENTRY_POINTS
               and not p.endswith("__init__.py")
               and not p.startswith("tests/")]
    if orphans:
        print(f"  ORPHANS (nothing imports them, not entry points): {len(orphans)}")
        for p in orphans[:10]:
            print(f"    {p}")

    if a.check:
        cur = open(dst, encoding="utf-8").read() if os.path.exists(dst) else ""
        if cur != text:
            print("  DRIFT: docs/FILE_MAP.md does not match the code.")
            print("     Regenerate before shipping - the land command does this")
            print("     automatically; a hand-landed change did not.")
            fail = True
        else:
            print("  file map is current")
    else:
        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        open(dst, "w", encoding="utf-8").write(text)
        print(f"  wrote {a.out}: {len(files)} modules, "
              f"{sum(len(v) for v in calls.values())} local edges")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
