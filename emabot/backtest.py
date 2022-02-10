"""Backtest using the 1m-olhcv csv files

emaA=1,emaB=2 tested the best from the bruteforce.
"""
from abc import ABCMeta, abstractmethod
from abc import ABC
import argparse
import warnings
from decimal import Decimal
from tabulate import tabulate
from tqdm import tqdm
import numpy as np
import pandas as pd
import pandas_ta as ta
from .util import huf, pdiff, import_class

warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)

FEE = Decimal(0.6/100)

class Stats:
    wallet: Decimal = Decimal('1000.00')
    losses: int = 0
    wins: int = 0
    per_day: dict = {
        'fee':{}, 'net_profit':{}, 'percent':{}
    }
    sell_log: list = []

class BacktestBase(ABC):
    def __init__(self, csv_file: str, progress_bar: bool = True, debug: bool = False):
        self._csv_file = csv_file
        self._progress_bar = progress_bar
        self._debug = debug
        self._df = self._get_dataframe()
        self._last_timestamp = None
        self.buys = []
        self.fee = FEE
        self.stats = Stats()

    @abstractmethod
    def init(self, *args, **kwargs) -> None:
        """Setup any extra initialization here (e.g. apply ema to dataframe)"""
        pass

    @abstractmethod
    def backtest(self, timestamp, row) -> None:
        """Each row is fed into here for applying a backtest strategy on a stream of data"""
        pass

    def run(self) -> None:
        """Run the backtest"""
        for (timestamp, row) in self._next_row():
            self.backtest(timestamp, row)
            if self.stats.wallet < 1:
                break

    def _next_row(self) -> tuple:
        """Generate from self._df.iterrows()"""
        if self._progress_bar:
            progress_bar = tqdm(total=len(self._df))
            for (timestamp, row) in self._df.iterrows():
                progress_bar.update(1)
                self._last_timestamp = timestamp
                yield timestamp, row
        else:
            for (timestamp, row) in self._df.iterrows():
                yield timestamp, row

    def _get_dataframe(self) -> pd.DataFrame:
        """Read csv file using pandas and convert and set index to timestamp col

        Expects form:
            "timestamp","low","high","open","close","volume"
        """
        df = pd.read_csv(self._csv_file)
        df.timestamp = pd.to_datetime(df.timestamp, unit='s')
        df = df.set_index("timestamp")
        df.dropna(axis='rows', how='any', inplace=True)
        return df

    def do_buy(self, price: Decimal):
        self.buys.append(price)
        size = self.stats.wallet / price

    def do_sell(self, price: Decimal, buy_index: int):
        fee = self.stats.wallet * self.fee
        bought = self.buys[buy_index]
        percent = pdiff(bought, price)
        profit = self.stats.wallet * ((percent/100)-FEE)
        self.stats.wallet = self.stats.wallet + profit
        timestamp = self._last_timestamp
        self.stats.sell_log.append(
            (timestamp, huf(bought), huf(price), huf(profit), huf(percent), huf(self.stats.wallet))
        )
        del(self.buys[buy_index])
        if profit > 0:
            self.stats.wins += 1
        else:
            self.stats.losses += 1
        year_month_day = str(timestamp).rsplit('-', 1)[0]
        if not year_month_day in self.stats.per_day['fee']:
            self.stats.per_day['fee'][year_month_day] = []
        if not year_month_day in self.stats.per_day['percent']:
            self.stats.per_day['percent'][year_month_day] = []
        if not year_month_day in self.stats.per_day['net_profit']:
            self.stats.per_day['net_profit'][year_month_day] = []
        self.stats.per_day['fee'][year_month_day].append(fee)
        self.stats.per_day['percent'][year_month_day].append(percent)
        self.stats.per_day['net_profit'][year_month_day].append(profit)

def backtest(
        emaA: int = 1,
        emaB: int = 2,
        resample: str = '1D',
        csv_file: str = None,
        debug: bool = False,
        c2c: bool = False,
        dump_ohlc: bool = False,
        strategy: str = 'emabot.strats.backtestema.BacktestEma') -> Stats:

    backtest_cls = import_class(strategy)
    backtester = backtest_cls(csv_file, debug=debug)
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
        help='Set the emaA paramater (default:1)', dest='ema_a', required=False, default=1,
        type=int)
    parser.add_argument('--ema-b',
        help='Set the emaB paramater (default:2)', dest='ema_b', required=False, default=2,
        type=int)
    parser.add_argument('--strategy',
        help='Select which strategy class to use (see emabot/strats/)', dest='strategy',
        required=False, default='emabot.strats.backtestema.BacktestEma', type=str)
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
        dump_ohlc=args.dump_ohlc,
        strategy=args.strategy)
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
