#!/usr/bin/env python3
# options-trader-v4/tests/check_doc_menu_refs.py — v1.0
# v1.0 (2026-09-20) — r409 / DOC.27. THE ROUTING SECTION NAMED 53 MENU NUMBERS
#   AND EVERY ONE OF THEM WAS WRONG.
#   WORKING_AGREEMENT §13 is the section whose entire job is to route a reader
#   to an existing devtools item instead of writing a one-off. It carried a
#   numbered inventory taken 2026-07-24. Measured at r409 against the live
#   render (devtools v1.63, 78 items): **53 of 53 numbered citations wrong,
#   ZERO correct**, and NINE of the items it names do not exist at all
#   (`Pull trades.db`, `Pull OHLC for a day`, `view the diary`, the four
#   regime-replay items, `full spool-up`, `reset mock`).
#   🔑 THE NUMBERS COULD NOT HAVE BEEN RIGHT, AND THE REPO ALREADY KNEW.
#   `menu_render()` assigns them from a RENDER-TIME LOOP COUNTER over the
#   `MENU` array and stores them nowhere — read at source, menu_registry.sh.
#   [[C.15]] states it: *"nothing may be tied to the number"*, and WA §15 and
#   §17 each say CITE BY LABEL after being bitten. §13 was the one routing
#   document nobody applied the rule to.
#   ⚠️ SO THE FIX IS NOT RENUMBERING — a renumbered list is wrong again on the
#   next land. The numbers go, the LABELS stay, and the section names the
#   command that prints the live list.
#
#   SCOPING (§20). D1 reads §13's BODY ONLY. The CHANGELOG at the foot of the
#   working agreement must describe this removal and §5 requires it to name
#   what it removed, so a file-wide digit canary would fire on the very
#   documentation the version discipline demands — §20's collision exactly,
#   and the shape that trains a reader to loosen a check until it misses the
#   real regression. D3 likewise anchors on a VERSION DISAGREEMENT inside one
#   file rather than on the token `v3`, because this repo carries 81
#   legitimate "Ported from options_trader_v3" provenance lines (§32, r407's
#   I1-I4 record the same trap).
"""Gate: no document routes by a menu NUMBER, and install.sh does not
disagree with itself about its own version.

D1   WA §13 carries no numbered devtools-item citation.
D2   WA §13 states the cite-by-LABEL rule.
D3   install.sh's prose self-description agrees with its operative banner.
D4   WA §13 names the live source a reader can actually run.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WA = os.path.join(ROOT, "docs", "WORKING_AGREEMENT.md")
INSTALL = os.path.join(ROOT, "install.sh")

rc = 0


def report(tag, ok, msg):
    global rc
    print(f"{'PASS' if ok else 'FAIL'} {tag}: {msg}")
    if not ok:
        rc = 1


def section_13(text):
    """§13's body — from its heading to the next top-level heading."""
    m = re.search(r"\n## 13\..*?(?=\n## \d)", text, re.S)
    return m.group(0) if m else None


def main():
    global rc
    if not os.path.exists(WA):
        report("D1", False, f"WORKING_AGREEMENT.md not found at {WA}")
        return 1
    wa = open(WA, encoding="utf-8", errors="replace").read()
    body = section_13(wa)
    if body is None:
        report("D1", False, "could not locate §13 in WORKING_AGREEMENT.md")
        return 1

    # ── D1 — no numbered menu citations in the routing section ─────────────
    # The SHAPE of a citation in this section is a bare 1-2 digit number at a
    # list position — line start, or after a `·` / `|` separator — followed by
    # a word. That is how every one of the 53 was written. Anchored on the
    # shape rather than on any label, so a re-introduced list in any wording
    # is caught.
    cites = []
    for ln in body.splitlines():
        for m in re.finditer(
                r"(?:^|[·|])\s*\*{0,2}(\d{1,2})\s+(?=[A-Za-z`])", ln):
            cites.append((m.group(1), ln.strip()[:70]))
    report("D1", not cites,
           "no numbered menu citations in §13"
           if not cites else
           f"{len(cites)} numbered citation(s) in §13, e.g. "
           + "; ".join(f"{n} -> {t}" for n, t in cites[:3]))

    # ── D2 — the section states the rule that replaces them ────────────────
    has_rule = bool(re.search(r"by\s+\*{0,2}LABEL\*{0,2}", body, re.I))
    report("D2", has_rule,
           "§13 states the cite-by-LABEL rule"
           if has_rule else
           "§13 does not tell the reader to cite by LABEL (C.15)")

    # ── D4 — and names a command that prints the live list ─────────────────
    has_src = ("menu_extract" in body) or ("menu_render" in body)
    report("D4", has_src,
           "§13 names the live source (menu_extract/menu_render)"
           if has_src else
           "§13 names no runnable source for the current item list")

    # ── D3 — install.sh must not disagree with itself ──────────────────────
    if not os.path.exists(INSTALL):
        report("D3", False, f"install.sh not found at {INSTALL}")
        return rc
    ins = open(INSTALL, encoding="utf-8", errors="replace").read()
    # The OPERATIVE banner is the one the running installer echoes.
    ban = re.search(r'echo\s+".*?options_trader\s+v(\d+)\.(\d+)', ins)
    if not ban:
        report("D3", False, "no operative banner found in install.sh")
        return rc
    ban_major = ban.group(1)
    # Any OTHER self-description of this file's own version.
    # 🔑 PROVENANCE IS PERMITTED; AN UNMARKED SELF-DESCRIPTION IS NOT.
    # This file deliberately preserves its inherited v3 header (§32, r240's
    # precedent) and the repo carries 81 "Ported from options_trader_v3"
    # lines that must survive — so keying on the token `v3` would fire on the
    # record the doctrine exists to keep (§20). A candidate is EXCUSED when a
    # provenance marker stands on it or in the eight lines above it, which is
    # what makes the claim honest to a reader rather than merely absent.
    MARK = re.compile(r"INHERITED|PROVENANCE|Ported from|superseded|⬛", re.I)
    lines = ins.splitlines()  # noqa: F841 - kept for line numbering
    bad = []
    for i, ln in enumerate(lines, 1):
        if "echo" in ln:
            continue
        m = re.search(r"options_trader\s+v(\d+)\.(\d+)", ln)
        if not m or m.group(1) == ban_major:
            continue
        # 🔴 THE MARKER MUST STAND ON THIS LINE. An earlier cut of D3 scanned
        # the eight lines above and was VACUOUSLY GREEN AT HEAD — the file's
        # own "INHERITED DOCTRINE" block header sits in that window and
        # satisfied it, so the check passed on the unmarked line it was
        # written to catch. Proven by mutation: stripping the marker left it
        # green. C.23's shape. A reader greps ONE line, so the disclaimer
        # belongs on that line and nowhere else.
        if MARK.search(ln):
            continue
        bad.append((i, m.group(0), ln.strip()[:60]))
    report("D3", not bad,
           f"install.sh self-description agrees with its banner (v{ban_major}.x)"
           if not bad else
           f"banner says v{ban_major}.x but UNMARKED line(s) "
           + "; ".join(f"{i}: {v!r}" for i, v, _ in bad)
           + " disagree — mark them as provenance or correct them")
    return rc


if __name__ == "__main__":
    sys.exit(main())
