# S1–S4 research engines

Implemented in quant/features.py and quant/strategies.py against spec sections 5–6.
S1 uses momentum/volatility ranks, top 15% and score >=70. S2 uses the previous
20 highs and volumes, with current-low/ATR stop. S3 uses EMA20/50/200 pullback,
RSI and raw bullish candle. S4 mean reversion is EXPERIMENTAL, 5/10-session holds.

All active symbols retain scores or null, exclusions, exact source dates,
features and stops. Ties break by symbol. Missing scores are not replaced with
zero; unrelated strategies are not averaged. Config PATCH appends an immutable
version. Scan identity includes dataset, feature and strategy engine hashes.
No future known calendar date means informational signal only.

Golden tests cover EMA/ATR/RSI/warmup, adjustment continuity, previous-bar-only
breakout windows, lifecycle membership, deterministic ranks and future
perturbation. None of these strategies has demonstrated real-market alpha.
