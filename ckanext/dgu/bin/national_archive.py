'''Fix links that are broken by using the National Archive cache.
'''

import os
import random
import time
import datetime

from optparse import OptionParser
import requests

import common
from running_stats import StatsList


USER_AGENT = {'User-agent': 'data.gov.uk - please contact david.read@hackneyworkshop.com with any problems'}


def fix_links(options):
    from ckan import model
    from ckanext.archiver.model import Archival
    write = options.write
    if write:
        rev = model.repo.new_revision()
        rev.author = 'script-fix-links-tna'
        needs_commit = False
    stats = StatsList()

    # Get resources
    results = model.Session.query(Archival, model.Resource)
    if options.resource:
        results = results.filter(Archival.resource_id==options.resource)
    elif options.dataset:
        pkg = model.Package.get(options.dataset)
        assert pkg
        results = results.filter(Archival.package_id==pkg.id)\
                             .order_by(model.Resource.position)
    results = results.filter(Archival.is_broken == True)\
                    .join(model.Package, Archival.package_id == model.Package.id)\
                    .filter(model.Package.state == 'active')\
                    .join(model.Resource, Archival.resource_id == model.Resource.id)\
                    .filter(model.Resource.state == 'active')\
                    .order_by(model.Package.name)
    if options.organization:
        org = model.Group.get(options.organization)
        assert org
        results = results.filter(model.Package.owner_org==org.id)
    results = results.all()
    print '%i broken resources' % len(results)

    for archival, res in results:
        def stats_add(msg):
            pkg = res.resource_group.package
            return stats.add(msg, ('%s/%s %s' % (pkg.name, res.id, res.url)).encode('latin7', 'ignore'))

        if is_webarchive(res.url):
            stats_add('Webarchive already - ignore')
            continue
        if is_broken_api(res.url, archival):
            stats_add('It is an API error - ignore')
            continue
        if archival.last_success and \
           datetime.datetime.now() - archival.last_success < datetime.timedelta(days=3):
            print stats_add('Not broken for at least a month yet - ignore')
            continue
        if archival.failure_count < 3:
            print stats_add('Not broken for at least 3 occasions yet - ignore')
            continue

        # see if it is on the webarchive
        url = "http://webarchive.nationalarchives.gov.uk/+/" + res.url
        print '%s' % res.url.encode('latin7', 'ignore')

        try:
            req = requests.head(url, headers=USER_AGENT, verify=False)
        except Exception, e:
            if 'ukgwacnf.html?url=' in str(e):
                print stats_add('Not in the webarchive, %s' % get_cache_status(archival))
                continue
            print stats_add('!! Problem with request %s' % e)
            continue
        if req.status_code == 200:
            print stats_add('On webarchive - fixed')
            if write:
                res.url = url
                needs_commit = True
            continue
        elif not is_webarchive(req.url):
            if res.url.startswith('http://www.dft.gov.uk/'):
                result_str, good_url = try_earlier_webarchivals(url)
                print stats_add('Trying earlier webarchivals - %s' % result_str)
                if good_url and write:
                    res.url = good_url
                    needs_commit = True
                continue
            if 'ukgwacnf.html?url=' in (req.url + ''.join((resp.url for resp in req.history))):
                # webarchive seems to add this to the url!
                print stats_add('Not in the webarchive, %s' % get_cache_status(archival))
                continue
            print stats_add('Redirected off webarchive to an error - check manually')
            continue
        print stats_add('Not on webarchive, %s' % get_cache_status(archival))
        time.sleep(random.randint(1, 3))

        '''
        if not archival.url_redirected_to:
            # we've filtered for redirects and broken, so must be broken
            stats_add('Broken, but not a redirect - not interested')
            continue
        if is_gov_uk(res.url) and is_gov_uk(archival.url_redirected_to):
            stats_add('Internal gov.uk redirect - ignore')
            continue
        if not is_gov_uk(res.url) and is_gov_uk(archival.url_redirected_to):
            print stats_add('Redirect to gov.uk - change')
            if write:
                res.url = archival.url_redirected_to
                needs_commit = True
            continue
        if is_webarchive(res.url) and is_webarchive(archival.url_redirected_to):
            stats_add('Internal webarchive redirect - ignore')
            continue
        if not is_webarchive(res.url) and is_webarchive(archival.url_redirected_to):
            print stats_add('Redirect to webarchive - change')
            if write:
                res.url = archival.url_redirected_to
                needs_commit = True
            continue
        if not is_gov_uk(archival.url_redirected_to) and not is_webarchive(archival.url_redirected_to):
            stats_add('Redirect nothing to do with gov.uk or webarchive - ignore')
            continue
        print stats_add('Dunno')
        '''

    stats.report_value_limit = 500
    print '\nSummary\n', stats.report()
    if write and needs_commit:
        print 'Writing...'
        model.repo.commit_and_remove()
        print '...done'
    elif write:
        print 'Nothing to write'
    else:
        print 'Not written'


def try_earlier_webarchivals(webarchive_url):
    '''A webarchive_url turns out to be a bad redirect. So try and earlier
    webarchive of it to find what was there before the bad redirect.

    Returns tuple: (result_string, good_url or None)
    '''
    attempts = 0
    while True:
        # request the link but without the redirect, revealing the earlier
        # webarchivals in the headers
        print webarchive_url + ' (no redirects)'
        try:
            req = requests.head(webarchive_url, headers=USER_AGENT, verify=False, allow_redirects=False)
        except Exception, e:
            return ('!! Problem with request %s' % e, None)
        attempts += 1
        # Link header has the options
        # e.g. from http://webarchive.nationalarchives.gov.uk/+/http://www.dft.gov.uk/statistics/releases/accessibility-2010
        # Link: <http://webarchive.nationalarchives.gov.uk/20140508043011/http://www.dft.gov.uk/statistics/releases/accessibility-2010>; rel="memento"; datetime="Thu, 08 May 2014 04:30:11 GMT", <http://webarchive.nationalarchives.gov.uk/20110826141806/http://www.dft.gov.uk/statistics/releases/accessibility-2010>; rel="first memento"; datetime="Fri, 26 Aug 2011 14:18:06 GMT", <http://webarchive.nationalarchives.gov.uk/20140508043011/http://www.dft.gov.uk/statistics/releases/accessibility-2010>; rel="last memento"; datetime="Thu, 08 May 2014 04:30:11 GMT", <http://webarchive.nationalarchives.gov.uk/20140109163921/http://www.dft.gov.uk/statistics/releases/accessibility-2010>; rel="prev memento"; datetime="Thu, 09 Jan 2014 16:39:21 GMT", <http://webarchive.nationalarchives.gov.uk/20140508043011/http://www.dft.gov.uk/statistics/releases/accessibility-2010>; rel="next memento"; datetime="Thu, 08 May 2014 04:30:11 GMT", <http://webarchive.nationalarchives.gov.uk/timegate/http://www.dft.gov.uk/statistics/releases/accessibility-2010>; rel="timegate", <http://www.dft.gov.uk/statistics/releases/accessibility-2010>; rel="original", <http://webarchive.nationalarchives.gov.uk/timemap/http://www.dft.gov.uk/statistics/releases/accessibility-2010>; rel="timemap"; type="application/link-format"
        links = req.headers['Link']
        prev_links = [l.split('; ') for l in links.split(', <')
                      if 'rel="prev memento"' in l]
        if not prev_links:
            if attempts == 1:
                return ('No previous webarchive links', None)
            return ('No luck after trying %i previous webarchive links' % attempts, None)
        webarchive_url = prev_links[0][0].strip('<>')
        # Request the previous url to see if it is archived ok, or whether it
        # still redirects out
        print webarchive_url
        try:
            req = requests.head(webarchive_url, headers=USER_AGENT, verify=False)
        except Exception, e:
            return ('!! Problem with request %s' % e, None)
        if is_webarchive(req.url):
            return ('Earlier webarchive avoids bad redirect - fixed', req.url)

#def is_gov_uk(url):
#    return url.startswith('https://www.gov.uk/')
def is_webarchive(url):
    return url.startswith('http://webarchive.nationalarchives.gov.uk/')
def is_broken_api(url, archival):
    if archival.reason.startswith('Server content contained an API error message'):
        return True
    if url.startswith('https://www.spatialni.gov.uk/wss/service') or \
        url.startswith('http://webservices.spatialni.gov.uk/arcgis/services') or \
        url.startswith('http://wlwin5.nerc-wallingford.ac.uk/arcgis/services'):
        # special case for where it now returns 404 but webarchive only has
        # an XML response from the service.
        # e.g. doe-marine-division-winter-nutrient-monitoring-inspire-view-service/0a4ca96f-4fec-4ee8-9492-a42c1e68c971 https://www.spatialni.gov.uk/wss/service/DOE_Marine_Division_Winter_Nutrient_Monitoring-WMS-INC-LIC/WSS?request=GetCapabilities&service=WMS&version=1.3.0
        return True

def get_cache_status(archival):
    if not archival.cache_filepath:
        return 'Not cached'
    if os.path.exists(archival.cache_filepath):
        return 'Cached'
    return 'Cache missing on disk!'

if __name__ == '__main__':
    usage = __doc__ + """
usage:

%prog [-w] <ckan.ini>
"""
    parser = OptionParser(usage=usage)
    parser.add_option("-w", "--write",
                      action="store_true", dest="write",
                      help="write the theme to the datasets")
    parser.add_option('-d', '--dataset', dest='dataset')
    parser.add_option('-r', '--resource', dest='resource')
    parser.add_option('-o', '--organization', dest='organization')
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error('Wrong number of arguments (%i)' % len(args))
    config_filepath = args[0]
    print 'Loading CKAN config...'
    common.load_config(config_filepath)
    common.register_translator()
    print 'Done'
    fix_links(options)
