# Indian equity market rules: quick reference

> These rules change. Treat every number here as a default that must be confirmed with a web search (NSE/BSE circulars, SEBI, your broker's charges page) before relying on it. Last reviewed: Oct 2026.

## Contents
1. Sessions and timings
2. Products (MIS / CNC / MTF)
3. Price bands and circuits
4. F&O ban period
5. Surveillance (ASM / GSM)
6. Charges (defaults used by costs.py)
7. Ticker formats
8. Regulatory notes

## 1. Sessions (IST)
| Window | Time |
|---|---|
| Pre-open (order entry / matching) | 09:00–09:08 / 09:08–09:15 |
| Normal market | 09:15–15:30 |
| Closing session (closing price calculation) | 15:30–15:40 |
| MIS auto square-off | ~15:15–15:25, broker-specific |

Trading holidays are on the NSE holiday calendar, so check it before planning multi-day holds. Muhurat trading happens on Diwali and is short, with thin liquidity.

## 2. Products
- **MIS (intraday):** leverage is capped by SEBI peak-margin rules (typically up to 5× for equity, less for volatile or illiquid stocks). The broker squares off positions automatically before the close and may charge a fee for doing so.
- **CNC (delivery):** no leverage. Settlement is T+1. Selling shares bought today is BTST, which carries short-delivery/auction risk if you short-sell in CNC.
- **MTF (margin trading facility):** funded delivery with daily interest. Include the interest in cost estimates for multi-day holds.
- Short selling in cash equity is intraday-only for retail investors.

## 3. Price bands and circuits
- Stock price bands are 2%, 5%, 10% or 20%. Stocks with F&O contracts have no fixed band and use dynamic price bands instead.
- An upper or lower circuit can trap a position, because there may be no counterparty. Avoid MIS in stocks near their band limit.
- Index-wide circuit breakers apply at Nifty/Sensex moves of 10%, 15% and 20%.

## 4. F&O ban period
A stock enters the ban when market-wide open interest exceeds 95% of its market-wide position limit (MWPL). During the ban, no fresh F&O positions can be opened; positions can only be reduced. NSE publishes the list daily, so check it before any F&O trade.

## 5. Surveillance
Stocks under ASM (Additional Surveillance Measure) or GSM (Graded Surveillance Measure) may require 100% margin, trade-for-trade settlement or periodic call auctions. Treat these as **no intraday** by default.

## 6. Charges (defaults used by `scripts/costs.py`, so verify them)
| Charge | Intraday (MIS) | Delivery (CNC) |
|---|---|---|
| Brokerage | min(₹20, 0.03%) per executed order | ₹0 (many discount brokers) |
| STT | 0.025% sell side | 0.1% buy and sell |
| Exchange transaction (NSE) | 0.00297% | 0.00297% |
| SEBI turnover fee | ₹10 per crore | ₹10 per crore |
| Stamp duty | 0.003% buy side | 0.015% buy side |
| GST | 18% on brokerage + exchange + SEBI fees | same |
| DP charge | none | ~₹15–16 per scrip per sell day |

Override any value in `config.json` (see `config.example.json`).

Tax: intraday equity profits are speculative business income. Delivery gains held ≤12 months are STCG. For specifics, refer the user to a CA, because rates change in Budgets.

## 7. Ticker formats
| Source | NSE | BSE |
|---|---|---|
| Yahoo / yfinance | `RELIANCE.NS` | `RELIANCE.BO` (or the scrip code, e.g. `500325.BO`) |
| TradingView | `NSE:RELIANCE` | `BSE:RELIANCE` |
| Nifty 50 index (Yahoo) | `^NSEI` | Sensex: `^BSESN` |
| Bank Nifty (Yahoo) | `^NSEBANK` | |

## 8. Regulatory notes
- Only SEBI-registered investment advisers and research analysts may give personalised buy/sell recommendations for a fee. This skill presents educational analysis and user-driven plans.
- Algo trading by retail investors through broker APIs falls under SEBI's retail algo framework (broker-approved strategies, order tagging, static IP rules). That is why this skill does not place orders.
- SEBI's FY23 study found that roughly 70% of individual intraday traders in the equity cash segment made losses, and that the share of loss-makers was higher among frequent traders.
