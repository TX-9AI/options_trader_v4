#!/usr/bin/env python3
"""
tests/exit_replay.py  v1.7
v1.7  2026-09-20  r397 / D1 - `stop_of_reason` TRUNCATED A REAL RULE AND
CARRIED A SECOND PARSER. Its token line did `.split(":")[0]`, which cuts
`hard_close_15:45_ET` - a stable token with NO per-trade part - down to
`hard_close_15`, rendering it as though it carried a percentage. That
truncation reached the 2026-09-20 Saturday brief, whose exit table carries a
`hard_close_15` row for it. It now calls `r_ledger.exit_reason_family`, the one
definition, which anchors on `": "` rather than a bare colon.
  ⚠️ THE FOLD IS FOR THE REPORT AND NEVER FOR THE REPLAY. `_STOP_RE` still
matches FIRST, so every recorded hard-stop percentage is replayed under its own
stop. `check_exit_replay_control` C4d is the control that pins it.
v1.6  2026-09-19  🔴 IT REPLAYED NOTHING, AND HAD NEVER REPLAYED ANYTHING FROM
S3. Measured 2026-09-19 over 2026-09-14..09-18: every symbol-day reported
"N object(s), 0 quote(s) kept" -- 14 of 14 -- and a bounded single-date run
refused 42 of 42 closed trades. TWO INDEPENDENT CAUSES, both silent:
  (a) `legs_of` read short_/long_/lower_/upper_/center_symbol and NOT
      `option_symbol`. ORB and RunawayContinuation record ONLY option_symbol
      (measured 09-15: 75 + 115 rows of 317), so every single-leg debit was
      refused "no leg symbols on row". r340 populated that field for exactly
      this tool and nothing taught this function to read it.
  (b) THE TWO SYMBOL FORMATS NEVER MET. Trade columns hold OCC
      ('QQQ   260915C00705000'); `quote_series` is keyed on DXFeed streamer
      ('.QQQ260915C705'). `path_for` looked up the OCC string against a
      streamer-keyed index, so every credit spread matched nothing. A grep of
      both repos found NO OCC->streamer transform anywhere.
PROVEN RATHER THAN ARGUED: transforming a real TrendCreditSpread's own legs and
looking for the result in that day's quote_series returned
['.QQQ260915C705', '.QQQ260915C706'] -- WANTED and FOUND identical. The quotes
were in the bucket the whole time; the entire gap was a format mapping.
🔴 AND THE VERDICT CONTRADICTED ITSELF IN FOUR LINES. `if refused:` prints
"these are the tool's gaps, not the tape's" (r39) and `if not counts:` then
printed "quote_series needs its first live sessions". `not counts` is true
EXACTLY when nothing replayed, which is exactly when `refused` is populated --
so both fired every time and THE TAPE-BLAMING ONE WAS LAST. It also named "the
series push, s3_push v4.2" as the remedy, sending the reader to audit a push
that is working. Now gated on `not counts and not refused`, and that clause is
gone. Independently reproduced on OTV4TEST (0 of 44 trades, same two causes,
identical inherited verdict line).
⚠️ AND `--selftest` COULD NOT HAVE CAUGHT ANY OF IT (WA 0.4): its fixture used
"X 260823C100" -- neither real format -- fed to BOTH sides, so it matched
itself and passed on a tool that replayed nothing. It now carries a REAL OCC
trade column and a REAL streamer quote key, which is the only shape that can
fail.
🔴 AND THE SAME REVISION CARRIES RPL.2 AND RPL.3, FOUND BECAUSE THE CONTROL
WAS TIGHTENED BEFORE ANYTHING WAS BUILT ON TOP OF IT.
RPL.2 - the positive control replayed EVERY row under a HARDCODED 25% premium
stop. Measured over 554 closed trades 2026-09-01..09-18: only 220 (40%) exited
on a premium stop at all and only 49 of those on a 25% one, so 505 of 554 -
91% - were reconciled against a rule they never ran under. It printed a clean
zero throughout because its band worked out to a flat 35% OF ENTRY COST. A
LOOSE TOLERANCE AND A CORRECT CONTROL BOTH PRINT 0. The stop is now DERIVED
from each row's own exit reason, NOT APPLICABLE is NAMED and tallied as
neither a pass nor a failure, and a control that applied to ZERO rows shouts
UNVERIFIED. The band keys on ENTRY COST ALONE: deriving the stop while leaving
the tolerance multiplied BY it makes a 20% stop tighten and a 40% stop WIDEN
to 56% of cost, so a wider stop would buy a looser check (measured on the
OTV4TEST fork, which shipped the derivation first and hit exactly that).
⚠️ RECONCILE_TOL = 0.10 WAS MEASURED, NOT CHOSEN - n=38, p90 0.059, then a gap
to 0.158 and 0.170 - and it deliberately FLAGS those two rather than absorbing
them, because a band of 0.20 would report the comfortable meaningless zero
this whole change exists to remove.
RPL.3 - tightening it immediately caught THIS REVISION'S OWN ORIENTATION
REWIRE INVERTING EVERY CREDIT SPREAD. `is_credit_position` is correct and was
correctly returning True; the FLIP was the defect. The spread columns are
ALREADY oriented by structure - short_symbol -1, long_symbol +1 - so a credit
vertical's combo is `long - short`, MINUS the spread's value, which already
rises as the seller wins. flip=-1 on top inverted it. MEASURED with one
variable and every other row byte-identical: NVDA SweepCreditSpread 09-17
replayed +55 against a recorded -55; after scoping the flip to the single-leg
fallback, -55 against -55. ⚠️ THEY WERE ACCIDENTALLY CORRECT BEFORE THE
REWIRE, because the flag had no writer and flip was +1 for every row this tool
ever saw - so the fix intended to repair orientation is what broke it, and the
old 35% band passed it at 0.333 in silence.
⚠️ TWO SELFTEST ASSERTIONS IN THIS FILE PINNED THE INVERTED ORIENTATION and
went red on the fix. THE RED WAS THE FIX WORKING and they were corrected WITH
the ruling rather than loosened (§36); the second now pins the stronger
property, that even a SET is_short_position cannot invert a multi-leg spread.
⚠️ AND THE v1.5 CHANGELOG LINE BELOW WAS DUPLICATED WHEN THIS HEADER WAS
WRITTEN. Caught by the land gate refusing the delivery; a changelog that
repeats itself is a record nobody can trust to be complete.

v1.5  2026-09-09  r328 - STILL OOM-KILLED AFTER r326, ON ONE DATE. Per-date was
the right direction and not far enough: quote_series is a per-tick stream over
~250 chain symbols and a single session does not fit control's memory either.
Now streams via warehouse_source.iter_series and INDEXES ONLY THE STREAMER
SYMBOLS THIS DATE'S TRADES NAME, taken from legs_of - the same function the
replay uses. Memory is bounded by what the trades need rather than by what the
tape held. Progress prints per symbol-day, so a slow one is visible while it is
slow.
v1.4  2026-09-09  r326 - THE S3 PATH READ ONE DATE AT A TIME; IT USED TO READ THE
WHOLE WINDOW AND GOT OOM-KILLED. `load_series("quote_series", dates)` returned
every batch row for every date in one list before a single trade was replayed,
and quote_series is the warehouse's highest-volume stream (1,437 objects for
2026-08-24 alone). Over `all` history the kernel killed it mid-listing and the
menu printed `Killed` with no traceback - indistinguishable from a crash in the
report. run() is split into accumulate() + render() so run_s3 can stream: one
date's quotes in memory at a time, and a date with NO closed trades never loads
quotes at all (60+ skipped sessions on the first run, the pre-epoch dates r314
emptied among them). Per DATE is not per TRADE - every trade on a date still
shares one indexed load, so r86's batching argument is untouched.
v1.3  2026-09-07  r299 - relaxed rows kept (operator ruling: it is all paper, and paper vs live is the split that matters).
v1.2  2026-09-07  r297 - --all-history added: `_r_tool` is shared and now passes it. The default
window also moves from TODAY to DAY ONE ONWARD via warehouse_source.
v1.1  2026-08-23  S3 DEFAULT SOURCE: trades from raw/trades, quote paths from
the raw/quote_series batches (push_series, r86) — loaded once per run and
indexed per streamer symbol, so control replays without touching a box.
--db/--feed remain the explicit local escape hatch. SOURCE lines always
printed; the positive control and the named-refusal machinery are unchanged.
v1.0  2026-08-23
REPLAY EVERY CLOSED TRADE'S REAL PREMIUM PATH — rebuilt from `quote_series` —
under alternative exit ladders. The manifold's first paying consumer.

v1.0  2026-08-23  Built for the R-factor project. stop_sweep.py works on two
extremes per trade; this works on the WHOLE PATH, so trail parameters (arm
level, giveback width) become measurable instead of argued. This is exactly
the data FEED_MANIFOLD.md said was being destroyed when chain_marks was
last-write-wins — kept per tick since r61, consumed here for the first time.

HOW A PATH IS BUILT
  · Legs come from the row's own symbol columns (short/long/lower/center/
    up🔴 CORRECTED 2026-09-19 — THIS PARAGRAPH DESCRIBED A FALLBACK THAT DOES NOT
EXIST AND NEVER DID. There was no symbol-prefix matching in `legs_of`; it
returned "no leg symbols on row" immediately, which is why every ORB and
Runaway trade was refused. So the "resolves to EXACTLY ONE contract, ambiguity
refused" safety property was a sentence, not a behaviour — and v1.6 does NOT
add it either. v1.6 reads `option_symbol`, which is an EXACT contract the trade
itself recorded, so there is nothing to disambiguate. ⚠️ AND THE DISTINCTION
MATTERS BECAUSE THE OLD SENTENCE WOULD LAUNDER THE NEW CODE: anyone later
loosening the lookup toward a prefix match would believe the ambiguity guard
was already there. It is not. The OTV4TEST session found this in its own copy
and flagged it here; their `quote_series` now carries a row whose
`streamer_symbol` is the bare underlying ("QQQ"), so a prefix match would
resolve to the UNDERLYING and replay its price path as a premium path —
plausible numbers, wrong instrument, no error.
  · Each leg's mid = (bid+ask)/2, forward-filled onto the union clock.
    Marks outside (0, 1e6) are dropped at ingest — finite is not sane.
  · ⚠️ COVERAGE IS A GATE. Expected points = trade lifetime / 15s. Below
    50% the trade is refused BY NAME with its drop reason (r39: a tool-caused
    absence must not wear the costume of a null). Refusals are summarised;
    a report with silent drops is the defect class this repo keeps finding.

RULES REPLAYED (premium-fraction space, per side convention as live):
  stop only · stop+TP · trail(arm A, give G): once favourable ≥ A, exit when
  path falls G below its running peak. The RECORDED exit is replayed too and
  must reconcile with pnl_usd within tolerance — a path that cannot
  reproduce what actually happened is not trusted to score hypotheticals
  (positive control, DRF.1's lesson).

Run:  python3 tests/exit_replay.py [--db trades.db] [--feed feed_store.db]
      python3 tests/exit_replay.py --selftest
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# 🔴 THE REPO ROOT TOO, AND THIS WAS A REAL BUG IN r390's FIRST CUT.
# The line above puts `tests/` on the path and nothing else, so
# `database.trade_logger` — the orientation resolver — was NOT importable when
# this file runs as a script. The fail-closed guard below then silently fell
# back to the unwritten `is_short_position` flag, which meant the rewire
# COMPILED, PASSED REVIEW AND DID NOTHING. Caught by the selftest's own
# credit-recovery assertion going red, not by reading.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from r_ledger import _f, DEFAULT_DB, exit_reason_family  # noqa: E402

DEFAULT_FEED = os.path.join(os.path.expanduser("~"), "options-trader", "data",
                            "feed_store.db")
POLL_S = 15.0
MIN_COVERAGE = 0.50
RECONCILE_TOL = 0.10        # |replayed pnl − pnl_usd| as a fraction of ENTRY COST
# 🔑 THIS NUMBER WAS MEASURED, NOT CHOSEN. Picking a tolerance and then
# reporting that nothing exceeded it is a self-agreeing proof, so the per-row
# deviation was dumped first (EXIT_REPLAY_DEV=1) across 2026-09-15..09-18,
# n=38 eligible rows, AFTER the orientation fix below:
#     min 0.001 · p25 0.012 · median 0.026 · p75 0.043 · p90 0.059 · max 0.170
# The population ends at ~0.06 and there is then a GAP to two rows at 0.158
# and 0.170. 0.10 is the geometric midpoint of that gap — 1.7x the observed
# p90 and 0.63x the nearest outlier — so it sits clear of the noise on one
# side and clear of the residue on the other.
# ⚠️ IT DELIBERATELY FLAGS TWO ROWS RATHER THAN ABSORBING THEM. A band of 0.20
# would report a clean zero, and that is exactly the comfortable, meaningless
# zero this whole row exists to remove. The two:
#     AMD  RunawayContinuation stop=20%  rec=-118 pnl=-260  frac=0.158
#     QQQ  ORBStrategy         stop=25%  rec= -36 pnl= -94  frac=0.170
# Both are DEBITS, both the RIGHT SIGN, and in both the replay UNDERSTATES the
# loss — consistent with the replay marking at the mid while a real exit fills
# at the bid. ⚠️ THAT IS A HYPOTHESIS AND IS NOT VERIFIED; it is recorded as
# named, unexplained residue rather than laundered into the band.
# 🔴 RPL.2 — THE BAND MUST NOT BE KEYED ON THE RULE UNDER TEST. The old
# expression was `RECONCILE_TOL * rec_stop * entry_prem * lot * 4`, and with
# `rec_stop` hardcoded at 0.25 the `0.25 * 4` cancelled to a flat 35% of entry
# cost. The moment the stop is DERIVED per row — which is the correct fix for
# the rule — that cancellation stops holding and the band starts tracking the
# stop: a 20% stop tightens to 28% of cost, a 40% butterfly stop WIDENS to 56%.
# A wider stop then means a LOOSER check, which is backwards. Measured on the
# OTV4TEST fork, which shipped the derivation first and hit exactly this: an
# ATPButterfly passing with a 15% deviation inside a 56% band.
# So the band keys on ENTRY COST alone, which does not move with the rule.

# 🔑 RPL.2 — THE RECORDED RULE IS READ OFF THE EXIT REASON, NEVER ASSUMED.
# `rec_stop = 0.25` was applied to EVERY row. Measured over 554 closed trades
# 2026-09-01..09-18: only 220 (40%) exited on a premium stop at all, and of
# those only 49 had a 25% stop. So 505 of 554 trades — 91% — were being
# reconciled against a rule they never ran under.
# ⚠️ THE OBVIOUS REGEX IS A TRAP. Our reasons carry a pnl tail
# (`hard_stop_20% pnl=-24.2%`), so a bare `(\d+)%` matches the TAIL and
# manufactures a 24% stop out of a P&L figure. The percentage is only
# meaningful BOUND TO A STOP TOKEN, which is why this anchors on the token.
# ⚠️ AND `tcs_stop_15%_of_credit` IS NOT A PREMIUM STOP — it is 15% of the
# CREDIT RECEIVED, a different basis entirely, so it is excluded by the
# negative lookahead rather than silently replayed as a premium stop.
_STOP_RE = re.compile(r"\b(?:hard_stop|premium_stop|stop)_(\d{1,3})%(?!_of_)")


def stop_of_reason(reason):
    """('premium', 0.20) if the row exited on a premium stop, else (None, tok).

    The second element on a refusal is the NAMED token, so a row that cannot
    be reconciled says WHICH rule it ran under instead of vanishing.
    """
    raw = str(reason or "").strip()
    if not raw:
        return None, "<no exit_reason>"
    m = _STOP_RE.search(raw)
    if m:
        pct = int(m.group(1)) / 100.0
        if 0.0 < pct < 1.0:
            return "premium", pct
    # 🔴 r397 — THE TOKEN COMES FROM THE ONE DEFINITION NOW, AND THE OLD ONE
    # TRUNCATED A REAL RULE. This line read
    #     re.split(r"\s+pnl=", raw)[0].split(":")[0].strip()
    # and `.split(":")[0]` cuts `hard_close_15:45_ET` down to `hard_close_15`
    # — a stable token with no per-trade part at all, rendered as though it
    # carried a percentage. That truncation reached the 2026-09-20 Saturday
    # brief, whose exit table carries a `hard_close_15` row for it.
    # 🔑 AND A SECOND PARSER WAS THE REAL DEFECT. [[GEX.2]] landed one revision
    # earlier for exactly this shape — `gex_from_chains` had reimplemented a
    # production quantity — so this does not get a private copy. `r_ledger`
    # owns `exit_reason_family`, this file already imports from it, and the
    # dependency runs the right way (r_ledger is stdlib-only).
    return None, (exit_reason_family(raw) or "<unparsed>")


TRAILS = [(0.25, 0.10), (0.25, 0.15), (0.50, 0.15), (0.50, 0.25), (0.75, 0.25)]
STOPS = [0.15, 0.25]


def _ts(v):
    try:
        return datetime.fromisoformat(str(v)).timestamp()
    except Exception:                                           # noqa: BLE001
        return None


_OCC_RE = re.compile(r"^([A-Z][A-Z0-9]*)(\d{6})([CP])(\d{8})$")


def streamer_symbol(sym):
    """OCC 'QQQ   260915C00705000' -> DXFeed '.QQQ260915C705'. None if unparseable.

    🔴 THE ONE TRANSFORM, AND IT LIVES HERE SO THERE CANNOT BE TWO. `legs_of`'s
    contract has always SAID streamer ("[(streamer_symbol, +1/-1 ...)]") while
    it returned whatever the trade column held, which is OCC. Converting at that
    single site means the index, `wanted`, `fetch` and the sqlite path all keep
    speaking one language and none of them needed changing.

    ⚠️ IDEMPOTENT ON STREAMER INPUT. The `--db` escape hatch and the selftest
    may already carry streamer keys; a transform that mangled them would trade
    one silent mismatch for another.

    ⚠️ THE STRIKE IS /1000 WITH TRAILING ZEROS STRIPPED, AND THE FRACTION IS
    REAL: verified against the bucket 2026-09-19 -- '.CRM260918C182.5' sits
    beside '.CRM260918C100'. Formatting every strike as an integer would have
    silently dropped every half-strike contract.

    ⚠️ THE ROOT MAY CONTAIN DIGITS. `GOOGL1`, `AMZN1`, `TSLA1` are the OCC
    convention for a contract adjusted by a split or special dividend, and a
    root pattern of `[A-Z]+` refuses them — loudly, by this function's own
    design, but it refuses a LEGITIMATE contract. All three of those
    underlyings are in the panel and all three have split. Measured
    2026-09-18: no adjusted root is present in the bucket today, so this is
    LATENT rather than live, and `[A-Z][A-Z0-9]*` costs nothing. The trailing
    groups are fixed-width and anchored, so the greedy root still backtracks
    correctly. Raised by the OTV4TEST session's review.

    ⚠️ QUARTER STRIKES DO NOT EXIST IN THIS BUCKET — MEASURED, NOT ASSUMED.
    28,936 streamer symbols across seven underlyings on 2026-09-18 carry only
    integer and `.5` strikes. The `.3f`-then-strip formatter would handle
    x.25/x.75 correctly anyway; what is now established is that the question
    cannot bite today.

    ⚠️ AND THE ROOT IS COPIED VERBATIM, WHICH WAS CHECKED RATHER THAN ASSUMED.
    A trade column reads 'SPXW  260918P07585000' while a first sample of the
    SPX prefix showed only '.SPX261016C7620', which looked like the root being
    rewritten. It is not: scanning 208,967 quote rows found '.SPXW260918P7630'
    at 180,742 occurrences beside a separate, genuinely different '.SPX' series.
    Had the root been rewritten, this would have half-worked -- correct on
    fourteen symbols and silently dead on the largest money in the book.
    """
    s = str(sym or "").replace(" ", "").upper()
    if not s:
        return None
    if s.startswith("."):
        return s
    m = _OCC_RE.match(s)
    if not m:
        return None
    root, exp, cp, strike = m.groups()
    k = int(strike) / 1000.0
    ks = f"{k:.3f}".rstrip("0").rstrip(".")
    return f".{root}{exp}{cp}{ks}"


def legs_of(row: dict):
    """[(streamer_symbol, +1/-1 in FAVOURABLE orientation)] or (None, reason)."""
    short = -1
    long_ = +1
    legs = []
    single_leg = False
    # 🔴 THE CENTRE IS SHORT **TWO**. A butterfly is 1/2/1, not 1/1/1 —
    # `entry_engine.py:921` builds `(center, 2, -1)` and its own comment at
    # :925 says the debit is `lower + upper - 2*center`. This weighted the
    # centre at -1, so every replayed butterfly path was too high by one
    # centre leg.
    # ⚠️ PRE-EXISTING AND INVISIBLE UNTIL NOW: with the OCC/streamer mismatch
    # above, no butterfly ever resolved a quote, so the mis-weighting could
    # never show. Fixing the symbols is what made it visible — the FIRST
    # replayed butterfly tripped the positive control at
    # replayed 1703.00 against pnl_usd 226.00 (MU, 2026-09-18).
    # 🔑 AND THIS IS WHY THE POSITIVE CONTROL EXISTS. It is not a formality:
    # it refused to certify 41 paths on the strength of 40 of them not
    # tripping it, and the one that did was a real defect in this file.
    for col, sign in (("short_symbol", short), ("long_symbol", long_),
                      ("lower_symbol", long_), ("upper_symbol", long_),
                      ("center_symbol", short * 2)):
        s = row.get(col)
        if s:
            legs.append((str(s), sign))
    if not legs:
        # 🔴 r340 WROTE THIS FIELD FOR THIS TOOL AND THIS TOOL NEVER READ IT.
        # ORB and RunawayContinuation are single-leg debits: they record
        # `option_symbol` and none of the five spread columns above, so every
        # one of them was refused "no leg symbols on row" -- 190 of 317 rows on
        # 2026-09-15. Long debit, so favourable is value UP (+1); the credit
        # flip below still applies if the row is ever marked short.
        s = row.get("option_symbol")
        if s:
            legs.append((str(s), long_))
            single_leg = True
    if not legs:
        return None, "no leg symbols on row"
    # ⚠️ TO STREAMER HERE, AT THE ONE SITE. Everything downstream -- `wanted`,
    # the S3 index, both fetch providers -- keys on what this returns, so one
    # conversion here is the whole fix. An unparseable contract refuses the
    # trade BY NAME rather than silently dropping a leg: half a spread is a
    # different position, not a partial answer.
    conv = []
    for sym_, sign in legs:
        ss = streamer_symbol(sym_)
        if ss is None:
            return None, f"unparseable contract symbol {sym_!r}"
        conv.append((ss, sign))
    # 🔴 ORIENTATION COMES FROM THE ROW'S OWN EVIDENCE, NOT FROM A FLAG WITH NO
    # WRITER. OPERATOR'S RULING, 2026-09-19.
    # [[RPT.26]]: `is_short_position` is READ by exit_engine, position_manager
    # and the adopted-position alert and was WRITTEN BY NOTHING on any entry
    # path — every row took the schema default of 0, credit spreads included.
    # r343 began writing it FORWARD-ONLY; r344 gave `position_dollars` the
    # fallback that recovers the history. **This function never got either**,
    # so `flip` was +1 for every row it has ever seen and a credit position's
    # path was replayed with the LONG sign — its wins read as losses.
    # 🔑 ONE RESOLVER, THE ONE THE EXIT PATH ALREADY TRUSTS.
    # `trade_logger.is_credit_position()` is r345's rule: the flag FIRST (so
    # r343's forward-written rows stay authoritative and a genuine long cannot
    # be flipped by a stray credit value), then `credit_received > 0`, then
    # `is_condor_leg`, then the condor's name. `r_ledger.is_credit` agrees with
    # it by `check_exit_credit_side` X6. Reimplementing the test here would be
    # a SECOND definition of "is this short", which is the drift this repo
    # keeps finding (C.23).
    # ⚠️ DEBITS ARE UNTOUCHED, WHICH IS THE HALF THAT WAS ACCIDENTALLY RIGHT:
    # ORB and Runaway write no credit, carry `is_condor_leg = 0` and are not
    # the condor, so every branch returns False and they keep +1. Verified
    # against the real function: ORB row -> False, butterfly -> False, credit
    # with the flag UNSET -> True (the recovery), credit with the flag set ->
    # True.
    # ⚠️ AND IT FAILS CLOSED (§22): if the import is unavailable the row keeps
    # the long orientation it has always had, rather than this tool silently
    # inventing a third answer.
    try:
        from database.trade_logger import is_credit_position as _is_credit
        _short = bool(_is_credit(row))
    except Exception as _exc:                                  # noqa: BLE001
        # 🔴 LOUD, ONCE. A SILENT FALLBACK HERE IS WORSE THAN THE BUG IT
        # GUARDS (§0.5). Falling back to the unwritten flag reverts this tool
        # to replaying every credit position with the LONG sign — its wins
        # read as losses — and it would do so while printing a clean report.
        # r390's own first cut fell into exactly that: the repo root was not
        # on `sys.path`, the import failed, and the rewire did nothing at all.
        if not getattr(legs_of, "_warned_resolver", False):
            legs_of._warned_resolver = True
            print(f"  ⚠️ orientation resolver unavailable ({_exc}) — falling "
                  f"back to the is_short_position flag, which HAS NO WRITER. "
                  f"Every credit path below is replayed with the LONG sign.",
                  file=sys.stderr)
        _short = bool(row.get("is_short_position"))
    # 🔴 THE FLIP APPLIES TO THE SINGLE-LEG FALLBACK ONLY, AND THAT IS THE
    # CORRECTION TO r390'S OWN FIRST CUT. The five spread columns above are
    # ALREADY ORIENTED BY STRUCTURE: `short_symbol` carries -1 and
    # `long_symbol` +1, so a credit vertical's combo is `long - short`, i.e.
    # MINUS the spread's value. A credit seller profits when the spread gets
    # CHEAPER — which is that combo going UP — so the multi-leg path is
    # already in favourable orientation with no flip at all.
    # ⚠️ APPLYING `flip = -1` ON TOP INVERTED EVERY CREDIT SPREAD. Before the
    # rewire `flip` was +1 for every row (the flag had no writer), so these
    # were ACCIDENTALLY CORRECT, and the rewire — intended to fix orientation —
    # is what broke them. MEASURED: NVDA SweepCreditSpread 2026-09-17 replayed
    # to +55 against a recorded pnl_usd of -55, an exact inversion, and the
    # three SweepCreditSpread rows in the 4-session sample clustered at 0.30,
    # 0.32 and 0.33 of entry cost — about TWICE their 15% stop, which is the
    # arithmetic signature of a sign error rather than of replay imprecision.
    # 🔑 AND THE 35% BAND HID ALL OF IT. The old control passed them at 0.33.
    # The single-leg case is the one where orientation is NOT already encoded:
    # `option_symbol` is appended at +1 unconditionally, so a genuinely short
    # single leg needs the flip to make favourable mean premium DOWN.
    # ⚠️ AND THIS BRANCH IS CURRENTLY UNREACHABLE, WHICH IS WORTH WRITING DOWN
    # BECAUSE IT IS THE KIND OF FACT THAT SILENTLY STOPS BEING TRUE. Of the
    # four shapes this tool sees, NONE needs a flip: a credit vertical is
    # `long - short` and rises as the seller wins; a butterfly is 1/-2/1 and
    # is its own debit; a single-leg debit is +1 and rises as it wins. Only a
    # NAKED SHORT single leg would need it, and no entry path writes one. It
    # is kept guarded and dead rather than deleted, so the next reader does
    # not have to re-derive why it is absent. Independently reached on the
    # OTV4TEST fork, whose entry validation fails closed on a naked short.
    flip = -1 if (_short and single_leg) else 1
    return [(s, sign * flip) for s, sign in conv], ""


def path_for(fetch, legs, t0, t1):
    """Combined signed-mid path on the union clock, forward-filled per leg.

    v1.1 — `fetch(sym, t0, t1)` -> [(ts_epoch, bid, ask)] abstracts the
    source: sqlite locally, the indexed S3 quote batches on control. One path
    builder, two providers, so the two sources cannot drift apart.
    """
    series = {}
    for sym, _sign in legs:
        rows = fetch(sym, t0 - 60, t1 + 60)
        pts = []
        for ts, b, a in rows:
            b, a = _f(b), _f(a)
            if b and a and 0 < b < 1e6 and 0 < a < 1e6 and a >= b:
                pts.append((ts, (b + a) / 2.0))
        if not pts:
            return None, f"no usable quotes for {sym}"
        series[sym] = pts
    clock = sorted({ts for pts in series.values() for ts, _ in pts if t0 <= ts <= t1})
    if not clock:
        return None, "no timestamps inside the trade window"
    idx = {s: 0 for s in series}
    last = {s: None for s in series}
    out = []
    for t in clock:
        val = 0.0
        ok = True
        for (sym, sign) in legs:
            pts = series[sym]
            i = idx[sym]
            while i < len(pts) and pts[i][0] <= t:
                last[sym] = pts[i][1]
                i += 1
            idx[sym] = i
            if last[sym] is None:
                ok = False
                break
            val += sign * last[sym]
        if ok:
            out.append((t, val))
    return out, ""


def replay(path, entry_val, risk, rule):
    """pnl in combo-value points for one rule. rule = ('stop',s) | ('tp',s,t)
    | ('trail',s,arm,give). Favourable = value UP (legs_of already oriented)."""
    kind = rule[0]
    stop = rule[1]
    peak = entry_val
    armed = False
    for _t, v in path:
        move = v - entry_val
        peak = max(peak, v)
        if move <= -stop * risk:
            return -stop * risk
        if kind == "tp" and move >= rule[2] * risk:
            return rule[2] * risk
        if kind == "trail":
            if not armed and move >= rule[2] * risk:
                armed = True
            if armed and (peak - v) >= rule[3] * risk:
                return v - entry_val
    return path[-1][1] - entry_val if path else 0.0


def _sqlite_fetch(fcon):
    def fetch(sym, lo, hi):
        return fcon.execute(
            "SELECT ts_epoch, bid_price, ask_price FROM quote_series"
            " WHERE streamer_symbol=? AND ts_epoch BETWEEN ? AND ?"
            " ORDER BY ts_epoch", (sym, lo, hi)).fetchall()
    return fetch


def _s3_fetch(qrows):
    from collections import defaultdict as _dd
    idx = _dd(list)
    for r in qrows:
        idx[r.get("streamer_symbol")].append(
            (r.get("ts_epoch") or 0, r.get("bid_price"), r.get("ask_price")))
    for v in idx.values():
        v.sort()

    def fetch(sym, lo, hi):
        return [p for p in idx.get(sym, ()) if lo <= p[0] <= hi]
    return fetch


def blank_acc() -> dict:
    """One accumulator, filled a date at a time and rendered once at the end."""
    return {"refused": defaultdict(int),
            "totals": defaultdict(lambda: defaultdict(float)),
            "counts": defaultdict(int),
            "control_na": defaultdict(int),
            "control_n": 0,
            "recon_fail": 0}


def accumulate(rows, fetch, acc: dict) -> None:
    """Replay one batch of trades into `acc`. NOTHING IS PRINTED HERE.

    🔴 r326 — SPLIT OUT OF run() SO THE S3 PATH CAN WORK ONE DATE AT A TIME.
    The old shape loaded every quote batch in the window into ONE list before
    a single trade was replayed, and quote_series is the highest-volume
    stream in the warehouse — 1,437 objects for 2026-08-24 alone. Over an
    `all` window that is not slow, it is FATAL: the kernel killed the process
    mid-listing on 2026-09-09 and the menu reported `Killed`, which looks
    like a crash in a report rather than a tool asking for more memory than
    control has.
    """
    for r in rows:
        t0, t1 = _ts(r.get("entry_time")), _ts(r.get("exit_time"))
        if not t0 or not t1 or t1 <= t0:
            acc["refused"]["bad timestamps"] += 1
            continue
        legs, why = legs_of(r)
        if legs is None:
            acc["refused"][why] += 1
            continue
        path, why = path_for(fetch, legs, t0, t1)
        if not path:
            acc["refused"][why or "empty path"] += 1
            continue
        cov = len(path) / max(1.0, (t1 - t0) / POLL_S)
        if cov < MIN_COVERAGE:
            acc["refused"][f"coverage<{MIN_COVERAGE:.0%}"] += 1
            continue
        entry_val = path[0][1]
        entry_prem = _f(r.get("entry_premium")) or abs(entry_val) or 1.0
        lot = 100.0 * (_f(r.get("contracts")) or 1)
        # positive control: the recorded stop, replayed, must land near pnl_usd
        pnl = _f(r.get("pnl_usd")) or 0.0
        kind, rec_stop = stop_of_reason(r.get("exit_reason"))
        cost = entry_prem * lot
        if kind != "premium":
            # 🔑 NOT APPLICABLE IS NEITHER A PASS NOR A FAILURE, AND IT IS
            # NAMED. A trail stop, a 15:45 hard close or a structure stop
            # cannot be reconciled by replaying a premium stop, so asserting
            # one produces a verdict about the TOOL rather than the trade.
            acc["control_na"][rec_stop] += 1
            rec = None
            _bad = False
        else:
            rec = replay(path, entry_val, entry_prem, ("stop", rec_stop)) * lot
            acc["control_n"] += 1
            _dev = abs(rec - pnl)
            _bad = _dev > max(50.0, RECONCILE_TOL * cost)
            if os.environ.get("EXIT_REPLAY_DEV") and cost > 0:
                import sys as _s
                _sgn = "SIGN?" if (pnl != 0 and abs(rec + pnl) < abs(rec - pnl) / 3.0) else ""
                print(f"    [DEV] {r.get('symbol')} {r.get('strategy')} "
                      f"stop={rec_stop:.0%} dev=${_dev:,.0f} "
                      f"cost=${cost:,.0f} frac={_dev/cost:.3f} "
                      f"rec={rec:,.0f} pnl={pnl:,.0f} "
                      f"credit={r.get('credit_received')!r} {_sgn}", file=_s.stderr)
        # 🔑 `EXIT_REPLAY_DIAG=1` NAMES THE TRADE THAT TRIPPED THE CONTROL.
        # This is what found the butterfly centre-weight defect: the control
        # said "1 trade does not reconcile" and could not say WHICH, so the
        # only way to chase it was to add this. Off by default, one line of
        # stderr when on, and it is the difference between a red control being
        # investigated and a red control being footnoted.
        if _bad and rec is not None and os.environ.get("EXIT_REPLAY_DIAG"):
            import sys as _sys
            print(f"    [DIAG] recon_fail: {r.get('symbol')} {r.get('strategy')} "
                  f"replayed={rec:.2f} pnl_usd={pnl:.2f} "
                  f"is_short={r.get('is_short_position')!r} "
                  f"credit={r.get('credit_received')!r} "
                  f"path={'option_symbol-FALLBACK' if not any(r.get(c) for c in ('short_symbol','long_symbol','lower_symbol','upper_symbol','center_symbol')) else 'leg-columns'} "
                  f"reason={str(r.get('exit_reason'))[:40]!r}", file=_sys.stderr)
        if _bad:
            acc["recon_fail"] += 1
        key = (r.get("strategy") or "?", (r.get("option_side") or "?").lower())
        acc["counts"][key] += 1
        acc["totals"][key]["recorded"] += pnl
        for s in STOPS:
            acc["totals"][key][f"stop {s:.2f}"] += replay(path, entry_val, entry_prem,
                                                   ("stop", s)) * lot
        for arm, give in TRAILS:
            acc["totals"][key][f"trail a{arm:.2f}/g{give:.2f}"] += replay(
                path, entry_val, entry_prem, ("trail", 1.0, arm, give)) * lot

def render(acc: dict) -> int:
    refused, totals = acc["refused"], acc["totals"]
    counts, recon_fail = acc["counts"], acc["recon_fail"]
    print("=" * 70)
    print("  EXIT REPLAY — real premium paths from quote_series, dollars")
    print("=" * 70)
    for key in sorted(counts):
        print(f"\n  {key[0]} · {key[1]}   n={counts[key]} replayed")
        for rule, net in sorted(totals[key].items(), key=lambda kv: -kv[1]):
            mark = "  <- recorded" if rule == "recorded" else ""
            print(f"    {rule:<22} ${net:>10,.0f}{mark}")
    if refused:
        print("\n  REFUSED (named, per r39 — these are the tool's gaps, not the tape's):")
        for why, n in sorted(refused.items(), key=lambda kv: -kv[1]):
            print(f"    {why:<40} {n}")
    na, cn = acc["control_na"], acc["control_n"]
    print(f"\n  POSITIVE CONTROL: applied to {cn} replayed trade(s), "
          f"{recon_fail} did not reconcile "
          f"(band {RECONCILE_TOL:.0%} of entry cost).")
    if na:
        # 🔑 NAMED, NOT SILENT. A row skipped without a name is indistinguishable
        # from a row that passed, which is the whole defect RPL.2 fixes.
        print("  NOT APPLICABLE — exited on a rule a premium-stop replay cannot "
              "reconcile (neither a pass nor a failure):")
        for why, n in sorted(na.items(), key=lambda kv: -kv[1]):
            print(f"    {why:<40} {n}")
    if cn == 0 and counts:
        print("  ⚠️ THE CONTROL APPLIED TO NOTHING — every replayed trade was "
              "NOT APPLICABLE, so the hypotheticals above are UNVERIFIED.")
    if recon_fail:
        print(f"\n  ⚠️ POSITIVE CONTROL: {recon_fail} trade(s) whose replayed "
              f"recorded-rule pnl did not reconcile with pnl_usd — treat every "
              f"hypothetical above as suspect until this is zero or explained.")
    # 🔴 GATED ON `not refused` TOO, AND THAT IS THE WHOLE POINT. `not counts`
    # is true EXACTLY when nothing replayed -- which is exactly when the block
    # above has just named every refusal as the tool's OWN gap. Both fired
    # every time and this one was LAST, so a reader who scrolls to the bottom
    # (which is what a reader does) got the opposite of the truth. The
    # "s3_push v4.2" clause is deleted outright rather than reworded: it sent
    # the reader to audit a healthy push, and on the OTV4TEST fork it names a
    # service that is MASKED BY OPERATOR RULING and must never run.
    if not counts and not refused:
        print("\n  nothing replayable yet — quote_series holds no rows for "
              "this window.")
    return 0


def run(rows, fetch) -> int:
    """Whole-book path: the --db escape hatch and the selftest. Unchanged."""
    acc = blank_acc()
    accumulate(rows, fetch, acc)
    return render(acc)


def run_s3(a) -> int:
    """ONE SYMBOL-DAY AT A TIME, STREAMED, INDEXING ONLY THE LEGS WE NEED.

    🔴 r328 — r326 WAS THE RIGHT DIRECTION AND NOT FAR ENOUGH. It narrowed the
    load from the whole window to one date, and control was still OOM-killed
    on a SINGLE session: `quote_series` is a per-tick stream over ~250 chain
    symbols, and one day of it does not fit either. Narrowing the window again
    only moves the wall — the list itself had to go.
    🔑 TWO CHANGES, AND THE SECOND IS THE ONE THAT MATTERS. (1) `iter_series`
    streams envelopes instead of returning a list. (2) **We index only the
    streamer symbols this date's trades actually name.** A session's quotes
    cover the whole chain; a day's trades touch a handful of contracts, and
    `legs_of` already knows exactly which. Memory is now bounded by what the
    trades need, not by what the tape held.
    ⚠️ PER SYMBOL-DAY IS STILL NOT PER TRADE. Every trade on one underlying
    shares one pass, so r86's batching argument is intact; the pass is just
    filtered on the way through.
    ⚠️ The refusal path is unchanged: a leg with no quotes in the window
    refuses BY NAME. A leg dropped by this filter would be indistinguishable
    from a leg the tape never carried, which is why `wanted` is built from
    `legs_of` — the same function the replay uses — and never guessed.
    """
    import warehouse_source as ws
    dates = ws.dates_of(a)
    acc = blank_acc()
    replayed = 0
    for d in dates:
        trades, m1 = ws.load_trades([d])
        if m1.error:
            print("  " + m1.banner())
            return 1
        rows = [t for t in trades if (t.get("status") or "").lower() == "closed"]
        if not rows:
            continue
        by_sym = defaultdict(list)
        for r in rows:
            by_sym[str(r.get("symbol") or "?")].append(r)
        print(f"  {d}: {len(rows)} closed trade(s), {len(by_sym)} symbol(s)")
        for sym in sorted(by_sym):
            srows = by_sym[sym]
            wanted = set()
            for r in srows:
                legs, _why = legs_of(r)
                for lsym, _sign in (legs or ()):
                    wanted.add(lsym)
            if not wanted:
                # no leg columns at all — accumulate so it refuses BY NAME
                accumulate(srows, lambda *_a: [], acc)
                continue
            print(f"    {d} {sym}: {len(srows)} trade(s), "
                  f"{len(wanted)} contract(s)", end="", flush=True)
            meta = ws.Meta(f"quote_series {d} {sym}")
            idx = defaultdict(list)
            kept = 0
            for q in ws.iter_series("quote_series", [d], meta, symbols=[sym]):
                ss = q.get("streamer_symbol")
                if ss in wanted:
                    idx[ss].append((q.get("ts_epoch") or 0,
                                    q.get("bid_price"), q.get("ask_price")))
                    kept += 1
            if meta.error:
                print()
                print("  " + meta.banner())
                return 1
            for v in idx.values():
                v.sort()
            print(f" — {meta.read} object(s), {kept} quote(s) kept")

            def fetch(s_, lo, hi, _idx=idx):
                return [p for p in _idx.get(s_, ()) if lo <= p[0] <= hi]

            accumulate(srows, fetch, acc)
            replayed += 1
            idx.clear()
    if not replayed:
        print("  no closed trades in the window — nothing to replay.")
    return render(acc)


def selftest() -> int:
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE quote_series (streamer_symbol TEXT, ts_epoch REAL,"
                " bid_price REAL, ask_price REAL)")
    # 🔴 REAL FORMATS ON BOTH SIDES, AND THIS IS THE FIX THAT MATTERS MOST.
    # v1.5's fixture used "X 260823C100" -- neither OCC nor streamer -- as the
    # quote key AND as the leg, so it matched ITSELF and passed on a tool that
    # replayed nothing from S3 for its entire life. WA 0.4: a fixture built from
    # the author's own assumption cannot fail. The quote table is now keyed the
    # way the bucket is keyed, and the legs are derived THROUGH `legs_of` from a
    # trade row carrying the OCC string a real trade carries.
    _OCC, _SS = "QQQ   260915C00705000", ".QQQ260915C705"
    # A long call: mid runs 1.00 -> 2.00 by t=300 then back to 1.20 at t=600
    for i in range(41):
        t = i * 15.0
        mid = 1.0 + (t / 300.0) if t <= 300 else 2.0 - 0.8 * ((t - 300) / 300.0)
        con.execute("INSERT INTO quote_series VALUES (?,?,?,?)",
                    (_SS, 1000 + t, mid - 0.02, mid + 0.02))
    legs, _wl = legs_of({"option_symbol": _OCC, "is_short_position": 0})
    ok0 = legs == [(_SS, +1)]
    if not ok0:
        print(f"exit_replay selftest: FAIL legs_of({_OCC!r}) -> {legs!r} "
              f"(expected [({_SS!r}, 1)])")
        return 1
    path, why = path_for(_sqlite_fetch(con), legs, 1000, 1600)
    ok = bool(path) and not why and len(path) == 41
    r_hold = replay(path, path[0][1], 1.0, ("stop", 0.25))
    ok &= abs(r_hold - 0.20) < 0.03           # rode up, gave back to +0.20
    r_trail = replay(path, path[0][1], 1.0, ("trail", 1.0, 0.25, 0.15))
    ok &= 0.80 < r_trail < 0.92               # trail keeps ~+0.85 of the +1.00 peak
    r_tp = replay(path, path[0][1], 1.0, ("tp", 0.25, 0.50))
    ok &= abs(r_tp - 0.50) < 1e-9
    # v1.1 — the S3 provider must build the IDENTICAL path from the same data
    qrows = [{"streamer_symbol": _SS, "ts_epoch": t, "bid_price": b,
              "ask_price": a2} for t, b, a2 in con.execute(
                  "SELECT ts_epoch, bid_price, ask_price FROM quote_series")]
    path2, _w = path_for(_s3_fetch(qrows), legs, 1000, 1600)
    ok &= path2 == path
    # deliberate failures: coverage refusal + ambiguity refusal
    sparse, _ = path_for(_sqlite_fetch(con), legs, 0, 20000)
    cov = len(sparse or []) / ((20000 - 0) / POLL_S)
    ok &= cov < MIN_COVERAGE
    lg, why2 = legs_of({"is_short_position": 0})
    ok &= lg is None and "no leg symbols" in why2
    # ⚠️ THE TRANSFORM IS PINNED IN BOTH DIRECTIONS AND ON THE SHAPES THAT BITE.
    # Whole strike, HALF strike (verified in the bucket: '.CRM260918C182.5'),
    # the SPXW root copied verbatim (208,967 rows scanned to confirm it is NOT
    # rewritten to .SPX), idempotence on streamer input, and a refusal on junk.
    ok &= streamer_symbol("QQQ   260915C00705000") == ".QQQ260915C705"
    ok &= streamer_symbol("CRM   260918C00267500") == ".CRM260918C267.5"
    ok &= streamer_symbol("SPXW  260918P07585000") == ".SPXW260918P7585"
    ok &= streamer_symbol(".QQQ260915C705") == ".QQQ260915C705"
    ok &= streamer_symbol("not a contract") is None
    # ADJUSTED ROOTS CARRY A DIGIT — latent today, free to support.
    ok &= streamer_symbol("GOOGL1260918C00150000") == ".GOOGL1260918C150"
    ok &= streamer_symbol("TSLA1 260918P00400000") == ".TSLA1260918P400"
    # AND A CREDIT SPREAD'S LEGS SURVIVE THE TRANSFORM WITH THEIR ORIENTATION.
    # THE DEAD FLIP, ASSERTED AS DEAD. If `is_short_position` ever starts
    # being written, this goes red and the orientation question becomes live
    # again rather than silently inverting a path.
    # ORIENTATION FROM EVIDENCE, NOT THE FLAG. The middle case is the one that
    # matters: a credit row with `is_short_position` UNSET — which is EVERY
    # credit row banked before r343 — must still read SHORT.
    _sh, _w1 = legs_of({"option_symbol": _OCC, "is_short_position": 1})
    ok &= _sh == [(_SS, -1)]
    _un, _w2 = legs_of({"option_symbol": _OCC})
    ok &= _un == [(_SS, +1)]
    # 🔴 CORRECTED — THIS ASSERTION PINNED THE BUG. It previously expected the
    # SHORT leg at +1 and the LONG leg at -1, i.e. the flipped orientation, and
    # it went red the moment RPL.3 scoped the flip to the single-leg fallback.
    # THE RED WAS THE FIX WORKING (§36: a check moves WITH a ruling, never
    # loosened to stay green). A credit vertical's combo is `long - short`,
    # which is MINUS the spread's value and already rises as the seller wins,
    # so the structural signs stand and no flip applies.
    _rec, _w3 = legs_of({"short_symbol": "QQQ   260915C00705000",
                         "long_symbol": "QQQ   260915C00706000",
                         "credit_received": 0.435})          # flag UNSET
    ok &= _rec == [(".QQQ260915C705", -1), (".QQQ260915C706", +1)]
    _dbt, _w4 = legs_of({"option_symbol": _OCC, "strategy": "ORBStrategy",
                         "credit_received": 0, "is_condor_leg": 0})
    ok &= _dbt == [(_SS, +1)]
    # A BUTTERFLY IS 1/2/1 — the centre carries TWICE the weight.
    fly, _wf = legs_of({"lower_symbol": "QQQ   260915C00700000",
                        "center_symbol": "QQQ   260915C00705000",
                        "upper_symbol": "QQQ   260915C00710000",
                        "is_short_position": 0})
    ok &= fly == [(".QQQ260915C700", +1), (".QQQ260915C710", +1),
                  (".QQQ260915C705", -2)]
    # ⚠️ AND THE FLAG DOES NOT CHANGE IT EITHER. Even with `is_short_position`
    # explicitly SET, a multi-leg spread keeps its structural orientation —
    # the flip is scoped to the single-leg fallback, so a written flag cannot
    # reach a vertical. This is the stronger half of the pair: it pins that
    # the r343 forward-written flag will NOT silently invert spreads later.
    cl, _wc = legs_of({"short_symbol": "QQQ   260915C00705000",
                       "long_symbol": "QQQ   260915C00706000",
                       "is_short_position": 1})
    ok &= cl == [(".QQQ260915C705", -1), (".QQQ260915C706", +1)]
    print("exit_replay selftest:", "ALL PASS" if ok else
          f"FAIL hold={r_hold} trail={r_trail} tp={r_tp} cov={cov:.2f}")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=None, help="LOCAL escape hatch")
    ap.add_argument("--feed", default=None, help="LOCAL escape hatch")
    ap.add_argument("--date")
    ap.add_argument("--from", dest="frm")
    ap.add_argument("--to", dest="to")
    ap.add_argument("--all-history", action="store_true",
                    help="reach back through the v3 engines; the default "
                         "stops at the 2026-08-25 epoch (r187). Added at r297 "
                         "because `_r_tool` is SHARED by three items and now "
                         "passes this flag - without it argparse would refuse "
                         "and two working menu items would break.")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.db or a.feed:
        db, feed = a.db or DEFAULT_DB, a.feed or DEFAULT_FEED
        for pth, name in ((db, "trades db"), (feed, "feed store")):
            if not os.path.exists(pth):
                print(f"  SOURCE: local {pth} — 🔴 {name} DOES NOT EXIST")
                return 1
        print(f"  SOURCE: local sqlite {db} + {feed}")
        tcon = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        tcon.row_factory = sqlite3.Row
        rows = [dict(r) for r in tcon.execute(
            "SELECT * FROM trades WHERE status='closed'"
            )]  # r299 — relaxed rows kept
        fcon = sqlite3.connect(f"file:{feed}?mode=ro", uri=True)
        return run(rows, _sqlite_fetch(fcon))
    return run_s3(a)


if __name__ == "__main__":
    sys.exit(main())
