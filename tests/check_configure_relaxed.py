#!/usr/bin/env python3
"""
tests/check_configure_relaxed.py  v4.0

configure.sh option 7 can actually turn relaxed entry ON.

v4.0  2026-08-20  Written with configure.sh v4.1, after option 7 was found
      calling an undefined `confirm` on the AMD box. C5 added the same day:
      the exec bit is asserted in the GIT INDEX, because that is the only
      place it survives a clone (r50) and a tarball cannot supply it. C6
      added the same evening: a set_env write with no daemon-reload leaves
      systemd restarting from its cached unit.

WHAT HAPPENED, because the shape matters more than the typo. `confirm` is not a
function in this repo — the helper is `ask_yn`. Bash printed
"configure.sh: line 281: confirm: command not found", returned 127, and the
`if` therefore took the ELSE branch. Consequences:

  · relaxed entry could NEVER be switched on, and
  · merely OPENING the item wrote OT_RELAXED_ENTRY=0.

⚠️ IT FAILED IN THE SAFE DIRECTION, WHICH IS EXACTLY WHY IT SURVIVED A PORT.
A command-not-found inside an `if` is indistinguishable from an honest "no":
the menu printed "Relaxed entry OFF." and carried on. That is this project's
named failure class — something computed, was used, and looked right while
being meaningless — wearing a shell script instead of Python.

⚠️ SO THIS CHECK EXECUTES THE MENU ITEM, BOTH ANSWERS, and additionally
installs `command_not_found_handle` so ANY undefined helper on that path
becomes a hard, named failure instead of a silent "no". `bash -n` cannot catch
this: an unbound command name is a runtime event, not a syntax error.

BORN RED, verified 2026-08-20 against pristine HEAD f68e228:
  C1 -> "answering 'y' left OT_RELAXED_ENTRY=0"
  C3 -> "MISSING_COMMAND: confirm"

Run:  cd ~/options-trader-v4 && python3 tests/check_configure_relaxed.py
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIGURE = os.path.join(ROOT, "configure.sh")

PROBLEMS: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  - {detail}" if (detail and not ok) else ""))
    if not ok:
        PROBLEMS.append(name)


def _functions_only(src: str) -> str:
    """Extract every column-0 `name() {` ... column-0 `}` block.

    configure.sh ends in a top-level `while` loop, so it cannot be sourced —
    sourcing it would launch the interactive menu. Pulling the definitions out
    is what lets the real function body run under a harness.
    """
    out, keep = [], False
    for line in src.splitlines():
        if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*\(\)\s*\{", line):
            keep = True
        if keep:
            out.append(line)
        if keep and line == "}":
            keep = False
    return "\n".join(out)


def _drive(answer: str, start_value: str) -> tuple[str, str, int]:
    """Run change_relaxed with a canned y/n. Returns (env_value, stderr, rc)."""
    src = open(CONFIGURE).read()
    with tempfile.TemporaryDirectory() as tmp:
        envfile = os.path.join(tmp, "env")
        with open(envfile, "w") as fh:
            fh.write(f"OT_RELAXED_ENTRY={start_value}\n")
        funcs = os.path.join(tmp, "funcs.sh")
        with open(funcs, "w") as fh:
            fh.write(_functions_only(src))

        harness = f"""
# Any undefined command on this path is a NAMED failure, not a silent "no".
command_not_found_handle() {{ echo "MISSING_COMMAND: $1" >&2; exit 42; }}
RESET=""; BOLD=""; GREEN=""; YELLOW=""; CYAN=""
source "{funcs}"
# Stub the two env accessors and the daemon reload; everything else is the
# real code. reload_daemon is stubbed because it shells out to `sudo
# systemctl`, which does not exist in every checkout — and a check that goes
# red on ENVIRONMENT rather than CONTENT teaches an operator to ignore reds.
# It still ANNOUNCES itself, so the call is asserted rather than assumed.
get_env() {{ sed -n "s/^$1=//p" "{envfile}"; }}
set_env() {{ grep -v "^$1=" "{envfile}" > "{envfile}.t" 2>/dev/null;
             mv "{envfile}.t" "{envfile}"; echo "$1=$2" >> "{envfile}"; }}
reload_daemon() {{ echo "RELOAD_CALLED" >&2; }}
change_relaxed
"""
        proc = subprocess.run(["bash", "-c", harness], input=f"{answer}\n",
                              capture_output=True, text=True, timeout=30)
        value = ""
        for line in open(envfile):
            if line.startswith("OT_RELAXED_ENTRY="):
                value = line.strip().split("=", 1)[1]
        return value, proc.stderr, proc.returncode


def main() -> int:
    print("=" * 68)
    print("CONFIGURE OPTION 7: relaxed entry can actually be turned on")
    print("=" * 68)

    # ── C1 the answer that was impossible before ─────────────────────────
    val, err, rc = _drive("y", "0")
    check("C1 answering 'y' sets OT_RELAXED_ENTRY=1", val == "1",
          f"answering 'y' left OT_RELAXED_ENTRY={val!r} (rc={rc})")
    check("C1 the ON branch reloads the daemon", "RELOAD_CALLED" in err,
          "set_env wrote the unit file and systemd was never told - the "
          "restart would come back on the OLD value")

    # ── C2 the other direction still works ───────────────────────────────
    val_n, err_n, _rc_n = _drive("n", "1")
    check("C2 answering 'n' sets OT_RELAXED_ENTRY=0", val_n == "0",
          f"answering 'n' left OT_RELAXED_ENTRY={val_n!r}")
    check("C2 the OFF branch reloads the daemon", "RELOAD_CALLED" in err_n,
          "the else branch writes the unit file too, and it must reload")

    # ── C3 no undefined helper anywhere on the path ──────────────────────
    check("C3 no command-not-found on the relaxed path",
          "MISSING_COMMAND" not in err and rc != 42,
          err.strip().splitlines()[-1] if err.strip() else f"rc={rc}")

    # ── C4 the helper it calls is really defined in this file ────────────
    src = open(CONFIGURE).read()
    called = re.findall(r"^\s*if (\w+) \"", src, re.M)
    defined = set(re.findall(r"^([a-zA-Z_][a-zA-Z0-9_]*)\(\)", src, re.M))
    # ⚠️ RESOLVE AGAINST THE SHELL, NOT AGAINST A LIST I MAINTAIN. The first
    # draft carried a hand-written allowlist of builtins and flagged `echo` —
    # a checker crying wolf on correct code, which trains an operator to ignore
    # it. `command -v` is the same lookup bash itself will do at runtime.
    undefined = []
    for c in sorted(set(called)):
        if c in defined:
            continue
        if subprocess.run(["bash", "-c", f"command -v {c}"],
                          capture_output=True).returncode != 0:
            undefined.append(c)
    check("C4 every `if <helper> \"...\"` names a defined function",
          not undefined, f"undefined: {undefined}")

    # ── C5 the exec bit, IN THE INDEX — where it actually has to live ────
    # r50 exists because a repointed box hit "Permission denied" on this very
    # file: git does not preserve the executable bit unless it is set in the
    # INDEX, and the working-tree mode is not what a fresh clone gets.
    # ⚠️ AND A TARBALL CANNOT FIX IT. `cp` preserves the DESTINATION file's
    # mode, so a 0755 archive member lands on a 0644 file and stays 0644 —
    # measured, not assumed. The archive's bit is decorative; the index's is
    # the one every clone reads.
    rc = subprocess.run(["git", "ls-files", "-s", "--", "*.sh"], cwd=ROOT,
                        capture_output=True, text=True)
    if rc.returncode != 0:
        # Not a failure: a red that means ENVIRONMENT teaches an operator to
        # ignore reds. Say what was not checked and move on.
        print("  NOTE  C5 skipped - git not available here; index modes "
              "unverified")
    else:
        nonexec = sorted(line.split("\t")[-1] for line in rc.stdout.splitlines()
                         if line and not line.startswith("100755"))
        check("C5 every root .sh is 100755 in the git index", not nonexec,
              f"not executable in the index: {nonexec} — a fresh clone or a "
              f"repoint gets Permission denied on these")

    # ── C6 a unit-file write must be followed by a daemon-reload ─────────
    # `set_env` edits the systemd UNIT FILE. Without `reload_daemon`, systemd
    # restarts from its CACHED unit, so the bot comes back on the OLD value
    # while configure.sh and the menu both report the NEW one — the setting
    # looks applied and is not. change_relaxed shipped that way (v4.1 -> v4.2).
    # ⚠️ EXACT, NOT HEURISTIC: this parses column-0 function blocks and asks
    # "does this body call set_env at all, and if so does it also reload?".
    # One reload after a batch of writes is correct and is what the other six
    # do, so the assertion is presence-per-function, not a count match.
    blocks, cur, fname = {}, [], None
    for line in src.splitlines():
        m = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\(\)\s*\{", line)
        if m:
            fname, cur = m.group(1), []
        if fname is not None:
            cur.append(line)
            if line == "}":
                blocks[fname] = "\n".join(cur)
                fname = None
    no_reload = sorted(n for n, b in blocks.items()
                       if n != "set_env" and "set_env" in b
                       and "reload_daemon" not in b)
    check("C6 every set_env caller also reloads the daemon", not no_reload,
          f"writes the unit file without reloading: {no_reload} — systemd "
          f"restarts from its cached unit and the bot runs the OLD value")

    print("=" * 68)
    if PROBLEMS:
        print(f"  {len(PROBLEMS)} problem(s): {PROBLEMS}")
        print("  An undefined command inside an `if` reads as an honest 'no'.")
        print("  The menu prints a plausible line and carries on.")
        return 1
    print("  ALL GREEN - option 7 works in both directions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
