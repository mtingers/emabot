from decimal import Decimal
import talib
import pandas as pd
import pandas_ta as ta
from ..util import huf
from .base import BacktestBase

class StochRsi(BacktestBase):
    def init(self, *args, **kwargs):
        self._df = self._df.drop(columns=['open','high','low','volume'])
        idf = self._df.resample(kwargs['resample']).ohlc()
        fastk, fastd = talib.STOCHRSI(idf['close']['close'])
        self._df['fastk'] = fastk
        self._df['fastd'] = fastd
        self._df.fillna(method='ffill', inplace=True)
        self._df.dropna(axis='rows', how='any', inplace=True)
        self._prev_fastk = 0.0
        self._prev_fastd = 0.0

    def backtest(self, timestamp, row):
        close = row['close'].item()
        fastk = row['fastk'].item()
        fastd = row['fastd'].item()
        if self._prev_fastk != fastk or self._prev_fastd != fastd:
            # print(timestamp, huf(fastk), huf(fastd), self.stats.wallet)
            self._prev_fastk = fastk
            self._prev_fastd = fastd
        price = Decimal(close)
        if not self.buys and fastk > 50 and fastd < fastk:
            self.do_buy(price)
        elif self.buys and fastk < 50 and fastd > fastk:
            self.do_sell(price, 0)

class StochRsi2(BacktestBase):
    def init(self, *args, **kwargs):
        self._df = self._df.drop(columns=['open','high','low','volume'])
        idf = self._df.resample(kwargs['resample']).ohlc()
        fastk, fastd = talib.STOCHRSI(idf['close']['close'])
        self._df['fastk'] = fastk
        self._df['fastd'] = fastd
        self._df.fillna(method='ffill', inplace=True)
        self._df.dropna(axis='rows', how='any', inplace=True)
        self._prev_fastk = 0.0
        self._prev_fastd = 0.0

    def backtest(self, timestamp, row):
        close = row['close'].item()
        fastk = row['fastk'].item()
        fastd = row['fastd'].item()
        if self._prev_fastk != fastk or self._prev_fastd != fastd:
            #print(timestamp, huf(fastk), huf(fastd), self.stats.wallet)
            self._prev_fastk = fastk
            self._prev_fastd = fastd
        price = Decimal(close)
        if not self.buys and fastk > 50:
            self.do_buy(price)
        elif self.buys and fastk < 50:
            self.do_sell(price, 0)

class StochRsi3(BacktestBase):
    def init(self, *args, **kwargs):
        self._df = self._df.drop(columns=['open','high','low','volume'])
        idf = self._df.resample(kwargs['resample']).ohlc()
        fastk, fastd = talib.STOCHRSI(idf['close']['close'])
        self._df['fastk'] = fastk
        self._df['fastd'] = fastd
        self._df.fillna(method='ffill', inplace=True)
        self._df.dropna(axis='rows', how='any', inplace=True)
        self._prev_fastk = 0.0
        self._prev_fastd = 0.0

    def backtest(self, timestamp, row):
        close = row['close'].item()
        fastk = row['fastk'].item()
        fastd = row['fastd'].item()
        if self._prev_fastk != fastk or self._prev_fastd != fastd:
            #print(timestamp, huf(fastk), huf(fastd), self.stats.wallet)
            self._prev_fastk = fastk
            self._prev_fastd = fastd
        price = Decimal(close)
        if not self.buys and fastd > 50:
            self.do_buy(price)
        elif self.buys and fastd <  50:
            self.do_sell(price, 0)

class StochRsi4(BacktestBase):
    def init(self, *args, **kwargs):
        self._df = self._df.drop(columns=['open','high','low','volume'])
        idf = self._df.resample(kwargs['resample']).ohlc()
        fastk, fastd = talib.STOCHRSI(idf['close']['close'])
        self._df['fastk'] = fastk
        self._df['fastd'] = fastd
        self._df.fillna(method='ffill', inplace=True)
        self._df.dropna(axis='rows', how='any', inplace=True)
        self._prev_fastk = 0.0
        self._prev_fastd = 0.0

    def backtest(self, timestamp, row):
        close = row['close'].item()
        fastk = row['fastk'].item()
        fastd = row['fastd'].item()
        if self._prev_fastk != fastk or self._prev_fastd != fastd:
            #print(timestamp, huf(fastk), huf(fastd), self.stats.wallet)
            self._prev_fastk = fastk
            self._prev_fastd = fastd
        price = Decimal(close)
        if not self.buys and fastk > 70 and fastd < fastk:
            self.do_buy(price)
        elif self.buys and fastk < 70 and fastd > fastk:
            self.do_sell(price, 0)
