#!/usr/bin/env python3
"""tests/check_midnight_halt.py — v1.0
v1.0  2026-09-06 — r289 / EOD.3.

🔴 THIS SCRIPT'S ONLY JOB IS TO STOP A MACHINE, so the cases are about the two
ways that goes wrong: halting a box that was deliberately held up, and NOT
halting one that was forgotten.

⚠️ IT MUST NOT ACQUIRE THE 16:45 PATH'S MACHINERY. `self_close` drains,
verifies, and stays up if short — all correct for a CLOSE, all wrong for a
backstop, because every one of those steps is a way to hang. M3 pins that this
file never imports boto3, never touches S3, and never calls the purge.
"""
import os
import subprocess
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name)


def _run(env_extra=None):
    env = dict(os.environ)
    env.update(env_extra or {})
    r = subprocess.run([sys.executable,
                        os.path.join(_root, "warehouse", "midnight_halt.py"),
                        "--dry-run"],
                       capture_output=True, text=True, env=env)
    return r.returncode, r.stdout + r.stderr


def main():
    # ══ 🔴 M1 — IT HALTS BY DEFAULT ══════════════════════════════════════
    with tempfile.TemporaryDirectory() as tmp:
        rc, out = _run({"OT_NO_MIDNIGHT_HALT": os.path.join(tmp, "absent")})
        check("M1 with no hold flag it would halt", rc == 0 and "would run" in out,
              f"rc={rc}")
        check("M1b ...via `shutdown`, the same mechanism self_close uses",
              "shutdown -h now" in out)

    # ══ 🔴 M2 — A HOLD FLAG KEEPS IT UP, SILENTLY AND SUCCESSFULLY ═══════
    # The one night the operator wants a box up all night is the night this
    # must not fight him. A held box is EXPECTED, so it must not read as a
    # failure — a timer that complains teaches him to stop reading its log.
    with tempfile.TemporaryDirectory() as tmp:
        flag = os.path.join(tmp, "NO_MIDNIGHT_HALT")
        open(flag, "w").close()
        rc, out = _run({"OT_NO_MIDNIGHT_HALT": flag})
        check("M2 a hold flag stops it halting", rc == 0 and "staying up" in out,
              f"rc={rc}")
        check("M2b ...and exits 0, because a held box is expected, not a fault",
              rc == 0)

    # ══ 🔴 M3 — IT HAS NONE OF THE 16:45 PATH'S MACHINERY ════════════════
    # Every step self_close takes is a way to hang. A backstop that can hang is
    # not a backstop.
    # ⚠️ ANCHORED ON CODE, NOT ON MENTIONS. A first cut banned the STRING
    # "boto3" and went red on the file's own note explaining why boto3 was
    # removed — the §20 trap, in a checker written to avoid it. An import is a
    # dependency; a sentence about one is documentation.
    src = open(os.path.join(_root, "warehouse", "midnight_halt.py")).read()
    for bad, why in (("import boto3", "no AWS client — no IAM, no network"),
                     ("from warehouse import s3_push", "no drain"),
                     ("import s3_push", "no drain"),
                     ("retention_purge.main", "no purge"),
                     ('urlopen("http://169.254', "no IMDS round trip")):
        check(f"M3 it does not use `{bad}` ({why})", bad not in src)

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — 9 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
