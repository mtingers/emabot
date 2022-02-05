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
apt install gcc g++

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

Setup a cronjob at every hour (set system tz to UTC first).

**TODO** Determine if running per hour makes sense.
The backtests show only transactions on `00:00:00`,
which kind of makes sense, but I haven't had time to think about it.
that will continue on until the next day,
causing the validity of it to slip from the original price point
if a buy is outside of `00:00:00`.  In somecases, it may be preferred to try on multiple hours, like
in the case of an error and a retry is needed (exchange is down).

Example setup:
```
00 * * * * (cd /opt/emabot && bash run.sh)
# TODO: or once per day
#00 00 * * * (cd /opt/emabot && bash run.sh)
# Or retry around 00
#00 00,01,02,03 * * * (cd /opt/emabot && bash run.sh)

# Monitor each buy to report drops
30 * * * * (cd /opt/emabot && bash monitor.sh)
```

# Backtesting
* [BTC Sample Backtest](/backtests/backtest-btc.log)
* [ETH Sample Backtest](/backtests/backtest-eth.log)
```bash
(venv) emabot@local:/opt/emabot$ backtest  -h
usage: backtest [-h] --csv-file CSV_FILE

optional arguments:
  -h, --help           show this help message and exit
    --csv-file CSV_FILE  Path to OHLC CSV file
```
```bash
(venv) emabot@local:/opt/emabot$ time backtest  --csv-file btc-history-1m-ohlc.csv
  5%|███████▎                            | 2425/46628 [00:01<00:32, 1359.63it/s]
```
