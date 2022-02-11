from abc import ABCMeta, abstractmethod
from abc import ABC
import warnings
from decimal import Decimal
from tqdm import tqdm
import numpy as np
import pandas as pd
import pandas_ta as ta
from ..util import huf, pdiff

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
                self._last_timestamp = timestamp
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
