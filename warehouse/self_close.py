#!/usr/bin/env python3
"""
warehouse/self_close.py  v1.2
The box closes ITSELF: drain to S3, verify it landed, then shut down.

v1.2  2026-08-23  AUDIT F1: THE VERIFIER WAS SPAWNED UNDER THE BOT VENV, WHICH
HAS NO boto3. The unit runs this file under `venv/bin/python` and v1.1 passed
`sys.executable` on to `s3_push.py`, whose late `import boto3` then raised
inside its rule-1 handler: it printed "run aborted, nothing confirmed", exited
0, and there was no DRAIN line. That parses as SHORT -> every box stayed up and
paged, every night, and the purge never ran. `deploy/s3-push.service` and
`install_s3_push_timer.sh` both state the constraint ("boto3 is present in
SYSTEM python fleet-wide and absent from the bot venv"); this file did not
carry it across. The verifier now runs under the SAME interpreter the s3-push
unit uses (`/usr/bin/python3`), so the two paths cannot disagree about the
environment either. Fail direction unchanged: a verifier that cannot run
still reads as unverified and the box stays up. Also: a verifier TIMEOUT
(`subprocess.TimeoutExpired`) was an uncaught raise - box held with no alert.
It is now held AND alerted like any other unverified close.

v1.1  2026-08-25  Runs the RETENTION PURGE after verification and before the
halt. Placed there deliberately: the purge must never touch unverified data,
and a held box never reaches that line, so the guarantee falls out of the
ordering rather than needing its own check. Dry unless OT_RETENTION_APPLY=1.

v1.0  2026-08-25  Operator's design, and it is a better architecture than the
control-only one it replaces:

  *"There should be a timer on the boxes that has them push to s3 if they are
   still awake after a certain time from market close. Rationale: they don't
   need to know they're controlled. If control is disabled, or not used, they
   push to s3 at a particular time, verify data landed & shut down. And if the
   box is down when the timer fires because conductor already did everything,
   then it fires into silence. Nothing happens. No warning. Just nothing
   needed."*

🔑 THE BOX'S AUTONOMY IS THE FALLBACK, NOT A COMPETING SYSTEM. Every box is
independently correct on its own. The conductor is an OPTIMISATION — it closes
the fleet sooner and in a coordinated order — and when it has already run, this
timer fires on a stopped machine and nothing happens. **A timer firing into
silence is the CORRECT outcome here, not a missed run**, so it must never warn.

🔴 IT INVERTS THE FAILURE MODE, WHICH IS THE REAL WIN. Before: control disabled
or broken meant fifteen boxes RAN ALL NIGHT and the operator found out from the
bill. Now a dead control server costs nothing — the fleet closes itself.

⚠️ 16:45 IS CHOSEN SO THE TWO CAN NEVER RACE. The conductor starts at 16:05 and
has the boxes down by ~16:08. A tighter gap risks both draining at once — two
writers on the same prefixes, which is precisely the collision class behind the
duplicate objects in the bucket.

⚠️ VERIFY BEFORE HALT, ALWAYS — and STAY UP IF SHORT. A box that shuts down on
unverified data is worse than one that stays up: the local store is the only
copy left, and a stopped box cannot be asked anything.

⚠️ AND A HELD BOX HAS NO ONE TO TELL, so it alerts for itself. The conductor
reports held boxes to the operator; autonomy does not give that for free, and a
box that quietly stays up short is a box nobody looks at until morning.
"""

from __future__ import annotations

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

# The interpreter `deploy/s3-push.service` uses. boto3 lives HERE, not in the
# bot venv. Falls back to the current interpreter only if system python is
# absent, which is not a fleet configuration that exists.
WAREHOUSE_PY = "/usr/bin/python3" if os.path.exists("/usr/bin/python3") else sys.executable


def _log(msg: str) -> None:
    print(f"[self-close] {msg}", flush=True)


def main(argv=None) -> int:
    dry = "--dry-run" in (argv or sys.argv)

    try:
        from config import INSTRUMENT
    except Exception:                                           # noqa: BLE001
        INSTRUMENT = os.environ.get("OT_INSTRUMENT", "?")

    _log(f"{INSTRUMENT}: nobody closed this box — closing it myself")

    # ── 1. stop trading. The feed stays up so a 16:00 candle can still land ──
    if not dry:
        subprocess.run(["sudo", "systemctl", "stop", "optionsbot"],
                       capture_output=True, timeout=120)
        _log("optionsbot stopped; feed left running to flush")

    # ── 2. drain + verify, one call ─────────────────────────────────────────
    # ⚠️ THE SAME `--verify` THE CONDUCTOR USES. One verification path, so the
    # two close routes cannot disagree about what "landed" means.
    # ⚠️ F1: SYSTEM python, never `sys.executable`. This file runs under the
    # bot venv (it needs config + the alert manager); the verifier needs boto3,
    # which lives only in system python. Same interpreter as s3-push.service.
    cmd = [WAREHOUSE_PY, os.path.join(HERE, "warehouse", "s3_push.py"), "--verify"]
    if dry:
        _log(f"[dry] would run: {' '.join(cmd)}")
        return 0
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        out = (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired as exc:
        out = ((exc.stdout or b"").decode("utf-8", "replace")
               if isinstance(exc.stdout, bytes) else (exc.stdout or ""))
        out += "\n[self-close] VERIFIER TIMED OUT after 1800s - unverified"
    print(out)

    line = next((l for l in out.splitlines() if l.startswith("DRAIN ")), "")
    ok = " short=0 " in line and line.rstrip().endswith("OK")
    drift = "COUNTER DRIFT" in out

    # ⚠️ DRIFT IS NOT LOSS. Same rule as the conductor: a small consistent
    # shortfall across many prefixes is an inflated ledger with every object
    # present. Holding the box for it would keep the whole fleet up nightly.
    if not ok and not drift:
        _log("SHORT — data not verified in S3. STAYING UP.")
        try:
            from notifications.alert_manager import get_alert_manager
            am = get_alert_manager()
            if am:
                am.send(f"⚠️ {INSTRUMENT}: self-close held — data NOT verified "
                        f"in S3. Box is still running.\n{line[:200]}")
        except Exception as exc:                                # noqa: BLE001
            _log(f"(could not alert: {exc})")
        return 1

    if drift:
        _log("shortfall is COUNTER DRIFT — objects present; proceeding")

    # ── 3. trim expired local data ──────────────────────────────────────────
    # 🔑 HERE, AND NOWHERE ELSE, BECAUSE VERIFICATION HAS JUST SUCCEEDED. The
    # purge's own rule is "never delete unverified data" — placing it after the
    # SHORT check makes that fall out of the ORDERING instead of needing its
    # own guard. A held box never reaches this line, so a box whose push failed
    # keeps every local row.
    # ⚠️ DRY UNLESS `OT_RETENTION_APPLY=1`. The policy numbers are arithmetic
    # from EMA_ANCHOR, not measurements; a week of dry runs says whether they
    # are right before anything is at risk.
    # ⚠️ AND IT NEVER BLOCKS THE HALT. A purge failure is reported and stepped
    # over — the machine still comes down, which is what ends the bill.
    try:
        from warehouse import retention_purge
        retention_purge.main([])
    except Exception as exc:                                    # noqa: BLE001
        _log(f"retention purge skipped: {exc}")

    # ── 4. halt ─────────────────────────────────────────────────────────────
    # ⚠️ `shutdown` NOT `systemctl stop` — the box stops the MACHINE, which is
    # what actually ends the EC2 bill. Stopping services would leave it running
    # and idle, which is the expensive half of the old failure mode.
    _log("verified in S3 — halting")
    subprocess.run(["sudo", "shutdown", "-h", "now"], capture_output=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
