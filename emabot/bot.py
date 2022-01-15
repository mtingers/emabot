"""
Use emaA and emaB to determine buy/sell
"""
import os
import sys
import time
import re
import json
import pickle
import warnings
import argparse
import numpy as np
import pandas as pd
import pandas_ta as ta
from datetime import datetime
from collections import deque
from decimal import Decimal
import smtplib
import requests
import yaml
import cbpro
from .history import generate_historical_csv

os.environ['TZ'] = 'UTC'
time.tzset()
TODAY = str(datetime.now()).split(' ')[0]

warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)

def _api_response_check(response, exception_to_raise):
    if 'message' in response:
        raise exception_to_raise(response['message'])

def truncate(x, n):
    if not '.' in str(x):
        return str(x) + '.0'
    a, b = str(x).split('.')
    b = b[:n]
    return a+'.'+b

def truncate_f(x, n):
    if not '.' in str(x):
        return str(x) + '.0'
    a, b = str(x).split('.')
    b = b[:n]
    return float(a+'.'+b)

def pchange(x1, x2):
    x1 = float(x1)
    x2 = float(x2)
    return round(((x2 - x1) / x1) * 100., 1)

def pchange_f(x1, x2):
    x1 = float(x1)
    x2 = float(x2)
    return truncate_f(((x2 - x1) / x1) * 100., 1)

class EmaBot:
    def __init__(self, config_path, dryrun=False, force_sell=False, monitor=False, debug=False):
        self.config_path = config_path
        self.debug = debug
        self.dryrun = dryrun
        self.monitor = monitor
        self.config = {}
        self.name = None
        self.pair = None
        self.b64secret = None
        self.passphrase = None
        self.key = None
        self.data_dir = None
        self.log_dir = None
        self.hist_file = None
        self.buy_path = None
        self.configure()
        self.close = None
        self.emaA = None
        self.emaB = None

    def configure(self):
        with open(self.config_path) as config_stream:
            tmp = list(yaml.safe_load_all(config_stream))
        config = {}
        for i in tmp:
            for k,v in i.items():
                config[k] = v
        missing = []
        if not 'general' in config:
            raise Exception('Missing config section "general"')
        for i in ('debug', 'name', 'log_dir', 'data_dir', 'key', 'passphrase', 'send_email',
                'b64secret', 'pair', 'hist_file', 'monitor_alert_change'):
            if not i in config['general']:
                missing.append(i)
        if missing:
            raise Exception('Missing general config items: {}'.format(', '.join(missing)))
        self.config = config
        self.name = self.config['general']['name']
        self.pair = self.config['general']['pair']
        self.b64secret = self.config['general']['b64secret']
        self.passphrase = self.config['general']['passphrase']
        self.key = self.config['general']['key']
        self.data_dir = re.sub(r'/$', '', self.config['general']['data_dir'])
        self.log_dir = re.sub(r'/$', '', self.config['general']['log_dir'])
        self.hist_file = self.config['general']['hist_file']
        self.buy_path = self.data_dir+'/'+self.name+'-buy.pickle'
        self.monitor_alert_change = self.config['general']['monitor_alert_change']
        self.email_enabled = self.config['general']['send_email']
        self.mail_host = None
        self.mail_to = None
        self.mail_from = None
        if self.email_enabled:
            self.mail_host = self.config['email']['mail_host']
            self.mail_to = self.config['email']['mail_to'].split(',')
            self.mail_from = self.config['email']['mail_from']

    def logit(self, msg):
        path = '{}/{}-{}.log'.format(self.log_dir, self.name, TODAY.split('-')[0])
        msg = '{} {}'.format(datetime.now(), msg.strip())
        if self.dryrun:
            msg = 'dryrun '+msg
        if not msg.startswith(self.pair):
            msg = '{} {}'.format(self.pair, msg)
        print(msg)
        with open(path, 'a') as fd:
            fd.write('{}\n'.format(msg))

    def send_email(self, subject: str, msg: str) -> None:
        """TODO: Add auth, currently setup to relay locally or relay-by-IP"""
        for email in self.mail_to:
            if not email.strip():
                continue
            headers = "From: %s\r\nTo: %s\r\nSubject: %s %s\r\n\r\n" % (
                self.mail_from, email, self.pair, subject)
            if not msg:
                msg2 = subject
            else:
                msg2 = msg
            msg2 = headers + msg2
            server = smtplib.SMTP(self.mail_host)
            server.sendmail(self.mail_from, email, msg2)
            server.quit()

    def load_hist(self, emaA=1, emaB=2):
        """ Note emaA=1 and emaB=2 backtested the best (by a lot) """
        # 1) Get historical to current OHLC
        generate_historical_csv(self.hist_file, pair=self.pair, days_ago=522)

        # 2) Process history csv file
        df = pd.read_csv(self.hist_file)
        df.timestamp = pd.to_datetime(df.timestamp, unit='s')
        df = df.set_index("timestamp")
        df = df.drop(columns=['open','high','low','volume'])
        df = df.resample('1h').ohlc()
        df['open'] = df['close']['open']
        df['high'] = df['close']['high']
        df['low'] = df['close']['low']
        df['close2'] = df['close']['low']
        df = df.drop(columns=['close'])
        df['close'] = df['close2']
        df = df.drop(columns=['close2'])
        idf = df.resample('1D').ohlc()
        df['emaA'] = ta.ema(idf['close']['']['close'], length=emaA)
        df['emaB'] = ta.ema(idf['close']['']['close'], length=emaB)
        df.fillna(method='ffill', inplace=True)
        df.dropna(axis='rows', how='any', inplace=True)

        # 3) Get last row and assign close price, emaA, emaB
        last_row = df.iloc[-1]
        #print(last_row)
        self.close = last_row['close'].item()
        self.emaA = last_row['emaA'].item()
        self.emaB = last_row['emaB'].item()


    def cb_auth(self):
        self.auth_client = cbpro.AuthenticatedClient(
            self.key, self.b64secret, self.passphrase)

    def get_usd_wallet(self):
        accounts = self.auth_client.get_accounts()
        _api_response_check(accounts, Exception)
        for account in accounts:
            if account['currency'] == 'USD':
                wallet = Decimal(account['available'])
                break
        assert wallet is not None, 'USD wallet was not found.'
        return wallet

    def get_fees(self):
        fees = self.auth_client._send_message('get', '/fees')
        _api_response_check(fees, Exception)
        maker_fee = Decimal(fees['maker_fee_rate'])
        taker_fee = Decimal(fees['taker_fee_rate'])
        usd_volume = Decimal(fees['usd_volume'])
        return (maker_fee, taker_fee, usd_volume)

    def get_price(self):
        ticker = self.auth_client.get_product_ticker(product_id=self.pair)
        _api_response_check(ticker, Exception)
        price = Decimal(ticker['price'])
        return price

    def get_order(self, order_id):
        order = self.auth_client.get_order(order_id)
        _api_response_check(order, Exception)
        return order

    def buy_market(self, funds):
        funds = truncate(funds, 2) #str(round(Decimal(funds), 2))
        response = self.auth_client.place_market_order(
            product_id=self.pair,
            side='buy',
            funds=funds,
        )
        _api_response_check(response, Exception)
        return response

    def sell_market(self, size):
        # TODO: Get precisions from api for the self.pair
        fixed_size = truncate(size, 8) #str(round(Decimal(size), 8))
        response = self.auth_client.place_market_order(
            product_id=self.pair,
            side='sell',
            size=fixed_size,
        )
        _api_response_check(response, Exception)
        return response

    def run(self):
        self.cb_auth()
        if self.monitor:
            return self._monitor()
        self.logit('run: ' + TODAY)
        self.load_hist()
        wallet = self.get_usd_wallet()
        fees = self.get_fees()
        price = self.get_price()
        if os.path.exists(self.buy_path):
            with open(self.buy_path, 'rb') as fd:
                buy = pickle.load(fd)
            pc = pchange(buy['real_price'], price)
        else:
            buy = None
            pc = None
        self.logit('wallet:{}  fees:{}  price:{} pc:{}'.format(
            wallet, [str(i) for i in fees], price, pc))

        # Debug settings and if sold now (if bought)
        if self.dryrun:
            print('Exiting before buy/sell logic because dryrun=True')
            print('Dump settings:')
            print('    ', self.name)
            print('    ', self.pair)
            print('    ', self.data_dir)
            print('    ', self.log_dir)
            print('    ', self.hist_file)
            print('    ', self.buy_path)

        # BUY logic
        if not buy and self.emaA > self.emaB:
            self.logit('BUY: {}'.format(price))
            if self.dryrun:
                sys.exit(0)
            response = self.buy_market(wallet)
            self.logit('RESPONSE: {}'.format(response))
            with open(self.buy_path+'.tmp', 'wb') as fd:
                info = {
                    'wallet':wallet,
                    'emaA': self.emaA,
                    'emaB':self.emaB,
                    'date':TODAY,
                    'real_price':price,
                    'response':response,
                    'settled':False,
                    'buy_epoch':time.time()
                }
                pickle.dump(info, fd)
            while 1:
                time.sleep(5)
                order = self.get_order(response['id'])
                settled = order['settled']
                status = order['status']
                if settled:
                    info['settled'] = order
                    self.logit('BUY_SETTLED: {}'.format(order))
                    with open(self.buy_path+'.tmp', 'wb') as fd:
                        pickle.dump(info, fd)
                    os.rename(self.buy_path+'.tmp', self.buy_path)
                    if self.email_enabled:
                        self.send_email('BOUGHT: {}'.format(price), '')
                    break
        # SELL logic
        elif buy and self.emaB > self.emaA:
            size = buy['settled']['filled_size']
            self.logit('SELL: {} size:{}'.format(price, size))
            if self.dryrun:
                u_before = float(buy['real_price']) * float(buy['settled']['filled_size'])
                u_after = float(price) * float(buy['settled']['filled_size'])
                print('IF_SOLD_NOW: {} -> {} {:.2f} {:.2f}% change'.format(
                    buy['real_price'], price, u_after - u_before, pchange_f(buy['real_price'], price)
                ))
                sys.exit(0)
            response = self.sell_market(size)
            self.logit('RESPONSE: {}'.format(response))
            while 1:
                time.sleep(5)
                order = self.get_order(response['id'])
                settled = order['settled']
                status = order['status']
                if settled:
                    self.logit('SELL_SETTLED: {}'.format(order))
                    os.rename(self.buy_path, self.buy_path+'.prev')
                    profit = Decimal(order['executed_value']) - Decimal(buy['settled']['executed_value'])
                    self.logit('PROFIT: {} -> {} {:.2f} ({:.2f}%)'.format(
                        buy['real_price'], price, profit, pchange(buy['real_price'], price)
                    ))
                    if self.email_enabled:
                        self.send_email('SOLD: profit={:,.2f}'.format(profit), '')
                    break
        else:
            self.logit('NOOP')

    def _monitor(self):
        """Track the status of a buy and log the history of percentage change. Alert on slippage
        from high percent change.
        """
        # Skip running if no buys in place
        if not os.path.exists(self.buy_path):
            return
        monitor_path = self.buy_path+'.monitor'
        monitor_history = []
        if os.path.exists(monitor_path):
            with open(monitor_path, 'rb') as fd:
                monitor_history = pickle.load(fd)
        price = self.get_price()
        with open(self.buy_path, 'rb') as fd:
            buy = pickle.load(fd)
        pc = pchange(buy['real_price'], price)
        duration_hours = (time.time() - buy['buy_epoch'])/ 60.0 / 60.0
        if self.debug:
            print('MONITOR: duration:{:.2f}h percent_change:{:,.2f}%  previous:'.format(
                duration_hours, pc))
            for m in monitor_history[::-1]:
                print('    {:.2f}%'.format(m))
        if len(monitor_history) > 1:
            mmax = max(monitor_history)
            mmin = min(monitor_history)
            diff = pc - mmax
            if diff <= self.monitor_alert_change:
                if self.email_enabled:
                    self.send_email('MONITOR-WARNING: diff={:.2f}'.format(diff), '')
            if self.debug:
                self.logit('MONITOR: diff={:.2f}'.format(diff))
        monitor_history.append(pc)
        with open(monitor_path, 'wb') as fd:
            pickle.dump(monitor_history, fd)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dryrun', help='Dryrun mode', action='store_true')
    parser.add_argument('--debug', help='Debug output', action='store_true')
    parser.add_argument('--force-sell', help='Force sell of holdings tracked in the buy cache',
            dest='force_sell', action='store_true')
    parser.add_argument('--config', help='Config file path', dest='config_path', required=True)
    parser.add_argument('--monitor', help='Monitor buy state/percent change', action='store_true')
    args = parser.parse_args()
    ema_bot = EmaBot(
        args.config_path,
        dryrun=args.dryrun,
        debug=args.debug,
        monitor=args.monitor,
        force_sell=args.force_sell)
    ema_bot.run()

if __name__ == '__main__':
    main()
