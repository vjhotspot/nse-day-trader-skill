"""Offline tests using synthetic data (no network needed). Run: pytest -q"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/nse-day-trader/scripts"))

from common import DataError, load_ohlcv, normalise_symbol  # noqa: E402
from costs import DEFAULTS, charges  # noqa: E402
from scan import analyse, rsi  # noqa: E402
from size import size  # noqa: E402
import journal  # noqa: E402


def make_csv(tmp_path, name="TEST", n=120, drift=0.004, freq="B", seed=1):
    rng = np.random.default_rng(seed)
    close = 1000 * np.exp(np.cumsum(drift + rng.normal(0, 0.01, n)))
    open_ = close * (1 + rng.normal(0, 0.003, n))
    high = np.maximum(open_, close) * 1.005
    low = np.minimum(open_, close) * 0.995
    vol = rng.integers(1e5, 3e5, n).astype(float)
    vol[-1] *= 3
    df = pd.DataFrame({"Date": pd.date_range("2026-04-01 09:15", periods=n, freq=freq),
                       "Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol})
    p = tmp_path / f"{name}.csv"
    df.to_csv(p, index=False)
    return p


def test_symbol_normalisation():
    assert normalise_symbol("reliance") == "RELIANCE.NS"
    assert normalise_symbol("M&M") == "M&M.NS"
    assert normalise_symbol("500325", "BSE") == "500325.BO"
    assert normalise_symbol("^NSEI") == "^NSEI"
    with pytest.raises(DataError):
        normalise_symbol("RELIANCE; rm -rf /")


def test_load_rejects_bad_csv(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("Date,Price\n2026-01-01,1\n")
    with pytest.raises(DataError):
        load_ohlcv(p)


def test_scan_uptrend_scores_higher(tmp_path):
    up = analyse(load_ohlcv(make_csv(tmp_path, "UP", drift=0.004)), "swing")
    down = analyse(load_ohlcv(make_csv(tmp_path, "DN", drift=-0.004)), "swing")
    assert up["trend_up"] and not down["trend_up"]
    assert up["score"] > down["score"]
    assert 0 <= up["score"] <= 100


def test_scan_intraday_has_vwap(tmp_path):
    res = analyse(load_ohlcv(make_csv(tmp_path, "INTRA", n=200, freq="5min", drift=0.0005)), "intraday")
    assert "vwap" in res and "orb_high" in res


def test_rsi_bounds():
    r = rsi(pd.Series(np.linspace(100, 200, 50)))
    assert r.between(0, 100).all()


def test_size_basic_and_caps():
    r = size(200000, 1, 1842, 1815, target=1900)
    assert r["qty"] == 74 and r["rupee_risk"] <= 2000
    assert r["reward_r"] > 2
    r2 = size(10000, 1, 1000, 999.5)  # tiny stop -> buying-power limited
    assert r2["limited_by"] == "buying power" and r2["qty"] == 10
    with pytest.raises(ValueError):
        size(200000, 5, 100, 95)  # risk too high
    with pytest.raises(ValueError):
        size(200000, 1, 100, 105, product="CNC")  # short in CNC


def test_costs_sane():
    c = charges(1842, 1900, 74, "MIS", DEFAULTS["MIS"])
    assert 0 < c["total_charges"] < 200
    assert c["net_pnl"] < c["gross_pnl"]
    d = charges(1842, 1900, 74, "CNC", DEFAULTS["CNC"])
    assert d["stt"] > c["stt"]  # delivery STT is higher


def test_journal_roundtrip(tmp_path):
    j = tmp_path / "j.csv"

    class A:  # minimal argparse stand-in
        date, symbol, side, product, qty = "2026-10-30", "SBIN", "LONG", "MIS", 10
        entry, stop, exit, charges, setup, note = 800.0, 790.0, 820.0, 30.0, "ORB", "=cmd()"

    journal.add(j, A)
    A.exit = 785.0
    journal.add(j, A)
    s = journal.stats(j)
    assert s["trades"] == 2 and s["win_rate_pct"] == 50.0
    assert s["losses_beyond_1r"] == 1
    assert not pd.read_csv(j)["note"].str.startswith("=").any()  # CSV-injection guard
