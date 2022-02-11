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

**IMPORTANT** Before continuing make sure to read and understand this section about cronjobs and
how it relates to resample time.

* Cronjobs need to match the resample time closely
* If there is a mismatch in the resample time and period at which the cronjob runs, an invalid EMA
  will be calculated.
* The bot selects the previous calculated EMA (not the latest since that require the entire resample
  period to be stable). This means that the cronjob needs to be scheduled closely after the resample
  time.
* Example: If a resample time of `1D` is specified, the cronjob will be:
  `04 00 * * *`
* Example: If a resample time of `12h` is specified, the cronjob should run twice per day:
  `04 00,12 * * *`
* Example: If a resample time of `1h` is specified, the cronjob should run once per hour like:
  `04 * * * *`
* It is recommended to set the cronjob's minute not to `00` but a few minutes after to ensure the
  exchange gives you the latest data that maps to the resample period.

Example setup:
```
# For a 1D resample time
04 00 * * * (cd /opt/emabot && venv/bin/emabot --config etc/myconfig.yml)
# For a 12h resample time
04 00,12* * * (cd /opt/emabot && venv/bin/emabot --config etc/myconfig.yml)

# Monitor each buy to report drops
30 * * * * (cd /opt/emabot && venv/bin/emabot --monitor --config etc/myconfig.yml)
```
# Backtesting
* [BTC Sample Backtest](/backtests/btc-2-3-1D.log)
* [ETH Sample Backtest](/backtests/eth-2-3-1D.log)
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
    --resample 1D
  5%|███████▎                            | 2425/46628 [00:01<00:32, 1359.63it/s]
```

# TODO
- Dump current buys from data dir
- Save buy/sell history to a structured format for stats
- Explain how the EMA calculations and timing work in depth
