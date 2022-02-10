from decimal import Decimal
import talib
import pandas as pd
import pandas_ta as ta
from ..backtest import BacktestBase
pd.options.mode.chained_assignment = None

class BacktestEmaStream(BacktestBase):
    def init(self, *args, **kwargs):
        self._df = self._df.drop(columns=['open','high','low','volume'])
        #idf = self._df.resample(kwargs['resample']).ohlc()
        #self._df['emaA'] = ta.ema(idf['close']['close'], length=kwargs['emaA'])
        #self._df['emaB'] = ta.ema(idf['close']['close'], length=kwargs['emaB'])
        self._df.fillna(method='ffill', inplace=True)
        self._df.dropna(axis='rows', how='any', inplace=True)
        self._emaA = kwargs['emaA']
        self._emaB = kwargs['emaB']
        self._resample = kwargs['resample']
        self._ticks = 0

    def backtest(self, timestamp, row):
        self._ticks += 1
        if self._ticks % 60 != 0:
            return
        df = self._df.loc[(self._df.index <= timestamp)] #copy(deep=True)
        idf = df.resample(self._resample).ohlc()
        #df['emaA'] = ta.ema(idf['close']['close'], length=self._emaA)
        #df['emaB'] = ta.ema(idf['close']['close'], length=self._emaB)
        df['emaA'] = talib.EMA(idf['close']['close'], self._emaA)
        df['emaB'] = talib.EMA(idf['close']['close'], self._emaB)
        df.fillna(method='ffill', inplace=True)
        df.dropna(axis='rows', how='any', inplace=True)
        if df.empty:
            return
        tail = df.tail(1)
        close = tail['close'].item()
        emaA = tail['emaA'].item()
        emaB = tail['emaB'].item()
        price = Decimal(close)
        if not self.buys and emaA > emaB:
            self.do_buy(price)
        elif self.buys and emaB > emaA:
            self.do_sell(price, 0)
