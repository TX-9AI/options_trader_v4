#!/usr/bin/env python3
"""
tests/check_exit_replay_control.py  v1.1
v1.1  2026-09-20  r397 / D1 - C4c and C4d. C4c pins that a stable token whose
colon is NOT a tail marker survives intact, asserted as an EXACT equality
because a `startswith` passes against the truncated value - which is the whole
failure being pinned. BORN RED at ff02d37, printing `hard_close_15`. C4d is the
CONTROL: every recorded hard-stop percentage is still read as its own rule for
the replay, so the report-side fold cannot leak into the stop derivation.
v1.0  2026-09-19  r390 / RPL.2 + RPL.3 — THE POSITIVE CONTROL ASSERTED A STOP
      91% OF TRADES NEVER RAN UNDER, PRINTED ZERO ANYWAY, AND WAS HIDING AN
      ORIENTATION REGRESSION SHIPPED IN THE SAME REVISION.

THE CONTROL MUST ASSERT THE RULE THE TRADE ACTUALLY RAN UNDER, AND THE BAND
MUST NOT MOVE WITH THAT RULE.

`exit_replay`'s positive control replayed EVERY row under a hardcoded 25%
premium stop and compared the result to `pnl_usd`. Measured over 554 closed
trades 2026-09-01..09-18: 326 (59%) never exited on a premium stop at all
(`orb_trail_stop` 206, `orb_structure_stop` 58, `target_hit` 18,
`hard_close_15:45_ET` 15, ...), and of the 220 that did, only 49 carried a 25%
stop. **505 of 554 — 91% — were reconciled against a rule they never ran
under**, and the control still printed 0 because the tolerance was 35% of
entry cost.

🔴 A LOOSE BAND AND A CORRECT CONTROL BOTH PRINT ZERO. That is the whole
reason this file exists: the failure is invisible from the output.

🔑 C5 IS THE ONE THAT WOULD HAVE BEEN MISSED. Deriving the stop is the
obvious fix and it silently regresses the band, because the old expression
multiplied the tolerance BY the stop and only cancelled at 0.25. The OTV4TEST
fork shipped the derivation first and hit exactly this — a butterfly passing
with a 15% deviation inside a 56% band. A wider stop must not buy a looser
check, and C5 proves that at RUNTIME rather than by reading the source (§21).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import exit_replay as er

FAILS = []
RAN = []


def ck(name, ok, msg):
    RAN.append(name)
    print(f"  {name:<5} {'PASS' if ok else 'FAIL'}  {msg}")
    if not ok:
        FAILS.append(name)


# ------------------------------------------------------------------------- C0
# 🔴 THE SELFTEST IS RUN FROM HERE BECAUSE THE LANDER CANNOT RUN IT ITSELF.
# `land.spec` carried `CHECK tests/exit_replay.py --selftest`, and land.sh
# executes a check as `python3 "$chk"` with the variable QUOTED — so the whole
# string is taken as ONE filename and python3 reports
#   can't open file '.../tests/exit_replay.py --selftest'
# The CHECK directive takes a PATH and no arguments; that line could never
# have passed and had never been exercised. A gate that cannot run is not a
# weak gate, it is the ABSENCE of one wearing a gate's costume — SHD.5 and
# LAND.9's shape, where check_land_sh sat dead for five days.
# So the selftest is invoked in-process here, where a real CHECK line reaches
# it, and its failure is this file's failure.
_rc = er.selftest()
ck("C0", _rc == 0, f"exit_replay --selftest passes in-process (rc={_rc})")

# ---------------------------------------------------------------- C1 / C2 / C3
# Verbatim strings from the corpus, not invented shapes.
PREMIUM = [("hard_stop_20% pnl=-24.2%", 0.20),
           ("hard_stop_25% pnl=-26.3%", 0.25),
           ("premium_stop_15% pnl=-16.7%", 0.15),
           ("stop_25% pnl=-30.0%", 0.25),
           ("hard_stop_18% pnl=-19.0%", 0.18),
           ("stop_26% pnl=-27.0%", 0.26)]
bad = [(r, er.stop_of_reason(r)) for r, want in PREMIUM
       if er.stop_of_reason(r) != ("premium", want)]
ck("C1", not bad, f"{len(PREMIUM)} real premium-stop reasons derive their own stop: {bad or 'all ok'}")

# ⚠️ THE TRAP. Our reasons carry a pnl tail, so a bare (\d+)% reads the TAIL.
TRAPS = ["orb_trail_stop pnl=-26.5%", "orb_structure_stop pnl=-24.0%",
         "target_hit pnl=100.0%", "nickel_close pnl=79.2%",
         "breach: 1m close 397.13 through 397.07 pnl=-1.3%"]
leaked = [(r, er.stop_of_reason(r)) for r in TRAPS
          if er.stop_of_reason(r)[0] == "premium"]
ck("C2", not leaked, f"a pnl= tail is NEVER read as a stop: {leaked or 'no leak'}")

tcs = er.stop_of_reason("tcs_stop_15%_of_credit: 0.51 >= 0.51 (credit 0.44)")
ck("C3", tcs == (None, "tcs_stop_15%_of_credit"),
   f"15% OF CREDIT is a different basis, not a premium stop: {tcs}")

# ⚠️ C3 ABOVE DOES NOT TEST THE LOOKAHEAD, AND SAYING SO IS THE POINT. In
# `tcs_stop_15%`, the character before `stop` is `_` — a word character — so
# `\b` never matches there and the token is rejected by the word boundary
# alone. Mutation-proven: deleting `(?!_of_)` leaves C3 GREEN. The lookahead
# only bites on a BARE `stop_15%_of_credit`, a form this corpus does not emit
# today, so C3b covers it deliberately rather than leaving the guard untested.
bare = er.stop_of_reason("stop_15%_of_credit: 0.51 >= 0.51")
ck("C3b", bare == (None, "stop_15%_of_credit"),
   f"a BARE credit-basis token is refused by the lookahead, not read as a "
   f"15% premium stop: {bare}")

# ------------------------------------------------------------------------- C4
NA = ["orb_trail_stop pnl=43.2%", "orb_structure_stop pnl=-5.0%",
      "hard_close_15:45_ET", "orb_fvg_trail_stop pnl=12.0%",
      "orb_stop_respected pnl=-3.0%", "target_hit pnl=100.0%"]
named = [er.stop_of_reason(r) for r in NA]
ok4 = all(k is None and isinstance(t, str) and t and not t.startswith("<") for k, t in named)
ck("C4", ok4, f"every non-premium rule refuses BY NAME: {[t for _, t in named]}")

ck("C4b", er.stop_of_reason("")[1] == "<no exit_reason>",
   f"a missing reason is named too, not silently skipped: {er.stop_of_reason('')}")

# 🔴 C4c — r397. THE NAMED TOKEN MUST NOT BE TRUNCATED AT A BARE COLON.
# Until r397 `stop_of_reason` did `.split(":")[0]`, which cut the real rule
# `hard_close_15:45_ET` down to `hard_close_15` — a rule renamed into
# something that reads like a percentage-bearing stop. It is not cosmetic:
# that string is what the NOT-APPLICABLE tally prints and what a reader
# carries away, and it reached the 2026-09-20 Saturday brief's exit table.
# ⚠️ ASSERTED AS AN EXACT EQUALITY, NOT A `startswith`. A prefix test passes
# against the truncated value, which is the whole failure being pinned.
ck("C4c", er.stop_of_reason("hard_close_15:45_ET")[1] == "hard_close_15:45_ET",
   f"a stable token whose colon is NOT a tail marker survives intact: "
   f"{er.stop_of_reason('hard_close_15:45_ET')[1]!r}")

# 🔴 C4d — r397. ONE RULE, MANY RECORDED PERCENTAGES, ONE NAME.
# `exit_engine.py:1169` computes the hard-stop label from the row's own fill
# (`1 - stop_prem/entry_prem`), so the tape carries hard_stop_19/20/24/25/26%
# for a single rule. If these ever stop collapsing, the exit tables go back to
# printing one row per trade, which is the [[RPL.1]]-class defect r397 fixed.
_fams = {er.stop_of_reason(f"hard_stop_{p}% pnl=-{p + 2}.0%")[1]
         for p in (19, 20, 24, 25, 26)}
_prem = {er.stop_of_reason(f"hard_stop_{p}% pnl=-{p + 2}.0%")[0]
         for p in (19, 20, 24, 25, 26)}
ck("C4d", _prem == {"premium"},
   f"every recorded hard-stop percentage is still READ AS ITS OWN RULE for "
   f"the replay ({_prem}) — the fold is for the report, never the replay")


# ------------------------------------------------------------------------- C5
# 🔴 THE REGRESSION GUARD. Drive `accumulate` with two synthetic trades that
# are IDENTICAL except for the stop named in their exit reason, and give both
# the same true pnl error. If the band scales with the stop, the wider-stop
# row is forgiven and the tighter one is not.
def _mk_fetch(prem_path):
    def fetch(sym, t0, t1):
        return [(ts, v - 0.01, v + 0.01) for ts, v in prem_path]
    return fetch


def _row(reason, pnl_usd):
    return {"symbol": "TEST", "strategy": "S", "option_side": "call",
            "status": "closed", "entry_time": "2026-09-18T10:00:00",
            "exit_time": "2026-09-18T10:10:00", "option_symbol": "TEST  260918C00100000",
            "entry_premium": 1.00, "contracts": 10, "pnl_usd": pnl_usd,
            "exit_reason": reason, "is_short_position": 0}


# ⚠️ THE PATH MUST OVERLAP THE ROW'S OWN WINDOW. Built from a hardcoded epoch
# first, which put every quote outside [t0,t1] -- `path_for` then returned
# nothing, the rows never reached the control, and C5 PASSED VACUOUSLY at
# 0 == 0. That is the same shape as the defect under test, so C5 now asserts
# the control actually APPLIED before comparing verdicts.
_T0 = er._ts("2026-09-18T10:00:00")
path = [(_T0 + 15 * i, 1.00) for i in range(41)]
res = {}
for reason in ("hard_stop_20% pnl=-24.0%", "hard_stop_40% pnl=-44.0%"):
    acc = er.blank_acc()
    # true pnl is 0 (flat path); claim a 320 dollar error on BOTH rows.
    er.accumulate([_row(reason, -320.0)], _mk_fetch(path), acc)
    res[reason] = (acc["control_n"], acc["recon_fail"], dict(acc["control_na"]))

n20, f20, na20 = res["hard_stop_20% pnl=-24.0%"]
n40, f40, na40 = res["hard_stop_40% pnl=-44.0%"]
ck("C5a", n20 == 1 and n40 == 1,
   f"both rows were APPLIED to the control (not skipped): n20={n20} n40={n40} na={na20}/{na40}")
ck("C5", (n20 == n40 == 1) and f20 == f40,
   f"SAME error, SAME entry cost, different stop -> SAME verdict "
   f"(20%:{f20} 40%:{f40}, applied {n20}/{n40}) — the band must not scale "
   f"with the rule under test. CANNOT pass vacuously: requires n==1 on both.")

# ------------------------------------------------------------------------- C6
acc = er.blank_acc()
er.accumulate([_row("orb_trail_stop pnl=5.0%", -9999.0)], _mk_fetch(path), acc)
ck("C6", acc["control_n"] == 0 and acc["recon_fail"] == 0
   and acc["control_na"].get("orb_trail_stop") == 1,
   f"a NOT-APPLICABLE row is neither applied nor failed, and is named: "
   f"n={acc['control_n']} fail={acc['recon_fail']} na={dict(acc['control_na'])}")

# ------------------------------------------------------------------------- C7
acc = er.blank_acc()
er.accumulate([_row("orb_trail_stop pnl=5.0%", -10.0)], _mk_fetch(path), acc)
import io
import contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    er.render(acc)
out = buf.getvalue()
ck("C7", "THE CONTROL APPLIED TO NOTHING" in out and "UNVERIFIED" in out,
   "a control that applied to ZERO rows says so loudly — '0 failed' out of 0 "
   "applied is the most convincing possible zero and means nothing")
ck("C7b", "orb_trail_stop" in out,
   "the NOT APPLICABLE tally is printed by name, not swallowed")

# ------------------------------------------------------------------- C8
# 🔴 THE FLIP MUST NOT TOUCH A MULTI-LEG SPREAD. `short_symbol` is -1 and
# `long_symbol` is +1, so a credit vertical's combo is `long - short` — MINUS
# the spread's value — which is ALREADY favourable-up for a credit seller.
# r390's own first cut applied `flip = -1` on top and inverted every credit
# spread; measured NVDA 2026-09-17 replayed +55 against pnl_usd -55.
# ⚠️ AND IT WAS ACCIDENTALLY CORRECT BEFORE THE REWIRE, because the flag had
# no writer and flip was always +1 — so the fix is what broke it, and a gate
# that only checked "is the resolver wired" would have called that a success.
_credit_spread = {"strategy": "SweepCreditSpread", "credit_received": 0.73,
                  "short_symbol": "NVDA  260918C00180000",
                  "long_symbol": "NVDA  260918C00185000"}
legs, why = er.legs_of(_credit_spread)
# ⚠️ PER LEG, NOT SORTED. The first cut of this check compared a SORTED sign
# list, and [-1, 1] is the same list whichever leg carries which — so it
# passed the very regression it was written for. Mutation G proved it: the
# flip was reapplied to spreads and C8 stayed GREEN. The assertion has to name
# WHICH symbol carries WHICH sign.
_by = {sym: sg for sym, sg in (legs or [])}
_short_leg = er.streamer_symbol(_credit_spread["short_symbol"])
_long_leg = er.streamer_symbol(_credit_spread["long_symbol"])
ck("C8", legs is not None and _by.get(_short_leg) == -1 and _by.get(_long_leg) == 1,
   f"a credit VERTICAL keeps its structural orientation — the SHORT leg -1 and "
   f"the LONG leg +1, not flipped: short={_by.get(_short_leg)} "
   f"long={_by.get(_long_leg)} {why}")

# the single-leg fallback is the one place the flip is real.
_short_single = {"strategy": "X", "credit_received": 1.20,
                 "option_symbol": "NVDA  260918C00180000"}
legs_s, _ = er.legs_of(_short_single)
_long_single = {"strategy": "ORBStrategy", "credit_received": 0.0,
                "option_symbol": "NVDA  260918C00180000"}
legs_l, _ = er.legs_of(_long_single)
ck("C8b", legs_s and legs_l and legs_s[0][1] == -1 and legs_l[0][1] == 1,
   f"a SHORT single leg IS flipped and a long one is not: "
   f"short={legs_s[0][1] if legs_s else None} long={legs_l[0][1] if legs_l else None}")

ck("C8c", er.legs_of({"strategy": "GEXPinButterfly", "lower_symbol": "A 260918C00100000",
                      "upper_symbol": "A 260918C00110000",
                      "center_symbol": "A 260918C00105000"})[0] is not None
   and sorted(sg for _s, sg in er.legs_of(
       {"strategy": "GEXPinButterfly", "lower_symbol": "A 260918C00100000",
        "upper_symbol": "A 260918C00110000",
        "center_symbol": "A 260918C00105000"})[0]) == [-2, 1, 1],
   "the butterfly stays 1/2/1 with the centre short TWO, unflipped")

print()
if FAILS:
    print(f"FAILED: {', '.join(FAILS)}")
    sys.exit(1)
print(f"ALL PASS ({len(RAN)})")
