
## [2.1.0] - 2022-02-09
- Modularize backtest strats
- Update README cron notes
- Add dump_ohlc to debug the results

## [2.0.0] - 2022-02-08
- Refactor to make EMA and OHLC sizes configurable
- Add ema_a, ema_b, and resample configuration options (to general)

## [1.7.0] - 2022-02-07
- Pass debug arg down to backtester

## [1.6.1] - 2022-02-07
- Fix self.currency initialization

## [1.6.0] - 2022-02-07
- Add debug logger
- Scope decision variable from local to method to local to EmaBot class

## [1.5.0] - 2022-02-07
- Work for non-USD pairs in place but untested (e.g. ETH-BTC)
- Add currency config option to allow non-USD pairs
