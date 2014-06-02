"""
A very simple script to ping a handful of URLs and make sure that they return
200 and not 5XX, to be used during the switchover from master to stable when
deploying to staging.
"""
import sys
import requests
import time
from urlparse import urljoin

urls = [
    "/data",
    "/publisher",
    "/publisher/office-for-national-statistics",
    "/data/search",
    "/data/map-based-search",
    "/dataset/uk-tariff-codes-2009-2010",
    "/dataset/mot-active-vts/resource/2ac8abba-4a71-4f12-af1b-57ad0e36b6a4",
    "/data/preview/9f4c0f50-984d-49a6-b81e-6e7ad0cd14e8",
    "/data/openspending-report/index",
    "/data/openspending-report/publisher-cabinet-office.html",
    "/data/site-usage",
    "/data/site-usage/publisher",
    ("/publisher/new", 401),
]

def build_url(name):
    if name == 'localhost':
        return "http://localhost"
    elif name == 'localhost:8080':
        return "http://localhost:8080"
    elif name == 'prod1':
        return "http://data.gov.uk"
    return "http://co-{0}.dh.bytemark.co.uk".format(name)

servers = []
server_name = build_url(sys.argv[1] if len(sys.argv) > 1 else "dev1")
print "Testing {0}".format(server_name)
error_occurred = False

for url in urls:
    if isinstance(url, tuple):
        url, expected_status = url
    else:
        expected_status = 200
    target = urljoin(server_name, url)
    s = time.time()
    r = requests.get(target)
    took = time.time() - s
    if r.status_code == expected_status:
        msg = 'OK'
    else:
        msg = 'STATUS ERROR'
        error_occurred = True
    print msg, r.status_code, "{0:.2}s".format(took), target

print
if error_occurred:
    print 'ERROR OCCURRED'
    sys.exit(1)
else:
    print 'All OK'
