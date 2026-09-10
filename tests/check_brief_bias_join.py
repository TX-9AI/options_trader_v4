#!/usr/bin/env python3
"""
tests/check_brief_bias_join.py  v1.3
v1.3  2026-09-10  r338 - J11 and J12 for table F. J11 plants five weak LONG
      calls against two strong SHORT ones: a vote count returns LONG and a
      conviction-weighted sum returns SHORT, which is the whole difference
      between the two designs. J12 pins that the floor drops sub-floor calls
      entirely rather than shrinking them, and that SPX and QQQ can never be
      members of the composite that predicts SPX.
v1.2  2026-09-10  r336 - J9 and J10 for table D. J9 plants conviction on a
      0..8 scale and asserts the quartiles still SPREAD: hardcoded 0..1 cut
      points would put every call in one bucket and print a flat correlation
      that is an artefact of the scale, not of the data. J10 pins that a NULL
      conviction is excluded and counted rather than bucketed as zero.
v1.1  2026-09-10  r335 - J7 and J8 for `--rows`. J7 asserts table C's net
      RECONCILES with the bucket totals, because both views come off one join
      and a divergence between them would mean the grain was recomputed rather
      than re-rendered. J8 pins MIXED for a symbol-day traded both ways.
v1.0  2026-09-10  r333 / BRF.1 — the land gate for the brief-bias study.

Drives `main()` end to end against a fixture brief DB, a fixture tape and a
fixture trade set, so the whole render path is exercised rather than the
arithmetic alone.

  J0  the lookback: the window's FIRST session is measurable, not dropped
  J1  edge is ALWAYS hit% minus that direction's base rate, on every row —
      the invariant the whole study rests on. (The zero-edge case, an
      always-LONG call on an up-only tape, is pinned in the selftest.)
  J2  a blended hit rate is NEVER printed
  J3  AGREE / DISAGREE are assigned by price_bias, so a PUT CREDIT spread
      counts as AGREE with a BULLISH brief
  J4  a symbol-day with no prior-session close is EXCLUDED, not a miss
  J5  the severed count is surfaced when trades come from behind a marker
  J11 the SPX composite is conviction-WEIGHTED, not a vote count: two strong
      calls outrank five weak ones
  J12 the floor-gated composite drops sub-floor calls entirely, and SPX/QQQ
      are never members of their own predictor
  J9  conviction buckets are QUARTILES OF THE DATA, so an unexpected scale
      cannot collapse every call into one bucket
  J10 a NULL conviction is excluded and counted, never bucketed as zero
  J7  --rows prints one line per symbol-day, and its net RECONCILES with
      the bucket totals (same join, two views — they cannot disagree)
  J8  a symbol-day traded both ways reads MIXED, never one direction
  J6  it REFUSES if load_trades_versioned is absent — no quiet fallback to
      the post-epoch window
"""
import io
import os
import sqlite3
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
FAILS = []


def check(name, ok, detail=""):
    print("  {:<4} {}  {}".format(name, "PASS" if ok else "FAIL", detail))
    if not ok:
        FAILS.append(name)


def _brief_db(path):
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE composites (id INTEGER PRIMARY KEY, "
                "report_date TEXT, ticker TEXT, score REAL, direction TEXT, "
                "conviction REAL)")
    rows = [("2026-09-02", "N", 0.8, "BULLISH", 0.9),
            ("2026-09-03", "N", 0.8, "BULLISH", 0.9),
            ("2026-09-02", "M", 0.8, "BULLISH", 0.9),   # no prior close -> excl
            ("2026-09-03", "Q", 0.7, "BEARISH", 0.6)]
    con.executemany("INSERT INTO composites (report_date,ticker,score,"
                    "direction,conviction) VALUES (?,?,?,?,?)", rows)
    con.commit()
    con.close()


def main():
    tmp = tempfile.mkdtemp()
    db = os.path.join(tmp, "screener.db")
    _brief_db(db)
    os.environ["SCREENER_DB"] = db

    import warehouse_source as ws
    try:
        import brief_bias_join as bj
    except Exception as exc:                                    # noqa: BLE001
        print("  FAIL  brief_bias_join did not import: {}".format(exc))
        return 1

    # ── fixture tape: N rises both days, Q falls. M has one session only.
    def _envs(_s3, datatype, dates, meta, symbols=None):
        tape = {("2026-09-01", "N"): 10.0, ("2026-09-02", "N"): 11.0,
                ("2026-09-03", "N"): 12.0,
                ("2026-09-02", "Q"): 50.0, ("2026-09-03", "Q"): 49.0,
                ("2026-09-02", "M"): 5.0}
        for (d, s), c in tape.items():
            if d in dates:
                yield {"symbol": s, "dt": d,
                       "record": "ts,close\n1,{}\n".format(c)}

    class _Meta:
        listed = read = bad = severed = 0

        def banner(self):
            return "SOURCE: fixture, 3 behind a delete marker"

    # ── fixture trades: a PUT CREDIT spread on N (bullish) = AGREE.
    def _trades(dates, s3=None):
        m = _Meta()
        m.severed = 3
        return [
            {"status": "closed", "pnl_usd": 100.0, "_dt": "2026-09-02",
             "symbol": "N", "option_side": "put", "is_short_position": 1},
            {"status": "closed", "pnl_usd": -40.0, "_dt": "2026-09-02",
             "symbol": "N", "option_side": "call", "is_short_position": 1},
        ], m

    ws._envelopes = _envs
    ws.client = lambda: None
    ws.Meta = lambda *_a, **_k: _Meta()
    ws.load_trades_versioned = _trades
    ws._et_today = lambda: "2026-09-03"

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = bj.main(["--from", "2026-09-01", "--to", "2026-09-03"])
    out = buf.getvalue()

    long_line = [l for l in out.splitlines() if l.strip().startswith("LONG")]
    check("J0", bool(long_line) and long_line[0].split()[1] == "2",
          "LONG n={} (both sessions measurable)".format(
              long_line[0].split()[1] if long_line else "-"))
    def _pc(x):
        return float(x.rstrip("%").lstrip("+"))
    bad = []
    for ln in out.splitlines():
        f = ln.split()
        if f[:1] and f[0] in ("LONG", "SHORT") and len(f) >= 5 and "%" in f[2]:
            hit, base_, edge = _pc(f[2]), _pc(f[3]), _pc(f[4])
            if abs((hit - base_) - edge) > 0.15:
                bad.append((f[0], hit, base_, edge))
    check("J1", not bad and bool(long_line),
          "edge = hit - base on every row" if not bad else "mismatch: {}".format(bad))
    check("J2", "blended" in out.lower() and "not printed" in out.lower(),
          "blended-rate warning present")
    b_rows = {l.split()[0]: l for l in out.splitlines()
              if l.strip().startswith(("AGREE", "DISAGREE"))}
    check("J3", "AGREE" in b_rows and "DISAGREE" in b_rows
          and "100" in b_rows["AGREE"] and "-40" in b_rows["DISAGREE"],
          "AGREE={} DISAGREE={}".format(
              b_rows.get("AGREE", "-").split()[1:4],
              b_rows.get("DISAGREE", "-").split()[1:4]))
    check("J4", "EXCLUDED" in out and "1 composite(s)" in out,
          "excluded line present")
    check("J5", "behind a delete marker" in out, "severed surfaced")

    buf2 = io.StringIO()
    with redirect_stdout(buf2):
        bj.main(["--from", "2026-09-01", "--to", "2026-09-03", "--rows"])
    out2 = buf2.getvalue()
    crows = [l for l in out2.splitlines()
             if l.strip().startswith(("2026-09-02", "2026-09-03"))]
    net_c = sum(float(l.split()[-1].replace(",", "")) for l in crows)
    net_b = 100.0 - 40.0
    check("J7", len(crows) == 1 and abs(net_c - net_b) < 1e-6,
          "{} row(s), table C net {} vs bucket net {}".format(
              len(crows), net_c, net_b))
    check("J8", any(" MIXED " in l for l in crows),
          crows[0].strip() if crows else "no rows")

    # J9/J10 — conviction on a 0..8 scale must still spread across quartiles,
    # and a None must not become a zero.
    comps = {("2026-09-0%d" % d, "N"): ("SHORT", 1.0, v)
             for d, v in zip(range(1, 9), [0.4, 1.9, 3.1, 4.4, 5.2, 6.6, 7.1, 8.0])}
    comps[("2026-09-09", "N")] = ("SHORT", 1.0, None)
    cl = {("2026-09-0%d" % d, "N"): 100.0 - d for d in range(0, 10)}
    pv = bj.prior_sessions(cl)
    cv, cbase, cuts, nulls = bj.by_conviction(comps, cl, pv)
    qs = sorted({q for (_c, q) in cv})
    check("J9", len(cuts) == 3 and len(qs) >= 3,
          "cuts={} quartiles used={}".format(
              [round(c, 2) for c in cuts], qs))
    check("J10", nulls == 1 and all(
        b["n"] for b in cv.values()),
        "null conviction(s) excluded={}".format(nulls))

    # J11 — five weak LONGs vs two strong SHORTs on one day. A vote count says
    # LONG; a conviction-weighted sum says SHORT.
    day = "2026-09-02"
    weak = {(day, t): ("LONG", 1.0, 0.20) for t in
            ("NVDA", "AMZN", "GOOGL", "META", "AVGO")}
    strong = {(day, t): ("SHORT", 1.0, 0.95) for t in ("TSLA", "UNH")}
    cmix = dict(weak); cmix.update(strong)
    clx = {("2026-09-01", "SPX"): 100.0, (day, "SPX"): 99.0}
    pvx = bj.prior_sessions(clx)
    rws, _b = bj.spx_composite(cmix, clx, pvx, floor=None)
    check("J11", len(rws) == 1 and rws[0][1] == "SHORT",
          "5x0.20 LONG vs 2x0.95 SHORT -> {}".format(
              rws[0][1] if rws else "no row"))

    # J12 — with the floor, the five weak calls vanish and SPX itself is
    # never a member of the composite that predicts it.
    rwf, _b2 = bj.spx_composite(cmix, clx, pvx, floor=0.640)
    poisoned = dict(cmix); poisoned[(day, "SPX")] = ("LONG", 1.0, 0.99)
    rwp, _b3 = bj.spx_composite(poisoned, clx, pvx, floor=0.640)
    check("J12", rwf and rwf[0][3] == 2 and "SPX" not in bj.SPX_PROXY
          and "QQQ" not in bj.SPX_PROXY and rwp[0][3] == 2,
          "gated members={} spx_self_excluded={}".format(
              rwf[0][3] if rwf else "-", rwp[0][3] if rwp else "-"))

    del ws.load_trades_versioned
    try:
        with redirect_stdout(io.StringIO()):
            bj.main(["--from", "2026-09-01", "--to", "2026-09-03"])
        refused = False
    except SystemExit:
        refused = True
    check("J6", refused, "refuses without the versioned reader"
          if refused else "ran anyway — silent fallback")

    print("")
    if FAILS:
        print("FAILED: {}".format(", ".join(FAILS)))
        return 1
    print("ALL PASS (13)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
