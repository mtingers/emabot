#!/bin/bash
# Schedule from cron for 00:00:00 UTC
set -e
HOMEDIR="/opt/emabot"
CONFDIR=$HOMEDIR/etc

cd $HOMEDIR
for config in $CONFDIR/*.yml; do
    echo "Run config: $config"
    $HOMEDIR/venv/bin/emabot --config "${config}"
done
