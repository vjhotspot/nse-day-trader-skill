#!/usr/bin/env python3
"""Estimate Indian equity trading charges and break-even for a round trip.

Usage:
  python costs.py --entry 1842 --exit 1900 --qty 74 --product MIS
  python costs.py --entry 1842 --exit 1900 --qty 74 --product CNC --config ../config.json

Defaults reflect common discount-broker / NSE rates (see references/market-rules.md)
and MUST be verified against your broker's current charges page. Override any rate
in a JSON config under the keys "MIS" / "CNC". Assumes a long trade (buy then sell);
for a short, the sell leg comes first but the charges are the same.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULTS = {
    "MIS": {
        "brokerage_pct": 0.03, "brokerage_cap": 20.0,   # per executed order
        "stt_sell_pct": 0.025, "stt_buy_pct": 0.0,
        "exchange_pct": 0.00297,
        "sebi_per_crore": 10.0,
        "stamp_buy_pct": 0.003,
        "gst_pct": 18.0,
        "dp_charge_per_sell": 0.0,
    },
    "CNC": {
        "brokerage_pct": 0.0, "brokerage_cap": 0.0,
        "stt_sell_pct": 0.1, "stt_buy_pct": 0.1,
        "exchange_pct": 0.00297,
        "sebi_per_crore": 10.0,
        "stamp_buy_pct": 0.015,
        "gst_pct": 18.0,
        "dp_charge_per_sell": 15.93,
    },
}


def load_rates(product: str, config: str | None) -> dict:
    rates = dict(DEFAULTS[product])
    if config:
        try:
            user = json.loads(Path(config).read_text(encoding="utf-8")).get(product, {})
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"bad config file: {exc}") from exc
        for k, v in user.items():
            if k not in rates:
                raise ValueError(f"unknown rate key {k!r} in config")
            if not isinstance(v, (int, float)) or v < 0:
                raise ValueError(f"rate {k!r} must be a non-negative number")
            rates[k] = float(v)
    return rates


def charges(entry: float, exit_: float, qty: int, product: str, rates: dict) -> dict:
    if entry <= 0 or exit_ <= 0:
        raise ValueError("prices must be > 0")
    if qty <= 0 or int(qty) != qty:
        raise ValueError("qty must be a positive whole number")
    buy, sell = entry * qty, exit_ * qty
    turnover = buy + sell

    def brok(v):
        b = v * rates["brokerage_pct"] / 100
        return min(b, rates["brokerage_cap"]) if rates["brokerage_cap"] > 0 else b

    brokerage = brok(buy) + brok(sell)
    stt = buy * rates["stt_buy_pct"] / 100 + sell * rates["stt_sell_pct"] / 100
    exch = turnover * rates["exchange_pct"] / 100
    sebi = turnover * rates["sebi_per_crore"] / 1e7
    stamp = buy * rates["stamp_buy_pct"] / 100
    gst = (brokerage + exch + sebi) * rates["gst_pct"] / 100
    dp = rates["dp_charge_per_sell"]
    total = brokerage + stt + exch + sebi + stamp + gst + dp
    gross = sell - buy
    return {
        "product": product, "qty": qty, "turnover": round(turnover, 2),
        "brokerage": round(brokerage, 2), "stt": round(stt, 2), "exchange": round(exch, 2),
        "sebi": round(sebi, 2), "stamp": round(stamp, 2), "gst": round(gst, 2), "dp": round(dp, 2),
        "total_charges": round(total, 2),
        "gross_pnl": round(gross, 2), "net_pnl": round(gross - total, 2),
        "breakeven_move_per_share": round(total / qty, 2),
        "breakeven_pct": round(total / buy * 100, 3),
        "charges_pct_of_gross": round(total / gross * 100, 1) if gross > 0 else None,
        "note": "Estimates only; verify rates with your broker. Excludes income tax.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--entry", type=float, required=True)
    ap.add_argument("--exit", type=float, required=True)
    ap.add_argument("--qty", type=int, required=True)
    ap.add_argument("--product", default="MIS", choices=["MIS", "CNC"])
    ap.add_argument("--config", help="JSON with rate overrides")
    a = ap.parse_args()
    try:
        res = charges(a.entry, a.exit, a.qty, a.product, load_rates(a.product, a.config))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
