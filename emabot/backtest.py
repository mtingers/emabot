"""Backtest using the 1m-olhcv csv files

emaA=1,emaB=2 tested the best from the bruteforce.
"""
import sys
import time
import numpy as np
import pandas as pd
import pandas_ta as ta
from collections import deque
import glob
import json
from random import choice
import warnings
import argparse
from dataclasses import dataclass
from decimal import Decimal
from tqdm import tqdm
from tabulate import tabulate

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
    #df = df.resample('1h').ohlc()
    #df['open'] = df['close']['open']
    #df['high'] = df['close']['high']
    #df['low'] = df['close']['low']
    #df['close2'] = df['close']['close']
    #df = df.drop(columns=['close'])
    #df['close'] = df['close2']
    #df = df.drop(columns=['close2'])
    idf = df.resample('1D').ohlc()
    df['emaA'] = ta.ema(idf['close']['close'], length=emaA)
    df['emaB'] = ta.ema(idf['close']['close'], length=emaB)
    df.fillna(method='ffill', inplace=True)
    df.dropna(axis='rows', how='any', inplace=True)
    return df


def huf(f: Decimal):
    return '{:,.2f}'.format(f)

def _backtest(df, emaA: int = 1, emaB: int = 2, progress_bar: tqdm = None, debug: bool = False):
    stats = Stats()
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
            sell = cur_price
            percent = pdiff(bought, sell)
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

def backtest(emaA: int = 1, emaB: int = 2, csv_file: str = None):
    df = get_dataframes(csv_file, emaA=emaA, emaB=emaB)
    with tqdm(total=len(df)) as progress_bar:
        stats = _backtest(df, emaA=emaA, emaB=emaB, progress_bar=progress_bar)
    return stats

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv-file',
        help='Path to OHLC CSV file', dest='csv_file', required=True)
    args = parser.parse_args()
    stats = backtest(emaA=1, emaB=2, csv_file=args.csv_file)
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
        day_results.append((
            timestamp,
            #'{:,.2f}'.format(sum(stats.per_day['fee'][timestamp])),
            #'{:,.2f}'.format(np.mean(stats.per_day['fee'][timestamp])),
            #'{:,.2f}'.format(np.median(stats.per_day['fee'][timestamp])),
            '{:,.2f}'.format(sum(stats.per_day['percent'][timestamp])),
            '{:,.2f}'.format(np.mean(stats.per_day['percent'][timestamp])),
            '{:,.2f}'.format(np.median(stats.per_day['percent'][timestamp])),
            len(stats.per_day['percent'][timestamp]),
            #'{:,.2f}'.format(sum(stats.per_day['net_profit'][timestamp])),
            #'{:,.2f}'.format(np.mean(stats.per_day['net_profit'][timestamp])),
            #'{:,.2f}'.format(np.median(stats.per_day['net_profit'][timestamp])),
        ))

    print(tabulate(day_results, tablefmt='fancy_grid', headers=[
        'Date',
        #'Fees', 'FeesMean', 'FeesMedian',
        'Percent', 'Percent Mean', 'Percent Median',
        #'NetProfitMean', 'NetProfitMedian', 'NetProfit',
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
