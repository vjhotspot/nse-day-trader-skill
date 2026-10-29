#!/usr/bin/env python3
"""Download OHLCV for NSE/BSE symbols via yfinance and save one CSV per symbol.

Usage:
  python fetch_data.py RELIANCE TCS HDFCBANK --exchange NSE --period 6mo --interval 1d --out data/
  python fetch_data.py --watchlist ../assets/watchlist.example.txt --interval 15m --period 5d

Notes:
- Yahoo data is free and may be delayed or incomplete. Label it as such.
- Intraday intervals (1m-60m) have short lookback limits on Yahoo (e.g. 1m: 7 days).
- Sandboxed environments (claude.ai) may block Yahoo. On failure, ask the user
  to upload a broker/TradingView CSV instead of retrying in a loop.
- No API keys are needed, and none should ever be added to this script.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import DataError, normalise_symbol

VALID_INTERVALS = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "1wk"}
VALID_PERIODS = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd", "max"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("symbols", nargs="*", help="e.g. RELIANCE TCS or RELIANCE.NS")
    ap.add_argument("--watchlist", help="text file, one symbol per line (# comments allowed)")
    ap.add_argument("--exchange", default="NSE", choices=["NSE", "BSE"])
    ap.add_argument("--period", default="6mo")
    ap.add_argument("--interval", default="1d")
    ap.add_argument("--out", default="data")
    a = ap.parse_args()

    if a.interval not in VALID_INTERVALS:
        print(f"ERROR: interval must be one of {sorted(VALID_INTERVALS)}", file=sys.stderr)
        return 2
    if a.period not in VALID_PERIODS:
        print(f"ERROR: period must be one of {sorted(VALID_PERIODS)}", file=sys.stderr)
        return 2

    raw = list(a.symbols)
    if a.watchlist:
        try:
            lines = Path(a.watchlist).read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            print(f"ERROR: cannot read watchlist: {exc}", file=sys.stderr)
            return 2
        raw += [ln.split("#")[0].strip() for ln in lines if ln.split("#")[0].strip()]
    if not raw:
        print("ERROR: give symbols or --watchlist", file=sys.stderr)
        return 2
    if len(raw) > 200:
        print("ERROR: max 200 symbols per run (be polite to the data source)", file=sys.stderr)
        return 2

    tickers = []
    for s in raw:
        try:
            tickers.append(normalise_symbol(s, a.exchange))
        except DataError as exc:
            print(f"SKIP {s}: {exc}", file=sys.stderr)

    try:
        import yfinance as yf  # imported lazily so other scripts work without it
    except ImportError:
        print("ERROR: yfinance not installed. Run: pip install yfinance  "
              "(or upload a CSV with Date,Open,High,Low,Close,Volume)", file=sys.stderr)
        return 3

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ok = 0
    for t in tickers:
        try:
            df = yf.download(t, period=a.period, interval=a.interval, auto_adjust=False,
                             progress=False, threads=False)
        except Exception as exc:  # network blocked, rate-limited, etc.
            print(f"FAIL {t}: {exc}", file=sys.stderr)
            continue
        if df is None or df.empty:
            print(f"FAIL {t}: no data (bad symbol, delisted, or network blocked)", file=sys.stderr)
            continue
        if hasattr(df.columns, "levels"):  # flatten yfinance MultiIndex columns
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df.index.name = "Date"
        name = t.replace("^", "IDX_").replace(".NS", "").replace(".BO", "_BSE")
        df.to_csv(out / f"{name}.csv")
        ok += 1
        print(f"OK   {t}: {len(df)} rows, last bar {df.index[-1]}")

    print(f"\n{ok}/{len(tickers)} saved to {out}/  (source: Yahoo Finance, may be delayed)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
