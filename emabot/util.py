import warnings
from decimal import Decimal
import pandas as pd
import pandas_ta as ta
from tqdm import tqdm

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

def pdiff(old, new):
    return ((Decimal(new) - Decimal(old)) / Decimal(old)) * Decimal('100.0')

def get_dataframes(csv_file, emaA=1, emaB=2):
    df = pd.read_csv(csv_file)
    df_test = pd.read_csv(csv_file)
    df_test.timestamp = pd.to_datetime(df_test.timestamp, unit='s')
    df.timestamp = pd.to_datetime(df.timestamp, unit='s')
    df_test = df_test.set_index("timestamp")
    df = df.set_index("timestamp")
    df = df.drop(columns=['open','high','low','volume'])
    idf = df.resample('1D').ohlc()
    df['emaA'] = ta.ema(idf['close']['close'], length=emaA)
    df['emaB'] = ta.ema(idf['close']['close'], length=emaB)
    df.fillna(method='ffill', inplace=True)
    df.dropna(axis='rows', how='any', inplace=True)
    return df

def huf(f: Decimal):
    return '{:,.2f}'.format(f)

def _backtest(df, emaA: int = 1, emaB: int = 2, progress_bar: tqdm = None, debug: bool = False, c2c: bool = False):
    stats = Stats()
    if c2c:
        # If its a coin-to-coin (e.g. ETH-BTC), set to ~$1000 BTC @41k
        stats.wallet = Decimal('0.0245')
    bought = None
    fee = None
    for (timestamp, row) in df.iterrows():
        close = row['close'].item()
        emaA = row['emaA'].item()
        emaB = row['emaB'].item()
        cur_price = Decimal(close)
        if not bought and emaA > emaB:
            bought = cur_price
            size = stats.wallet / bought
            fee = stats.wallet * FEE
            if debug:
                print('{} BOUGHT: price={:,.2f} A={:,.2f} B={:,.2f} '
                    'size={:,.2f} fee={:,.2f} wallet={:,.2f}'.format(
                        timestamp, cur_price, emaA,
                        emaB, size, fee, stats.wallet))
        elif bought and emaB > emaA:
            percent = pdiff(bought, cur_price)
            net_profit = stats.wallet * ((percent/100)-FEE)
            stats.wallet = stats.wallet + net_profit
            if debug:
                print('{} SOLD : price={:,.2f} A={:,.2f} B={:,.2f} '
                    'profit={:,.2f} percent={:,.2f} wallet={:,.2f}'.format(
                        timestamp, cur_price, emaA,
                        emaB, net_profit, percent, stats.wallet))
            stats.sell_log.append(
                (timestamp, huf(bought),
                    huf(cur_price), huf(net_profit), huf(percent), huf(stats.wallet)))
            if net_profit > 0:
                stats.wins += 1
            else:
                stats.losses += 1
            bought = None
            year_month_day = str(timestamp).rsplit('-', 1)[0]
            if not year_month_day in stats.per_day['fee']:
                stats.per_day['fee'][year_month_day] = []
            if not year_month_day in stats.per_day['percent']:
                stats.per_day['percent'][year_month_day] = []
            if not year_month_day in stats.per_day['net_profit']:
                stats.per_day['net_profit'][year_month_day] = []
            stats.per_day['fee'][year_month_day].append(fee)
            stats.per_day['percent'][year_month_day].append(percent)
            stats.per_day['net_profit'][year_month_day].append(net_profit)
        progress_bar.update(1)
    return stats

def backtest(emaA: int = 1, emaB: int = 2, csv_file: str = None, debug: bool = False, c2c: bool = False):
    df = get_dataframes(csv_file, emaA=emaA, emaB=emaB)
    with tqdm(total=len(df)) as progress_bar:
        stats = _backtest(df, emaA=emaA, emaB=emaB, progress_bar=progress_bar, c2c=c2c, debug=debug)
    return stats
