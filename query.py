"""
query.py  v4.1
v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

Ad-hoc trade and store queries.

v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

query.py — OptionsTrader Performance Dashboard
None-guard the open-position setup_score display: condor
        legs log a NULL score (delta street-sign is NULL when Greeks are
        unavailable), which crashed the dashboard with TypeError on :.2f.
        Now renders "score=n/a" instead of raising.
v3.0 — original
Fix: read INSTRUMENT from systemd env via get_runtime_env()
W/L consistency: a $0 (scratch) trade is no longer counted
        as a loss (was pnl<=0), matching status.py (pnl<0). Reconciles the
        0W/0L vs 0W/1L mismatch between the two tools on breakeven trades.
                     config.py fallback is QQQ but live bot may be configured for SPX
repo-wide v3.0 bump: Yahoo-Finance purge & data stream
        mapping optimization (all market data now flows from the single
        shared TastyTrade candle feed — see data/candle_feed.py). No logic
        change in this file.
Options-specific: strikes, premiums, delta, P&L, butterfly legs, session stats.
"""

import sqlite3
import os
import re
import sys
import subprocess
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

INSTALL_DIR = os.path.expanduser("~/options-trader")
sys.path.insert(0, INSTALL_DIR)

try:
    from config import DB_PATH
    SERVICE_NAME = "optionsbot"
except Exception:
    DB_PATH            = os.path.join(INSTALL_DIR, "trades.db")
    SERVICE_NAME       = "optionsbot"

ET  = ZoneInfo("US/Eastern")
UTC = timezone.utc


def get_runtime_env(key: str, default: str = "") -> str:
    """Read a live environment variable from the systemd service — mirrors status.py."""
    try:
        result = subprocess.run(
            ["sudo", "systemctl", "show", SERVICE_NAME, "--property=Environment"],
            capture_output=True, text=True
        )
        match = re.search(rf'{re.escape(key)}=([^ ]+)', result.stdout)
        if match:
            return match.group(1)
    except Exception:
        pass
    return os.environ.get(key, default)


# Always read instrument and mode from live systemd environment — same as status.py
INSTRUMENT    = get_runtime_env("OT_INSTRUMENT",   "QQQ")
PAPER_TRADING = get_runtime_env("OT_PAPER_TRADING", "True") != "False"
BOT_NAME      = get_runtime_env("OT_BOT_NAME",      "OptionsTrader")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def connect():
    if not os.path.exists(DB_PATH):
        print(f"\n  Database not found at {DB_PATH}")
        print("  Has the bot entered any trades yet?")
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def to_et(ts: str) -> str:
    if not ts:
        return "N/A"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(ET).strftime("%m/%d %H:%M ET")
    except Exception:
        return ts[:16]


def now_et():
    return datetime.now(ET)


def today_et_prefix():
    return now_et().strftime("%Y-%m-%d")


def pnl_str(val: float) -> str:
    if val is None:
        return "  N/A"
    return f"+${val:.2f}" if val >= 0 else f"-${abs(val):.2f}"


def pct_str(val: float) -> str:
    if val is None:
        return "  N/A"
    return f"{val:+.1%}"


def bar(pct: float, width: int = 20) -> str:
    filled = max(0, min(width, int(pct / 100 * width)))
    return "█" * filled + "░" * (width - filled)


def sep(char: str = "─", width: int = 62):
    print(char * width)


def get_service_status() -> str:
    try:
        import subprocess
        result = subprocess.run(
            ["systemctl", "is-active", SERVICE_NAME],
            capture_output=True, text=True
        )
        status = result.stdout.strip()
        return "🟢 ACTIVE" if status == "active" else f"🔴 {status.upper()}"
    except Exception:
        return "UNKNOWN"


def get_live_price() -> float | None:
    try:
        sys.path.insert(0, INSTALL_DIR)
        from data.market_data import fetch_quote
        return fetch_quote(INSTRUMENT)
    except Exception:
        return None


# ─── Sections ─────────────────────────────────────────────────────────────────

def show_header():
    mode = "📄 PAPER" if PAPER_TRADING else "🔴 LIVE"
    status = get_service_status()
    sep("═")
    print(f"  {BOT_NAME} — PERFORMANCE DASHBOARD")
    print(f"  {now_et().strftime('%Y-%m-%d %H:%M:%S ET')}")
    sep("═")
    print(f"  Service:     {status}")
    print(f"  Instrument:  {INSTRUMENT}")
    print(f"  Mode:        {mode}")
    print()


def show_open_position(conn):
    row = conn.execute(
        "SELECT * FROM trades WHERE status='open' ORDER BY entry_time DESC LIMIT 1"
    ).fetchone()

    sep("═")
    print("  OPEN POSITION")
    sep("═")

    if not row:
        print("  ⏳ No open position.")
        print()
        return

    is_bf      = bool(row["is_butterfly"])
    entry_prem = row["entry_premium"] or 0
    stop_prem  = row["stop_premium"]  or 0
    target_prem= row["target_premium"]or 0
    contracts  = row["contracts"]     or 0
    total_cost = row["total_cost"]    or 0

    # Try to get live option premium
    live_prem  = None
    live_pnl   = None
    live_pnl_pct = None
    try:
        from data.market_data import fetch_quote
        underlying = fetch_quote(INSTRUMENT)
    except Exception:
        underlying = None

    # Position description
    if is_bf:
        pos_desc = (
            f"BUTTERFLY {(row['option_side'] or '').upper()}  "
            f"{row['lower_strike']:.0f} / {row['center_strike']:.0f} / {row['upper_strike']:.0f}"
        )
    else:
        pos_desc = f"{(row['option_side'] or '').upper()}  Strike {row['strike']:.0f}"

    # Live P&L from current_premium stored by position_manager each tick
    current_prem = row["current_premium"] if row["current_premium"] else None
    live_pnl_usd = None
    live_pnl_pct = None
    if current_prem and entry_prem:
        live_pnl_usd = (current_prem - entry_prem) * contracts * 100
        live_pnl_pct = (current_prem - entry_prem) / entry_prem

    print(f"  ID:            {row['trade_id'][:8]}")
    print(f"  Position:      {pos_desc}")
    print(f"  Strategy:      {row['strategy']}  |  Setup: {row['setup_type']}")
    _score = row['setup_score']
    _score_str = f"score={_score:.2f}" if _score is not None else "score=n/a"
    print(f"  Grade:         {row['setup_grade']}  ({_score_str})")
    print(f"  Expiry:        {row['expiry']}")
    print(f"  Contracts:     {contracts}")
    print()

    print(f"  Entry Premium: ${entry_prem:.2f}/share  (${entry_prem * 100:.2f}/contract)")
    print(f"  Total Cost:    ${total_cost:.2f}")
    if current_prem:
        print(f"  Current Mark:  ${current_prem:.2f}/share  (${current_prem * 100:.2f}/contract)")
    if live_pnl_usd is not None:
        pnl_label = f"+${live_pnl_usd:.2f}" if live_pnl_usd >= 0 else f"-${abs(live_pnl_usd):.2f}"
        pct_label = pct_str(live_pnl_pct)
        print(f"  Unrealized P&L:{pnl_label}  ({pct_label})")
    print(f"  Stop Premium:  ${stop_prem:.2f}  ({pct_str((stop_prem - entry_prem) / entry_prem if entry_prem else 0)} from entry)")
    print(f"  Target:        ${target_prem:.2f}  ({pct_str((target_prem - entry_prem) / entry_prem if entry_prem else 0)} from entry)")

    if row["trail_activation"]:
        print(f"  Trail Trigger: ${row['trail_activation']:.2f}")

    print()

    # Underlying price context
    if underlying:
        print(f"  Underlying:    ${underlying:,.2f}  (live)")
    if row["underlying_entry"]:
        print(f"  Entry Spot:    ${row['underlying_entry']:,.2f}")
    if row["underlying_stop"]:
        print(f"  Spot Stop:     ${row['underlying_stop']:,.2f}")
    if row["underlying_target"]:
        print(f"  Spot Target:   ${row['underlying_target']:,.2f}")

    print()
    print(f"  VIX at Entry:  {row['vix_at_entry']:.1f}" if row["vix_at_entry"] else "  VIX at Entry:  N/A")
    print(f"  Fed Day:       {'Yes ⚠️' if row['is_fed_day'] else 'No'}")
    print(f"  Paper:         {'Yes' if row['paper_trade'] else 'No'}")
    print(f"  Entered:       {to_et(row['entry_time'])}")
    print()


def show_today(conn):
    today = today_et_prefix()
    rows = conn.execute(
        """SELECT * FROM trades
           WHERE status='closed'
           AND date(datetime(entry_time, '-4 hours')) = ?
           ORDER BY exit_time""",
        (today,)
    ).fetchall()

    sep()
    print(f"  TODAY'S TRADES  ({today} ET)")
    sep()

    if not rows:
        print("  No closed trades today.")
        print()
        return

    wins      = [r for r in rows if (r["pnl_usd"] or 0) > 0]
    losses    = [r for r in rows if (r["pnl_usd"] or 0) < 0]   # v1.2: strict; $0 is a scratch, not a loss (match status.py)
    total_pnl = sum(r["pnl_usd"] or 0 for r in rows)
    win_rate  = len(wins) / len(rows) * 100 if rows else 0
    total_cost= sum(r["total_cost"] or 0 for r in rows)
    pnl_pct   = total_pnl / total_cost * 100 if total_cost else 0

    print(f"  Trades:        {len(rows)}  ({len(wins)}W / {len(losses)}L)")
    print(f"  Win Rate:      {win_rate:.0f}%  {bar(win_rate, 15)}")
    print(f"  Net P&L:       {pnl_str(total_pnl)}  ({pnl_pct:+.1f}% of capital deployed)")
    if wins:
        print(f"  Best Trade:    {pnl_str(max(r['pnl_usd'] or 0 for r in wins))}")
    if losses:
        print(f"  Worst Trade:   {pnl_str(min(r['pnl_usd'] or 0 for r in losses))}")
    print()

    # Trade detail table
    print(f"  {'ID':<10} {'Type':<8} {'Strike':<14} {'Grade':<6} "
          f"{'Entry':>7} {'Exit':>7} {'P&L':>9} {'P&L%':>7}  Exit Reason")
    sep()
    for r in rows:
        is_bf = bool(r["is_butterfly"])
        if is_bf:
            strike_str = f"{r['center_strike']:.0f} BF"
        else:
            side = (r["option_side"] or "")[:1].upper()
            strike_str = f"{side} {r['strike']:.0f}"

        trade_type = "BUTTERFLY" if is_bf else (r["setup_type"] or "")[:8]
        entry_p    = r["entry_premium"] or 0
        exit_p     = r["exit_premium"]  or 0
        pnl        = r["pnl_usd"]       or 0
        pnl_p      = r["pnl_pct"]       or 0

        print(
            f"  {r['trade_id'][:8]:<10} "
            f"{trade_type:<8} "
            f"{strike_str:<14} "
            f"{r['setup_grade'] or '?':<6} "
            f"${entry_p:>6.2f} "
            f"${exit_p:>6.2f} "
            f"{pnl_str(pnl):>9} "
            f"{pct_str(pnl_p):>7}  "
            f"{(r['exit_reason'] or '')[:28]}"
        )
    print()


def show_alltime(conn):
    rows = conn.execute(
        "SELECT * FROM trades WHERE status='closed' ORDER BY exit_time"
    ).fetchall()

    sep()
    print("  ALL-TIME PERFORMANCE")
    sep()

    if not rows:
        print("  No closed trades yet.")
        print()
        return

    wins         = [r for r in rows if (r["pnl_usd"] or 0) > 0]
    losses       = [r for r in rows if (r["pnl_usd"] or 0) <= 0]
    total_pnl    = sum(r["pnl_usd"] or 0 for r in rows)
    win_rate     = len(wins) / len(rows) * 100 if rows else 0
    avg_win      = sum(r["pnl_usd"] or 0 for r in wins) / len(wins) if wins else 0
    avg_loss     = sum(r["pnl_usd"] or 0 for r in losses) / len(losses) if losses else 0
    total_wins   = sum(r["pnl_usd"] or 0 for r in wins)
    total_losses = abs(sum(r["pnl_usd"] or 0 for r in losses))
    pf           = total_wins / total_losses if total_losses > 0 else 0

    # Max drawdown
    running = peak = max_dd = 0.0
    for r in rows:
        running += (r["pnl_usd"] or 0)
        peak     = max(peak, running)
        max_dd   = max(max_dd, peak - running)

    # Avg hold time
    hold_times = []
    for r in rows:
        try:
            entry = datetime.fromisoformat(r["entry_time"])
            exit_ = datetime.fromisoformat(r["exit_time"])
            hold_times.append((exit_ - entry).total_seconds() / 60)
        except Exception:
            pass
    avg_hold = sum(hold_times) / len(hold_times) if hold_times else 0

    print(f"  Total Trades:    {len(rows)}  ({len(wins)}W / {len(losses)}L)")
    print(f"  Win Rate:        {win_rate:.1f}%  {bar(win_rate)}")
    print(f"  Net P&L:         {pnl_str(total_pnl)}")
    print(f"  Avg Win:         {pnl_str(avg_win)}")
    print(f"  Avg Loss:        {pnl_str(avg_loss)}")
    print(f"  Profit Factor:   {pf:.2f}")
    print(f"  Max Drawdown:    ${max_dd:.2f}")
    print(f"  Avg Hold Time:   {avg_hold:.0f} min")
    print()


def show_by_strategy(conn):
    sep()
    print("  PERFORMANCE BY STRATEGY")
    sep()

    strategies = conn.execute(
        "SELECT DISTINCT strategy FROM trades WHERE status='closed' AND strategy IS NOT NULL"
    ).fetchall()

    if not strategies:
        print("  No closed trades yet.")
        print()
        return

    for strat in strategies:
        name = strat["strategy"]
        rows = conn.execute(
            "SELECT pnl_usd, pnl_pct, total_cost FROM trades WHERE status='closed' AND strategy=?",
            (name,)
        ).fetchall()
        wins     = [r for r in rows if (r["pnl_usd"] or 0) > 0]
        win_rate = len(wins) / len(rows) * 100 if rows else 0
        net_pnl  = sum(r["pnl_usd"] or 0 for r in rows)
        print(
            f"  {name:<24} {len(rows):>3} trades  "
            f"WR={win_rate:.0f}%  {bar(win_rate, 12)}  "
            f"Net={pnl_str(net_pnl)}"
        )
    print()


def show_by_grade(conn):
    sep()
    print("  PERFORMANCE BY SETUP GRADE")
    sep()

    for grade in ["A", "B", "C"]:
        rows = conn.execute(
            "SELECT pnl_usd, pnl_pct FROM trades WHERE status='closed' AND setup_grade=?",
            (grade,)
        ).fetchall()
        if not rows:
            print(f"  Grade {grade}:  No trades yet")
            continue
        wins     = [r for r in rows if (r["pnl_usd"] or 0) > 0]
        win_rate = len(wins) / len(rows) * 100
        net_pnl  = sum(r["pnl_usd"] or 0 for r in rows)
        avg_pct  = sum(r["pnl_pct"] or 0 for r in rows) / len(rows)
        print(
            f"  Grade {grade}:  {len(rows):>3} trades  "
            f"WR={win_rate:.0f}%  {bar(win_rate, 12)}  "
            f"Net={pnl_str(net_pnl)}  AvgPnl%={avg_pct:+.1%}"
        )
    print()


def show_by_setup_type(conn):
    sep()
    print("  PERFORMANCE BY SETUP TYPE")
    sep()

    types = conn.execute(
        "SELECT DISTINCT setup_type FROM trades WHERE status='closed' AND setup_type IS NOT NULL"
    ).fetchall()

    if not types:
        print("  No closed trades yet.")
        print()
        return

    for st in types:
        stype = st["setup_type"]
        rows  = conn.execute(
            "SELECT pnl_usd FROM trades WHERE status='closed' AND setup_type=?",
            (stype,)
        ).fetchall()
        wins     = [r for r in rows if (r["pnl_usd"] or 0) > 0]
        win_rate = len(wins) / len(rows) * 100 if rows else 0
        net_pnl  = sum(r["pnl_usd"] or 0 for r in rows)
        print(
            f"  {stype:<28} {len(rows):>3} trades  "
            f"WR={win_rate:.0f}%  Net={pnl_str(net_pnl)}"
        )
    print()


def show_recent(conn, n: int = 10):
    rows = conn.execute(
        "SELECT * FROM trades WHERE status='closed' ORDER BY exit_time DESC LIMIT ?", (n,)
    ).fetchall()

    sep()
    print(f"  LAST {n} CLOSED TRADES")
    sep()

    if not rows:
        print("  No closed trades yet.")
        print()
        return

    print(f"  {'ID':<10} {'Type':<8} {'Strike':<14} {'Contr':>5} "
          f"{'Entry':>7} {'Exit':>7} {'P&L':>9} {'P&L%':>7}  Reason")
    sep()

    for r in rows:
        is_bf = bool(r["is_butterfly"])
        if is_bf:
            strike_str = f"{r['center_strike']:.0f} BF"
        else:
            side = (r["option_side"] or "")[:1].upper()
            strike_str = f"{side} {r['strike']:.0f}" if r["strike"] else "N/A"

        trade_type = "BUTTERFLY" if is_bf else (r["setup_type"] or "")[:8]
        entry_p    = r["entry_premium"] or 0
        exit_p     = r["exit_premium"]  or 0
        pnl        = r["pnl_usd"]       or 0
        pnl_p      = r["pnl_pct"]       or 0

        print(
            f"  {r['trade_id'][:8]:<10} "
            f"{trade_type:<8} "
            f"{strike_str:<14} "
            f"{r['contracts'] or 0:>5} "
            f"${entry_p:>6.2f} "
            f"${exit_p:>6.2f} "
            f"{pnl_str(pnl):>9} "
            f"{pct_str(pnl_p):>7}  "
            f"{(r['exit_reason'] or '')[:25]}"
        )
    print()


def show_circuit_breakers(conn):
    rows = conn.execute(
        "SELECT * FROM circuit_breaker_events ORDER BY event_time DESC LIMIT 5"
    ).fetchall()

    if not rows:
        return

    sep()
    print("  RECENT CIRCUIT BREAKER EVENTS")
    sep()
    for r in rows:
        print(
            f"  {to_et(r['event_time'])}  "
            f"losses={r['session_losses']}  "
            f"{r['reason'] or ''}"
        )
    print()



# ═══════════════════════════════════════════════════════════════════════════
# MARKET DATA — r76. The derived layer, which query.py could not see until now.
# ═══════════════════════════════════════════════════════════════════════════
# ⚠️ EVERY SECTION BELOW READS THE DERIVED STORE, NOT trades.db. It opens
# READ-ONLY and every section degrades to a printed note rather than an
# exception: a dashboard that cannot render because one sensor is empty is
# worse than one that says which sensor is empty.
#
# ⚠️ AND ABSENCE IS PRINTED AS ABSENCE. "no rows yet" and "this box has never
# written this table" are different facts; a blank section conflates them,
# which is the habit this project has paid for repeatedly.

def _derived():
    """Read-only handle on the derived store, or None."""
    try:
        import os as _os
        import sqlite3 as _sq
        path = _os.environ.get(
            "OT_DERIVED_DB",
            _os.path.expanduser("~/options-trader/data/derived_store.db"))
        if not _os.path.exists(path):
            return None
        return _sq.connect(f"file:{path}?mode=ro", uri=True)
    except Exception:                                           # noqa: BLE001
        return None


def _q(dc, sql, args=()):
    try:
        return dc.execute(sql, args).fetchall()
    except Exception:                                           # noqa: BLE001
        return None                    # None = table absent; [] = no rows


def show_character(dc):
    """The tape's character now, and the last few CHANGES with timestamps.

    🔴 A CHARACTER THAT HELD ALL SESSION AND ONE THAT FLIPPED SIX TIMES ARE
    DIFFERENT SESSIONS. The transitions are the object, which is why this shows
    changes rather than a current value repeated.

    ⚠️ THE ACCEPTANCE GATE IS VISIBLE HERE: the operator's 20-year prior is
    1-3 changes per symbol-day. If this list is long, the deriver is wrong —
    the retired engine produced ~20/symbol-day and that gap is what made its
    churn visible at all.
    """
    sep("═")
    print("  CHARACTER  (state, not signal — informs nothing, gates nothing)")
    sep("═")
    rows = _q(dc, "SELECT character, from_character, entered_ts, held_s,"
                  " persistence, vol_ratio, gap_pct, gap_class"
                  " FROM character_ledger WHERE symbol=?"
                  " ORDER BY entered_ts DESC LIMIT 8", (INSTRUMENT,))
    if rows is None:
        print("  (character_ledger not present on this box)")
        print(); return
    if not rows:
        print("  No character recorded yet today.")
        print(); return

    cur = rows[0]
    held = (datetime.now(ET).timestamp() - cur[2]) / 60.0
    print(f"  Now:  {str(cur[0]).upper():<12} held {held:.0f} min")
    if cur[4] is not None or cur[5] is not None:
        pv = "n/a" if cur[4] is None else f"{cur[4]:.2f}"
        vv = "n/a" if cur[5] is None else f"{cur[5]:.2f}x"
        print(f"        persistence {pv}   volatility {vv}")
    if cur[6] is not None:
        # ⚠️ THE GAP IS ADDITIVE CONTEXT, NEVER A FINDING ON ITS OWN. It
        # qualifies the reading above; it does not assert anything by itself.
        print(f"        on a {cur[6]:+.2f}% gap day"
              + (f"  ({cur[7]})" if cur[7] else ""))
    print()
    print(f"  Changes today: {len(rows)}   (expected 1-3)")
    for r in rows:
        t = datetime.fromtimestamp(r[2], ET).strftime("%H:%M")
        frm = f"{r[1]} → " if r[1] else ""
        hs = f"  held {r[3]/60:.0f}m" if r[3] else ""
        print(f"    {t}  {frm}{r[0]}{hs}")
    print()


def show_gates(dc):
    """Which rung is refusing each strategy, and for how long.

    🔴 THIS IS THE SECTION THAT WOULD HAVE ANSWERED 2026-08-21. The fleet
    declined every setup on every box all session and could not say why: the
    journal held one event type and every other refusal was a debug line. SPX
    re-confirmed at 10:46 and sat refused for 44 minutes with nothing recording
    which gate said no.
    """
    sep("═")
    print("  GATES  (why a strategy is not trading)")
    sep("═")
    rows = _q(dc, "SELECT strategy, gate, reason, event, held_s, ticks,"
                  " ts_epoch FROM gate_disposition"
                  " WHERE symbol=? AND ts_epoch > ?"
                  " ORDER BY ts_epoch DESC LIMIT 12",
              (INSTRUMENT, datetime.now(ET).timestamp() - 86400))
    if rows is None:
        print("  (gate_disposition not present on this box)")
        print(); return
    if not rows:
        print("  No gate transitions recorded in the last 24h.")
        print(); return
    for st, gate, reason, ev, held, ticks, ts in rows:
        t = datetime.fromtimestamp(ts, ET).strftime("%H:%M")
        mark = {"CLEARED": "✓", "CHANGED": "→"}.get(ev, "✗")
        extra = f"  ({held/60:.0f}m, {ticks} ticks)" if held else ""
        print(f"    {t} {mark} {st:<22} {gate}{extra}")
        if reason and ev != "CLEARED":
            print(f"           {reason[:78]}")
    print()


def show_plans(dc):
    """Intent — including the plans that never became trades.

    🔴 A PLAN CAN PRODUCE NO TRADE AT ALL, and that is the population worth
    mining: an unfired plan still has a knowable outcome, so scoring it later
    is a free backtest on live data. It is also how the trigger itself gets
    measured — if unfired plans would have won at the same rate as fired ones,
    the trigger filters noise; if better, it costs money.
    """
    sep("═")
    print("  PLANS  (intent — fired, expired, and never triggered)")
    sep("═")
    rows = _q(dc, "SELECT strategy, state, terminal_reason, created_ts,"
                  " closed_ts, short_strike, trigger_price, trade_ids"
                  " FROM plan_ledger WHERE symbol=?"
                  " ORDER BY created_ts DESC LIMIT 10", (INSTRUMENT,))
    if rows is None:
        print("  (plan_ledger not present on this box)")
        print(); return
    if not rows:
        print("  No plans recorded.")
        print(); return
    for strat, state, term, cts, clts, ss, tp, tids in rows:
        t = datetime.fromtimestamp(cts, ET).strftime("%m-%d %H:%M")
        at = ss or tp
        atx = f" @ {at:.2f}" if at else ""
        # ⚠️ WIPED_BY_RESTART IS ITS OWN CATEGORY, not folded into CANCELLED —
        # it is the countable cost of deploying mid-session.
        flag = "⚠️ " if term == "WIPED_BY_RESTART" else "   "
        live = "" if clts else "  ← LIVE"
        traded = f"  traded={len(__import__('json').loads(tids))}" if tids else ""
        print(f"  {flag}{t}  {strat:<22} {state}{atx}{traded}{live}")
        if term:
            print(f"        terminal: {term}")
    print()


def show_market(dc):
    """Levels, forks and the second-order surface — the market picture."""
    sep("═")
    print("  MARKET")
    sep("═")

    lv = _q(dc, "SELECT price, kind, provenance, touch_count, is_live_session"
                " FROM level_ledger WHERE symbol=? AND retired_ts IS NULL"
                " ORDER BY touch_count DESC LIMIT 8", (INSTRUMENT,))
    if lv:
        print("  Live levels (by touches — a touch is a HOLD):")
        for pr, kind, prov, touches, live in lv:
            star = " ⟲" if live else ""
            print(f"    {pr:>9.2f}  {str(kind or ''):<11} {str(prov or ''):<10}"
                  f" touches={touches}{star}")
    elif lv is None:
        print("  (level_ledger not present)")
    else:
        print("  No live levels.")

    fk = _q(dc, "SELECT interval, built, reject_reason, containment, span_bars"
                " FROM fork_series WHERE symbol=? ORDER BY ts_epoch DESC LIMIT 2",
            (INSTRUMENT,))
    if fk:
        print("\n  Pitchfork:")
        for iv, built, rr, cont, span in fk:
            if built:
                print(f"    {iv}: BUILT  containment={cont:.2f} span={span} bars")
            else:
                # ⚠️ THE REASON, NOT JUST "absent". Six distinct causes used to
                # collapse into one message, which is why a diagnosis took two
                # wrong turns.
                print(f"    {iv}: no fork — {rr}")

    sf = _q(dc, "SELECT ROUND(AVG(charm),4), ROUND(AVG(vanna),4),"
                " ROUND(MAX(gex)/1e6,2), COUNT(*) FROM surface_series"
                " WHERE symbol=? AND ts_epoch > ?",
            (INSTRUMENT, datetime.now(ET).timestamp() - 3600))
    if sf and sf[0][3]:
        c, v, g, n = sf[0]
        print(f"\n  Surface (1h): charm={c}  vanna={v}  GEX={g}M  ({n} samples)")
    print()


def main():
    conn = connect()
    print()
    show_header()
    # ── TRADES: what happened ────────────────────────────────────────────
    show_open_position(conn)
    show_today(conn)
    show_alltime(conn)
    show_by_strategy(conn)
    show_by_grade(conn)
    show_by_setup_type(conn)
    show_recent(conn)
    show_circuit_breakers(conn)

    # ── MARKET: what the tape was doing, and why nothing fired ───────────
    # ⚠️ SEPARATE CONNECTION, SEPARATE FAILURE. The derived store is a
    # different database; if it will not open, the trades dashboard above is
    # unaffected and this half says so.
    dc = _derived()
    if dc is None:
        sep("═")
        print("  MARKET DATA — derived store not found on this box.")
        print("  (expected at ~/options-trader/data/derived_store.db)")
        sep("═")
    else:
        show_character(dc)
        show_gates(dc)
        show_plans(dc)
        show_market(dc)
        dc.close()

    sep("═")
    print()
    conn.close()


if __name__ == "__main__":
    main()
