#!/usr/bin/env python3
"""Risk-based position sizing for a long or short equity trade.

Usage:
  python size.py --capital 200000 --risk-pct 1 --entry 1842 --stop 1815
  python size.py --capital 200000 --risk-pct 1 --entry 1842 --stop 1815 --product MIS --leverage 5 --target 1900

Quantity = floor(capital * risk% / |entry - stop|), then capped by buying power
(capital x leverage for MIS, capital for CNC) and by --max-position-pct.
"""
from __future__ import annotations

import argparse
import json
import math
import sys

HARD_MAX_RISK_PCT = 2.0      # refuse anything above this per trade
HARD_MAX_LEVERAGE = 5.0      # SEBI peak-margin rules cap equity intraday around 5x


def size(capital, risk_pct, entry, stop, product="CNC", leverage=1.0, max_position_pct=100.0, target=None):
    # Input validation: wrong signs or zero distances would give infinite or negative sizes.
    if capital <= 0:
        raise ValueError("capital must be > 0")
    if not 0 < risk_pct <= HARD_MAX_RISK_PCT:
        raise ValueError(f"risk-pct must be in (0, {HARD_MAX_RISK_PCT}]; above that, one bad day ends the month")
    if entry <= 0 or stop <= 0:
        raise ValueError("entry and stop must be > 0")
    if entry == stop:
        raise ValueError("stop must differ from entry")
    if product not in ("MIS", "CNC"):
        raise ValueError("product must be MIS or CNC")
    if product == "CNC":
        leverage = 1.0
    if not 1.0 <= leverage <= HARD_MAX_LEVERAGE:
        raise ValueError(f"leverage must be 1..{HARD_MAX_LEVERAGE}")
    if not 0 < max_position_pct <= 100:
        raise ValueError("max-position-pct must be in (0, 100]")

    side = "LONG" if stop < entry else "SHORT"
    if side == "SHORT" and product == "CNC":
        raise ValueError("retail short selling in cash equity is intraday only: use MIS")
    per_share_risk = abs(entry - stop)
    stop_pct = per_share_risk / entry * 100
    risk_budget = capital * risk_pct / 100

    qty_risk = math.floor(risk_budget / per_share_risk)
    # Margin you are willing to commit (max_position_pct of capital) x leverage.
    buying_power = capital * max_position_pct / 100 * leverage
    qty_bp = math.floor(buying_power / entry)
    qty = max(0, min(qty_risk, qty_bp))

    res = {
        "side": side, "product": product, "qty": qty,
        "entry": entry, "stop": stop, "per_share_risk": round(per_share_risk, 2),
        "stop_pct": round(stop_pct, 2),
        "position_value": round(qty * entry, 2),
        "margin_used": round(qty * entry / leverage, 2),
        "rupee_risk": round(qty * per_share_risk, 2),
        "risk_pct_of_capital": round(qty * per_share_risk / capital * 100, 3),
        "limited_by": "risk" if qty_risk <= qty_bp else "buying power",
        "warnings": [],
    }
    if qty == 0:
        res["warnings"].append("quantity is 0: stop too wide for this risk budget, or price too high")
    if stop_pct < 0.3:
        res["warnings"].append("stop < 0.3% from entry: likely inside normal noise/spread")
    if product == "MIS" and stop_pct > 3:
        res["warnings"].append("intraday stop > 3%: unusual; check the setup")
    if target is not None:
        if (side == "LONG" and target <= entry) or (side == "SHORT" and target >= entry):
            raise ValueError("target is on the wrong side of entry")
        r_multiple = abs(target - entry) / per_share_risk
        res["target"] = target
        res["reward_r"] = round(r_multiple, 2)
        res["gross_reward"] = round(qty * abs(target - entry), 2)
        if r_multiple < 1.5:
            res["warnings"].append(f"reward is only {r_multiple:.2f}R (< 1.5R): skip or improve entry")
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--capital", type=float, required=True, help="trading capital in INR")
    ap.add_argument("--risk-pct", type=float, default=1.0)
    ap.add_argument("--entry", type=float, required=True)
    ap.add_argument("--stop", type=float, required=True)
    ap.add_argument("--target", type=float)
    ap.add_argument("--product", default="CNC", choices=["MIS", "CNC"])
    ap.add_argument("--leverage", type=float, default=1.0)
    ap.add_argument("--max-position-pct", type=float, default=100.0,
                    help="cap margin used as %% of capital")
    a = ap.parse_args()
    try:
        res = size(a.capital, a.risk_pct, a.entry, a.stop, a.product, a.leverage, a.max_position_pct, a.target)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
