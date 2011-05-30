#! /usr/bin/python
#
# Script for Simon Demissie to take a CKAN JSON dump and extract all the URLS.
#
# For help:
#   python extract_urls.py
#

import sys
import json

usage = '''
URL extractor
=============

Takes a CKAN dump (JSON) format and writes all the urls to a CSV file.

Usage:
  %s data.gov.uk-ckan-meta-data.json urls.csv
  ''' % sys.argv[0]
if len(sys.argv) < 3:
    print usage
    sys.exit(1)
in_fname = sys.argv[1]
out_fname = sys.argv[2]
f = open(in_fname)
try:
    print 'Reading %r' % in_fname
    pkgs_json = f.read()
finally:
    f.close()
print 'Parsing'
pkgs = json.loads(pkgs_json)
print 'Found %i packages' % len(pkgs)
print 'Writing URLs to %r' % out_fname
out = open(out_fname, 'w')
try:
    for pkg in pkgs:
        urls = set()
        for url in (pkg['url'],
                    pkg['extras'].get('taxonomy_url')):
            if url:
                urls.add(url)
        for res in pkg['resources']:
            url = res.get('url')
            if url:
                urls.add(url)
        for url in urls:
            out.write('%s\r\n' % url.encode('utf8'))
finally:
    f.close()
print 'Finished successfully'
