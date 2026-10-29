# NSE Day Trader skill for Claude

A Claude skill for planning intraday and short-term (1–15 day) trades in Indian equities on NSE and BSE. It covers market context, a technical scanner, risk-based position sizing, Indian charges and break-even, and a trade journal.

**Plan-only by design.** The skill never places orders and never handles broker credentials. You enter orders yourself in Zerodha, Groww, Upstox, Angel One or another broker.

> Not investment advice. The author and Claude are not SEBI-registered investment advisers or research analysts. SEBI's FY23 study found that about 70% of individual intraday traders in the cash segment lost money.

## What's inside

```
skills/nse-day-trader/
├── SKILL.md                     # workflow + guardrails Claude follows
├── references/market-rules.md   # timings, MIS/CNC, circuits, F&O ban, ASM/GSM, charges
├── scripts/
│   ├── fetch_data.py            # yfinance OHLCV for .NS/.BO (optional)
│   ├── scan.py                  # EMA20/50, RSI14, ATR, volume, breakout, VWAP, ORB → score
│   ├── size.py                  # position size from capital × risk% ÷ stop distance
│   ├── costs.py                 # brokerage, STT, exchange, SEBI, stamp, GST, DP → break-even
│   └── journal.py               # log trades; win rate, expectancy (R), profit factor, drawdown
├── assets/trade_plan_template.md
├── assets/watchlist.example.txt
└── config.example.json          # override charge rates for your broker
```

## Install

### Option A: claude.ai (web, desktop or mobile)
1. Download `nse-day-trader.skill` from Releases, or build it yourself (see below).
2. In Claude, open **Settings → Capabilities**, make sure **Code execution and file creation** is on, then upload the file under **Skills**.
3. Ask something like *"Pre-market brief and scan my watchlist for intraday setups"*.

On claude.ai the sandbox may block Yahoo Finance. In that case, upload a CSV exported from your broker or TradingView with the columns `Date,Open,High,Low,Close,Volume`. Market context comes from Claude's web search.

### Option B: Claude Code plugin
```
/plugin marketplace add vjhotspot/nse-day-trader-skill
/plugin install nse-day-trader-skill@nse-day-trader-skill
```

### Option C: Claude Code, manual
```bash
git clone https://github.com/vjhotspot/nse-day-trader-skill.git
cp -r nse-day-trader-skill/skills/nse-day-trader ~/.claude/skills/
pip install -r nse-day-trader-skill/requirements.txt
```

## Use the scripts directly
```bash
cd skills/nse-day-trader/scripts
python fetch_data.py --watchlist ../assets/watchlist.example.txt --period 6mo --interval 1d --out data
python scan.py data --mode swing --min-score 60
python size.py --capital 200000 --risk-pct 1 --entry 1842 --stop 1815 --target 1900 --product MIS --leverage 5
python costs.py --entry 1842 --exit 1900 --qty 74 --product MIS
python journal.py stats journal.csv
```

## Guardrails
- Risk per trade is capped at 2% in code, with a default of 1%. Targets below 1.5R are flagged.
- Short trades in CNC are rejected, because retail short selling in cash equity is intraday-only.
- The journal flags losses beyond 1R (stops that weren't honoured) and sanitises text fields against CSV injection.
- Charge rates are defaults. Verify them on your broker's charges page and put overrides in `config.json`, which is gitignored.
- **Never commit secrets.** No API keys, TOTP seeds or client IDs belong anywhere in this repo.

## Build the .skill package
```bash
cd skills && zip -r ../nse-day-trader.skill nse-day-trader -x '*/__pycache__/*'
```

## Tests
```bash
pip install -r requirements.txt && pytest -q
```

## Possible extensions
- A broker integration (for example via an official broker MCP or API). Keep it paper-first, require per-order confirmation, and follow SEBI's retail algo framework.
- NSE bhavcopy ingestion for end-of-day scans across the whole market.

MIT licensed.
