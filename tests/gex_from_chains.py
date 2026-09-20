#!/usr/bin/env python3
"""
tests/gex_from_chains.py  v2.0
v2.0  2026-09-19  r391 / GEX.1 — 🔴 IT READ A DIRECTORY FROM ANOTHER MACHINE,
      FOUND NOTHING, AND CALLED THE NOTHING A RESULT.
      `ROOT` defaulted to `/home/claude/cc`, which does not exist on control.
      So `snapshots()` globbed an absent tree, returned `[]` in silence, and
      the report printed — verbatim —
        "NO GAMMA FLIP FOUND IN ANY SNAPSHOT — there is no pin on this tape by
         this definition. ... and that is a REAL ANSWER, NOT A MISSING ONE."
      on ZERO loaded snapshots, exit code 0.
      🔑 THAT SENTENCE IS r39 EXACTLY INVERTED. The tool asserted its own
      absence was the tape's answer, which is the one thing r39 forbids, and
      it is the identical failure `exit_replay` carried for its whole life
      (RPL.1: "quote_series needs its first live sessions" printed while the
      quotes sat in the bucket). MEASURED 2026-09-19: `snapshots()` -> 0,
      rc=0, and a confident five-line conclusion underneath it.
      ⚠️ AND IT WAS ABOUT TO BE LOAD-BEARING. The operator's standing prior is
      that gamma or a derivative does the heavy lifting on ORB, so this was
      the instrument his next hypothesis would have leaned on — the third
      ungated analysis tool in one day found returning confident nothing,
      which is [[CHK.8]] measured rather than argued.
      FIX: input comes from the WAREHOUSE through `warehouse_source`, the same
      lineage every other reader uses; an empty load REFUSES BY NAME and exits
      non-zero; and the conclusion block cannot be reached on an empty set.

REAL GEX FROM THE WAREHOUSE CHAINS — no stub, no proxy.

Input: raw/chain_snapshots/dt=<date>/sym=<symbol>/ via warehouse_source.

⚠️ WHAT IS AND IS NOT REAL HERE
  · `gamma` and `oi` ARE POPULATED — verified: 123/222 contracts carry
    non-zero gamma, 159/222 carry non-zero OI (max 7,326). So dealer gamma
    is computable from this data rather than assumed.
  · ⚠️ `vol` IS ZERO ON ALL 222 CONTRACTS. Anything keyed on contract volume
    is DEAD on this payload and must not be silently substituted.
  · ⚠️ THE DEALER SIGN CONVENTION IS AN ASSUMPTION, NOT A MEASUREMENT.
    Standard practice is dealers long calls / short puts, so
    GEX = gamma*OI*(+1 for calls, -1 for puts). That convention is NOT
    verified against this fleet's own definition and the pin location
    depends on it. Marked ⟨ASSUMPTION⟩ everywhere it matters.

GEX per strike = gamma × OI × 100 × spot² × 0.01, signed by the convention
above. The PIN is the strike where cumulative signed gamma flips — the level
dealer hedging pushes price toward.
"""
from __future__ import annotations

import glob
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))


def snapshots(date, symbol):
    """Chain snapshots for one symbol-session, or (None, reason) — NEVER [].

    🔴 THE RETURN CONTRACT IS THE FIX. v1.0 returned a bare list, so "nothing
    was there" and "nothing came back" were the same value and the caller
    could not tell them apart. An empty load now comes back as `None` with a
    NAMED reason, which is the only shape that cannot be mistaken for a tape
    with no pin in it.
    """
    import warehouse_source as ws
    meta = ws.Meta(f"chain_snapshots {date} {symbol}")
    out = []
    try:
        for env in ws._envelopes(ws.client(), "chain_snapshots", [date],
                                 meta, [symbol]):
            r = env.get("record")
            r = json.loads(r) if isinstance(r, str) else r
            if isinstance(r, dict) and r.get("event") == "chain_snapshot":
                out.append(r)
    except Exception as exc:                                    # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"
    if getattr(meta, "error", None):
        return None, str(meta.error)
    if not out:
        return None, (f"no chain_snapshots for {symbol} on {date} — this is "
                      f"the TOOL's gap, not the tape's (r39)")
    out.sort(key=lambda r: str(r.get("ts_et") or ""))
    return out, ""
    out.sort(key=lambda r: r["ts_et"])
    return out


def gex_profile(snap):
    """Signed dealer gamma per strike. ⟨ASSUMPTION⟩ long calls / short puts."""
    spot = float(snap["underlying"])
    per = defaultdict(float)
    for c in snap["contracts"]:
        g, oi = float(c.get("gamma") or 0), float(c.get("oi") or 0)
        if g <= 0 or oi <= 0:
            continue
        sign = 1.0 if c["type"] == "C" else -1.0
        per[float(c["strike"])] += sign * g * oi * 100 * spot * spot * 0.01
    return spot, dict(per)


def pin_from(per, spot):
    """The strike where cumulative signed gamma crosses zero — the flip.

    ⚠️ If gamma never changes sign the flip does not exist and this returns
    None rather than the nearest strike. A pin that is really 'no pin' is
    exactly the kind of clean-looking wrong answer this project exists to
    prevent."""
    if not per:
        return None, 0.0
    ks = sorted(per)
    cum, prev = 0.0, None
    for k in ks:
        cum += per[k]
        if prev is not None and (prev < 0 <= cum or prev > 0 >= cum):
            return k, cum
        prev = cum
    return None, cum


def run(date: str, symbol: str) -> int:
    snaps, why = snapshots(date, symbol)
    # 🔴 THE REFUSAL COMES FIRST AND EXITS. v1.0 fell straight through an empty
    # list into the conclusion block and declared "no pin on this tape ... a
    # REAL answer, not a missing one" having loaded NOTHING. A report that can
    # reach its own conclusion on an empty input is not a report.
    if snaps is None:
        print(f"\n  ⚠️ REFUSED: {why}")
        print("  Nothing is concluded from an empty load — r39: a tool-caused "
              "absence must not wear the costume of a null.")
        return 1
    print("=" * 74)
    print(f"  {symbol} {date} · {len(snaps)} chain snapshot(s) · expiry "
          f"{snaps[0].get('expiry', '?')}")
    print("=" * 74)
    print(f"\n  {'TIME':>8}  {'SPOT':>8}  {'PIN':>8}  {'NET GEX ($M)':>13}  "
          f"{'|GEX| TOP STRIKE':>16}")
    rows = []
    for sn in snaps:
        spot, per = gex_profile(sn)
        pin, _cum = pin_from(per, spot)
        net = sum(per.values()) / 1e6
        top = max(per, key=lambda k: abs(per[k])) if per else None
        rows.append((str(sn.get("ts_et"))[11:16], spot, pin, net, top))
    for t, spot, pin, net, top in rows[::6]:
        print(f"  {t:>8}  {spot:8.2f}  {(f'{pin:.0f}' if pin else '   none'):>8}  "
              f"{net:13.1f}  {(f'{top:.0f}' if top else '-'):>16}")
    print(f"\n{'='*74}\n  WHAT THIS SAYS\n{'='*74}")
    print("  ⚠️ ⟨ASSUMPTION⟩ dealer sign convention (long calls / short puts) is "
          "NOT verified\n     against this fleet's own definition. The pin "
          "location depends on it.")
    pins = [p for _, _, p, _, _ in rows if p]
    if pins:
        from collections import Counter
        c = Counter(pins)
        print(f"  Pin located in {len(pins)}/{len(rows)} snapshot(s).")
        print(f"  Most common pin strikes: "
              f"{', '.join(f'{k:.0f} ({v}x)' for k, v in c.most_common(4))}")
    else:
        # ⚠️ REACHABLE ONLY WITH SNAPSHOTS IN HAND. The count is printed beside
        # the claim so "no pin" can never again be read without the n it rests on.
        print(f"  NO GAMMA FLIP IN ANY OF {len(rows)} LOADED SNAPSHOT(S) — no pin "
              f"on this tape\n  by this definition. A butterfly plan declared "
              f"here would have no anchor.")
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-09-18")
    ap.add_argument("--symbol", default="AMD")
    a = ap.parse_args()
    print(__doc__)
    sys.exit(run(a.date, a.symbol))
