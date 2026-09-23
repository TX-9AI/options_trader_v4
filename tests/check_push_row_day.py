#!/usr/bin/env python3
# options-trader-v4/tests/check_push_row_day.py — v1.0
# v1.0 (2026-09-23) — r417 / WH.20. A PARTITION IS THE ROW'S DAY, AND A ROW IS
#   NOT DELETED BEFORE S3 HAS IT.
#   🔴 THE DEFECT, MEASURED IN THE BUCKET AND NOT INFERRED. `push_series` set
#   `day = datetime.now(ET).date()` at PUSH time and filed every object under
#   it. `SERIES_BATCH_ROWS` caps each run at 50,000 rows, so on the biggest
#   writers a backlog drains across midnight and the rows land in the NEXT
#   day's partition. Counted 2026-09-23 over raw/: 566 of 224,336 series
#   objects sat in the wrong `dt=` — `quote_series` 389, `surface_series` 146
#   — and QQQ's 2026-09-22 session was split 6 objects into dt=2026-09-22 and
#   50 into dt=2026-09-23, while dt=2026-09-22 ALSO held 27 objects of 09-21
#   rows. A single-partition reader gets a smaller, entirely plausible number,
#   which is [[C.9]]'s failure mode one prefix over.
#   🔑 R3 IS THE CHECK THAT MATTERS AND THE ONE THE OLD CODE COULD NOT PASS:
#   the high-water mark must NOT advance when any group of a split batch fails
#   to land. Advancing past an unwritten group skips those rows FOREVER — the
#   box deletes them on a 3-day clock and S3 is the only durable home.
#   🔴 R5/R6 ARE A DIFFERENT DEFECT FOUND IN THE SAME HOUR: the purge deleted
#   on AGE ALONE while the pusher drains on its own clock, so a pusher more
#   than the retention window behind loses the tape silently. Measured lag was
#   ~1 day against a 3-day policy — ~2 days of margin, and NOTHING measured it.
"""Gate: `dt=` is the row's ET day, and retention never outruns the push mark.

R1   a row from a previous ET day is filed under THAT day, not today
R2   a batch straddling an ET day boundary is SPLIT, one object per day
R3   a failed group does NOT advance the high-water mark (the data-loss fix)
R4   a fully successful push DOES advance it to the last row  [control]
R5   retention clamps its cutoff to the push high-water mark
R6   an ABSENT ledger falls back to age-only and NAMES the absence  [control]
"""
import datetime
import json
import os
import sqlite3
import sys
import tempfile

try:
    from zoneinfo import ZoneInfo
except ImportError:                                   # pragma: no cover
    ZoneInfo = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ET = ZoneInfo("America/New_York") if ZoneInfo else None
_fails = []


def ck(tag, ok, msg=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {tag}  {msg}")
    if not ok:
        _fails.append(tag)


class FakeS3:
    """put/get backed by a dict, so `put_and_verify`'s byte-compare passes."""

    def __init__(self, fail_keys=()):
        self.store = {}
        self.fail_keys = tuple(fail_keys)

    def put_object(self, Bucket=None, Key=None, Body=None):
        for frag in self.fail_keys:
            if frag in Key:
                raise RuntimeError("injected put failure")
        self.store[Key] = Body

    def get_object(self, Bucket=None, Key=None):
        class _B:
            def __init__(self, b):
                self._b = b

            def read(self):
                return self._b
        return {"Body": _B(self.store[Key])}


def _db(rows):
    """A feed_store-shaped db holding one series table."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE quote_series (ts_epoch REAL, v TEXT)")
    con.executemany("INSERT INTO quote_series VALUES (?,?)",
                    [(t, "x") for t in rows])
    con.commit()
    con.close()
    return path


def _days_of(store):
    """dt= values present in the fake bucket, with their object counts."""
    out = {}
    for k in store:
        for part in k.split("/"):
            if part.startswith("dt="):
                out[part[3:]] = out.get(part[3:], 0) + 1
    return out


def main():
    try:
        from warehouse import s3_push as SP
    except Exception as exc:                          # pragma: no cover
        ck("R0", False, f"cannot import warehouse.s3_push ({exc})")
        print("\nRED — 1 check(s) failed: R0")
        return 1

    push_series = getattr(SP, "push_series", None)
    if push_series is None:
        ck("R0", False, "push_series is absent")
        print("\nRED — 1 check(s) failed: R0")
        return 1

    now = datetime.datetime.now(ET)
    today = now.date()
    y = today - datetime.timedelta(days=1)

    # ── R1 — a yesterday row is filed under YESTERDAY ────────────────────
    # Built at 14:00 ET so the timestamp cannot drift across a boundary while
    # the test runs, which would make this check flap at midnight.
    y_noon = datetime.datetime.combine(
        y, datetime.time(14, 0), tzinfo=ET).timestamp()
    path = _db([y_noon, y_noon + 1, y_noon + 2])
    s3 = FakeS3()
    led = {}
    try:
        push_series(s3, "B", path, led, "QQQ", None, tables=("quote_series",))
        days = _days_of(s3.store)
        ck("R1", days == {y.isoformat(): 1},
           f"dt= partitions written: {days} (want {{{y.isoformat()}: 1}})")
    except Exception as exc:
        ck("R1", False, f"raised {exc!r}")
    finally:
        os.unlink(path)

    # ── R2 — a straddling batch is SPLIT, one object per ET day ──────────
    y_late = datetime.datetime.combine(
        y, datetime.time(23, 30), tzinfo=ET).timestamp()
    t_early = datetime.datetime.combine(
        today, datetime.time(9, 35), tzinfo=ET).timestamp()
    path = _db([y_late, y_late + 60, t_early, t_early + 60])
    s3 = FakeS3()
    led = {}
    try:
        push_series(s3, "B", path, led, "QQQ", None, tables=("quote_series",))
        days = _days_of(s3.store)
        want = {y.isoformat(): 1, today.isoformat(): 1}
        ck("R2", days == want, f"dt= partitions written: {days} (want {want})")
    except Exception as exc:
        ck("R2", False, f"raised {exc!r}")
    finally:
        os.unlink(path)

    # ── R3 — a failed group must NOT advance the high-water mark ─────────
    # The SECOND group (today) is rejected; the mark must stay at 0 so the
    # whole batch is retried, rather than advancing past rows S3 never got.
    path = _db([y_late, y_late + 60, t_early, t_early + 60])
    s3 = FakeS3(fail_keys=(f"dt={today.isoformat()}",))
    led = {}
    try:
        push_series(s3, "B", path, led, "QQQ", None, tables=("quote_series",))
        mark = led.get("series|quote_series", 0)
        ck("R3", not mark,
           f"high-water after a failed group = {mark!r} (want unset/0)")
    except Exception as exc:
        ck("R3", False, f"raised {exc!r}")
    finally:
        os.unlink(path)

    # ── R4 — CONTROL: a clean push DOES advance the mark ─────────────────
    path = _db([y_noon, y_noon + 1, y_noon + 2])
    s3 = FakeS3()
    led = {}
    try:
        push_series(s3, "B", path, led, "QQQ", None, tables=("quote_series",))
        mark = led.get("series|quote_series", 0)
        ck("R4", abs(float(mark) - (y_noon + 2)) < 1e-6,
           f"high-water = {mark!r} (want {y_noon + 2!r})")
    except Exception as exc:
        ck("R4", False, f"raised {exc!r}")
    finally:
        os.unlink(path)

    # ── R5 / R6 — retention never outruns the push mark ──────────────────
    try:
        from warehouse import retention_purge as RP
    except Exception as exc:
        ck("R5", False, f"cannot import warehouse.retention_purge ({exc})")
        ck("R6", False, "not reached")
        RP = None

    if RP is not None:
        safe = getattr(RP, "_safe_cutoff", None)
        if safe is None:
            ck("R5", False, "_safe_cutoff is absent")
            ck("R6", False, "_safe_cutoff is absent")
        else:
            day = getattr(RP, "DAY", 86400.0)
            age_cutoff = 1_000_000.0
            hwm = age_cutoff - 2 * day          # pusher 2 days behind
            fd, lpath = tempfile.mkstemp(suffix=".json")
            os.close(fd)
            with open(lpath, "w", encoding="utf-8") as fh:
                json.dump({"series|quote_series": hwm}, fh)
            try:
                got, note = safe("quote_series", age_cutoff, lpath, "series")
                ck("R5", abs(got - hwm) < 1e-6 and bool(note),
                   f"cutoff={got!r} (want {hwm!r}), note={note[:48]!r}")
            except Exception as exc:
                ck("R5", False, f"raised {exc!r}")
            finally:
                os.unlink(lpath)

            # R6 — CONTROL: no ledger at all must NOT block deletion, and must
            # say so. Refusing everything here fills the disk by morning.
            try:
                got, note = safe("quote_series", age_cutoff,
                                 "/nonexistent/ledger.json", "series")
                ck("R6", abs(got - age_cutoff) < 1e-6 and bool(note),
                   f"cutoff={got!r} (want age {age_cutoff!r}), "
                   f"note={note[:48]!r}")
            except Exception as exc:
                ck("R6", False, f"raised {exc!r}")

    if _fails:
        print(f"\nRED — {len(_fails)} check(s) failed: {' '.join(_fails)}")
        return 1
    print("\nGREEN — dt= is the row's day and retention respects the push mark")
    return 0


if __name__ == "__main__":
    sys.exit(main())
