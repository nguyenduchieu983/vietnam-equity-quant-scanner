# Backtest methodology — M3 pending

No backtest engine or performance output exists in M0. The lab explicitly displays that state.

Required gates from spec section 8: t+1 earliest fills; event-time universe/actions; effective dated bands/ticks; halt/limit no-fill policy; round lots; fees/tax/slippage; settled cash and shares; aggregate portfolio constraints; adverse-first ambiguous candles; embargoed walk-forward; separate untouched OOS; survivorship warnings; deterministic immutable artifacts. Undefined metrics must be null, never invented.

No strategy may be auto-promoted to VALIDATED. Credentials alone will not establish historical data completeness or execution-model fidelity.
