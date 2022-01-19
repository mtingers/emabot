"""Backtest using the 1m-olhcv csv files

Sorry for the mess.

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

warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)

FEE = 0.6/100

def pdiff(old, new):
    return ((float(new) - float(old)) / float(old)) * float('100.0')

def backtest2(do_print=True, emaA=12, emaB=26):
    # 2) Process history csv file
    df = pd.read_csv(sys.argv[1])
    df.timestamp = pd.to_datetime(df.timestamp, unit='s')
    df = df.set_index("timestamp")
    df = df.drop(columns=['open','high','low','volume'])
    df = df.resample('1h').ohlc()
    df['open'] = df['close']['open']
    df['high'] = df['close']['high']
    df['low'] = df['close']['low']
    df['close2'] = df['close']['close']
    #df['close2'] = df['close']['low']
    df = df.drop(columns=['close'])
    df['close'] = df['close2']
    df = df.drop(columns=['close2'])
    idf = df.resample('1D').ohlc()
    df['emaA'] = ta.ema(idf['close']['']['close'], length=emaA)
    df['emaB'] = ta.ema(idf['close']['']['close'], length=emaB)
    df.fillna(method='ffill', inplace=True)
    df.dropna(axis='rows', how='any', inplace=True)
    df = df.drop(columns=['open', 'high', 'low'])
    print(df)

    # 3) Get last row and assign close price, emaA, emaB
    last_row = df.iloc[-1]
    #print(last_row)
    close = last_row['close'].item()
    emaA = last_row['emaA'].item()
    emaB = last_row['emaB'].item()
    print('last_row:')
    print(last_row)
    if emaA > emaB:
        print('BUYABLE')
    elif emaB > emaA:
        print('SELLABLE')
    else:
        print('NOOPABLE')

def backtest1(do_print=True, emaA=12, emaB=26):
    df = pd.read_csv(sys.argv[1])
    # filter by date range here:
    # 2018-01-01 00:00:00
    #df = df[~(df['timestamp'] < 1514764800)]
    # 2020-01-01 01:00:00
    #df = df[~(df['timestamp'] < 1577883600)]
    df.timestamp = pd.to_datetime(df.timestamp, unit='s')
    df = df.set_index("timestamp")
    df = df.drop(columns=['open','high','low','volume'])
    df = df.resample('1h').ohlc()
    # flatten
    df['open'] = df['close']['open']
    df['high'] = df['close']['high']
    df['low'] = df['close']['low']
    df['close2'] = df['close']['close']
    #df['close2'] = df['close']['low']
    df = df.drop(columns=['close'])
    df['close'] = df['close2']
    df = df.drop(columns=['close2'])
    idf = df.resample('1D').ohlc()
    df['emaA'] = ta.ema(idf['close']['']['close'], length=emaA)
    df['emaB'] = ta.ema(idf['close']['']['close'], length=emaB)
    df.fillna(method='ffill', inplace=True)
    df.dropna(axis='rows', how='any', inplace=True)
    if do_print:
        print(df)
    losses = 0
    wins = 0
    # end flatten
    profits = {}
    profits_p = {}
    wallet = 1000.00
    bought = None
    fee = None
    ema_x_buy = 0
    ema_x_sell = 0
    for (dt, r) in df.iterrows():
        close = r['close'].item()
        emaA = r['emaA'].item()
        emaB = r['emaB'].item()
        if not bought and emaA > emaB:
            bought = close
            size = wallet / bought
            fee = wallet * FEE
            if do_print:
                print('{} BUY:, {:,.2f} wallet={:,.2f} size={:,.4f} emaA={:.2f} emaB={:.2f}'.format(
                    dt, bought, wallet, size, emaA, emaB))
        elif bought and emaB > emaA:
            sell = close
            px = pdiff(bought, sell)
            #profit = ((sell * size) - wallet)
            #wallet = (wallet + profit) - fee
            profit = wallet * ((px/100.)-FEE)
            wallet = wallet + profit
            #fee = wallet * FEE
            if profit > 0:
                wins += 1
            else:
                losses += 1
            if do_print:
                print('{} SELL:, {:,.2f} wallet={:,.2f} bought={:,.2f} profit={:,.2f} fee={:,.2f} p={:,.2f} emaA={:.2f} emaB={:.2f}'.format(
                    dt, sell, wallet, bought, profit, fee, px, emaA, emaB))
            bought = None
            pdate = str(dt).rsplit('-', 1)[0]
            if not pdate in profits:
                profits[pdate] = profit
                profits_p[pdate] = [px]
            else:
                profits[pdate] += profit
                profits_p[pdate].append(px)
    if do_print:
        for k, v in profits.items():
            print('{} {:,.2f} {:,.2f}%'.format(k, v, sum(profits_p[k])))
    pvals = []
    pvals_month = []
    for i in profits_p.values():
        for j in i:
            pvals.append(j)
    for k, v in profits_p.items():
        pvals_month.append(sum(v))
    print('mean-p: {:,.2f}%'.format(np.mean(pvals)))
    print('median-p: {:,.2f}%'.format(np.median(pvals)))
    print('mean-month-p: {:,.2f}%'.format(np.mean(pvals_month)))
    print('median-month-p: {:,.2f}%'.format(np.median(pvals_month)))
    print('wins:', wins, 'losses:', losses)
    return wallet

if __name__ == '__main__':
    combinations = []
    # emaA=1,emaB=2 tested the best from the bruteforce below
    #result = backtest1(emaA=1, emaB=2, do_print=True)
    result = backtest1(emaA=1, emaB=2, do_print=True)
    print('{:,.2f}'.format(result))
    sys.exit(0)
    # Bruteforce to find best combinations of emaA/emaB
    for i in range(1, 26):
        for j in range(1, 26):
            combinations.append((i, j))
    results = {}
    for (emaA, emaB) in combinations:
        key = '{},{}'.format(emaA, emaB)
        if not key in results:
            result = test5(emaA=emaA, emaB=emaB, do_print=False)
            results[key] = result
            print(emaA, emaB, '->', '{:,.2f}'.format(result))
    for k,v in results.items():
        print(k, '{:,.2f}'.format(v))

