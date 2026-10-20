"""
utils/heartbeat.py  v1.0
v1.0  2026-10-20  r494 / WDOG.3 (port of OTV4TEST r295 e0ca234 LIVE.2, blob 99785cb5; the one
      difference is path(): mainline has no utils/paths.py, so its two-line _resolve is inlined) —
      ONE WRITER FOR data/BOT_HEARTBEAT, CALLABLE FROM A POLL LOOP.
      main._touch_heartbeat (r474) wrote the file once per main-loop pass and nothing else did, so a
      live close ladder that polled the broker for LIVE_FILL_DEADLINE_SECONDS (8) + a 6 s cancel
      grace per position, serially, with main's loop frozen, would stand still for >= 180 s at
      ~13 unfilled positions - and tools/emergency_watchdog.py (STALE_S = 180, two consecutive
      minutes) would SIGKILL the laddering bot. The two live poll loops
      (exit_engine._confirm_and_book_live_exit_pass, order_confirm.confirm_order_fill) and
      flatten_all now touch this on every iteration.

      THE FILE'S FORMAT IS UNCHANGED: "<epoch> <note>" - main writes the tick number, the loops a
      short word. The watchdog reads only the mtime. OT_HEARTBEAT_FILE moves it for ONE process (a
      checker that drives a live poll loop must not touch the live file); unset it is
      <repo>/data/BOT_HEARTBEAT, exactly main's path. NEVER RAISES: a heartbeat that could stop a
      close would be the hang it exists to catch; a failed write warns once per process.
"""
import logging
import os
import time

logger = logging.getLogger(__name__)
_warned = False
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def path() -> str:
    v = (os.environ.get("OT_HEARTBEAT_FILE") or "").strip()
    return os.path.expanduser(v) if v else os.path.join(_DATA_DIR, "BOT_HEARTBEAT")


def touch(note: str = "", file_path: str = None) -> bool:
    """Write "<epoch> <note>" to the heartbeat file. True on success; False (warned once) on failure."""
    global _warned
    try:
        with open(file_path or path(), "w") as f:
            f.write(f"{time.time():.0f} {note}\n")
        return True
    except Exception as exc:                                    # noqa: BLE001
        if not _warned:
            _warned = True
            logger.warning("heartbeat write failed (%s) — the emergency watchdog will read this bot as stuck", exc)
        return False
