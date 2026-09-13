#!/usr/bin/env python3
"""
tests/check_runtime_ignored.py  v1.0
v1.0  2026-09-13  r380 / LVL.19 — EVERY RUNTIME PATH UNDER data/ IS IGNORED BY
      GIT, CHECKED FROM THE CODE THAT WRITES IT.
      r379 shipped a reader for `data/level_history/` — the defense history
      control delivers to every box — and no `.gitignore` line for it. otv4's
      ignore list is BY NAME, not by directory, because `data/` holds real
      modules (`candle_feed.py`), so every new runtime path has to be added by
      hand, and nothing checked that anyone did. The sweep this check performs
      found FOUR more: `data/retention_purge.lock`, `data/DEBUG_LOG`,
      `data/DRILL_DISK` and `data/NO_MIDNIGHT_HALT` — operator sentinels and a
      lock, the exact class r108 fixed for `FEED_MAINTENANCE` and `REHEARSAL_OFF`
      and did not sweep.
      🔴 WHY IT MATTERS FOR THE HISTORY IN PARTICULAR: an unignored runtime path
      is exposed to `git add -A` (per-box state committed and baked to every
      other box) and to `git clean -fd` (the delivered file deleted with no
      error) — and a deleted history reads as "this symbol has no record",
      which is a legitimate answer. A loss that looks like a normal state is
      the plausible-silence class.

HOW IT WORKS, AND WHAT IT CANNOT SEE:
  It reads every TRACKED `.py` outside `tests/` (tests are control-only, §34)
  and collects every `"data", "<literal>"` argument pair — the shape of
  `os.path.join(<anything>, "data", "<literal>")`, which every in-repo runtime
  path uses today, matched as the PAIR so a nested first argument cannot hide
  it. For each literal it asks GIT,
  not a copy of the ignore rules: `git check-ignore` on `data/<name>` and on a
  child of it, so a directory rule and a file rule both count.
  A name that git TRACKS (a real module under data/) is source, not runtime,
  and is skipped by name in the output.
  ⚠️ BLIND TO: a path built from a VARIABLE (`os.path.join(HERE, "data", tree)`
  in retention_purge), a path spelled as one string (`"data/x"`), and a path
  rooted in `config.DATA_DIR`. Each is listed here so a green is not read as
  covering them. `*.db` files are covered by the glob rule regardless.
  ⚠️ NO git, OR NOT A CHECKOUT → FAIL, never skip: a check that cannot run must
  not read like one that passed.
"""
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The PAIR of literals, not the whole call: a join whose first argument is
# itself a call (`os.path.join(os.path.dirname(LOG_FILE), "data", "DEBUG_LOG")`)
# defeats any paren-balanced pattern, and the first cut of this check missed
# three paths exactly that way.
JOIN = re.compile(r'["\']data["\']\s*,\s*(?:\n\s*)?["\']([A-Za-z0-9_.\-]+)["\']')
FAILS = []


def check(n, ok, d=""):
    print("  {:<5} {}  {}".format(n, "PASS" if ok else "FAIL", d))
    if not ok:
        FAILS.append(n)


def git(*args):
    return subprocess.run(["git", "-C", REPO] + list(args),
                          capture_output=True, text=True)


def main():
    print("check_runtime_ignored — every runtime path under data/ is ignored")
    try:
        ls = git("ls-files", "*.py")
    except Exception as exc:                                    # noqa: BLE001
        check("R0", False, "git could not run: {}".format(exc))
        return 1
    if ls.returncode != 0:
        check("R0", False, "not a git checkout at {}: {}".format(
            REPO, ls.stderr.strip()))
        return 1
    files = [f for f in ls.stdout.split() if not f.startswith("tests/")]
    tracked = set(git("ls-files", "data").stdout.split())
    found = {}
    for rel in files:
        try:
            with open(os.path.join(REPO, rel), encoding="utf-8") as fh:
                src = fh.read()
        except Exception as exc:                                # noqa: BLE001
            check("R0", False, "unreadable {}: {}".format(rel, exc))
            continue
        for m in JOIN.finditer(src):
            line = src.count("\n", 0, m.start()) + 1
            found.setdefault(m.group(1), []).append("{}:{}".format(rel, line))
    # R1 — the scan found something. A regex that silently stopped matching
    # would otherwise turn this whole check into a green nothing.
    check("R1", "level_history" in found and "liquidity_ledger" in found,
          "scan found {} runtime name(s) (must include level_history and "
          "liquidity_ledger)".format(len(found)))
    for name in sorted(found):
        p = "data/" + name
        if any(t == p or t.startswith(p + "/") for t in tracked):
            print("  skip  {} is TRACKED source, not runtime".format(p))
            continue
        ign = (git("check-ignore", "-q", p).returncode == 0
               or git("check-ignore", "-q", p + "/probe").returncode == 0)
        check("R2", ign, "{} {}  (referenced at {})".format(
            p, "ignored" if ign else "NOT IGNORED", ", ".join(found[name][:3])))
    print()
    if FAILS:
        print("FAILED: {}".format(", ".join(sorted(set(FAILS)))))
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
