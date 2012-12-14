import os
import json
import datetime
import logging
import requests
import collections
from ckan.lib.cli import CkanCommand

log = logging.getLogger("ckanext")

class ScrapeResources(CkanCommand):
    """
    Uses scrapers on ScraperWiki to maintain a list of scrapers we
    should query, and then queries those scrapers to see what possibly
    new resources are available.

    Currently it only supports 'simple' scrapers that have a hard-coded
    url to query, but this is extensible enough that the scraper might
    only need to know the publisher to be able to operate.
    """
    summary = __doc__.strip().split('\n')[0]
    usage = '\n' + __doc__
    max_args = 0
    min_args = 0

    def command(self):
        self._load_config()

        import ckan.model as model
        model.Session.remove()
        model.Session.configure(bind=model.meta.engine)
        model.repo.new_revision()
        log.info("Database access initialised")

        s = ScraperWiki()
        scrapers = s.get_simple_scraper_list()
        log.info("Processing %d simple scrapers" % len(scrapers))

        for scrapername in scrapers:

            # Get the data for this scraper and give up if there is none
            datalist = s.get_simple_scraper_data(scrapername)
            if not datalist:
                continue

            log.info("Found %d resources for scraper %s" % (len(datalist), scrapername))
            grouped_datasets = collections.defaultdict(list)

            # Groups the data we have retrieved into a dict, where each value is a
            # list of json blobs back from ScraperWiki.
            for r in datalist:
                grouped_datasets[r['dataset']].append(r)

            # For each dataset name, and the list of data, process it.
            for k,v in grouped_datasets.iteritems():
                self._process_dataset(k, v)


    def _process_dataset(self, name, datalist):
        import ckan.model as model

        log.info("Processing data for dataset => %s" % name)
        dataset = model.Package.get(name)
        if not dataset or not dataset.state == 'active':
            log.error('Unable to update dataset %s, not found or not active' % name)

        log.info("Dataset currently has %d resources" % len(dataset.resources))
        modified = False

        # Get a list of the URLs in the current resources, so we can check against
        # them when adding data.
        current_urls = [resource.url for resource in dataset.resources]

        for d in datalist:
            if d['url'] in current_urls:  # We already have a resource with this url
                log.info("%s is already present" % d['url'])
            else:
                # if there was an error, or the status code wasn't (eventually) a 200
                # then we should skip the adding of this data.
                if d.get('error'):
                    log.info("Skipping resource due to error: %s" % d.get('error'))
                    continue
                if d.get('status_code') != "200":
                    log.info("Skipping resource due to request failure: %s" % d.get('status_code'))
                    continue

                # Add a resource, and flag the dataset as modified
                dataset.add_resource(d.get('url'), format=d.get('format',''),
                                     description=d.get('label', ''), size=d.get('size',0))
                modified = True

        if modified:
            model.Session.add(dataset)
            model.Session.commit()


class ScraperWiki(object):

    def get_simple_scraper_list(self):
        """
            Asks the ScraperWiki API to run select * from `data`
            on the listing scraper
        """
        url = "https://api.scraperwiki.com/api/1.0/datastore/sqlite?format=jsondict&name=dgu_dataset_scrapers&query=select%20*%20from%20%60data%60"
        response = requests.get(url)
        if not response.status_code == 200:
            log.error("ScraperWiki returned a %d response when fetching the list"
                % response.status_code)
            return []

        scrapers = json.loads(response.content)
        if 'error' in scrapers:
            log.error(scrapers['error'])
            return []

        return [d['name'] for d in scrapers if d['type'] == 'simple']


    def get_simple_scraper_data(self, name):
        """
        The data returned from this always looks like the following, and we perform
        a simple select * to get this.  Means that the scrapers have to be consistent
        though:

        {
            "url": "http://www.ecodriver.uk.com/eCMS/Files/DFID/dfid_sep-2012.csv",
            "status_code": "200",
            "error": "",
            "label": "dfid_sep-2012.csv",
            "headers": "{\"content-length\": \"162018\", \"x-powered-by\": \"ASP.NET\", \"accept-ranges\": \"bytes\", \"server\": \"Microsoft-IIS/6.0\", \"last-modified\": \"Mon, 01 Oct 2012 00:00:12 GMT\", \"connection\": \"close\", \"etag\": \"\\\"66d891ba679fcd1:100f\\\"\", \"date\": \"Fri, 14 Dec 2012 15:28:34 GMT\", \"content-type\": \"application/octet-stream\"}",
            "scrape_time": "2012-12-14T15:28:34.898178",
            "dataset": "dfid-energy-and-water-consumption",
            "size": "100",
            "format": "csv"
        },
        """
        url = "https://api.scraperwiki.com/api/1.0/datastore/sqlite?format=jsondict&name=%s&query=select%%20*%%20from%%20%%60data%%60" % name

        log.info("Fetching data for %s" % name)
        response = requests.get(url)
        if not response.status_code == 200:
            log.error("ScraperWiki returned a %d response when fetching the list"
                % response.status_code)
            return None

        data = json.loads(response.content)
        if 'error' in data:
            log.error(data['error'])
            return None

        return data
