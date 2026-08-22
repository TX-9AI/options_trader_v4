"""
derived/base.py  v4.0
The contract every derived engine implements.

v4.0  2026-08-22  Built with the manifold. See docs/DERIVED_STORES.md.

    raw port -> home -> DERIVER -> derived home -> ctx -> engine

ONE ENGINE PER STORE. Each subclass owns exactly one table in
`data/derived_store.py` end to end: it reads the raw it needs, computes, and
writes its own home. Nothing else writes that table.

⚠️ WHY ONE-PER-STORE AND NOT ONE BIG DERIVER. A single module writing five
tables is a single point whose failure takes all five with it, and a single
place where "did the fork deriver run?" and "did the surface deriver run?"
become the same question. Separate engines fail separately and report
separately — which is the only way `manifold_status` can name WHICH derived
port went dark.

🔴 DERIVERS ARE CONTRIBUTORS, NEVER GATES. Operator's ruling, 2026-08-22.
Derived values INFORM; they never authorise. This class enforces it
structurally: `run()` is wrapped so a subclass CANNOT raise into the caller,
no matter what it does internally. A missing derived value is not an error —
the engine trades without it.

⚠️ THE WRAP IS THE POINT, NOT A COURTESY. The regime gate was a value nothing
computed that became a veto and stopped the fleet for a whole session. A
deriver that can throw into the tick loop is the same shape: an observation
becoming an authority. It is made impossible here rather than promised in a
comment.

⚠️ ABSENCE IS RECORDED AS ABSENCE. Subclasses return None or an empty list
when they cannot measure. They NEVER substitute 0.0. A measured zero and an
unmeasurable value are different facts (VW.1, the gap prior_dir, the sweep
score — all silent zeros that read as measurements).
"""

from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class DerivedEngine:
    """Base class. Subclasses implement `derive(ctx)` and set `name`/`table`."""

    name: str = "base"
    table: str = ""
    # Minimum seconds between runs. A deriver that scans backward does not need
    # to run every tick; one that tracks state does.
    min_interval_s: float = 0.0

    def __init__(self, store=None):
        self._store = store
        self._last_run: float = 0.0
        self._last_rows: int = 0
        self._last_error: Optional[str] = None
        self._runs: int = 0
        self._failures: int = 0

    # ── subclass surface ────────────────────────────────────────────────
    def derive(self, ctx: dict) -> int:
        """Compute and persist. Return rows written. Never called directly."""
        raise NotImplementedError

    # ── driver surface ──────────────────────────────────────────────────
    def run(self, ctx: dict) -> int:
        """Drive one cycle. NEVER raises. Returns rows written (0 on failure).

        ⚠️ THE BARE `except Exception` IS DELIBERATE AND IS THE CONTRACT.
        Narrowing it to expected exception types would let an unexpected one
        through into the tick loop, which is exactly the failure this class
        exists to make impossible.
        """
        now = time.time()
        if self.min_interval_s and (now - self._last_run) < self.min_interval_s:
            return 0
        self._last_run = now
        self._runs += 1
        try:
            n = int(self.derive(ctx) or 0)
            self._last_rows, self._last_error = n, None
            return n
        except Exception as exc:                                # noqa: BLE001
            self._failures += 1
            self._last_error = f"{type(exc).__name__}: {exc}"
            logger.warning("[derived:%s] %s — this derived value is absent "
                           "this cycle; nothing downstream is blocked",
                           self.name, self._last_error)
            self._last_rows = 0
            return 0

    def status(self) -> dict:
        """What this engine has actually been doing. For manifold_status."""
        return {"name": self.name, "table": self.table,
                "runs": self._runs, "failures": self._failures,
                "last_rows": self._last_rows,
                "last_run_age_s": (round(time.time() - self._last_run)
                                   if self._last_run else None),
                "last_error": self._last_error}


def run_all(engines, ctx: dict) -> dict:
    """Drive every engine once. Returns {name: rows}. NEVER raises.

    ⚠️ ONE ENGINE'S FAILURE MUST NOT SKIP THE NEXT. Each `run()` is already
    wrapped, but the loop itself is guarded too: a subclass that somehow breaks
    `run` must not stop the engines after it in the list.
    """
    out = {}
    for e in engines:
        try:
            out[getattr(e, "name", "?")] = e.run(ctx)
        except Exception as exc:                                # noqa: BLE001
            logger.warning("[derived] engine %r broke its own wrapper: %s",
                           getattr(e, "name", e), exc)
            out[getattr(e, "name", "?")] = 0
    return out
