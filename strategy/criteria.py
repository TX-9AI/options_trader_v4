"""
strategy/criteria.py  v1.0  (2026-08-25)

EVERY STRICT AND RELAXED CRITERION, IN ONE FILE.

🔴 OPERATOR, 2026-08-25: *"All of our relaxed & strict criteria could live in 1
file. Not in the strategy, not in the plan. But a separate file that toggles
with the relaxed entry flag & unless already specified, it 'mutes' the r-value
rejection but everything else stays the same. On 'strict' the r-value must
clear the hurdle. Remove the relaxed reference out of the strategies and
plans."*

WHY THIS IS THE RIGHT SHAPE: before this file, answering "what does relaxed
actually change?" meant reading `relaxed.widen()` call sites scattered across
five strategy files. The answer to that question is now one screen.

════════════════════════════════════════════════════════════════════════════
WHAT RELAXED IS FOR — and it is NOT loose entries
════════════════════════════════════════════════════════════════════════════
🔴 OPERATOR, 2026-08-25, and this is the governing statement:
*"The relaxed sample will exercise our stops. Which in my opinion are more
important at this phase than entry price & timing. A good stop placement is
the difference between a modest loss & a catastrophic one."*

So relaxed exists to GENERATE TRADES FOR THE EXITS TO WORK ON. The entries are
knowingly mediocre; that is the point, not a side effect. Measured on
2026-08-25, the exits are earning it: `orb_structure_stop` capped five TSLA
losses between -7.3% and -18.4% of premium, against the OLD engine's
`hard_stop_41%` at -40.6% / -$645 on the same box. Roughly half the damage.
⚠️ NOT YET ESTABLISHED: that the stop CAUSED the tight band. That needs the
premium path from `quote_series` replayed through `exit_replay`; a trade that
stops at -17% might have recovered. Tight is not the same as proven.

════════════════════════════════════════════════════════════════════════════
THE ONE THING RELAXED CHANGES BY DEFAULT
════════════════════════════════════════════════════════════════════════════
**IT MUTES THE R-VALUE REJECTION. NOTHING ELSE, UNLESS NAMED BELOW.**

⚠️ BE CLEAR ABOUT WHAT THAT ADMITS. Muting R lets through trades that are
KNOWN UNPROFITABLE BY THEIR OWN ARITHMETIC. Today's CVX loop is exactly that
population: twelve put spreads at R 0.19, needing an 84% win rate to break
even, every one stopped out for about -$400. Under strict, the R gate refuses
all of them before any other machinery matters. Under relaxed they fire, ON
PURPOSE, so the stops get exercised.

⚠️ CONSEQUENCE THAT MUST NOT BE FORGOTTEN AT FIT TIME: a relaxed session
carries NO R EVIDENCE, because R was not allowed to decide anything. **The R
floor can therefore only ever be fitted from STRICT sessions.** Pooling the two
would fit a threshold on data where the threshold was disabled — the same
class of error as validating a tight threshold on a relaxed sample, which
`relaxed.py` already forbids.

════════════════════════════════════════════════════════════════════════════
WHAT RELAXED MAY NEVER TOUCH
════════════════════════════════════════════════════════════════════════════
🔴 **A TRIGGER OR AN INVALIDATION IS A STRUCTURAL PRICE AND IS NEVER WIDENED.**
Loosening evidence produces MORE PLANS of the same trade. Loosening a trigger
produces A DIFFERENT TRADE WEARING THE SAME NAME, and the two populations stop
being comparable — which destroys the only thing the relaxed/strict split is
for. `assert_not_structural()` below enforces it and `check_criteria.py` fails
the build if any structural constant is routed through this file.

⚠️ AND THE TAGGING STAYS WHERE IT IS. `relaxed.tag(sig)` stamps
`relaxed_entry=1` on the trade record, and `entry_engine` / `trade_logger`
read it. That is the POPULATION LABEL, not a criterion — purging it alongside
the thresholds would make relaxed and strict trades indistinguishable forever,
which is the one property this whole design depends on. Thresholds moved here;
tagging did not move.
"""
from __future__ import annotations

import logging
import os
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# ── the switch ──────────────────────────────────────────────────────────
# 🔴 THIS FILE OWNS NO FLAG. It ROUTES through `relaxed.is_allowed()`, which
# already exists and already carries the guard that matters:
#
#     RELAXED IS REFUSED ON A LIVE BOX, whatever the env var says, and
#     `is_live()` FAILS CLOSED — an unreadable flag reads as LIVE.
#
# A first draft of this file read its own `OT_RELAXED_ENTRIES`. That would have
# been a SECOND SOURCE OF TRUTH for the mode, silently bypassing the live
# guard — the exact failure `relaxed.is_live()` documents, where a first draft
# satisfied a guard from a repo default nobody asserted. Operator, 2026-08-25:
# *"Let the flag get set by the new process. Just re-route it."*
#
# ⚠️ READ PER CALL, NOT CACHED AT IMPORT. `configure.sh` may set the flag after
# this module is first imported, and a module-level constant would freeze the
# mode at whatever it was when the first import happened.
def relaxed_active() -> bool:
    """True when relaxed criteria apply. Delegates — never re-decides."""
    try:
        from strategy import relaxed
        return bool(relaxed.is_allowed())
    except Exception:                                          # noqa: BLE001
        # ⚠️ FAIL CLOSED. If the mode cannot be established, STRICT applies —
        # the R hurdle stays up. An unreadable flag must never mute a gate.
        return False


def mode() -> str:
    return "RELAXED" if relaxed_active() else "STRICT"


# ── the R hurdle: the ONLY thing relaxed changes by default ─────────────
R_FLOOR = float(os.environ.get("OT_PLAN_R_FLOOR", "1.00"))


def r_hurdle() -> Optional[float]:
    """The R a plan must clear, or None when the hurdle is MUTED.

    ⚠️ None MEANS MUTED, NOT ZERO. A floor of 0.0 would still reject a
    negative-R plan and would look like a decision nobody made; None says
    plainly that R did not participate. Same discipline second_order.py uses
    for an unmeasurable greek, and for the same reason: the fit must be able
    to tell "did not gate" from "gated at zero".
    """
    return None if relaxed_active() else R_FLOOR


def r_verdict(r: Optional[float]) -> Tuple[str, str]:
    """(verdict, reason) for a plan's R. The single decision point."""
    h = r_hurdle()
    if h is None:
        return "MUTED", ("R hurdle MUTED (relaxed) — the trade is taken to "
                         "exercise the exits, not because it pays")
    if r is None:
        return "FAIL", "R not measurable — a missing input is not a safe trade"
    if r < h:
        return "FAIL", f"R {r:.2f} below {h:.2f}"
    return "PASS", f"R {r:.2f} clears {h:.2f}"


# ── WA §36 GATE CATEGORIES ──────────────────────────────────────────────
# ⚠️ REQUIRED, AND `tests/check_gates.py` ENFORCES IT. This file lives in
# strategy/ and mediates relaxable constants, so it owes the same declaration
# every strategy owes: name each gate and say what KIND it is.
#
#   SELECTION     — a measured preference. Loosening gives a WORSE EXAMPLE OF
#                   THE SAME TRADE, which is exactly what a debug session
#                   wants. These are the only things relaxed may touch.
#   FOUNDATIONAL  — relax one and it stops being the trade at all.
#   FEASIBILITY   — physical possibility. Loosening buys nothing because the
#                   trade cannot be executed anyway.
#
# 🔴 `R_FLOOR` IS FOUNDATIONAL, AND IT IS THE INTERESTING CASE. A trade that
# cannot clear 1:1 is not a worse example of the same trade — by its own
# arithmetic it is a losing trade. Muting it is therefore NOT a normal
# relaxation, and this file says so rather than filing it as SELECTION to make
# the categories tidy. It is muted DELIBERATELY and ONLY to generate positions
# for the exits to work on (see the header). Filing it as SELECTION would have
# been the lie that let a future reader loosen it for the ordinary reason.
GATES = {
    "R_FLOOR":                "FOUNDATIONAL",
    "sweep_max_age_bars":     "SELECTION",
    "sweep_pierce_ceiling":   "SELECTION",
    "runaway_cutoff_et":      "SELECTION",
    "butterfly_reach_max":    "SELECTION",
    "level_hold_min":         "SELECTION",
}


# ── everything else, named explicitly ───────────────────────────────────
# ⚠️ A CRITERION THAT DIFFERS BETWEEN MODES MUST APPEAR HERE, WITH BOTH
# VALUES SIDE BY SIDE. That is the whole point of the file: "what does relaxed
# change?" is answerable by reading one screen instead of five strategies.
# Anything absent from this table is IDENTICAL in both modes.
#
#   name                       STRICT          RELAXED
CRITERIA = {
    "sweep_max_age_bars":     (8,              24),      # SELECTION
    "sweep_pierce_ceiling":   (0.25,           0.75),    # SELECTION
    "runaway_cutoff_et":      ("11:30",        "14:00"), # SELECTION
    "butterfly_reach_max":    (1.00,           1.50),    # SELECTION
    "level_hold_min":         (0.75,           0.50),    # SELECTION
}

# ⚠️ STRUCTURAL PRICES. Never widened, never routed through here, in EITHER
# mode. Named so the checker can assert their absence from CRITERIA.
STRUCTURAL = (
    "trigger_price", "invalidation", "orb_high", "orb_low",
    "pool_price", "sweep_price", "gex_pin", "short_strike",
)


def get(name: str, default=None):
    """The value of `name` for the CURRENT mode."""
    if name in STRUCTURAL:
        raise ValueError(
            f"'{name}' is a STRUCTURAL price and must never be mode-dependent. "
            "Loosening evidence produces more plans of the same trade; "
            "loosening a trigger produces a different trade wearing the same "
            "name, and the two populations stop being comparable.")
    pair = CRITERIA.get(name)
    if pair is None:
        return default
    return pair[1] if relaxed_active() else pair[0]


def assert_not_structural() -> None:
    """Refuse to start if a structural price ever enters the table."""
    bad = [k for k in CRITERIA if k in STRUCTURAL]
    if bad:
        raise ValueError(f"STRUCTURAL constants in CRITERIA: {bad}")


def describe() -> str:
    """One line per differing criterion — for the log and the status board."""
    _r = relaxed_active()
    rows = [f"{k}: {v[1] if _r else v[0]} "
            f"(strict {v[0]} / relaxed {v[1]})" for k, v in sorted(CRITERIA.items())]
    h = r_hurdle()
    rows.insert(0, f"R hurdle: {'MUTED' if h is None else f'{h:.2f}'}")
    return f"[criteria] MODE={mode()} · " + " · ".join(rows)


assert_not_structural()
# ⚠️ NOT LOGGED AT IMPORT. The mode is not knowable yet if configure.sh sets
# the flag after this module loads. main.py calls describe() once the process
# is configured, alongside relaxed.announce_once().
