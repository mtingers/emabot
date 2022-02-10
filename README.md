# emabot

# Requirements

1. Linux VM (a cheap digitalocean $5/month VM will suffice)
2. Python3.6+
3. A Coinbase Pro account
4. Funds in your Coinbase Pro account :)

# Setup

Install emabot:
```
# debian:
apt install gcc g++ make

# Install TA-lib so pandas_ta uses a stable EMA calculation
# Required for Python TA-lib to build on pip install
cd talib/
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib
./configure --prefix=/usr
make
sudo make install
cd ../../

python3 -m venv venv
. venv/bin/activate
pip install pip -U
# Some of these take a while to build
pip install .
```

Decompress the `*.csv.gz` files to get started.
```
gunzip csv/*.csv.gz
```

Create directories:
```
mkdir log data
```

Configure a bot:
1. In Coinbase, create a new portofolio dedicated to this bot (it uses all
   available funds).
2. Create new Coinbase API keys with view & trade permissions (assigned to the
   new portfolio).
3. Create a new emabot config labeled after that portfolio:
```
cp -a etc/yml.example etc/PORTFOLIO-NAME.yml
chmod 600 etc/PORTFOLOIO-NAME.yml
# Edit config and update parameters accordingly
vi etc/PORTFOLIO-NAME.yml
```

*IMPORTANT* Before continuing make sure to read and understand this section about cronjobs and
how it relates to resample time.

* Cronjobs need to match the resample time closely
* If there is a mismatch in the resample time and period at which the cronjob runs, an invalid EMA
  will be calculated.
* Example: If a resample time of `1D` is specified, the cronjob should _only_ run at `00` hour.
* Example: If a resample time of `12h` is specified, the cronjob should run at both `12` and `00`
  hours.
* Example: If a resample time of `1h` is specified, the cronjob should run at every hour.
* If you are setting up different resample times for config, you will need to manually create
  separate copies of run.sh.


Example setup:
```
# For a 1D resample time
00 00 * * * * (cd /opt/emabot && bash run.sh)
# For a 12h resample time
00 00,12 * * * * (cd /opt/emabot && bash run.sh)

# Monitor each buy to report drops
30 * * * * (cd /opt/emabot && bash monitor.sh)
```
# TODO
- Dump current buys from data dir
- Save buy/sell history to a structured format for stats

# Backtesting
* [BTC Sample Backtest](/backtests/backtest-btc.log)
* [ETH Sample Backtest](/backtests/backtest-eth.log)
```bash
(venv) $ backtest --help
usage: backtest [-h] --csv-file CSV_FILE [--resample RESAMPLE] [--ema-a EMA_A]
                [--ema-b EMA_B] [--strategy STRATEGY] [--debug] [--dump-ohlc]
                [--c2c]

optional arguments:
  -h, --help           show this help message and exit
  --csv-file CSV_FILE  Path to OHLC CSV file
  --resample RESAMPLE  Set the OHLC resample size (default:1D)
  --ema-a EMA_A        Set the emaA paramater (default:2)
  --ema-b EMA_B        Set the emaB paramater (default:3)
  --strategy STRATEGY  Select which strategy class to use (see emabot/strats/)
  --debug              Enable debug output
  --dump-ohlc          Dump the OHLC sequence data
  --c2c                Coin-to-coin (higher precision)
```
```bash
(venv) $ time backtest  --csv-file csv/btc-history-1m-ohlc.csv \
    --ema-a 2 --ema-b 3 \
    --resample 1D \
    --strategy emabot.strats.backtestema.BacktestEma
  5%|███████▎                            | 2425/46628 [00:01<00:32, 1359.63it/s]
```

Example log:
```
Sell log:
╒═════════════════════╤═════════════╤══════════════╤═══════════════════════╤═══════════╤════════════════════════╕
│ Date                │ Buy Price   │ Sell Price   │ Net Profit            │   Percent │ Wallet                 │
╞═════════════════════╪═════════════╪══════════════╪═══════════════════════╪═══════════╪════════════════════════╡
│ 2017-12-05 00:00:00 │ 433.60      │ 468.29       │ 74.00                 │      8    │ 1,074.00               │
├─────────────────────┼─────────────┼──────────────┼───────────────────────┼───────────┼────────────────────────┤
│ 2017-12-10 00:00:00 │ 433.39      │ 484.41       │ 119.99                │     11.77 │ 1,194.00               │
├─────────────────────┼─────────────┼──────────────┼───────────────────────┼───────────┼────────────────────────┤
│ 2017-12-15 00:00:00 │ 447.03      │ 705.01       │ 681.89                │     57.71 │ 1,875.88               │
├─────────────────────┼─────────────┼──────────────┼───────────────────────┼───────────┼────────────────────────┤
│ 2017-12-20 00:00:00 │ 693.78      │ 826.65       │ 348.01                │     19.15 │ 2,223.89               │
├─────────────────────┼─────────────┼──────────────┼───────────────────────┼───────────┼────────────────────────┤
│ 2017-12-24 00:00:00 │ 682.04      │ 733.99       │ 156.05                │      7.62 │ 2,379.94               │
├─────────────────────┼─────────────┼──────────────┼───────────────────────┼───────────┼────────────────────────┤
│ 2017-12-27 00:00:00 │ 698.35      │ 755.71       │ 181.20                │      8.21 │ 2,561.14               │
├─────────────────────┼─────────────┼──────────────┼───────────────────────┼───────────┼────────────────────────┤
│ 2017-12-30 00:00:00 │ 719.50      │ 748.90       │ 89.29                 │      4.09 │ 2,650.42               │
├─────────────────────┼─────────────┼──────────────┼───────────────────────┼───────────┼────────────────────────┤
│ 2018-01-11 00:00:00 │ 710.01      │ 1,256.20     │ 2,022.99              │     76.93 │ 4,673.41               │
├─────────────────────┼─────────────┼──────────────┼───────────────────────┼───────────┼────────────────────────┤
│ 2018-01-15 00:00:00 │ 1,138.54    │ 1,362.00     │ 889.21                │     19.63 │ 5,562.62               │
├─────────────────────┼─────────────┼──────────────┼───────────────────────┼───────────┼────────────────────────┤
│ 2018-01-21 00:00:00 │ 1,037.77    │ 1,150.01     │ 568.25                │     10.82 │ 6,130.87               │
├─────────────────────┼─────────────┼──────────────┼───────────────────────┼───────────┼────────────────────────┤
│ 2018-01-29 00:00:00 │ 985.00      │ 1,215.01     │ 1,394.85              │     23.35 │ 7,525.72               │
├─────────────────────┼─────────────┼──────────────┼───────────────────────┼───────────┼────────────────────────┤
│ 2018-02-01 00:00:00 │ 1,055.00    │ 1,105.01     │ 311.59                │      4.74 │ 7,837.31               │
├─────────────────────┼─────────────┼──────────────┼───────────────────────┼───────────┼────────────────────────┤
│ 2018-02-04 00:00:00 │ 912.00      │ 965.00       │ 408.43                │      5.81 │ 8,245.74               │
├─────────────────────┼─────────────┼──────────────┼───────────────────────┼───────────┼────────────────────────┤
│ 2018-02-07 00:00:00 │ 699.10      │ 789.00       │ 1,010.88              │     12.86 │ 9,256.62               │
├─────────────────────┼─────────────┼──────────────┼───────────────────────┼───────────┼────────────────────────┤
│ 2018-02-11 00:00:00 │ 748.00      │ 850.83       │ 1,217.00              │     13.75 │ 10,473.61              │
...
...
╘═════════════════════╧═════════════╧══════════════╧═══════════════════════╧═══════════╧════════════════════════╛

Month breakdown (percent):
╒═════════╤═══════════╤════════════════╤══════════════════╤════════════════╕
│ Date    │   Percent │   Percent Mean │   Percent Median │   Transactions │
╞═════════╪═══════════╪════════════════╪══════════════════╪════════════════╡
│ 2017-12 │    116.55 │          16.65 │             8.21 │              7 │
├─────────┼───────────┼────────────────┼──────────────────┼────────────────┤
│ 2018-01 │    130.72 │          32.68 │            21.49 │              4 │
├─────────┼───────────┼────────────────┼──────────────────┼────────────────┤
│ 2018-02 │     72.35 │           8.04 │             5.81 │              9 │
├─────────┼───────────┼────────────────┼──────────────────┼────────────────┤
│ 2018-03 │     16.1  │           3.22 │             3.27 │              5 │
├─────────┼───────────┼────────────────┼──────────────────┼────────────────┤
│ 2018-04 │    107.74 │          21.55 │             8.37 │              5 │
├─────────┼───────────┼────────────────┼──────────────────┼────────────────┤
│ 2018-05 │     33.87 │          11.29 │             6.83 │              3 │
├─────────┼───────────┼────────────────┼──────────────────┼────────────────┤
│ 2018-06 │     45.5  │           9.1  │             9.2  │              5 │
├─────────┼───────────┼────────────────┼──────────────────┼────────────────┤
│ 2018-07 │     42.82 │           7.14 │             4.97 │              6 │
├─────────┼───────────┼────────────────┼──────────────────┼────────────────┤
│ 2018-08 │     31.88 │           5.31 │             4.13 │              6 │
...
...
├─────────┼───────────┼────────────────┼──────────────────┼────────────────┤
│ 2022-01 │     24.81 │           3.54 │             3.44 │              7 │
├─────────┼───────────┼────────────────┼──────────────────┼────────────────┤
│ 2022-02 │     15.22 │          15.22 │            15.22 │              1 │
╘═════════╧═══════════╧════════════════╧══════════════════╧════════════════╛
Results:
╒════════════════════════╤══════════════════════════╤════════╤══════════╤════════════════════════╕
│   Monthly Mean Percent │   Monthly Median Percent │   Wins │   Losses │ Total Net Profit       │
╞════════════════════════╪══════════════════════════╪════════╪══════════╪════════════════════════╡
│                  58.71 │                    50.43 │    295 │       11 │ 113,010,519,465,138.79 │
╘════════════════════════╧══════════════════════════╧════════╧══════════╧════════════════════════╛
```
