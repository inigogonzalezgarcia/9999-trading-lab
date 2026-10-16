"""Strategy V1 engine split into causal layers.

Modules:

- ``ids``         stable identifiers, configuration hashes, rejection normalisation
- ``frames``      numpy views over closed-candle DataFrames (timestamps, OHLC, true range)
- ``structure``   fractal swings, ATR, H1 bias, pullback qualification
- ``liquidity``   liquidity level history and ACTIVE/TOUCHED/SWEPT/INVALIDATED lifecycle
- ``zones``       supply/demand zone lifecycle from completed M15 candles
- ``candidates``  sweep detection and the sweep -> displacement -> two legs -> BOS state machine
- ``simulation``  deterministic M1 execution of a single candidate with spread/slippage/commission
- ``portfolio``   daily contexts, portfolio limits, and the public ``run_v1_portfolio`` entry point

``backend.app.strategy_v1`` remains the public facade and re-exports every name used by
callers and tests.
"""
