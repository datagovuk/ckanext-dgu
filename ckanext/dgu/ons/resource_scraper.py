""" A class for scraping ONS redirection urls """
import re
import datetime
import time
import logging
import requests
import itertools
from urlparse import urljoin
from lxml.html import fromstring

log = logging.getLogger(__name__)

class InvalidONSShortcut(Exception):
    pass

class ONSResourceScraper(object):

    def __init__(self, *args, **kwargs):
        self.seen_urls = None
        self.url_regex = re.compile('^http://www.ons.gov.uk/ons/.*$')
        self.follow_regex = re.compile('^.*ons/publications/re-reference-tables.html.*$')

    def get_resources(self, url):
        """ 
        Returns a generator that contains dictionaries of all the data found
        either from the source url, or the 'data' page linked from there
        """
        # Reset the seen urls
        self.seen_urls = []

        # If this isn't a shortcut URL then we should exit
        if not self.url_regex.match(url):
            log.error("The url {0} raised doesn't look like a valid ONS link".format(url))
            raise InvalidONSShortcut("The url does not look like an ONS shortcut")

        # Fetch the page and only continue if it is a 200 and we have 
        # content to process.
        req = requests.get(url)
        if req.status_code != 200:
            log.error("The url {0} raised a {1}".format(url, req.status_code))            
            raise InvalidONSShortcut("URL raised a 404")

        if not req.content:
            log.error("The url {0} returned no content".format(url))            
            raise InvalidONSShortcut("No page content was returned")

        # Process the root page for links
        for r in self._inner_page_resources(req.content, url):
            yield r

        # Looks at the specific data page.
        for r in self._data_page(req.content, url):
            yield r

    def _data_page(self, content, url):
        """ 
        Finds the 'data' page for a source url and scrapes it
        """
        page = fromstring(content)
        nodes = page.cssselect('a')
        href = None
        # Find the URL on the source page
        for node in nodes:
            h = node.get('href')
            if h and self.follow_regex.match(h) and not h in self.seen_urls:
                href = urljoin(url, h)
                # Make sure we get all results on a single page
                href = self._get_paged_url(href)


        if not href:
            log.info("The url {0} didn't contain a link to the data page".format(url))

        # If we find the data page then scrape it after ensuring we are
        # getting all results
        if href:
            r = requests.get(href)
            if r.status_code != 200:
                log.info("The data page at {0} raised a 404".format(href))                   
                return

            page = fromstring(r.content)
            outerdivs = page.cssselect('.table-info')
            u, title, description = None, None, None

            for odiv in outerdivs:

                # URL
                dldiv = odiv.cssselect('.download-options ul li a')[0]
                u = dldiv.get('href')

                # Title
                dlinfo = odiv.cssselect('.download-info')[0]
                title = dlinfo.cssselect('h3')[0].text_content()

                description = dlinfo.cssselect('div')[2].text_content()
                description = description.strip()[len('Description: '):]

                if u in self.seen_urls:
                    log.info("The url {0} in 'data' page has already been processed".format(u))                    
                    continue

                self.seen_urls.append(u)

                yield {'url': urljoin(url, u),
                       'description': description,
                       'title': title,
                       'original': url}


    def _inner_page_resources(self, content, url):
        """
        From the original source page, check all of the links
        for a .html page, and scrape any .xls, .csv etc on that
        page.  This is only a single level deep
        """
        page = fromstring(content)
        attempt_inner = page.cssselect('#page-content a')

        for node in attempt_inner:
            h = node.get('href')
            if h and h.lower().endswith('.html'):
                if h in self.seen_urls:
                    log.error("The url {0} from 'source' page has already been processed".format(h))
                    continue

                self.seen_urls.append(h)

                h = urljoin(url, h)
                ar = requests.get(h)

                if ar.status_code != 200:
                    log.info("The url {0} raised a 404".format(h))
                    continue

                ap = fromstring(ar.content)
                links = ap.cssselect("a.xls,a.csv,a.zip")
                for link in links:
                    l = link.get('href')
                    if not l:
                        continue

                    if l in self.seen_urls:
                        log.info("The url {0} from depth 1 has already been processed".format(l))                        
                        continue

                    self.seen_urls.append(l)
                    if self._is_tabular_url(l):
                        yield {'url': urljoin('url', l),
                                     'description': '',
                                     'title': link.get('title', ''),
                                     'original': url}


    def _is_tabular_url(self, url):
        """ Returns true if a link appears to point to a data file """
        u = url.lower()
        if '/downloads/xls-download.xls?' in url \
                or '/downloads/csv.csv?' in url \
                or '/downloads/data.zip?' in url \
                or '/downloads/structured.zip?' in url \
                or '/downloads/navidata.zip?' in url:
            return True            
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


if __name__ == "__main__":
    """ Basic test to make sure it behaves """
    logging.basicConfig(level=logging.DEBUG)

    p = ONSResourceScraper()
    try:
        p.get_resources("http://www.google.com").next()
    except InvalidONSShortcut:
        print "Passed non-ONS url"

    try:
        p.get_resources("http://www.ons.gov.uk/ons/dcp19975_51766.xml").next()
    except InvalidONSShortcut:
        print "Passed 404 page"

    assert len(list(p.get_resources("http://www.ons.gov.uk/ons/dcp19975_54804.xml"))) == 1
    assert len(list(p.get_resources("http://www.ons.gov.uk/ons/dcp19975_269809.xml"))) == 30
    assert len(list(p.get_resources("http://www.ons.gov.uk/ons/dcp19975_242398.xml"))) == 6
    print "Found all resources at a valid link"
