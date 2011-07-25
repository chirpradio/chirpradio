#!/usr/bin/env python
"""Script to check the integrity of the local music library.

First, download all known library data from App Engine:

    ./appcfg.py download_data . --filename=tracks.csv --kind=Track --config_file=adhoc/libcheck_download.yaml --url https://chirpradio.appspot.com/remote_api

Then run this script.
"""
import csv
import os
import optparse
import sqlite3


def main():
    p = optparse.OptionParser(usage='%prog [options] tracks.csv /traktor/Library/vol01')
    (options, args) = p.parse_args()
    if len(args) != 2:
        p.error('Incorrect usage')
    tracks_csv, libpath = args
    libpath = os.path.abspath(libpath)
    rdr = csv.DictReader(open(tracks_csv))
    found = total = 0
    for row in rdr:
        total += 1
        # djdb/t:vol01/20090614-212042/0ce263395ee7c173db3a77b56e3c7e1470e7fcb3
        key = row['key']
        dir, fingerprint = key.split('/')[-2:]
        dest = '%s.mp3' % os.path.join(libpath, dir, fingerprint)
        if not os.path.exists(dest):
            print '* MISSING: %s; PATH: %s' % (fingerprint, dest)
        else:
            found += 1
    print 'Done. FOUND: %s; TOTAL: %s' % (found, total)

    # conn = sqlite3.connect(dbfile)
    # cursor = conn.cursor()
    # cursor.execute('select fingerprint from audio_files')
    # while True:
    #     row = cursor.fetchone()
    #     if row is None:
    #         break
    #     print row[0]

if __name__ == '__main__':
    main()
