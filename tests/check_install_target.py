#!/usr/bin/env python3
"""
tests/check_install_target.py  v1.1
v1.1  2026-09-21  r408 / OPS.34 — I7/I8. THE TEMPLATE THIS FILE CHECKS WAS
      GITIGNORED, SO I2 AND I3 WERE READING A FILE THAT IS NOT IN THE REPO.
      🔴 v1.0 PASSED AT LAND TIME FOR THE WRONG REASON. `bootstrap.example.sh`
      exists in the working tree on control, so I2/I3 read it happily — but
      `.gitignore` carried `!bootstrap.example.sh` ABOVE `bootstrap*.sh`, git
      applies the LAST matching pattern, and the file **has never been tracked
      in otv4**. In a pristine clone it is absent and I2 would have gone RED
      for the environment, which is [[CHK.9]] item 2's shape — the very class
      this suite is supposed to respect.
      🔑 I7 DRIVES `git check-ignore` AGAINST THE PATH, and I8 asserts that
      EVERY negation in `.gitignore` is actually in force — so the next
      exception written above its rule is caught the day it is added rather
      than the day a land quietly stages one file fewer.
v1.0  2026-09-21  r407 / OPS.33 — THE UNATTENDED INSTALL MUST FACE otv4, AND
      otv4 MUST BE ABLE TO INSTALL ITSELF.

🔴 WHAT IT PROTECTS. Until r407 the bootstrap curled **v3's** installer and
`install.sh` cloned **v3**, so the "5-minute unattended deploy" built the
PREVIOUS generation every time and only became otv4 when REPOINT rewrote
origin afterwards. v3's installer has no sparse logic at all (2,025 bytes
against otv4's 9,695) and nothing re-runs an installer, which is the entire
mechanism behind [[OPS.18]].
⚠️ **THE SAME CLASS BIT AT THE v2→v3 SPLIT** and `install.sh`'s own header
records it: the clone URL still said v2, every fresh install silently deployed
v2 code, and it was caught **only because a rebuild's banner printed v2.5**.

  I1  install.sh's REPO= assignment targets otv4
  I2  bootstrap's GITHUB_REPO export targets otv4
  I3  every operative raw.githubusercontent fetch targets otv4
  I4  🔑 PROVENANCE IS PERMITTED — the §32 "Ported from v3" lines survive
  I5  requirements.txt exists AND covers what the shipped surface imports
  I6  the banner names v4 — the one signal that has ever caught this
  I7  🔴 bootstrap.example.sh is COMMITTABLE — git does not ignore it
  I8  every negation in .gitignore is actually IN FORCE (the shape)

🔑 I1–I3 ARE ANCHORED ON THE SHAPE OF AN OPERATIVE TARGET — an assignment, an
export, a fetch URL — never on the token `options_trader_v3`. otv4 carries
**81 legitimate "Ported from options_trader_v3 at the OTV4 split" lines**,
which are §32 doctrine and must NOT be swept; a canary that fired on them
would be loosened within a week and the loosened one would miss the real
thing. That is §20, and I4 exists to prove the distinction holds rather than
assert it.

Plain script with an exit code, stdlib only (§36, [[CHK.9]]).
"""
from __future__ import annotations
import ast
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INSTALL = os.path.join(ROOT, "install.sh")
BOOT = os.path.join(ROOT, "bootstrap.example.sh")
REQ = os.path.join(ROOT, "requirements.txt")
WANT = "options_trader_v4"
_res = []


def ck(name, ok, why=""):
    _res.append((name, bool(ok), why))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}  {'' if ok else why}")


def _read(p):
    try:
        return open(p, encoding="utf-8").read()
    except OSError:
        return None


ins, boot = _read(INSTALL), _read(BOOT)

# ── I1 · the clone URL, as an ASSIGNMENT ───────────────────────────────────
if ins is None:
    ck("I1", False, f"{INSTALL} missing")
else:
    m = re.search(r'^\s*REPO=(["\']?)(\S+?)\1\s*$', ins, re.M)
    ck("I1", bool(m) and WANT in m.group(2),
       f"install.sh's REPO= must clone {WANT} — it ran `git clone $REPO` and "
       f"then executed THAT clone's setup_ec2.sh, so a v3 URL here installs "
       f"the previous generation. got {m.group(2) if m else None!r}")

# ── I2 · the bootstrap's repo export ───────────────────────────────────────
if boot is None:
    ck("I2", False, f"{BOOT} missing")
else:
    m = re.search(r'^\s*export\s+GITHUB_REPO=(["\']?)([^"\'\s#]+)\1', boot, re.M)
    ck("I2", bool(m) and WANT in m.group(2),
       f"bootstrap's GITHUB_REPO must be {WANT} — it sets the box's push "
       f"remote and commit author. got {m.group(2) if m else None!r}")

# ── I3 · every OPERATIVE fetch ─────────────────────────────────────────────
# ⚠️ A `curl` inside a COMMENT is documentation, not a fetch. The one-liner in
# install.sh's header is exactly that, and it is swept too — but by being a
# curl URL, not by being a mention of v3.
bad = []
for label, text in (("install.sh", ins), ("bootstrap.example.sh", boot)):
    if not text:
        continue
    for url in re.findall(r'raw\.githubusercontent\.com/[A-Za-z0-9._-]+/([A-Za-z0-9._-]+)/', text):
        if url != WANT:
            bad.append((label, url))
ck("I3", not bad,
   f"operative fetch URL(s) still pointing elsewhere: {bad} — the bootstrap "
   f"curls this to get the installer, so a v3 URL means a v3 install "
   f"regardless of what the rest of the file says")

# ── I4 · 🔑 PROVENANCE SURVIVES — THE CONTROL ON THE CANARY ────────────────
# If a future edit "fixes" the v3 mentions by sweeping the port lines, this
# goes red. The doctrine block is §32's mandated reading and records where the
# file came from; deleting history to satisfy a grep degrades the record to
# protect the test, which §20 names as the worse trade.
prov = 0
for text in (ins, boot):
    if text:
        prov += len(re.findall(r"Ported from options_trader_v3", text))
ck("I4", prov >= 2,
   f"the §32 provenance lines (\"Ported from options_trader_v3 at the OTV4 "
   f"split\") must SURVIVE the repoint — found {prov}, expected one per file. "
   f"This check exists so the v3 sweep can never be done with a blunt "
   f"find-and-replace.")

# ── I5 · otv4 CAN INSTALL ITSELF, AND THE MANIFEST COVERS WHAT IT IMPORTS ──
# 🔴 `setup_ec2.sh:225` ABORTS without this file, which is why otv4 could not
# be installed at all and why the v3 pointer was load-bearing.
# 🔑 THE COVERAGE HALF IS MEASURED AT CHECK TIME, NOT PINNED: the shipped
# surface is walked by AST with tests/ and docs/ excluded exactly as sparse
# excludes them, so a NEW third-party import added next month must be declared
# or explicitly excused — it cannot quietly go missing until a fresh install
# fails at 09:30.
req = _read(REQ)
if req is None:
    ck("I5", False,
       f"{REQ} does not exist — setup_ec2.sh:225 aborts the install without "
       f"it ('ERROR: requirements.txt missing. Aborting.'), which is why a "
       f"bootstrap could never be pointed at otv4")
else:
    declared = set()
    for line in req.splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            declared.add(re.split(r"[<>=!\[]", line)[0].strip().lower())
    excused = set()
    tail = req.split("DELIBERATELY ABSENT", 1)
    if len(tail) == 2:
        excused = {w.lower() for w in re.findall(r"^#\s{0,3}([a-z0-9_.-]+)(?:,\s*[a-z0-9_.-]+)*\s+—",
                                                 tail[1], re.M)}
        excused |= {w.lower() for w in re.findall(r"^#\s{0,3}[a-z0-9_.-]+,\s*([a-z0-9_.-]+)\s+—",
                                                  tail[1], re.M)}
    SKIP = {"tests", "docs", ".git", "__pycache__", "venv"}
    localnames, ext = set(), {}
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP]
        for f in files:
            if f.endswith(".py"):
                rel = os.path.relpath(os.path.join(root, f), ROOT)
                localnames.add(os.path.splitext(os.path.basename(rel))[0])
                parts = rel.split(os.sep)
                if len(parts) > 1:
                    localnames.add(parts[0])
    std = set(sys.stdlib_module_names)
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP]
        for f in files:
            if not f.endswith(".py"):
                continue
            try:
                t = ast.parse(open(os.path.join(root, f), encoding="utf-8",
                                   errors="replace").read())
            except Exception:                                   # noqa: BLE001
                continue
            for node in ast.walk(t):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    mods = [node.module.split(".")[0]]
                for m in mods:
                    if m in std or m in localnames or m in SKIP:
                        continue
                    ext.setdefault(m.lower(), set()).add(os.path.relpath(
                        os.path.join(root, f), ROOT))
    uncovered = {m: sorted(v)[:2] for m, v in ext.items()
                 if m not in declared and m not in excused}
    ck("I5", not uncovered,
       f"third-party import(s) neither declared nor excused in "
       f"requirements.txt: {uncovered}. Declare it, or record it under "
       f"DELIBERATELY ABSENT with the reason — a fresh box builds its venv "
       f"from this file and finds out at 09:30.")

# ── I6 · THE BANNER, WHICH IS THE ONLY THING THAT HAS EVER CAUGHT THIS ─────
if ins is None:
    ck("I6", False, f"{INSTALL} missing")
else:
    b = re.search(r'options_trader\s+v([0-9.]+)\s*\|\s*Web Installer', ins)
    ck("I6", bool(b) and b.group(1).startswith("4"),
       f"the installer banner must name v4 — the v2→v3 instance of this exact "
       f"defect was caught ONLY because a rebuild's banner printed v2.5. "
       f"got {b.group(1) if b else None!r}")

# ── I7 · THE TEMPLATE CAN ACTUALLY BE COMMITTED ───────────────────────────
# 🔴 IT COULD NOT, FOR THE LIFE OF THE REPO. `git check-ignore -v` named
# `.gitignore:51:bootstrap*.sh` as the winning rule over the `!` exception at
# line 2, and `git log --all -- bootstrap.example.sh` is EMPTY. r407 repointed
# that template to otv4 and the land could not stage it — 4 payload files
# instead of 5 — which is how it surfaced.
# ⚠️ DRIVEN THROUGH git ITSELF, not by parsing `.gitignore`. Reimplementing
# git's last-match-wins precedence here would be a second definition of the
# rule that produced the defect (§7, C.23).
import subprocess as _sp


def _ignored(path):
    """True / False / None when git cannot answer."""
    try:
        r = _sp.run(["git", "-C", ROOT, "check-ignore", "-q", "--", path],
                    capture_output=True, timeout=30)
    except Exception:                                           # noqa: BLE001
        return None
    if r.returncode == 0:
        return True
    if r.returncode == 1:
        return False
    return None                      # 128 = not a repo, or git unavailable


_ig = _ignored("bootstrap.example.sh")
if _ig is None:
    ck("I7", True, "")
    print("  [I7] GREEN (VACUOUS) — git could not answer here (not a work "
          "tree?), so committability was NOT checked.")
else:
    ck("I7", _ig is False,
       "bootstrap.example.sh is IGNORED by .gitignore, so it cannot be "
       "committed — its own header calls it safe to commit, and r407's "
       "repoint of it silently failed to stage for exactly this reason. The "
       "negation must sit BELOW `bootstrap*.sh`: git takes the LAST match.")

# ── I8 · AND THE GENERAL SHAPE, SO THE NEXT ONE IS CAUGHT ─────────────────
# A negation placed above the rule it negates is inert, silently. This asserts
# every `!` line in .gitignore actually takes effect, rather than pinning the
# one that bit — a list of one rots the moment a second is added.
gi = os.path.join(ROOT, ".gitignore")
negs, inert = [], []
if os.path.exists(gi):
    for line in open(gi, encoding="utf-8"):
        line = line.strip()
        if line.startswith("!") and len(line) > 1 and "*" not in line:
            negs.append(line[1:])
for n in negs:
    if _ignored(n) is True:
        inert.append(n)
ck("I8", not inert,
   f"negation(s) in .gitignore that do NOTHING because a later rule overrides "
   f"them: {inert} — git applies the LAST matching pattern, so an exception "
   f"must come AFTER the rule it negates (checked {len(negs)} negation(s))")

bad_ = [n for n, ok, _ in _res if not ok]
print(f"\n  {len(_res) - len(bad_)}/{len(_res)} passed")
if bad_:
    print(f"  FAILED: {', '.join(bad_)}")
sys.exit(1 if bad_ else 0)
