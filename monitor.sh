#!/bin/bash
# Schedule from cron every 30 minutes, not on the hour
set -e
HOMEDIR="/opt/emabot"
CONFDIR=$HOMEDIR/etc

cd $HOMEDIR
for config in $CONFDIR/*.yml; do
    $HOMEDIR/venv/bin/emabot --monitor --config "${config}"
done
