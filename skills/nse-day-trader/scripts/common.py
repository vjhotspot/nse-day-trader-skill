"""Shared helpers: symbol normalisation, OHLCV loading and validation.

Input validation matters here: a bad CSV (wrong columns, unsorted dates,
zero/negative prices) silently produces wrong indicators, and wrong
indicators produce wrong stop-losses. So we fail loudly instead.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

REQUIRED = ["Open", "High", "Low", "Close", "Volume"]

# Accept common header variants from broker / TradingView / bhavcopy exports.
ALIASES = {
    "date": "Date", "datetime": "Date", "timestamp": "Date", "time": "Date",
    "open": "Open", "open_price": "Open", "open price": "Open",
    "high": "High", "high_price": "High", "high price": "High",
    "low": "Low", "low_price": "Low", "low price": "Low",
    "close": "Close", "close_price": "Close", "close price": "Close",
    "ltp": "Close", "last": "Close", "adj close": "Adj Close",
    "volume": "Volume", "vol": "Volume", "ttl_trd_qnty": "Volume",
    "total traded quantity": "Volume", "shares traded": "Volume",
}

# NSE symbols: letters, digits, &, -, _ (e.g. M&M, BAJAJ-AUTO). BSE codes are digits.
SYMBOL_RE = re.compile(r"^[A-Z0-9&\-_]{1,20}$")


class DataError(ValueError):
    """Raised when input data cannot be trusted."""


def normalise_symbol(raw: str, exchange: str = "NSE") -> str:
    """Return a yfinance ticker (RELIANCE -> RELIANCE.NS). Rejects junk input."""
    if not isinstance(raw, str) or not raw.strip():
        raise DataError("Empty symbol")
    s = raw.strip().upper()
    if s.startswith("^"):  # index tickers such as ^NSEI pass through unchanged
        return s
    for suffix in (".NS", ".BO"):
        if s.endswith(suffix):
            base = s[: -len(suffix)]
            if not SYMBOL_RE.match(base):
                raise DataError(f"Invalid symbol: {raw!r}")
            return s
    if not SYMBOL_RE.match(s):
        raise DataError(f"Invalid symbol: {raw!r}")
    ex = exchange.upper()
    if ex not in ("NSE", "BSE"):
        raise DataError(f"Exchange must be NSE or BSE, got {exchange!r}")
    return f"{s}.NS" if ex == "NSE" else f"{s}.BO"


def load_ohlcv(path: str | Path) -> pd.DataFrame:
    """Load and validate an OHLCV CSV. Returns a DataFrame indexed by datetime, ascending."""
    p = Path(path)
    if not p.is_file():
        raise DataError(f"File not found: {p}")
    try:
        df = pd.read_csv(p)
    except Exception as exc:  # malformed CSV, encoding issues, etc.
        raise DataError(f"Could not read {p.name}: {exc}") from exc
    if df.empty:
        raise DataError(f"{p.name} is empty")

    df.columns = [ALIASES.get(str(c).strip().lower(), str(c).strip()) for c in df.columns]
    if "Date" not in df.columns:
        # yfinance CSVs sometimes write the index as an unnamed first column
        df = df.rename(columns={df.columns[0]: "Date"})
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise DataError(f"{p.name}: missing columns {missing}; found {list(df.columns)}")

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce", utc=False, format="mixed")
    df = df.dropna(subset=["Date"])
    for c in REQUIRED:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=REQUIRED)
    df = df[(df[["Open", "High", "Low", "Close"]] > 0).all(axis=1) & (df["Volume"] >= 0)]
    # Basic sanity: High must be the highest and Low the lowest price of the bar.
    bad = (df["High"] < df[["Open", "Close", "Low"]].max(axis=1)) | (
        df["Low"] > df[["Open", "Close", "High"]].min(axis=1)
    )
    if bad.mean() > 0.05:
        raise DataError(f"{p.name}: {bad.sum()} rows have inconsistent High/Low; check the export")
    df = df[~bad]
    df = df.drop_duplicates(subset="Date").sort_values("Date").set_index("Date")
    if len(df) < 30:
        raise DataError(f"{p.name}: only {len(df)} valid rows; need at least 30 for indicators")
    return df


def symbol_from_path(path: str | Path) -> str:
    return Path(path).stem.upper()
