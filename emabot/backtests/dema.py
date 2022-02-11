from decimal import Decimal
import talib
import pandas as pd
import pandas_ta as ta
from .base import BacktestBase

class Dema(BacktestBase):
    def init(self, *args, **kwargs):
        self._df = self._df.drop(columns=['open','high','low','volume'])
        idf = self._df.resample(kwargs['resample']).ohlc()
        #self._df['emaA'] = ta.ema(idf['close']['close'], length=kwargs['emaA'])
        #self._df['emaB'] = ta.ema(idf['close']['close'], length=kwargs['emaB'])
        self._df['emaA'] = talib.DEMA(idf['close']['close'], kwargs['emaA'])
        self._df['emaB'] = talib.DEMA(idf['close']['close'], kwargs['emaB'])
        self._df.fillna(method='ffill', inplace=True)
        self._df.dropna(axis='rows', how='any', inplace=True)

    def backtest(self, timestamp, row):
        close = row['close'].item()
        emaA = row['emaA'].item()
        emaB = row['emaB'].item()
        price = Decimal(close)
        if not self.buys and emaA > emaB:
            self.do_buy(price)
        elif self.buys and emaB > emaA:
            self.do_sell(price, 0)

