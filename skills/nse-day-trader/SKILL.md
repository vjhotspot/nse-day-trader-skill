---
name: nse-day-trader
description: 'Day-trading and short-term swing workflow for the Indian stock market (NSE/BSE). Use this skill whenever the user asks about intraday or short-term trades in Indian stocks: pre-market briefs, Nifty/Bank Nifty levels, scanning stocks for breakouts or momentum, RSI/EMA/VWAP/ATR checks, position sizing, stop-losses, intraday or delivery brokerage/STT/charges, MIS/CNC, circuit limits, F&O ban list, or reviewing a trade journal. Trigger even when the user only names an Indian stock (e.g. "RELIANCE", "HDFCBANK.NS", "is Tata Motors a buy for tomorrow") or mentions Sensex, Nifty, Zerodha, Groww, Upstox or Angel One. Paper/plan mode only: this skill never places orders.'
---

# NSE/BSE Day Trader

A disciplined workflow for planning intraday and short-term (1–15 day) trades in Indian equities. It turns "what should I buy?" into a checked, sized, written trade plan, or a clear "no trade".

## Ground rules (always apply)

1. **No order placement.** This skill produces trade plans and order tickets the user enters manually in their own broker app. Never ask for, accept or store broker API keys, passwords, TOTP secrets or account numbers. If the user pastes any, tell them to rotate the credential and do not repeat it.
2. **Not investment advice.** Say once per conversation that you are not a SEBI-registered investment adviser or research analyst, and that the output is educational. Do not repeat it on every message.
3. **No guaranteed returns.** Never promise or imply a return. State every setup as a conditional plan: entry trigger, stop, target and invalidation.
4. **Risk first.** Every plan needs a stop-loss and a position size from `scripts/size.py` before anything else. Default risk is 1% of trading capital per trade and a 3% daily loss limit. The user can lower these, and you should push back if they raise them above 2% / 5%.
5. **Data honesty.** Label every price with its source and timestamp. If data is delayed, stale or missing, say so. Never invent levels, prices or news.
6. **Base rate.** If the user is new or sizing aggressively, mention SEBI's FY23 finding that about 7 in 10 individual intraday traders in the cash segment lost money.

## Workflow

Choose the step(s) that match the request. A full "find me a trade" request runs all five in order.

### 1. Market context (pre-market or intraday)
Use web search for: Nifty 50, Sensex and Bank Nifty previous close and levels; GIFT Nifty indication; India VIX; FII/DII cash flows for the last session; crude oil, USD/INR and US market close; and any results, RBI or Fed events today. Summarise in at most 6 lines with a bias of **risk-on / neutral / risk-off**. In risk-off conditions (VIX rising sharply, Nifty below key support), halve the position size or skip trading.

### 2. Data
Get daily OHLCV, plus 5- or 15-minute candles for intraday work:
- First try `python scripts/fetch_data.py SYMBOL [SYMBOL...] --exchange NSE --period 6mo --interval 1d --out data/`. This uses yfinance, so tickers need the `.NS`/`.BO` suffix, which the script adds itself. The sandbox may block Yahoo Finance; if it fails, do not retry repeatedly.
- Fallback: ask the user to upload a CSV exported from their broker, TradingView or NSE bhavcopy with columns `Date,Open,High,Low,Close,Volume`. The scanner accepts common header variants.

### 3. Scan
`python scripts/scan.py data/ --mode swing` for daily candles, or `--mode intraday` for intraday candles. It reports trend (EMA 20/50), RSI(14), ATR(14)%, volume vs its 20-period average, 20-period high/low breakouts, gap %, and VWAP and opening-range breakout in intraday mode, plus a 0–100 setup score. Treat the score as a filter, not a signal. Only discuss stocks scoring at least 60, and say why the others failed.

Then use web search for stock-specific checks on each shortlisted name: results dates within the holding period, the NSE F&O ban list (no fresh F&O positions for stocks in the ban period), corporate actions (ex-dates, splits), ASM/GSM surveillance listing, and the circuit band (2/5/10/20%). See `references/market-rules.md`.

### 4. Plan and size
For each surviving candidate:
- Set entry on a trigger, not at market. Examples: "above today's high 1,842 on a 15-min close", "pullback to 20 EMA ~1,805".
- Set the stop at structural invalidation (the swing low or below the opening range) or 1.5× ATR, whichever is tighter but outside normal noise.
- Set target 1 at ≥1.5R and target 2 at ≥2.5R. Reject the trade if T1 is below 1.5R.
- Run `python scripts/size.py --capital C --risk-pct 1 --entry E --stop S [--product MIS --leverage 5]` to get quantity, capital used and rupee risk.
- Run `python scripts/costs.py --entry E --exit T1 --qty Q --product MIS|CNC` to get charges and break-even. If charges exceed 20% of expected gross profit, flag the trade as cost-inefficient.

Output each plan using `assets/trade_plan_template.md`, keeping it short.

### 5. Review
When the user shares closed trades, log them with `python scripts/journal.py add ...` or import their broker P&L CSV, then run `python scripts/journal.py stats journal.csv`. Report win rate, average R, expectancy, profit factor, maximum drawdown and the largest loss. Point out rule breaks such as no stop, oversizing, revenge trades or trading in the last 15 minutes. Be direct about losing patterns.

## Timing reference (IST)
Pre-open 09:00–09:15, normal session 09:15–15:30. Brokers auto square-off MIS positions around 15:15–15:25 (this varies by broker). Avoid fresh entries in the first 5 minutes and after 15:00 unless the plan specifies otherwise. Equity settlement is T+1. Full rules are in `references/market-rules.md`; read it before answering questions on charges, circuits, MIS/CNC, F&O ban or surveillance.

## Output style
Be concise. Use one table for multiple candidates, then one plan block per trade. Always end with the invalidation level and the daily loss limit remaining.
