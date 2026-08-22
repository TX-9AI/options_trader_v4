"""
derived/character_engine.py  v4.0
Owns `character_ledger`. Transitions, not per-tick values.

v4.0  2026-08-25  See analysis/character.py for the measurement and the
operator's rulings. This module only decides WHEN a change is real enough to
record, and writes it down.

🔴 THE ACCEPTANCE GATE IS THE OPERATOR'S 20-YEAR PRIOR: **1-3 character changes
per symbol-day.** The retired L2 engine produced ~20/symbol-day, and that
10-20x gap against the same prior is what made its churn visible at all. If
this deriver yields fifteen a day the design is wrong no matter how sensible
the maths looks — check the count before trusting anything downstream.

⚠️ TRANSITIONS ARE THE OBJECT, NOT SAMPLES. A per-tick character value would
be ~1,560 rows per symbol-day saying almost nothing. What is worth knowing is
that the tape CHANGED, when, and what it changed from. The raw axes stay at
full resolution in the row so a study can see how close the call was.

⚠️ A CHARACTER THAT HELD ALL SESSION AND ONE THAT FLIPPED SIX TIMES ARE
DIFFERENT SESSIONS — operator's point, and the reason the ledger stores
`held_s` on the row that closes.

⚠️ ADX AND ATR ARE RECORDED PARALLEL, NOT FED IN. See analysis/character.py.
They are on the row so a study can ask whether they agree; blending them would
make agreement true by construction.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from derived.base import DerivedEngine

logger = logging.getLogger(__name__)

# Vol baseline window: how many prior readings define "normal for this symbol".
BASELINE_N = 40


def _f(v) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


class CharacterEngine(DerivedEngine):
    name = "character"
    table = "character_ledger"
    min_interval_s = 15.0

    def __init__(self, store=None, symbol: str = ""):
        super().__init__(store)
        self.symbol = symbol
        self._state: Optional[str] = None
        self._since: float = 0.0
        self._row_id: Optional[int] = None
        self._vol_hist: list = []
        self._made = False

    def _ensure(self):
        if self._made or self._store is None:
            return
        try:
            self._store.conn.execute("""
                CREATE TABLE IF NOT EXISTS character_ledger (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol      TEXT NOT NULL,
                    character   TEXT NOT NULL,
                    entered_ts  REAL NOT NULL,
                    exited_ts   REAL,
                    held_s      REAL,
                    from_character TEXT,
                    -- the axes AT THE MOMENT OF THE CHANGE, full resolution
                    persistence REAL,
                    vol_ratio   REAL,
                    realised_vol_cc REAL,
                    realised_vol_parkinson REAL,
                    -- ⚠️ PARALLEL CORROBORATORS, NOT INPUTS. Recorded so a
                    -- study can ask whether they agree; feeding them in would
                    -- make agreement true by construction.
                    adx         REAL,
                    atr_normalized REAL,
                    -- ⚠️ THE OPENING GAP, ALSO PARALLEL. Operator's ruling
                    -- 2026-08-25: recorded beside the axes, never fed into
                    -- them. The temptation was real — the volatility axis is
                    -- UNMEASURABLE on the opening rows until the baseline has
                    -- 10 readings, and the gap is the one quantity fully known
                    -- at 09:30. Seeding the axis with it would have made "does
                    -- the gap predict the opening character" UNANSWERABLE,
                    -- because the answer would be built in.
                    -- ⚠️ AND THE v3 SCOPE FLAG APPLIES: a window spanning the
                    -- overnight boundary reads a large slope from the gap
                    -- ALONE, and ATR across the gap spikes. The gap must be
                    -- VISIBLE without CONTAMINATING intraday geometry — which
                    -- is the argument for its own column rather than a blend.
                    gap_pct     REAL,
                    gap_class   TEXT,
                    price       REAL
                );""")
            self._store.conn.execute(
                "CREATE INDEX IF NOT EXISTS ix_char_sym "
                "ON character_ledger(symbol, entered_ts)")
            self._made = True
        except Exception as exc:                                # noqa: BLE001
            logger.debug("character_ledger table: %s", exc)

    def current(self) -> dict:
        """What status.py reads: the live character and how long it has held."""
        if not self._state:
            return {}
        return {"character": self._state,
                "held_s": round(time.time() - self._since),
                "since": self._since}

    def recent(self, limit: int = 5) -> list:
        """The last N CHANGES with timestamps — what query.py reads."""
        if self._store is None:
            return []
        try:
            self._ensure()
            cur = self._store.conn.execute(
                "SELECT character, from_character, entered_ts, held_s,"
                " persistence, vol_ratio, gap_pct, gap_class"
                " FROM character_ledger"
                " WHERE symbol=? ORDER BY entered_ts DESC LIMIT ?",
                (self.symbol, int(limit)))
            return [{"character": r[0], "from": r[1], "at": r[2],
                     "held_s": r[3], "persistence": r[4], "vol_ratio": r[5],
                     "gap_pct": r[6], "gap_class": r[7]}
                    for r in cur.fetchall()]
        except Exception:                                       # noqa: BLE001
            return []

    def derive(self, ctx: dict) -> int:
        from analysis.character import (persistence, volatility_state,
                                        read_character, qualifies_to_displace)
        if self._store is None:
            return 0
        cc = _f(ctx.get("realised_vol_cc"))
        pk = _f(ctx.get("realised_vol_parkinson"))

        # Volatility is judged against THIS SYMBOL'S OWN recent baseline.
        # ⚠️ NOT AN ABSOLUTE THRESHOLD — see analysis/character.py. A rolling
        # median is used rather than a mean so one spike cannot redefine
        # "normal" for the rest of the session.
        if cc is not None:
            self._vol_hist.append(cc)
            if len(self._vol_hist) > BASELINE_N:
                self._vol_hist.pop(0)
        base = None
        if len(self._vol_hist) >= 10:
            s = sorted(self._vol_hist)
            base = s[len(s) // 2]

        p = persistence(cc, pk)
        vr = volatility_state(cc, base)
        challenger = read_character(p, vr)

        if not qualifies_to_displace(self._state, challenger, p, vr):
            return 0

        now = time.time()
        try:
            self._ensure()
            # Close the outgoing row so `held_s` is a fact, not a computation.
            if self._row_id is not None:
                self._store.conn.execute(
                    "UPDATE character_ledger SET exited_ts=?, held_s=?"
                    " WHERE id=?", (now, now - self._since, self._row_id))
            cur = self._store.conn.execute(
                "INSERT INTO character_ledger (symbol, character, entered_ts,"
                " from_character, persistence, vol_ratio, realised_vol_cc,"
                " realised_vol_parkinson, adx, atr_normalized, gap_pct,"
                " gap_class, price) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (self.symbol, challenger, now, self._state, p, vr, cc, pk,
                 _f(getattr(ctx.get("trend"), "primary_adx", None)),
                 _f(getattr(ctx.get("vol"), "atr_normalized", None)),
                 _f((ctx.get("gap") or {}).get("gap_pct")),
                 (ctx.get("gap") or {}).get("gap_class"),
                 _f(ctx.get("price"))))
            self._row_id = cur.lastrowid
            self._store.commit()
        except Exception as exc:                                # noqa: BLE001
            logger.debug("character write: %s", exc)
            return 0

        held = (now - self._since) / 60.0 if self._since else 0.0
        if self._state:
            logger.info("[character] %s -> %s after %.0f min "
                        "(persistence %.2f, vol %.2fx)", self._state,
                        challenger, held, p if p is not None else -1,
                        vr if vr is not None else -1)
        else:
            logger.info("[character] %s (persistence %.2f, vol %.2fx)",
                        challenger, p if p is not None else -1,
                        vr if vr is not None else -1)
        self._state, self._since = challenger, now
        return 1
