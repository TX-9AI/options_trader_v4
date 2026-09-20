#!/usr/bin/env python3
"""
tests/check_discriminator_inputs.py  v1.0
v1.0  2026-09-20  r395 / DISC.2 — A COLUMN THAT WAS NEVER MEASURED MUST NOT
      READ AS "TESTED AND REJECTED".

🔴 THE DEFECT THIS EXISTS FOR, MEASURED ON 187 CLOSED ORB TRADES:
      spread_width    187 rows, 1 distinct value  — ALL ZERO
      level_strength  141 rows, 1 distinct value  — ALL ZERO
      chain_iv_rank    45 rows, 1 distinct value  — ALL ZERO
      flat_angle_deg  187 rows, 1 distinct value  — ALL -1  (NOT COMPUTED)
      setup_score       0 rows                    — never written
In a discrimination scan every one of these returns a separation of 0.000 and
reads as **tested and rejected** when it was never measured at all. That is
r39's class — an absence wearing the costume of a null — and `flat_angle_deg`
is the sharpest case, because `main.py` documents -1 as NOT COMPUTED while the
column's type says it is a number.

🔑 WHY THE GATE AND NOT JUST FIVE FIXES. Repairing five encodings repairs five
columns. This refuses the SIXTH, which nobody has written yet. The encodings
are still worth fixing — a `getattr(signal, "level_strength", 0.0)` that turns
absence into zero is a real defect — but the gate is the part that generalises
and it lands first.

🔑 AND THE CLASSIFICATION IS KEYED ON *STRUCTURE*, NOT ON STRATEGY NAME.
`spread_width` is inapplicable to any SINGLE-LEG LONG DEBIT — ORB, Runaway,
and every single-leg strategy nobody has written yet. Keyed by structure a new
strategy INHERITS the classification; keyed by name it fails until a human
hand-classifies it, which sounds like fail-closed and is in practice friction
that gets waved through at 23:00. OTV4TEST's precedent is exact: their
`RiskManager.size_for` docstring says geometry is chosen by the caller
SUPPLYING the parameters "rather than by naming ORB ... it does not get added
to a list somewhere that later rots" — and a name list was kept anyway, and a
strategy silently fell through it for a whole revision.

⚠️ AN UNKNOWN (structure, column) STILL FAILS. Fail-closed survives the change
of key; what changes is that the answer generalises instead of accumulating.
"""
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

FAILS, RAN = [], []


def ck(n, ok, msg):
    RAN.append(n)
    print(f"  {n:<4} {'PASS' if ok else 'FAIL'}  {msg}")
    if not ok:
        FAILS.append(n)


# ── STRUCTURE, not strategy name ───────────────────────────────────────────
SINGLE_LEG_DEBIT = "single_leg_debit"
VERTICAL = "vertical"
BUTTERFLY = "butterfly"

STRUCTURE = {
    "ORBStrategy":          SINGLE_LEG_DEBIT,
    "RunawayContinuation":  SINGLE_LEG_DEBIT,
    "SweepCreditSpread":    VERTICAL,
    "TrendCreditSpread":    VERTICAL,
    "GEXPinButterfly":      BUTTERFLY,
}

# A column may be dead ONLY if its structure makes it meaningless, and the
# reason is written down. Anything else dead is a defect.
INAPPLICABLE = {
    (SINGLE_LEG_DEBIT, "spread_width"):
        "one leg, so there are no two strikes to subtract",
    (SINGLE_LEG_DEBIT, "short_strike"):
        "one leg, and it is long",
    (SINGLE_LEG_DEBIT, "setup_score"):
        "no grading model runs on this structure; entry_engine writes None",
    (BUTTERFLY, "spread_width"):
        "width is lower/upper, not a two-leg vertical spread",
}

# ── KNOWN DEBT, 2026-09-20 ────────────────────────────────────────────────
# 🔴 THIS IS A DEBT REGISTER, NOT AN EXCUSE LIST, AND THE DIFFERENCE IS THE
# WHOLE DESIGN. These 36 pairs are DEFECTS measured on 554 closed trades:
# four of the five strategies write 0.0 where ORB writes a measurement.
#     vix_at_entry   ORB varies (35 distinct) · the other four: 0.000, n=1
#     adx_at_entry   ORB varies (185)         · the other four: 0.000, n=1
# VIX CANNOT BE CONSTANT ACROSS 18 TRADING SESSIONS. 293 Runaway trades over
# three weeks all recording 0.000 is a default, not a market that did not move.
# ⚠️ 0.0 IS THE WORST ENCODING AVAILABLE HERE — a legal ADX and a legal-looking
# VIX — so a scan reads it as "measured, and it was zero".
# 🔑 THE GATE IS GREEN ON THESE AND RED ON A 37th. Landing it red would refuse
# every future delivery until 36 write-sites across four entry paths were
# repaired, which is how a gate gets deleted. Pinning the COUNT would rot the
# moment one is fixed — CHK.6 exactly, where EXPECT_N against a growing corpus
# went red the next day. So the register is explicit, it is PRINTED EVERY RUN
# so it cannot go quiet, and the assertion is the RELATIONSHIP: nothing dead
# that is not either structurally excused or on this list.
# ⚠️ AND IT MUST SHRINK. A pair leaving this list is the fix working; a pair
# arriving is a regression and D2 catches it.
KNOWN_DEAD_NOTE = ("four of five strategies write 0.0 for the shared "
                   "at-entry context columns; ORB alone populates them")
KNOWN_DEAD = {
    ("GEXPinButterfly", c) for c in
    ("adx_at_entry", "chain_iv_rank", "flat_angle_deg", "level_strength",
     "planned_r", "setup_score", "stop_width_pct", "tape_prints_at_level",
     "tape_vol_at_level", "vix_at_entry")
} | {
    ("ORBStrategy", c) for c in
    ("chain_iv_rank", "flat_angle_deg", "level_strength")
} | {
    ("RunawayContinuation", c) for c in
    ("adx_at_entry", "chain_iv_rank", "flat_angle_deg", "level_strength",
     "vix_at_entry")
} | {
    ("SweepCreditSpread", c) for c in
    ("adx_at_entry", "chain_iv_rank", "flat_angle_deg", "level_strength",
     "planned_r", "stop_width_pct", "tape_prints_at_level",
     "tape_vol_at_level", "vix_at_entry")
} | {
    ("TrendCreditSpread", c) for c in
    ("adx_at_entry", "chain_iv_rank", "flat_angle_deg", "level_strength",
     "planned_r", "stop_width_pct", "tape_prints_at_level",
     "tape_vol_at_level", "vix_at_entry")
}

SENTINELS = {-1.0, -1}

CANDIDATES = ["entry_gamma", "entry_delta", "entry_iv", "entry_theta",
              "adx_at_entry", "vix_at_entry", "chain_iv_rank", "flat_angle_deg",
              "gap_pct", "level_strength", "setup_score", "spread_width",
              "stop_width_pct", "planned_r", "tape_prints_at_level",
              "tape_vol_at_level", "entry_premium", "underlying_entry"]


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def classify(values):
    """('ok'|'unpopulated'|'constant'|'sentinel', n_distinct, n_present)."""
    present = [v for v in values if v is not None]
    if not present:
        return "unpopulated", 0, 0
    distinct = len(set(present))
    if distinct <= 1:
        only = present[0]
        if only in SENTINELS:
            return "sentinel", distinct, len(present)
        return "constant", distinct, len(present)
    return "ok", distinct, len(present)


def audit(rows):
    """{(strategy, column): (verdict, distinct, present)} over closed trades."""
    by = defaultdict(list)
    for r in rows:
        s = str(r.get("strategy") or "?")
        for c in CANDIDATES:
            by[(s, c)].append(_f(r.get(c)))
    out = {}
    for (s, c), vals in by.items():
        if len(vals) < 20:                 # too few trades to judge the column
            continue
        out[(s, c)] = classify(vals)
    return out


def excused(strategy, column):
    st = STRUCTURE.get(strategy)
    return (st, column) in INAPPLICABLE if st else False


def load_closed(d0="2026-09-01", d1="2026-09-18"):
    import warehouse_source as ws
    rows = []
    for d in ws._span(d0, d1):
        try:
            t, m = ws.load_trades([d])
        except Exception:                                      # noqa: BLE001
            continue
        if not getattr(m, "error", None):
            rows += [r for r in t if (r.get("status") or "").lower() == "closed"]
    return rows


# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    rows = load_closed()
    # ⚠️ GREEN VACUOUS IS NOT GREEN. An empty corpus must say nothing was
    # checked, so "nothing to check" can never read as "everything passed" —
    # CV.1's shape, and the reason check_floor_overshoot was rewritten.
    if not rows:
        print("  ⚠️ NO CLOSED TRADES IN THE WINDOW — nothing was audited.")
        print("  GREEN VACUOUS. This is not a pass.")
        sys.exit(0)

    res = audit(rows)
    dead = {k: v for k, v in res.items() if v[0] != "ok"}
    unexcused = {k: v for k, v in dead.items()
                 if not excused(*k) and k not in KNOWN_DEAD}
    ok_excused = {k: v for k, v in dead.items() if excused(*k)}
    debt = {k: v for k, v in dead.items()
            if k in KNOWN_DEAD and not excused(*k)}

    print(f"  corpus: {len(rows)} closed trades · "
          f"{len({r.get('strategy') for r in rows})} strategies · "
          f"{len(res)} (strategy, column) pairs audited\n")

    if ok_excused:
        print("  EXCUSED — structurally inapplicable, reason on record:")
        for (s, c), (v, d, n) in sorted(ok_excused.items()):
            print(f"    {s:22s} {c:22s} {v:12s} — "
                  f"{INAPPLICABLE[(STRUCTURE[s], c)]}")
        print()

    ck("D1", True, f"{len(res)} pairs audited over {len(rows)} trades")

    # 🔑 PRINTED EVERY RUN SO THE DEBT CANNOT GO QUIET. A register nobody sees
    # is an excuse list.
    print(f"  📌 KNOWN DEBT: {len(debt)} dead pair(s) on the register — "
          f"{KNOWN_DEAD_NOTE}")
    for (s_, c), (v, d, n) in sorted(debt.items())[:6]:
        print(f"       {s_:22s} {c:22s} {v:12s} present={n}")
    if len(debt) > 6:
        print(f"       ... and {len(debt)-6} more")
    ck("D4", len(debt) <= len(KNOWN_DEAD),
       f"the debt register has not GROWN: {len(debt)} dead of "
       f"{len(KNOWN_DEAD)} registered")
    _fixed = len(KNOWN_DEAD) - len(debt)
    if _fixed > 0:
        print(f"  ✅ {_fixed} registered pair(s) are NO LONGER DEAD — remove "
              f"them from KNOWN_DEAD so the register keeps shrinking.")

    # 🔴 THE GATE. A dead column that nobody has classified is a defect, and it
    # must be loud NOW rather than returning 0.000 in a scan six weeks from now
    # and reading as a rejected hypothesis.
    if unexcused:
        print("  🔴 DEAD AND UNCLASSIFIED — these would score 0.000 in a scan\n"
              "     and read as TESTED AND REJECTED when never measured:")
        for (s, c), (v, d, n) in sorted(unexcused.items()):
            print(f"    {s:22s} {c:22s} {v:12s} distinct={d} present={n}")
    ck("D2", not unexcused,
       f"every dead column is excused by structure or on the debt register: "
       f"{len(unexcused)} unaccounted")

    ck("D3", all(excused(*k) for k in ok_excused),
       "excused columns are excused BY STRUCTURE, not by strategy name")

    # 🔴 D5 EXISTS BECAUSE A MUTATION SURVIVED. Emptying SENTINELS left every
    # check green: `flat_angle_deg` merely reclassified from "sentinel" to
    # "constant", stayed dead, stayed on the register, and D2 passed. So the
    # sentinel rule was DECORATIVE — it changed a label nobody asserted on.
    # ⚠️ THE DISTINCTION IS THE WHOLE POINT OF THE ROW. `main.py` documents -1
    # as NOT COMPUTED while the column's type says it is a number, so a reader
    # who sees "constant" believes the angle was measured and never moved;
    # "sentinel" says it was never computed. Different facts about the tape,
    # and a gate that cannot tell them apart is not reading the thing the
    # defect is made of.
    _fa = res.get(("ORBStrategy", "flat_angle_deg"))
    ck("D5", _fa is not None and _fa[0] == "sentinel",
       f"a NOT-COMPUTED sentinel is classified 'sentinel', never merely "
       f"'constant': flat_angle_deg -> {_fa[0] if _fa else 'absent'}")

    # ⚠️ AND THE CLASSIFIER MUST NOT CALL EVERYTHING A SENTINEL EITHER — the
    # cheap way to pass D5 is to widen SENTINELS until it swallows real zeros.
    _lv = res.get(("ORBStrategy", "level_strength"))
    ck("D5b", _lv is not None and _lv[0] == "constant",
       f"an all-ZERO column stays 'constant' and is NOT absorbed into the "
       f"sentinel set: level_strength -> {_lv[0] if _lv else 'absent'}")

    print()
    if FAILS:
        print(f"FAILED: {', '.join(FAILS)}")
        sys.exit(1)
    print(f"ALL PASS ({len(RAN)})")
