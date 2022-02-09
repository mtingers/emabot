"""Backtest using the 1m-olhcv csv files

emaA=1,emaB=2 tested the best from the bruteforce.
"""
import warnings
import argparse
from decimal import Decimal
from tqdm import tqdm
from tabulate import tabulate
import numpy as np
import pandas as pd
import pandas_ta as ta
from .util import *

warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv-file',
        help='Path to OHLC CSV file', dest='csv_file', required=True)
    parser.add_argument('--resample',
        help='Set the OHLC resample size (default:1D)', dest='resample', required=False,
        default='1D')
    parser.add_argument('--ema-a',
        help='Set the emaA paramater (default:1)', dest='ema_a', required=False, default=1,
        type=int)
    parser.add_argument('--ema-b',
        help='Set the emaB paramater (default:2)', dest='ema_b', required=False, default=2,
        type=int)
    parser.add_argument('--debug',
        help='Enable debug output', dest='debug', action='store_true', required=False)
    parser.add_argument('--dump-ohlc',
        help='Dump the OHLC sequence data', dest='dump_ohlc', action='store_true', required=False)
    parser.add_argument('--c2c',
        help='Coin-to-coin (higher precision)', dest='c2c', action='store_true', required=False)
    args = parser.parse_args()
    print('ARGS: emaA={} emaB={} resample={} c2c={}'.format(
        args.ema_a, args.ema_b, args.resample, args.c2c))
    stats = backtest(
        emaA=args.ema_a, emaB=args.ema_b, resample=args.resample,
        csv_file=args.csv_file,
        c2c=args.c2c, debug=args.debug,
        dump_ohlc=args.dump_ohlc)
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
