# emabot

# Requirements

1. Linux VM (a cheap digitalocean $5/month VM will suffice)
2. Python3.6+
3. A Coinbase Pro account
4. Funds in your Coinbase Pro account :)

# Setup

Install emabot:
```
pip install .
```

Decompress the `*.csv.gz` files to get started.
```
gunzip *.csv.gz
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
cp -a etc/example.yml etc/PORTFOLIO-NAME.yml
chmod 600 etc/PORTFOLOIO-NAME.yml
# Edit config and update parameters accordingly
vi etc/PORTFOLIO-NAME.yml
```

Setup a cronjob at 00:00:00 UTC (set system tz to UTC first). Example:
```
00 00 * * * (cd /opt/emabot && bash run.sh)
```
