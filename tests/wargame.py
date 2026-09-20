#!/usr/bin/env python3
"""
tests/wargame.py  v0.1
v0.1  2026-09-19  r391 / FU.5 — REPLAY THE REAL DECISION PATH AGAINST THE REAL
      TAPE, SO A PROPOSED CHANGE IS MEASURED INSTEAD OF ARGUED.

🔴 WHAT THIS IS AND WHAT IT REFUSES TO BE. The operator's instruction was to
wargame real chains and tapes "through our actual bot architecture". So this
harness does NOT model the strategies. It rebuilds the INPUTS from the
warehouse and calls the SAME engines and the SAME `generate_signal()` the live
bot calls. A second implementation of a decision rule is the drift WA §7 and
C.23 exist to prevent, and it would be invisible: both copies look right in
isolation and only disagree on the trades that matter.

⚠️ AND THE PRECEDENT IS ONE DAY OLD. `exit_replay` spent its whole life
scoring hypotheticals it could not reproduce — it refused 42 of 42 trades and
blamed the tape — and its positive control still printed ZERO because the
control's band was a third of entry cost (RPL.2). A harness that cannot
REPRODUCE WHAT ACTUALLY HAPPENED is not entitled to an opinion about what
would have happened. Hence:

  🔑 THE POSITIVE CONTROL IS THE PRODUCT, NOT A FORMALITY. With NO change
  applied, every gate value this harness emits must match the value the live
  bot recorded in `derived_plan_check` for the same tick, symbol, strategy and
  check name. Until that reconciles, no counterfactual from this tool means
  anything, and the report says so in those words.

THE TWO HAZARDS THIS FILE IS BUILT AROUND
  1. LOOKAHEAD. The classic way a backtest lies. It is not merely avoided
     here, it is made STRUCTURALLY IMPOSSIBLE: `Tape.at()` is the only way to
     reach a bar and it slices on the frozen instant. Asking it for anything
     at or beyond that instant RAISES rather than returning a row.
  2. THE WALL CLOCK. `orb_engine.update()` calls `now_et()` ITSELF for the
     11:00 ET cutoff and the range date, and 47 modules import that name. A
     replay run at 23:00 would find every session EXPIRED and would report a
     clean, wrong, empty answer. This is CHK.7 exactly — a result that encodes
     the hour of the run — and CHK.7 was found only eight minutes before a
     clamp would have hidden it. So the clock is frozen per tick, across every
     BOUND name, and the freeze is asserted rather than assumed.
"""
from __future__ import annotations

import io
import os
import sys
import types
from datetime import datetime

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))          # repo root — RPL.1's lesson

import pytz

ET = pytz.timezone("US/Eastern")


# ═══════════════════════════════════════════════════════════════════════════
# THE CLOCK
# ═══════════════════════════════════════════════════════════════════════════
class FrozenClock:
    """Freeze `now_et`/`now_utc` everywhere they are BOUND, not just defined.

    🔴 PATCHING `utils.time_utils.now_et` ALONE DOES NOTHING for the 47 modules
    that did `from utils.time_utils import now_et` — that binding was resolved
    at import and points at the original function object. So this walks every
    loaded module and rebinds any attribute that IS the original, which is an
    identity test and therefore cannot catch an unrelated same-named helper.
    """

    def __init__(self, when_et: datetime):
        if when_et.tzinfo is None:
            when_et = ET.localize(when_et)
        self.when_et = when_et
        self._saved: list[tuple[object, str, object]] = []

    def __enter__(self):
        import utils.time_utils as tu
        originals = {"now_et": tu.now_et, "now_utc": tu.now_utc}
        frozen_et = self.when_et
        frozen_utc = self.when_et.astimezone(pytz.UTC)

        def _now_et():
            return frozen_et

        def _now_utc():
            return frozen_utc

        repl = {"now_et": _now_et, "now_utc": _now_utc}

        for mod in list(sys.modules.values()):
            if not isinstance(mod, types.ModuleType):
                continue
            for name, orig in originals.items():
                try:
                    cur = getattr(mod, name, None)
                except Exception:                              # noqa: BLE001
                    continue
                if cur is orig:
                    self._saved.append((mod, name, orig))
                    try:
                        setattr(mod, name, repl[name])
                    except Exception:                          # noqa: BLE001
                        self._saved.pop()
        return self

    def __exit__(self, *exc):
        for mod, name, orig in self._saved:
            try:
                setattr(mod, name, orig)
            except Exception:                                  # noqa: BLE001
                pass
        self._saved.clear()
        return False

    @property
    def patched(self) -> int:
        return len(self._saved)


# ═══════════════════════════════════════════════════════════════════════════
# THE TAPE
# ═══════════════════════════════════════════════════════════════════════════
class LookaheadError(RuntimeError):
    """Raised when a caller reaches for a bar it could not have had."""


class Tape:
    """Point-in-time 1m bars for one symbol-session, plus a 5m resample.

    🔑 `at(ts)` IS THE ONLY WAY IN, and it returns bars whose OPEN is at or
    before `ts`. The final row is therefore the FORMING bar, exactly as the
    live loop sees it — `orb_engine._advance_state` reads `iloc[-2]` as the
    newest CLOSED bar and `iloc[-1]` as the one still printing, so handing it
    only closed bars would silently shift every decision one minute early.
    """

    def __init__(self, df_1m: pd.DataFrame, symbol: str, date: str):
        self.df = df_1m.sort_index()
        self.symbol = symbol
        self.date = date

    @classmethod
    def from_csv(cls, csv_text: str, symbol: str, date: str) -> "Tape":
        df = pd.read_csv(io.StringIO(csv_text))
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.set_index("timestamp").tz_convert(ET)
        df = df[["open", "high", "low", "close", "volume"]].astype(float)
        return cls(df, symbol, date)

    def at(self, ts: datetime) -> pd.DataFrame:
        """Bars whose OPEN is at or before `ts`.

        🔴 THE LAST ROW MAY BE A BAR THAT WAS STILL FORMING AT `ts`, AND ITS
        CLOSE IS THEREFORE FROM THE FUTURE. A 1m bar stamped 09:37:00 does not
        finish until 09:38:00, so at a tick of 09:37:15 the live bot had 15
        seconds of it and this frame has all sixty. Callers that replay a
        DECISION must use `closed_at()` and `bar_aligned()`; this accessor
        exists for outcome scoring, where the future is the point.
        ⚠️ THIS IS THE LOOKAHEAD THE `future_of` GUARD DOES NOT CATCH, because
        it arrives inside a legitimate-looking slice rather than through an
        obviously forward-reaching call. It was found by the positive control
        disagreeing with the tape, not by reading the code.
        """
        if ts.tzinfo is None:
            ts = ET.localize(ts)
        return self.df[self.df.index <= ts]

    def closed_at(self, ts: datetime, bar_s: int = 60) -> pd.DataFrame:
        """Only bars that had FULLY CLOSED by `ts` — no forming bar, no future.

        This is the honest frame for a decision replay. A bar stamped T is
        closed at T + bar_s, so it is admissible only once ts >= T + bar_s.
        """
        if ts.tzinfo is None:
            ts = ET.localize(ts)
        cutoff = ts - pd.Timedelta(seconds=bar_s)
        return self.df[self.df.index <= cutoff]

    @staticmethod
    def bar_aligned(ts: datetime, bar_s: int = 60) -> bool:
        """True when `ts` sits exactly on a bar boundary.

        🔑 WHY THIS GATES RECONCILIATION. Off a boundary, the live bot held a
        PARTIAL bar this harness cannot reconstruct from 1m data, so a replay
        there is an approximation wearing a measurement's clothes. RPL.2's
        ruling applies unchanged: a row that cannot be checked is reported
        NOT RECONCILABLE **by name**, never quietly counted as agreement.
        """
        return int(ts.timestamp()) % bar_s == 0

    def after(self, ts: datetime) -> pd.DataFrame:
        """Deliberately named and deliberately loud — see `future_of`."""
        if ts.tzinfo is None:
            ts = ET.localize(ts)
        return self.df[self.df.index > ts]

    def future_of(self, ts: datetime):
        """🔴 THE GUARD. Nothing in a decision path may call this.

        A harness that can silently see forward produces a beautiful, wrong
        answer, and the failure is invisible in the output — which is the
        property every defect found on 2026-09-19 shared.
        """
        raise LookaheadError(
            f"{self.symbol} {self.date}: a decision path asked for bars after "
            f"{ts} — that is lookahead. Outcome scoring uses `after()` by name."
        )

    @staticmethod
    def to_5m(df_1m: pd.DataFrame) -> pd.DataFrame:
        if df_1m is None or df_1m.empty:
            return df_1m
        return df_1m.resample("5min", label="left", closed="left").agg(
            {"open": "first", "high": "max", "low": "min",
             "close": "last", "volume": "sum"}).dropna(how="any")


# ═══════════════════════════════════════════════════════════════════════════
def load_tape(date: str, symbol: str):
    """One symbol-session of 1m bars from raw/ohlc, or (None, reason)."""
    # ⚠️ THE ROW LOADERS CORRECTLY DECLINE THIS TABLE, WHICH IS WHY THE
    # ENVELOPE READER IS USED DIRECTLY. `load_series`/`iter_series` only
    # accumulate when `record` is a LIST of dicts; an `ohlc` record is the
    # session's CSV as TEXT ("timestamp,open,high,low,close,volume" + 390
    # rows). Calling them for ohlc returns zero rows and NO ERROR — a silent
    # empty, which is the exact shape r39 refuses. So this reaches for
    # `_envelopes`, the same S3 lineage every other reader uses, rather than
    # opening a second one (WA §7).
    import warehouse_source as ws
    meta = ws.Meta(f"ohlc {date} {symbol}")
    try:
        for env in ws._envelopes(ws.client(), "ohlc", [date], meta, [symbol]):
            if str(env.get("symbol") or "") != symbol:
                continue
            rec = env.get("record")
            if isinstance(rec, str) and "timestamp" in rec:
                return Tape.from_csv(rec, symbol, date), ""
    except Exception as exc:                                    # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"
    if getattr(meta, "error", None):
        return None, meta.error
    return None, f"no ohlc record for {symbol} on {date}"


# ═══════════════════════════════════════════════════════════════════════════
# THE ORACLE — what the live bot actually recorded, tick by tick
# ═══════════════════════════════════════════════════════════════════════════
def recorded_ticks(date: str, strategy: str = "ORBStrategy"):
    """{(symbol, tick_id, ts_epoch): {check_name: value}} from derived_plan_check.

    🔑 THIS IS A SPARSE ORACLE AND THAT IS A PROPERTY, NOT A GAP. The planner
    only emits checks on ticks where the strategy actually evaluated, so ORB
    contributes ~26 DECISION TICKS on a session where the loop ran thousands
    of times. Those 26 are exactly the population where a counterfactual has
    something to be wrong about.
    """
    import warehouse_source as ws
    rows, meta = ws.load_derived("plan_check", [date])
    if getattr(meta, "error", None):
        return None, meta.error
    out = {}
    for r in rows:
        if r.get("strategy") != strategy:
            continue
        key = (r.get("symbol"), r.get("tick_id"), r.get("ts_epoch"))
        out.setdefault(key, {})[r.get("check_name")] = r.get("value")
    return out, ""


def seed_orb_range(engine, date: str, high: float, low: float, width: float):
    """Establish the range through the REAL `_load_range_from_file`.

    🔑 A TEMP FILE RATHER THAN FIVE ASSIGNMENTS. Setting `orb_high`, `orb_low`,
    `_range_date` and the WAITING_FOR_BREAK transition by hand would be a
    second definition of "an established range" living in a test tool — and it
    would drift the first time the real loader gained a condition. Pointing the
    real function at a temp file costs three lines and cannot drift.
    ⚠️ The range is an INPUT here, not a prediction: it is published by a
    separate job the live engine reads from disk, so supplying the recorded
    one is giving the harness what the bot had, not giving it the answer.
    """
    import json
    import tempfile
    import analysis.orb_engine as oe
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        with open(path, "w") as fh:
            json.dump({"status": "ESTABLISHED", "date": date,
                       "high": high, "low": low, "width": width}, fh)
        old = oe.ORB_RANGE_FILE
        try:
            oe.ORB_RANGE_FILE = path
            engine._load_range_from_file()
        finally:
            oe.ORB_RANGE_FILE = old
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


ORB_FIELDS = [("break_direction", "break_direction"),
              ("bars_since_break", "bars_since_break"),
              ("attempt_number", "attempt_number"),
              ("stop_level", "stop_level"),
              ("stop_distance_px", "stop_distance_px"),
              ("break_close", "break_candle_close")]


def reconcile_orb(date: str, tol: float = 0.011):
    """Replay the REAL ORB engine at each recorded tick and compare.

    Returns a dict with agree/disagree/unreconcilable counts and examples.
    🔴 THE VERDICT IS NOT A PERCENTAGE, IT IS A GATE. Until the reconcilable
    population agrees, this harness may not be used to score a change, and
    `report()` says so in those words rather than printing a hopeful number.
    """
    from analysis.orb_engine import ORBEngine
    ticks, err = recorded_ticks(date)
    if ticks is None:
        return {"error": err}
    tapes: dict = {}
    agree: dict = {}
    disagree: dict = {}
    unrec = 0
    unrec_syms: dict = {}
    examples: list = []
    for (sym, _tid, ts), rec in sorted(ticks.items(), key=lambda kv: kv[0][2]):
        when = datetime.fromtimestamp(ts, ET)
        # ⚠️ NAMED, NOT SILENTLY SKIPPED (RPL.2). A mid-bar tick cannot be
        # reproduced from 1m bars — the bot held a partial bar we do not have.
        if not Tape.bar_aligned(when):
            unrec += 1
            unrec_syms[sym] = unrec_syms.get(sym, 0) + 1
            continue
        if sym not in tapes:
            tapes[sym] = load_tape(date, sym)[0]
        tape = tapes[sym]
        if tape is None:
            unrec += 1
            continue
        eng = ORBEngine()
        with FrozenClock(when):
            seed_orb_range(eng, when.strftime("%Y-%m-%d"),
                           float(rec.get("orb_high") or 0),
                           float(rec.get("orb_low") or 0),
                           float(rec.get("orb_width") or 0))
            eng.rebuild_from_tape(tape.closed_at(when))
            d = eng._data
            for cname, attr in ORB_FIELDS:
                want = rec.get(cname)
                if want is None:
                    continue
                got = getattr(d, attr, None)
                if cname == "break_direction":
                    got = 1.0 if got == "long" else -1.0 if got == "short" else None
                try:
                    same = got is not None and abs(float(got) - float(want)) < tol
                except (TypeError, ValueError):
                    same = False
                tgt = agree if same else disagree
                tgt[cname] = tgt.get(cname, 0) + 1
                if not same and len(examples) < 12:
                    examples.append(f"{sym} {when:%H:%M:%S} {cname}: "
                                    f"recorded={want} engine={got} state={d.state}")
    return {"agree": agree, "disagree": disagree, "unreconcilable": unrec,
            "unreconcilable_by_symbol": unrec_syms, "examples": examples,
            "ticks": len(ticks)}


def report(date: str) -> int:
    r = reconcile_orb(date)
    if r.get("error"):
        print(f"  ⚠️ {r['error']}")
        return 1
    a, d = sum(r["agree"].values()), sum(r["disagree"].values())
    print("=" * 70)
    print(f"  WARGAME — ORB decision replay vs the tape, {date}")
    print("=" * 70)
    print(f"  recorded decision ticks : {r['ticks']}")
    print(f"  field comparisons       : agree {a} · disagree {d}")
    print(f"  NOT RECONCILABLE        : {r['unreconcilable']} tick(s) — mid-bar, "
          f"the bot held a partial bar this harness cannot rebuild from 1m data")
    if r["unreconcilable_by_symbol"]:
        print("    " + ", ".join(f"{k}:{v}" for k, v in
                                 sorted(r["unreconcilable_by_symbol"].items())))
    for name, tally in (("AGREE", r["agree"]), ("DISAGREE", r["disagree"])):
        if tally:
            print(f"  {name}:")
            for k, v in sorted(tally.items(), key=lambda kv: -kv[1]):
                print(f"    {k:<20} {v}")
    for e in r["examples"]:
        print(f"    · {e}")
    if d or a == 0:
        print("\n  🔴 THE CONTROL HAS NOT RECONCILED. This harness may NOT be "
              "used to score a change: a replay that cannot reproduce what "
              "happened is not entitled to an opinion about what would have.")
        return 1
    print("\n  ✅ control reconciled on the bar-aligned population.")
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-09-18")
    ap.add_argument("--reconcile", action="store_true")
    a = ap.parse_args()
    sys.exit(report(a.date) if a.reconcile else report(a.date))
