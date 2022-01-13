# emabot

# Setup

Decompress the `*.csv.gz` files to get started.
```
gunzip *.csv.gz
```

Create directories:
```
mkdir log data
```

Configure a bot:
1. In Coinbase, create a new portofolio dedicated to this bot.
2. Create a new emabot config labeled after that portfolio:
```
cp -a etc/example.yml etc/PORTFOLIO-NAME.yml
chmod 600 etc/PORTFOLOIO-NAME.yml
vi etc/PORTFOLIO-NAME.yml
```

Setup a cronjob at 00:00:00 UTC (set system tz to UTC first). Example:
```
00 00 * * * (cd /opt/emabot && bash run.sh)
```
