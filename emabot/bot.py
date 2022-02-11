"""
Use emaA and emaB to determine buy/sell
"""
import os
import sys
import time
import re
import pickle
import warnings
import argparse
from datetime import datetime
from decimal import Decimal
import logging
import smtplib
import yaml
import cbpro
import numpy as np
import talib
import pandas as pd
import pandas_ta as ta
from .history import generate_historical_csv

pd.set_option('display.max_rows', None)
os.environ['TZ'] = 'UTC'
time.tzset()
TODAY = str(datetime.now()).split(' ')[0]

warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)

logger = logging.getLogger('emabot')


class TradingDisabledError(Exception):
    """Trading is disabled for currency"""

def _api_response_check(response: dict, exception_to_raise: Exception) -> None:
    """Check the coinbase API response for 'message' (an error)"""
    if 'message' in response:
        raise exception_to_raise(response['message'])

def truncate(x, n: int) -> str:
    """Truncate to N decimals, return as string"""
    if not '.' in str(x):
        return str(x) + '.0'
    a, b = str(x).split('.')
    b = b[:n]
    return a+'.'+b

def truncate_f(x, n: int) -> float:
    """Truncate to N decimals, return as float"""
    if not '.' in str(x):
        return str(x) + '.0'
    a, b = str(x).split('.')
    b = b[:n]
    return float(a+'.'+b)

def pchange(x1, x2) -> float:
    """Percent change"""
    x1 = float(x1)
    x2 = float(x2)
    return round(((x2 - x1) / x1) * 100., 1)

def pchange_f(x1, x2) -> float:
    """Percent change as truncated float"""
    x1 = float(x1)
    x2 = float(x2)
    return truncate_f(((x2 - x1) / x1) * 100., 1)

def backtest_decider(
        emaA: int = 2,
        emaB: int = 3,
        resample: str = '1D',
        cur_price: float = None,
        csv_path: str = None,
        debug: bool = False) -> str:
    """Main buy/sell logic
        1) Read CSV OHLC file
        2) Convert timestamp to datetime index column
        3) Drop all columns except timestamp and close
        4) Resample OHLC
        5) Calculate EMAs
        6) Fill NaNs (pandas ffill)
        7) Drop NaN rows as a mistake guard
        8) Compare the last dataframe's EMAs to make decision
    """
    df = pd.read_csv(csv_path)
    if cur_price:
        # Add the current price to the tail end for a more accurate calculation
        # timestamp       low      high      open     close    volume
        df.loc[len(df.index)] = [
            int(time.time()),
            float(cur_price),
            float(cur_price),
            float(cur_price),
            float(cur_price), 2.0
        ]
    df.timestamp = pd.to_datetime(df.timestamp, unit='s')
    df = df.set_index("timestamp")
    df = df.drop(columns=['open','high','low','volume'])
    # Resample needs to be done for further stabalization of EMA, otherwise it will vary per run
    idf = df.resample(resample).ohlc()
    # explicitly use talib because pandas_ta sometimes doesn't work right and provides an
    # unstable EMA (as far as testing could tell)
    # It is important to note that this can differ from backtests since those are calculated in
    # one call for the entire dataset. It is even more _important_ to note that 'resample' needs
    # to match the timing of the cronjob. Example: 1D should run once per day at 00, or 12h should
    # run twice per day at 00 and 12
    emaA = talib.EMA(idf['close']['close'], emaA)
    emaB = talib.EMA(idf['close']['close'], emaB)
    # don't need this anymore since EMA calc was moved outside of storing within df
    #df.fillna(method='ffill', inplace=True)
    #df.dropna(axis='rows', how='any', inplace=True)
    # Decision time
    last_decision = 'noop'
    close = df['close'].tail(1).item()
    # Take the 2nd to last item (assuming cronjob is scheduled properly)
    if debug:
        print(emaA.tail(10))
    emaA = emaA.tail(2).head(1).item()
    emaB = emaB.tail(2).head(1).item()
    if emaA > emaB:
        last_decision = 'buy'
    elif emaB > emaA:
        last_decision = 'sell'
    return {'emaA':emaA, 'emaB':emaB, 'decision':last_decision, 'close':close}

class EmaBot:
    """Main code for running the bot"""
    def __init__(self,
            config_path: str,
            dryrun: bool = False,
            force_sell: bool = False,
            monitor: bool = False,
            debug: bool = False):
        self.config_path = config_path
        self.debug = debug
        self.force_sell = force_sell
        self.dryrun = dryrun
        self.monitor = monitor
        self.config = {}
        self.name = None
        self.currency = None
        self.pair = None
        self.b64secret = None
        self.passphrase = None
        self.key = None
        self.data_dir = None
        self.log_dir = None
        self.hist_file = None
        self.buy_path = None
        self.decision = {'emaA':0.0, 'emaB':0.0, 'decision':'noop'}
        if self.debug:
            logger.setLevel(logging.DEBUG)
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            logger.debug('DEBUG=on')
        self.configure()

    def configure(self) -> None:
        """Configure from yaml file"""
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
                'b64secret', 'pair', 'hist_file', 'monitor_alert_change', 'currency',
                'ema_a', 'ema_b', 'resample',):
            if not i in config['general']:
                missing.append(i)
        if missing:
            raise Exception('Missing general config items: {}'.format(', '.join(missing)))
        self.config = config
        self.name = self.config['general']['name']
        self.pair = self.config['general']['pair']
        self.ema_a = int(self.config['general']['ema_a'])
        self.ema_b = int(self.config['general']['ema_b'])
        self.resample = str(self.config['general']['resample'])
        self.currency = self.config['general']['currency']
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

    def logit(self, msg) -> None:
        """Logger with some customizations.
        TODO: Maybe convert to logging module"""
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
        """Send an email
        TODO: Add auth, currently setup to relay locally or relay-by-IP"""
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

    def cb_auth(self) -> None:
        """Authenticate to coinbase api"""
        self.auth_client = cbpro.AuthenticatedClient(
            self.key, self.b64secret, self.passphrase)

    def get_wallet(self) -> Decimal:
        accounts = self.auth_client.get_accounts()
        _api_response_check(accounts, Exception)
        for account in accounts:
            if account['currency'] == self.currency:
                wallet = Decimal(account['available'])
                if not account['trading_enabled']:
                    raise TradingDisabledError('trading_enabled=False for {}'.format(self.currency))
                break
        assert wallet is not None, 'USD wallet was not found.'
        return wallet

    def get_fees(self) -> tuple:
        """Get the current account fees for maker/taker"""
        fees = self.auth_client._send_message('get', '/fees')
        _api_response_check(fees, Exception)
        maker_fee = Decimal(fees['maker_fee_rate'])
        taker_fee = Decimal(fees['taker_fee_rate'])
        usd_volume = Decimal(fees['usd_volume'])
        return (maker_fee, taker_fee, usd_volume)

    def get_price(self) -> Decimal:
        """Get current pair price"""
        ticker = self.auth_client.get_product_ticker(product_id=self.pair)
        _api_response_check(ticker, Exception)
        price = Decimal(ticker['price'])
        return price

    def get_order(self, order_id: str) -> dict:
        """Get an order by id"""
        order = self.auth_client.get_order(order_id)
        _api_response_check(order, Exception)
        return order

    def buy_market(self, funds: float) -> dict:
        funds = truncate(funds, 2) #str(round(Decimal(funds), 2))
        response = self.auth_client.place_market_order(
            product_id=self.pair,
            side='buy',
            funds=funds,
        )
        _api_response_check(response, Exception)
        return response

    def sell_market(self, size: float) -> dict:
        # TODO: Get precisions from api for the self.pair
        fixed_size = truncate(size, 8) #str(round(Decimal(size), 8))
        response = self.auth_client.place_market_order(
            product_id=self.pair,
            side='sell',
            size=fixed_size,
        )
        _api_response_check(response, Exception)
        return response

    def _run_setup(self):
        generate_historical_csv(self.hist_file, pair=self.pair, days_ago=522)
        wallet = self.get_wallet()
        fees = self.get_fees()
        price = self.get_price()
        buy = None
        pc = None
        if os.path.exists(self.buy_path):
            with open(self.buy_path, 'rb') as fd:
                buy = pickle.load(fd)
                pc = pchange(buy['real_price'], price)
        self.logit('>\n  bought_at={}\n  wallet={}\n  current_fees={}\n  price={}\n  percent_change={}'.format(
            buy['real_price'] if buy and 'real_price' in buy else "-",
            wallet, [str(i) for i in fees], price, pc))
        return (wallet, fees, price, buy)

    def _run_buy(self, price, wallet) -> None:
        self.logit('action=buy price={}'.format(price))
        if self.dryrun:
            sys.exit(0)
        response = self.buy_market(wallet)
        self.logit('buy_response={}'.format(response))
        with open(self.buy_path+'.tmp', 'wb') as fd:
            info = {
                'wallet':wallet,
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
                self.logit('buy_settled={}'.format(order))
                with open(self.buy_path+'.tmp', 'wb') as fd:
                    pickle.dump(info, fd)
                os.rename(self.buy_path+'.tmp', self.buy_path)
                if self.email_enabled:
                    self.send_email('BOUGHT: price={} decision={}'.format(price, self.decision), '')
                break

    def _run_sell(self, buy, price):
        size = buy['settled']['filled_size']
        self.logit('action=sell price={} size={}'.format(price, size))
        if self.dryrun:
            u_before = float(buy['real_price']) * float(buy['settled']['filled_size'])
            u_after = float(price) * float(buy['settled']['filled_size'])
            print('if_sold_now: {} -> {} {:.2f} {:.2f}% change'.format(
                buy['real_price'], price, u_after - u_before, pchange_f(buy['real_price'], price)
            ))
            sys.exit(0)
        response = self.sell_market(size)
        self.logit('sell_response={}'.format(response))
        while 1:
            time.sleep(5)
            order = self.get_order(response['id'])
            settled = order['settled']
            status = order['status']
            if settled:
                self.logit('sell_settled={}'.format(order))
                os.rename(self.buy_path, self.buy_path+'.prev')
                profit = Decimal(order['executed_value']) - Decimal(buy['settled']['executed_value'])
                self.logit('profit: buy_price={} -> sold_price={} profit={:.2f} ({:.2f}%)'.format(
                    buy['real_price'], price, profit, pchange(buy['real_price'], price)
                ))
                if self.email_enabled:
                    self.send_email('SOLD: price={} profit={} decision={}'.format(
                        price, profit, self.decision), '')
                    monitor_path = self.buy_path+'.monitor'
                    os.rename(monitor_path, monitor_path+'.prev')
                break


    def run(self) -> None:
        self.cb_auth()
        if self.monitor:
            return self._monitor()
        wallet, fees, price, buy = self._run_setup()

        ###################################################################
        # buy/sell phase is here
        ###################################################################
        self.decision = backtest_decider(
            emaA=self.ema_a,
            emaB=self.ema_b,
            csv_path=self.hist_file,
            resample=self.resample,
            debug=self.debug,
            # this should not matter unless a not so sane resmaple size is used
            #cur_price=price
        )
        self.logit('backtest_decider={}'.format(self.decision))
        logger.debug('decider=%s price=%s', self.decision, price)
        if not buy and self.decision['decision'] == 'buy':
            self._run_buy(price, wallet)
        # SELL logic
        elif buy and (self.decision['decision'] == 'sell' or self.force_sell):
            if self.force_sell:
                self.logit('WARNING: Selling because force_sell=True')
            self._run_sell(buy, price)
        else:
            self.logit('action=NOOP')
            if buy and self.dryrun:
                u_before = float(buy['real_price']) * float(buy['settled']['filled_size'])
                u_after = float(price) * float(buy['settled']['filled_size'])
                print('if_sold_now: {} -> {} {:.2f} {:.2f}% change'.format(
                    buy['real_price'], price, u_after - u_before, pchange_f(buy['real_price'], price)
                ))

    def _monitor(self) -> None:
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
            logger.debug('MONITOR: duration=%sh percent_change=%s%%  previous=',
                duration_hours, pc)
            for m in monitor_history[::-1]:
                logger.debug('    %.2f%%', m)
        if len(monitor_history) > 1:
            mmax = max(monitor_history)
            mmin = min(monitor_history)
            diff = pc - mmax
            if diff <= self.monitor_alert_change:
                if self.email_enabled:
                    self.send_email('MONITOR-WARNING: diff={:.2f}'.format(diff), '')
            logger.debug('MONITOR: diff=%s', diff)
        monitor_history.append(pc)
        with open(monitor_path, 'wb') as fd:
            pickle.dump(monitor_history, fd)

def main() -> None:
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
