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
from urlparse import urljoin
from lxml.html import fromstring

from ckan.lib.cli import CkanCommand

url_regex = re.compile('^http://www.ons.gov.uk/ons/.*$')
follow_regex = re.compile('^.*ons/publications/re-reference-tables.html.*$')


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
        self.parser.add_option('-d', '--delete-resources',
            action='store_true',
            default=False,
            dest='delete_resources',
            help='If specified, old resources that are replaced will be deleted')
        self.parser.add_option('-s', '--server',
            dest='server',
            help='Allows an alternative server URL to be used')

    def command(self):
        """
        """
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

        opts = {'external_reference': 'ONSHUB', 'offset': 0, 'limit': 20} # WIP
        q = ''
        if len(self.args) == 1:
            q = self.args[0].replace(',', '')

        search_results = ckan.package_search(q, opts)
        log.debug("There are %d results" % search_results['count'])
        datasets = search_results['results']

        self.csv_file = open("ons_scrape.csv", "wb")
        self.csv_log = csv.writer(self.csv_file)
        self.csv_log.writerow(["dataset", "resource", "url", "status code", "error"])

        counter = 0
        resource_count = 0
        for dsname in datasets:
            dataset = ckan.package_entity_get(dsname)
            counter = counter + 1
            time.sleep(1)

            log.info('Processing %s' % (dsname,))

            moved_resources = False
            new_resources = self.scrape_ons_publication(dataset)
            if new_resources:
                # Update the old resources, if they need to have their type set.
                for r in dataset['resources']:
                    # Only move resources to documentation if they are a link to a documentation
                    # page and haven't been added by scraping.
                    if r['resource_type'] != 'documentation' and not 'scraped_date' in r:
                        r['resource_type'] = 'documentation'
                        moved_resources = True
                    else:
                        log.info("Not moving resource with type %s, which has been scraped: %s" %
                            (r['resource_type'], 'scraped_date' in r,))

                # Save the update to the resources for this dataset if we moved
                # any to become documentation
                if moved_resources:
                    ckan.package_entity_put(dataset)

                for r in new_resources:
                    # Check if the URL already appears in the dataset's
                    # resources, and if so then skip it.
                    existing = [x for x in dataset['resources'] if x['url'] == r['url']]
                    if existing:
                        log.error("The URL for this resource was already found in this dataset")
                        continue

                    resource_count = resource_count + 1
                    # Add the resource along with a scraped_date
                    ckan.add_package_resource(dataset['name'], r['url'],
                                              resource_type='data',
                                              format=r['url'][-3:],
                                              description=r['description'],
                                              name=r['title'],
                                              scraped_date=datetime.datetime.now().isoformat())

        self.csv_file.close()
        log.info("Processed %d datasets" % (counter))
        log.info("Added %d resources" % (resource_count))

    def scrape_ons_publication(self, dataset):
        """
        Narrows down the datasets, and resources that can be scraped
        and processed by this scraper.
        """
        resources = []
        for resource in dataset['resources']:
            if url_regex.match(resource['url']):
                resources.append(resource)

        if not resources:
            self._log({"dataset": dataset['name'], "resource": "",
                       "url": resource["url"], "status code": ""},
                       "No matching resources found on dataset")
            return None

        return filter(None, [self._process_ons_resource(dataset, r) for r in resources])

    def _log(self, line, err_msg):
        """ Writes out a CSV file with the output of this scraping session """
        self.csv_log.writerow([line["dataset"], line["resource"], line["url"],
                              line["status code"], err_msg])
        self.csv_file.flush()

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
            self._log(line, "HTTP error")
            return None

        # need to follow the link to the data page. Somewhere on the page
        # is a link that looks like
        #  ^.*ons/publications/re-reference-tables.html.*$
        if not r.content:
            log.debug("Successfully fetched %s but page was empty" %
                (resource['url'],))
            self._log(line, "Page was empty")
            return None

        page = fromstring(r.content)
        nodes = page.cssselect('a')
        href = None
        for node in nodes:
            h = node.get('href')
            if h and follow_regex.match(h):
                # Will return href if it includes proto://host..
                href = urljoin(resource['url'], h)
                break

        if not href:
            self._log(line, "No data page")
            log.debug("Unable to find the 'data' page which contains links " +
                "to resources")
            return None

        r = requests.get(href)
        if r.status_code != 200:
            self._log(line, "Failed to fetch data page")
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

        if not url:
            self._log(line, "No link to data page")
            log.info("Could not find a link on the data page at %s" % (href,))
            return None
        else:
            self._log(line, "OK")
            log.debug("Found a link on the data page")

        return {'url': urljoin(resource['url'], url),
                'description': description,
                'title': title,
                'original': resource}
