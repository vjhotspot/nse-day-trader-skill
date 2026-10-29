#!/usr/bin/env python3
"""Scan OHLCV CSVs for long setups and score them 0-100.

Usage:
  python scan.py data/ --mode swing            # daily candles, 1-15 day holds
  python scan.py data/ --mode intraday --orb 15  # 5/15-min candles, today's session
  python scan.py data/RELIANCE.csv --json

The score is a FILTER, not a buy signal. It rewards trend alignment, healthy
momentum (not overbought), volume confirmation and breakouts, and it penalises
extreme volatility and overextension above the 20 EMA.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from common import DataError, load_ohlcv, symbol_from_path


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    """Wilder's RSI."""
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(100)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = df["Close"].shift()
    tr = pd.concat([df["High"] - df["Low"], (df["High"] - pc).abs(), (df["Low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def analyse(df: pd.DataFrame, mode: str, orb_minutes: int = 15) -> dict:
    c = df["Close"]
    e20, e50 = ema(c, 20), ema(c, 50)
    r = rsi(c)
    a = atr(df)
    vol_avg = df["Volume"].rolling(20).mean().shift(1)  # exclude current bar
    hi20 = df["High"].rolling(20).max().shift(1)
    lo20 = df["Low"].rolling(20).min().shift(1)

    last = df.iloc[-1]
    price = float(last["Close"])
    out = {
        "last_bar": str(df.index[-1]),
        "close": round(price, 2),
        "ema20": round(float(e20.iloc[-1]), 2),
        "ema50": round(float(e50.iloc[-1]), 2),
        "rsi14": round(float(r.iloc[-1]), 1),
        "atr14": round(float(a.iloc[-1]), 2),
        "atr_pct": round(float(a.iloc[-1]) / price * 100, 2),
        "vol_ratio": round(float(last["Volume"] / vol_avg.iloc[-1]), 2) if vol_avg.iloc[-1] > 0 else None,
        "hi20": round(float(hi20.iloc[-1]), 2),
        "lo20": round(float(lo20.iloc[-1]), 2),
        "gap_pct": round((float(last["Open"]) / float(df["Close"].iloc[-2]) - 1) * 100, 2),
        "ext_from_ema20_pct": round((price / float(e20.iloc[-1]) - 1) * 100, 2),
    }
    out["trend_up"] = bool(price > out["ema20"] > out["ema50"])
    out["breakout20"] = bool(price > out["hi20"])

    score, notes = 0, []
    if out["trend_up"]:
        score += 25; notes.append("trend aligned (C>20>50 EMA)")
    elif price > out["ema50"]:
        score += 10; notes.append("above 50 EMA only")
    else:
        notes.append("below 50 EMA: no long")
    if 50 <= out["rsi14"] <= 68:
        score += 20; notes.append("RSI healthy")
    elif 68 < out["rsi14"] <= 78:
        score += 8; notes.append("RSI hot")
    elif out["rsi14"] > 78:
        notes.append("RSI overbought")
    else:
        notes.append("RSI weak")
    vr = out["vol_ratio"] or 0
    if vr >= 1.5:
        score += 20; notes.append(f"volume {vr}x avg")
    elif vr >= 1.0:
        score += 8
    if out["breakout20"]:
        score += 20; notes.append("20-bar breakout")
    elif price >= 0.98 * out["hi20"]:
        score += 10; notes.append("near 20-bar high")
    if out["ext_from_ema20_pct"] > 3 * out["atr_pct"]:
        score -= 15; notes.append("overextended vs 20 EMA, so chase risk")
    if out["atr_pct"] > 5:
        score -= 10; notes.append("very volatile (ATR > 5%)")
    elif 1 <= out["atr_pct"] <= 4:
        score += 15

    if mode == "intraday":
        idx = pd.DatetimeIndex(df.index)
        today = df[idx.date == idx[-1].date()]
        if len(today) >= 2:
            tp = (today["High"] + today["Low"] + today["Close"]) / 3
            vwap = float((tp * today["Volume"]).cumsum().iloc[-1] / max(today["Volume"].sum(), 1))
            start = today.index[0]
            orb = today[today.index < start + pd.Timedelta(minutes=orb_minutes)]
            if orb.empty:
                orb = today.iloc[:1]
            out.update({
                "vwap": round(vwap, 2),
                "orb_high": round(float(orb["High"].max()), 2),
                "orb_low": round(float(orb["Low"].min()), 2),
                "day_high": round(float(today["High"].max()), 2),
                "day_low": round(float(today["Low"].min()), 2),
            })
            if price > vwap:
                score += 10; notes.append("above VWAP")
            else:
                score -= 10; notes.append("below VWAP")
            if price > out["orb_high"]:
                score += 10; notes.append(f"above {orb_minutes}-min ORB high")
        else:
            notes.append("not enough bars today for VWAP/ORB")

    out["score"] = int(max(0, min(100, score)))
    out["notes"] = notes
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="CSV file or directory of CSVs")
    ap.add_argument("--mode", choices=["swing", "intraday"], default="swing")
    ap.add_argument("--orb", type=int, default=15, help="opening-range minutes (intraday)")
    ap.add_argument("--min-score", type=int, default=0)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if not 1 <= a.orb <= 120:
        print("ERROR: --orb must be 1..120", file=sys.stderr); return 2

    p = Path(a.path)
    files = sorted(p.glob("*.csv")) if p.is_dir() else [p]
    if not files:
        print(f"ERROR: no CSVs in {p}", file=sys.stderr); return 2

    rows, errors = [], []
    for f in files:
        try:
            res = analyse(load_ohlcv(f), a.mode, a.orb)
            res["symbol"] = symbol_from_path(f)
            rows.append(res)
        except (DataError, IndexError, KeyError) as exc:
            errors.append(f"{f.name}: {exc}")

    rows = sorted((r for r in rows if r["score"] >= a.min_score), key=lambda r: r["score"], reverse=True)
    if a.json:
        print(json.dumps({"results": rows, "errors": errors}, indent=2))
    else:
        cols = ["symbol", "score", "close", "rsi14", "atr_pct", "vol_ratio", "ema20", "hi20"]
        if a.mode == "intraday":
            cols += ["vwap", "orb_high"]
        print(pd.DataFrame(rows, columns=cols + ["notes"]).to_string(index=False) if rows else "No results.")
        for e in errors:
            print("SKIPPED", e, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
