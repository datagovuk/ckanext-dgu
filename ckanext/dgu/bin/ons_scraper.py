"""
ONS Scraper

Finds all of the resources that have ONSHUB in their extras and then for
each one:

- Scrapes each resource URL looking for a match on '^http://www.ons.gov.uk/ons/.*$'
- For each match, find the links to actual data files on the data page, if it exists
- If we have new resources, it updates the old ones to move them to become
  documentation resources.
- For each new resource, if the URL isn't already in the list of resources, it is
  added

This script will also generate a CSV file 'ons_scrape.csv' containing details of
each item scraped.  The log file will contain the dataset name, the resource ID,
the URL of the resource, an HTTP status_code and an error message.  The error
message will contain details of the failure.
"""
import re
import csv
import datetime
import time
import logging
import requests
import itertools
from urlparse import urljoin
from lxml.html import fromstring

from ckan.lib.cli import CkanCommand

# Logging setup
csv_file = open("ons_scrape.csv", "wb")
csv_log = csv.writer(csv_file)
csv_log.writerow(["dataset", "resource", "url", "status code", "error"])

def _log(line, err_msg):
    """ Helper that writes out a CSV file with the output of this scraping session """
    csv_log.writerow([line["dataset"], line["resource"], line["url"],
                          line["status code"], err_msg])
    csv_file.flush()


class ONSUpdateTask(CkanCommand):
    """
    Runs a one-off task to fetch more accurate resource links for ONS datasets
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 1
    min_args = 0

    def __init__(self, name):
        super(ONSUpdateTask, self).__init__(name)
        self.scraper = ONSScraper()

        self.parser.add_option('-d', '--delete-resources',
            action='store_true',
            default=False,
            dest='delete_resources',
            help='If specified, old resources that are replaced will be deleted')
        self.parser.add_option('-p', '--pretend',
            action='store_true',
            default=False,
            dest='pretend',
            help='Whether we should only pretend to write')        
        self.parser.add_option('-s', '--server',
            dest='server',
            help='Allows an alternative server URL to be used')
        self.parser.add_option('-t', '--test',
            dest='test',
            help='Allows testing with a single url')

    def command(self):
        import ckanclient
        from ckan.logic import get_action

        self._load_config()
        log = logging.getLogger(__name__)

        import ckan.model as model
        model.Session.remove()
        model.Session.configure(bind=model.meta.engine)
        model.repo.new_revision()

        site_user = get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
        apikey = site_user['apikey']

        ckan = ckanclient.CkanClient(base_location=self.options.server or 'http://localhost/api',
                                     api_key=apikey)

        opts = {#'external_reference': 'ONSHUB',
                'offset': 0,
                'limit': 0,
                'publisher': 'office-for-national-statistics'}
        q = ''
        if len(self.args) == 1:
            q = self.args[0].replace(',', '')

        if self.options.test:
            datasets = [self.options.test]
        else:
            search_results = ckan.package_search(q, opts)
            log.debug("There are %d results" % search_results['count'])
            datasets = search_results['results']

        counter = 0
        resource_count = 0
        for dsname in datasets:
            got = 3
            while got >= 0:
                try:
                    dataset = ckan.package_entity_get(dsname)
                    break
                except:
                    got = got - 1
                    time.sleep(2)

            if dataset['state'] != 'active':
                log.info("Package %s is not active" % dsname)
                continue

            counter = counter + 1
            time.sleep(1)

            log.info('Processing %s' % (dsname,))

            new_resources = None
            moved_resources = False

            new_resources = self.scraper.scrape(dataset)
            if not new_resources:
                log.info("No new resources for {0}".format(dataset))
                continue

            new_resources = sorted(new_resources, key=lambda r: r['title'])

            # Update the old resources, if they need to have their type set.
            for r in dataset['resources']:
                # Only move resources to documentation if they are a link to a documentation
                # page and haven't been added by scraping.
                if r['resource_type'] != 'documentation' and not 'scraped' in r:
                    log.info("Marking resource documentation as it was not previously scraped")
                    r['resource_type'] = 'documentation'
                    moved_resources = True
                else:
                    log.info("Resource is %s, not updating type. Was it prev scraped? %s" %
                        (r['resource_type'], 'scraped' in r))

            # Save the update to the resources for this dataset if we moved
            # any old resources to become documentation
            if moved_resources and not self.options.pretend:
                dataset['resources'] = sorted(dataset['resources'], key=lambda r: r['name'])
                got = 3
                while got >= 0:
                    try:
                        ckan.package_entity_put(dataset)
                        break
                    except:
                        got = got - 1
                        time.sleep(2)

            for r in new_resources:
                # Check if the URL already appears in the dataset's
                # resources, and if so, skip it.
                existing = [x for x in dataset['resources'] if x['url'] == r['url']]
                if existing:
                    log.error("The URL for this resource was already found in this dataset")
                    continue

                # Add the resource along with a scraped_date
                try:
                    resource_count = resource_count + 1                    
                    if not self.options.pretend:
                        got = 4
                        while got >= 0:
                            try:
                                ckan.add_package_resource(dataset['name'], r['url'],
                                                          resource_type='',
                                                          format=r['url'][-3:],
                                                          description=r['description'],
                                                          name=r['title'],
                                                          scraped=datetime.datetime.now().isoformat(),
                                                          scraper_source=r['original']['url'])
                                break
                            except:
                                got = got - 1
                                
                        log.info("Set source to %s" % r['original']['url'])
                    log.info("  Added {0}".format(r['url']))
                except Exception, err:
                    log.error(err)

        # Cleanup
        csv_file.close()
        log.info("Processed %d datasets" % (counter))
        log.info("Added %d resources" % (resource_count))


class ONSScraper(object):
    """ 
        When provided with a dataset this class will iterate through resources looking for 
        an ons.gov short url (.xml redirection) will attempt to find actually data on the page
        redirected to, and a specific 'data page' linked from there.
    """
    def __init__(self, *args, **kwargs):
        self.url_regex = re.compile('^http://www.ons.gov.uk/ons/.*$')
        self.follow_regex = re.compile('^.*ons/publications/re-reference-tables.html.*$')


    def scrape(self, dataset, rsrc=None):
        """
        Narrows down the datasets, and resources that can be scraped
        and processed by this scraper.
        """
        resources = []
        rsrcs = dataset['resources']
        if rsrc:
            rsrcs = [rsrc]

        for resource in rsrcs:
            if resource['resource_type'] == 'documentation':
                continue

            if self._is_tabular_url(resource['url']):
                continue

            if self.url_regex.match(resource['url']):
                resources.append(resource)

        if not resources:
            _log({"dataset": dataset['name'], "resource": "",
                       "url": resource["url"], "status code": ""},
                       "No matching resources found on dataset")
            return None

        results = filter(None, [self._process_ons_resource(dataset, r) for r in resources])
        return list(itertools.chain.from_iterable(results)) 


    def _process_ons_resource(self, dataset, resource):
        log = logging.getLogger(__name__)

        line = {"dataset": dataset['name'],
                "resource": resource['id'],
                "url": resource['url']
                }

        # Get the first page that we were pointed at.
        r = requests.get(resource['url'])
        line["status code"] = r.status_code
        if r.status_code != 200:
            log.error("Failed to fetch %s, got status %s" %
                (resource['url'], r.status_code))
            _log(line, "HTTP error")
            return None


        # need to follow the link to the data page. Somewhere on the page
        # is a link that looks like
        #  ^.*ons/publications/re-reference-tables.html.*$
        if not r.content:
            log.debug("Successfully fetched %s but page was empty" %
                (resource['url'],))
            _log(line, "Page was empty")
            return None

        items = []
        seen = []
        page = fromstring(r.content)

        # Attempt at the inner block (not the data link)
        attempt_inner = page.cssselect('#page-content a')

        for node in attempt_inner:
            h = node.get('href')
            if h and h.lower().endswith('.html'):
                seen.append(h)

                h = urljoin(resource['url'], h)
                ar = requests.get(h)

                if ar.status_code == 200:
                    ap = fromstring(ar.content)
                    links = ap.cssselect("#page-content a")
                    for link in links:
                        l = link.get('href')
                        if not l:
                            continue
                        if self._is_tabular_url(l):
                            items.append({'url': urljoin(resource['url'], l),
                                         'description': '',
                                         'title': link.get('title', ''),
                                         'original': resource})
                            log.debug("Found an item from a direct link")                           

        # Try all of the URLs to find the data link
        nodes = page.cssselect('a')
        href = None
        for node in nodes:
            h = node.get('href')
            if h and self.follow_regex.match(h) and not h in seen:
                # Will return href if it includes proto://host..
                href = urljoin(resource['url'], h)
                href = self._get_paged_url(href)
                break

        if not href:
            _log(line, "No data page")
            log.debug("Unable to find the 'data' page which contains links " +
                "to resources")
            if not items:
                return None
            else:
                log.debug("Continuing because we have already found items")

        if href:
            r = requests.get(href)
            if r.status_code != 200:
                _log(line, "Failed to fetch data page")
                log.error("Failed to fetch data page %s, got status %s" %
                    (resource['url'], r.status_code))
                return None

            log.debug("Found 'data' page content")
            page = fromstring(r.content)
            outerdivs = page.cssselect('.table-info')
            url, title, description = None, None, None

            for odiv in outerdivs:

                # URL
                dldiv = odiv.cssselect('.download-options ul li a')[0]
                url = dldiv.get('href')

                # Title
                dlinfo = odiv.cssselect('.download-info')[0]
                title = dlinfo.cssselect('h3')[0].text_content()

                description = dlinfo.cssselect('div')[2].text_content()
                description = description.strip()[len('Description: '):]

                items.append({'url': urljoin(resource['url'], url),
                    'description': description,
                    'title': title,
                    'original': resource})

            if not url:
                _log(line, "No link to data page")
                log.info("Could not find a link on the data page at %s" % (href,))
                return None
            else:
                _log(line, "OK")
                
        log.debug("Found {0} link(s) on the data page (and direct)".format(len(items)))

        return items

    def _is_tabular_url(self, url):
        return url.lower().endswith('.xls') or url.lower().endswith('.csv')

    def _get_paged_url(self, href):
        """
        We should convert a URL like 
        http://www.ons.gov.uk/ons/publications/re-reference-tables.html?edition=tcm%3A77-263579
        to a url like 
        http://www.ons.gov.uk/ons/publications/re-reference-tables.html?newquery=*&pageSize=2000&edition=tcm%3A77-263579
        to make sure we get every page
        """
        return "{0}{1}".format(href, "&newquery=*&pageSize=2000")
