import math
import statistics


def metrics(equity: list[dict], trades: list[dict], orders: list[dict], starting: float) -> dict:
    navs = [starting] + [float(d["nav"]) for d in equity]
    returns = [b/a-1 for a, b in zip(navs, navs[1:])]
    total_return = navs[-1]/starting-1
    cagr = (navs[-1]/starting)**(252/len(returns))-1 if len(returns) >= 2 and navs[-1] > 0 else None
    std = statistics.stdev(returns) if len(returns) >= 2 else 0
    downside = math.sqrt(statistics.mean(min(0, r)**2 for r in returns)) if returns else 0
    drawdown = min((float(d["drawdown"]) for d in equity), default=0)
    pnl = [float(t["pnl"]) for t in trades]
    wins, losses = [p for p in pnl if p > 0], [p for p in pnl if p < 0]
    yearly: dict[str, float] = {}
    monthly: dict[str, float] = {}
    for width, result in ((4, yearly), (7, monthly)):
        previous = starting
        for row in equity:
            key = row["session_date"][:width]
            result[key] = (1+result.get(key, 0)) * (float(row["nav"])/previous)-1
            previous = float(row["nav"])
    filled = [o for o in orders if o["status"] == "FILLED"]
    benchmark_return = float(equity[-1]["benchmark"])/starting-1 if equity else None
    return {
        "totalReturn": total_return, "cagr": cagr, "maxDrawdown": drawdown,
        "annualizedVolatility": std*math.sqrt(252) if len(returns) >= 2 else None,
        "sharpe": statistics.mean(returns)/std*math.sqrt(252) if std > 0 else None,
        "sortino": statistics.mean(returns)/downside*math.sqrt(252) if downside > 0 else None,
        "calmar": cagr/abs(drawdown) if cagr is not None and drawdown < 0 else None,
        "tradeCount": len(trades), "hitRate": len(wins)/len(pnl) if pnl else None,
        "averageWin": statistics.mean(wins) if wins else None,
        "averageLoss": statistics.mean(losses) if losses else None,
        "expectancy": statistics.mean(pnl) if pnl else None,
        "profitFactor": sum(wins)/abs(sum(losses)) if losses else None,
        "exposure": statistics.mean(float(d["exposure"]) for d in equity) if equity else None,
        "turnover": sum(float(o["price"])*o["quantity"] for o in filled)/statistics.mean(navs),
        "fees": sum(float(o["fee"]) for o in filled), "tax": sum(float(o["tax"]) for o in filled),
        "slippageCost": sum(float(o["slippage_cost"]) for o in filled),
        "yearlyReturns": yearly, "monthlyReturns": monthly, "worstMonth": min(monthly.values(), default=None),
        "benchmarkReturn": benchmark_return, "benchmarkExcess": total_return-benchmark_return if benchmark_return is not None else None,
        "riskFreeRate": 0, "cashBenchmarkReturn": 0, "sessions": len(equity),
    }


def walk_forward(calendar: list[str], end: str, train_sessions: int = 252,
                 test_sessions: int = 126, embargo: int = 30) -> list[dict]:
    last = calendar.index(end)
    start = train_sessions + embargo
    folds = []
    while start + test_sessions-1 <= last:
        folds.append({"trainStart": calendar[start-embargo-train_sessions],
                      "trainEnd": calendar[start-embargo-1], "testStart": calendar[start],
                      "testEnd": calendar[start+test_sessions-1], "embargoSessions": embargo})
        start += test_sessions
    return folds
