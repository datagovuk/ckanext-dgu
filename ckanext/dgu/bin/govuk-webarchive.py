'''Fix gov.uk links that then redirect to the webarchive to point directly to
the webarchive.'''

from optparse import OptionParser
import requests
from sqlalchemy import or_
import lxml.html

import common
from running_stats import StatsList


def fix_redirects(options):
    from ckan import model
    from ckanext.archiver.model import Archival
    write = options.write
    if write:
        rev = model.repo.new_revision()
        rev.author = 'Repoint 410 Gone to webarchive url'
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
    results = results.filter(or_(Archival.is_broken == True,
                                 Archival.url_redirected_to != None))\
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

    def is_gov_uk(url):
        return url.startswith('https://www.gov.uk/')
    def is_webarchive(url):
        return url.startswith('http://webarchive.nationalarchives.gov.uk/')

    for archival, res in results:
        def stats_add(msg):
            pkg = res.resource_group.package
            return stats.add(msg, ('%s/%s %s' % (pkg.name, res.id, res.url)).encode('latin7', 'ignore'))
        if archival.reason.endswith('410 Gone'):
            # Find out the redirect - it is in the html
            try:
                page = requests.get(res.url)
            except requests.exceptions.ConnectionError:
                print stats_add('410 Gone but connection error')
                continue
            if '<a href="https://www.gov.uk">' not in page.text:
                print stats_add('410 Gone but not gov.uk')
                continue
            root = lxml.html.fromstring(page.text)
            hrefs = root.xpath('//div[@id="detail"]//a')
            for href in hrefs:
                url = href.attrib['href']
                if is_webarchive(url):
                    break
            else:
                print stats_add('410 Gone but no forward link')
                continue
            print stats_add('410 Gone and link found - change')
            if write:
                res.url = url
                needs_commit = True
            continue

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

    stats.report_value_limit = 500
    print 'Summary', stats.report()
    if write and needs_commit:
        print 'Writing...'
        model.repo.commit_and_remove()
        print '...done'
    elif write:
        print 'Nothing to write'
    else:
        print 'Not written'

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
    fix_redirects(options)


