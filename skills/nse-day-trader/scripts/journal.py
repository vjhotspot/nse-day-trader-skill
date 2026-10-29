#!/usr/bin/env python3
"""Minimal trade journal: append trades and compute performance stats.

Usage:
  python journal.py add journal.csv --date 2026-10-30 --symbol RELIANCE --side LONG \
      --product MIS --qty 50 --entry 1420 --stop 1405 --exit 1445 --charges 62 --setup ORB --note "followed plan"
  python journal.py stats journal.csv

The journal stores trade data only: no account numbers, client IDs or credentials.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

FIELDS = ["date", "symbol", "side", "product", "qty", "entry", "stop", "exit", "charges", "setup", "note"]


def add(path: Path, a) -> None:
    try:
        date.fromisoformat(a.date)
    except ValueError as exc:
        raise ValueError("date must be YYYY-MM-DD") from exc
    if a.qty <= 0 or min(a.entry, a.stop, a.exit) <= 0 or a.charges < 0:
        raise ValueError("qty, prices must be > 0 and charges >= 0")
    if a.entry == a.stop:
        raise ValueError("stop must differ from entry (a trade without a stop has no R)")
    if (a.side == "LONG" and a.stop > a.entry) or (a.side == "SHORT" and a.stop < a.entry):
        raise ValueError("stop is on the wrong side of entry for this side")
    # Keep free-text fields short and single-line to avoid CSV injection/corruption.
    note = (a.note or "").replace("\n", " ")[:200].lstrip("=+-@")
    setup = (a.setup or "").replace("\n", " ")[:40].lstrip("=+-@")
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({"date": a.date, "symbol": a.symbol.upper()[:20], "side": a.side, "product": a.product,
                    "qty": a.qty, "entry": a.entry, "stop": a.stop, "exit": a.exit,
                    "charges": a.charges, "setup": setup, "note": note})


def stats(path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"no journal at {path}")
    df = pd.read_csv(path)
    missing = [c for c in FIELDS[:9] if c not in df.columns]
    if missing:
        raise ValueError(f"journal missing columns {missing}")
    if df.empty:
        raise ValueError("journal is empty")
    sign = df["side"].str.upper().map({"LONG": 1, "SHORT": -1})
    if sign.isna().any():
        raise ValueError("side must be LONG or SHORT in every row")
    df["net"] = sign * (df["exit"] - df["entry"]) * df["qty"] - df["charges"]
    df["risk"] = (df["entry"] - df["stop"]).abs() * df["qty"]
    df["r"] = df["net"] / df["risk"]
    wins, losses = df[df["net"] > 0], df[df["net"] <= 0]
    equity = df["net"].cumsum()
    dd = (equity - equity.cummax()).min()
    pf = wins["net"].sum() / abs(losses["net"].sum()) if len(losses) and losses["net"].sum() != 0 else None
    out = {
        "trades": int(len(df)),
        "win_rate_pct": round(len(wins) / len(df) * 100, 1),
        "net_pnl": round(df["net"].sum(), 2),
        "total_charges": round(df["charges"].sum(), 2),
        "avg_win": round(wins["net"].mean(), 2) if len(wins) else 0,
        "avg_loss": round(losses["net"].mean(), 2) if len(losses) else 0,
        "expectancy_r": round(df["r"].mean(), 3),
        "profit_factor": round(pf, 2) if pf is not None else None,
        "max_drawdown": round(float(dd), 2),
        "largest_loss": round(df["net"].min(), 2),
        "losses_beyond_1r": int((df["r"] < -1.1).sum()),  # stop not honoured
        "by_setup": df.groupby(df["setup"].fillna("-"))["r"].agg(["count", "mean"]).round(2).to_dict("index"),
    }
    if out["losses_beyond_1r"]:
        out["flag"] = "Some losses exceeded 1R: stops were moved or ignored."
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    pa = sub.add_parser("add")
    pa.add_argument("journal")
    pa.add_argument("--date", default=date.today().isoformat())
    pa.add_argument("--symbol", required=True)
    pa.add_argument("--side", choices=["LONG", "SHORT"], default="LONG")
    pa.add_argument("--product", choices=["MIS", "CNC"], default="MIS")
    for k in ("qty",):
        pa.add_argument(f"--{k}", type=int, required=True)
    for k in ("entry", "stop", "exit"):
        pa.add_argument(f"--{k}", type=float, required=True)
    pa.add_argument("--charges", type=float, default=0.0)
    pa.add_argument("--setup", default="")
    pa.add_argument("--note", default="")
    ps = sub.add_parser("stats")
    ps.add_argument("journal")
    a = ap.parse_args()
    try:
        if a.cmd == "add":
            add(Path(a.journal), a)
            print("logged")
        else:
            print(json.dumps(stats(Path(a.journal)), indent=2, default=str))
    except (ValueError, OSError, pd.errors.ParserError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
