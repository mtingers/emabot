import sys
import os
import time
import datetime
from datetime import timedelta
import json
import cbpro

os.environ['TZ'] = 'UTC'
time.tzset()

SIZE = 60

def date2str(dtobj_or_str):
    """Convert date to str"""
    return str(dtobj_or_str).replace(' ', 'T').split('.')[0]+'Z'

def generate_historical_csv(outfile, pair='BTC-USD', days_ago=522, debug=False):
    """Generate CSV file from coinbase get_product_historic_rates.
    Append to existing file if it exists.
    """
    # pylint: disable=too-many-locals
    public_client = cbpro.PublicClient()
    last_date = None
    first_date = None
    prev_data = []
    if os.path.exists(outfile):
        if debug:
            print('reading prev file')
        prev_data = open(outfile).read().strip().split('\n')
    if len(prev_data) > 10:
        if debug:
            print('prev_data length:', len(prev_data))
        first_date = float(prev_data[1].split(',')[0].replace('"', ''))
        last_date = float(prev_data[-1].split(',')[0].replace('"', ''))
        diff_first = int((time.time() - first_date) / 86400) + 86400
        diff_last = int((time.time() - last_date) / 86400)
        # if days_ago is > what the file had, rewrite everything
        if days_ago > diff_first:
            print('rewriting entire file since days_ago > diff_first: {} > {}'.format(days_ago, diff_first))
            start_date = datetime.datetime.now() - timedelta(days=days_ago)
            next_date = start_date # + timedelta(minutes=SIZE)
            last_date = None
            out_fd = open(outfile, 'w')
            out_fd.write('"timestamp","low","high","open","close","volume"\n')
        else:
            if debug:
                print('appending to file')
            start_date = datetime.datetime.now() - timedelta(days=diff_last+1)
            next_date = start_date #  + timedelta(minutes=SIZE)
            out_fd = open(outfile, 'a')
        end_date = datetime.datetime.now()+timedelta(days=1)
    else:
        if debug:
            print('truncate file, new data')
        start_date = datetime.datetime.now() - timedelta(days=days_ago)
        end_date = datetime.datetime.now()+timedelta(days=1)
        next_date = start_date # + timedelta(minutes=SIZE)
        out_fd = open(outfile, 'w')
        out_fd.write('"timestamp","low","high","open","close","volume"\n')

    if debug:
        print('start_date:', start_date, 'next_date:', end_date)
    misses = 0
    while next_date < end_date:
        start_str = date2str(next_date)
        end_str = date2str(next_date+timedelta(hours=4))
        stats = None
        error = False
        if debug:
            print('start_str:', start_str, 'end_str:', end_str)
        for attempt in range(14):
            try:
                stats = public_client.get_product_historic_rates(
                    pair,
                    granularity=SIZE,
                    start=date2str(next_date),
                    end=date2str(next_date+timedelta(hours=4)))
                error = False
                if debug:
                    print('stats length:', len(stats))
                break
            except json.decoder.JSONDecodeError as e:
                print(e)
                error = True
                time.sleep(10)
        if error:
            print('API_ERROR: history API failed after many retries')
            sys.exit(1)
        if 'message' in stats:
            print('API_ERROR:', stats['message'])
            sys.exit(1)
        next_date = next_date + timedelta(hours=4)
        # stats are from newest to oldest, so reverse it
        stats.reverse()
        if len(stats) < 1:
            misses += 1
            if misses > 10:
                print('stats len < 1 {} times. stopping.'.format(misses))
                break
        for i in stats:
            (tstamp, low, high, x_open, x_close, x_volume) = i
            if last_date and last_date >= tstamp:
                #print('skip: {} > {}'.format(last_date, tstamp))
                continue
            out_fd.write('"{}","{}","{}","{}","{}","{}"\n'.format(
                tstamp, low, high, x_open, x_close, x_volume))
            last_date = tstamp
        time.sleep(2.0)
    out_fd.close()

def main():
    generate_historical_csv(sys.argv[1], pair='BTC-USD', days_ago=522)

if __name__ == '__main__':
    main()

