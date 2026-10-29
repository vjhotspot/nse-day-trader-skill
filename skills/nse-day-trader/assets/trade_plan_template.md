### {SYMBOL} ({NSE|BSE}) · {LONG|SHORT} · {MIS|CNC} · score {score}/100
Data: {source}, last bar {timestamp} ({live|delayed|EOD})

| | Price | Note |
|---|---|---|
| Entry trigger | ₹ | e.g. 15-min close above ORB high |
| Stop | ₹ | structure / 1.5×ATR, {stop_pct}% |
| Target 1 | ₹ | {R1}R, book 50% and trail stop to entry |
| Target 2 | ₹ | {R2}R |
| Qty | | risk ₹{rupee_risk} = {risk_pct}% of capital |
| Charges | ₹ | break-even {breakeven_pct}% |

**Why:** {2 lines: trend, momentum, volume, catalyst}
**Skip if:** {gap beyond X, Nifty below Y, results/F&O ban/ASM, no trigger by HH:MM}
**Time stop:** {exit by 15:10 for MIS | exit if no progress in N days for swing}
Daily loss limit remaining: ₹{x}
