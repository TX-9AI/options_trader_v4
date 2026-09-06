#!/usr/bin/env python3
"""warehouse/midnight_halt.py — v1.0

v1.0 (2026-09-06) — r289 / EOD.3. IF THIS BOX IS STILL UP AT MIDNIGHT ET, STOP.

Operator: *"We have a self-directed drain and shutdown at 16:45 if the conductor
held them up or was absent. I want an addition that takes any boxes down that
happen to still be up at midnight. I do sometimes work on them late & might
forget. So I want another self shutdown at midnight eastern time to catch
anything I accidentally left up. No drain, or anything else. Just stop, that's
it."*

🔑 THIS IS A BACKSTOP, NOT AN EOD PATH, AND THE DIFFERENCE IS THE WHOLE DESIGN.
`self_close.py` at 16:45 drains to S3, VERIFIES, and deliberately STAYS UP IF
SHORT — because "a box that shuts down on unverified data is worse than one that
stays up: the local store is the only copy left, and a stopped box cannot be
asked anything." That reasoning is about the CLOSE. By midnight the close is
seven hours gone; whatever is still running is running for a reason nobody is
awake for.

⚠️ SO IT DELIBERATELY DOES NOT DRAIN, VERIFY, OR REPORT. Adding any of that
would recreate the 16:45 path with a second set of failure modes and a second
chance to hang — and a backstop that can hang is not a backstop. It stops the
instance. That is the entire contract.

🔑 IT HALTS THE SAME WAY `self_close` DOES — `sudo shutdown -h now` — and for
the reason recorded there: "the box stops the MACHINE, which is what actually
ends the EC2 bill. Stopping services would leave it running and idle, which is
the expensive half of the old failure mode." No IAM, no IMDS, no network: a
backstop whose value is that it cannot fail in novel ways must not acquire
dependencies the path it backs up does not have.

⚠️ IT OVERRIDES A DELIBERATE HOLD, AND THAT IS SAID OUT LOUD. A box held up by
`self_close` because its data was UNVERIFIED will be stopped by this at
midnight. Its data is then stranded until the next wake — not lost, but not
reachable either. The operator's instruction is explicit and the alternative is
a box that bills all weekend; the trade is recorded here so nobody has to
re-derive it.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [midnight_halt] %(message)s",
)
log = logging.getLogger(__name__)

# ⚠️ AN ESCAPE HATCH THAT SURVIVES A BAKE, because the one night the operator
# genuinely wants a box up all night is the night this must not fight him. Same
# sentinel idiom as FEED_MAINTENANCE and DRILL_DISK — a file, no restart.
HOLD_FLAG = os.environ.get(
    "OT_NO_MIDNIGHT_HALT",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "data", "NO_MIDNIGHT_HALT"))


def main(argv=None) -> int:
    dry = "--dry-run" in (argv if argv is not None else sys.argv[1:])

    if os.path.exists(HOLD_FLAG):
        # ⚠️ SILENT AND SUCCESSFUL. A held box is an EXPECTED condition, and a
        # timer that complains about one teaches the operator to stop reading
        # its log — §17's reasoning, applied to a journal rather than a page.
        log.info("HOLD flag present (%s) — staying up, by request.", HOLD_FLAG)
        return 0

    if dry:
        log.info("[dry-run] would run: sudo shutdown -h now")
        return 0

    # 🔑 `shutdown` — THE SAME MECHANISM `self_close` USES, AND FOR ITS REASON:
    # "the box stops the MACHINE, which is what actually ends the EC2 bill.
    # Stopping services would leave it running and idle, which is the expensive
    # half of the old failure mode." On these instances an OS halt stops the
    # instance, so this needs no IAM, no IMDS and no network.
    # ⚠️ A FIRST CUT READ THE INSTANCE ID FROM IMDS AND CALLED `stop_instances`
    # VIA boto3. That reinvented a solved problem and added two dependencies —
    # a metadata round trip and an IAM permission — to a backstop whose entire
    # value is that it cannot fail in novel ways.
    log.info("still up at midnight ET — halting (backstop, no drain)")
    subprocess.run(["sudo", "shutdown", "-h", "now"], capture_output=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
