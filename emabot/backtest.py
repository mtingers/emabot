"""Backtesting entry point.
See emabot/backtests/ for list of strats
"""
import sys
import argparse
from decimal import Decimal
from tabulate import tabulate
import numpy as np
from tinydb import TinyDB, Query
from tinydb.storages import JSONStorage
from tinydb_serialization import SerializationMiddleware
from tinydb_serialization import Serializer
from .util import huf, import_class
from .backtests.base import Stats


class DecimalSerializer(Serializer):
    OBJ_CLASS = Decimal

    def encode(self, obj):
        return str(obj)

    def decode(self, s):
        return float(s)

def backtest(
        emaA: int = 2,
        emaB: int = 3,
        resample: str = '1D',
        csv_file: str = None,
        debug: bool = False,
        c2c: bool = False,
        dump_ohlc: bool = False,
        progress_bar: bool = True,
        strategy: str = 'emabot.backtests.ema.Ema') -> Stats:

    backtest_cls = import_class(strategy)
    backtester = backtest_cls(csv_file, debug=debug, progress_bar=progress_bar)
    backtester.init(emaA=emaA, emaB=emaB, resample=resample)
    if dump_ohlc:
        print('Dumping OHLC:')
        for (timestamp, row) in backtester._df.iterrows():
            print(timestamp, row['close'].item(), row['emaA'].item(), row['emaB'].item())
    else:
        try:
            backtester.run()
        except KeyboardInterrupt:
            print('NOTICE: Early exit because ctrl-c')
    return backtester.stats

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv-file',
        help='Path to OHLC CSV file', dest='csv_file', required=True)
    parser.add_argument('--resample',
        help='Set the OHLC resample size (default:1D)', dest='resample', required=False,
        default='1D')
    parser.add_argument('--ema-a',
        help='Set the emaA paramater (default:2)', dest='ema_a', required=False, default=2,
        type=int)
    parser.add_argument('--ema-b',
        help='Set the emaB paramater (default:3)', dest='ema_b', required=False, default=3,
        type=int)
    parser.add_argument('--strategy',
        help='Select which strategy class to use (see emabot/backtests/)', dest='strategy',
        required=False, default='emabot.backtests.ema.Ema', type=str)
    parser.add_argument('--debug',
        help='Enable debug output', dest='debug', action='store_true', required=False)
    parser.add_argument('--dump-ohlc',
        help='Dump the OHLC sequence data', dest='dump_ohlc', action='store_true', required=False)
    parser.add_argument('--c2c',
        help='Coin-to-coin (higher precision)', dest='c2c', action='store_true', required=False)
    parser.add_argument('--no-progress-bar',
        help='Disable progress bar', dest='no_progress_bar', action='store_true', required=False)
    args = parser.parse_args()
    print('ARGS: emaA={} emaB={} resample={} c2c={} strategy={}'.format(
        args.ema_a, args.ema_b, args.resample, args.c2c, args.strategy))

    # Create a TinyDB table to store results in
    table_name = '{}-{}-{}-{}-{}'.format(
        args.ema_a, args.ema_b, args.resample, args.strategy.split('.')[-1],
        args.csv_file.split('.csv')[0])
    serialization = SerializationMiddleware(JSONStorage)
    serialization.register_serializer(DecimalSerializer(), 'TinyDecimal')
    db = TinyDB('backtests/db.json', storage=serialization)
    table = db.table(table_name)

    sys.stdout.flush() # make sure ARGS outputs before tqdm
    stats = backtest(
        emaA=args.ema_a, emaB=args.ema_b, resample=args.resample,
        csv_file=args.csv_file,
        c2c=args.c2c, debug=args.debug,
        dump_ohlc=args.dump_ohlc,
        strategy=args.strategy,
        progress_bar=True if not args.no_progress_bar else False,
    )
    if args.dump_ohlc:
        return
    fee_total = sum([sum(i) for i in stats.per_day['fee'].values()])
    percent_total = sum([sum(i) for i in stats.per_day['percent'].values()])
    net_profit_total = sum([sum(i) for i in stats.per_day['net_profit'].values()])
    percent_mean = np.mean([sum(i) for i in stats.per_day['percent'].values()])
    net_profit_mean = np.mean([sum(i) for i in stats.per_day['net_profit'].values()])
    percent_median = np.median([sum(i) for i in stats.per_day['percent'].values()])
    net_profit_median = np.median([sum(i) for i in stats.per_day['net_profit'].values()])
    day_results = []
    print('Sell log:')
    print(tabulate(stats.sell_log, tablefmt='fancy_grid', headers=[
        'Date', 'Buy Price', 'Sell Price', 'Net Profit', 'Percent', 'Wallet']))
    print('Month breakdown (percent):')
    for timestamp in stats.per_day['fee'].keys():
        if args.c2c:
            day_results.append((
                timestamp,
                '{:,.8f}'.format(sum(stats.per_day['percent'][timestamp])),
                '{:,.8f}'.format(np.mean(stats.per_day['percent'][timestamp])),
                '{:,.8f}'.format(np.median(stats.per_day['percent'][timestamp])),
                len(stats.per_day['percent'][timestamp]),
            ))
        else:
            day_results.append((
                timestamp,
                '{:,.2f}'.format(sum(stats.per_day['percent'][timestamp])),
                '{:,.2f}'.format(np.mean(stats.per_day['percent'][timestamp])),
                '{:,.2f}'.format(np.median(stats.per_day['percent'][timestamp])),
                len(stats.per_day['percent'][timestamp]),
            ))

    print(tabulate(day_results, tablefmt='fancy_grid', headers=[
        'Date',
        'Percent', 'Percent Mean', 'Percent Median',
        'Transactions',
        ])
    )
    db_results = {
        'fee_total':fee_total,
        'net_profit_total':net_profit_total,
        'net_profit_mean':net_profit_mean,
        'net_profit_median':net_profit_median,
        'percent_total':percent_total,
        'percent_mean':percent_mean,
        'percent_median':percent_median,
        'wins':stats.wins,
        'losses':stats.losses,
        'day_results':day_results,
    }
    table.insert(db_results)
    results = {
        'Monthly Mean Percent':[huf(percent_mean)],
        'Monthly Median Percent':[huf(percent_median)],
        'Wins':[stats.wins],
        'Losses':[stats.losses],
        'Total Net Profit':[huf(net_profit_total)],
    }
    print('Results:')
    print(tabulate(results, tablefmt='fancy_grid', headers='keys'))

if __name__ == '__main__':
    main()
