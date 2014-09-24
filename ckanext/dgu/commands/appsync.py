import json
import logging
import lxml.html
from urlparse import urljoin
from collections import defaultdict

import requests
from pylons import config

from ckan.plugins import toolkit
from ckan.lib.cli import CkanCommand
import ckan.model as model

from ckanext.dgu.bin.running_stats import StatsList

stats = StatsList()

class AppSync(CkanCommand):
    """
    Uses the Drupal API to synchronize apps.

    Fetches the app info from the Drupal API and syncs it by storing it
    in the CKAN Related models.
    """
    summary = __doc__.strip().split('\n')[0]
    usage = '\n' + __doc__
    max_args = 0
    min_args = 0


    def __init__(self, name):
        super(AppSync, self).__init__(name)
        self.log = logging.getLogger("ckanext")

        self.parser.add_option("-s", "--scrape",
                  dest="scrape", action="store_true",
                  help="Scrape web interface rather than using the API")


    def command(self):
        self._load_config()

        model.Session.remove()
        model.Session.configure(bind=model.meta.engine)
        model.repo.new_revision()
        self.log.info("Database access initialised")

        root_url = config.get('ckan.site_url', 'http://data.gov.uk')
        self.log.debug("Root url is " + root_url)
        if toolkit.asbool(config.get('debug')):
            root_url = "http://data.gov.uk"
            self.log.debug("Overriding root_url in DEBUG ")

        if self.options.scrape:
            self._scrape(root_url)
        else:
            self._use_api(root_url)

        print stats.report()


    def _scrape(self, root_url):
        try:
            import requests_cache
            requests_cache.install_cache('scrape_apps')
        except ImportError:
            pass

        apps = defaultdict(list)

        #response = requests.get('http://data.gov.uk/apps')
        response = requests.get('http://data.gov.uk/search/everything/?f[0]=bundle%3Aapp')
        
        while True:
            doc = lxml.html.fromstring(response.content)

            #for app_link in doc.xpath('//div[@class="field-content"]/a/@href'):
            for app_link in doc.xpath('//li[@class="search-result boxed node-type-app"]/a/@href'):
                related_url = urljoin(root_url, app_link)

                try:
                    response = requests.get(urljoin('http://data.gov.uk/apps', app_link))
                except requests.exceptions.TooManyRedirects:
                    stats.add("Error getting URL:", app_link)
                    continue
        
                app_doc = lxml.html.fromstring(response.content)
                app_title = app_doc.xpath("//h1[@property='dc:title']/text()")[0]
        
                related = app_doc.xpath('//div[contains(text(), "Uses dataset")]/following-sibling::div/div/a/@href')
                for dataset in related:
                    apps[(related_url, app_title)].append(dataset[9:])
        
            try:
                next_link = doc.xpath('//li[@class="next last"]/a/@href')[0]
                response = requests.get(urljoin('http://data.gov.uk', next_link))
            except IndexError:
                break
        
        for (app_url, app_title), package_names in apps.items():
            for package_name in package_names:
                package = model.Session.query(model.Package).filter(model.Package.name==package_name).first()
                if self._is_alread_related(package, app_url):
                    stats.add("Skipping existing related", "[%s] -> [%s]" % (package.name, app_title))
                else:
                    self._add_related(package, app_title, app_url)

    def _use_api(self, root_url):
        data = self._make_request()
        for d in data:
            # Eventually we might handle other types.
            if d['type'] != 'App':
                continue

            related_url = urljoin(root_url, d['path'])
            thumb = d.get('thumbnail', '').replace("://", "/")
            if thumb:
                thumb_url = urljoin(root_url, "/sites/default/files/styles/medium/")
                thumb_url = urljoin(thumb_url, thumb)
            else:
                thumb_url = ''

            package = model.Package.get(d['ckan_id'])
            if not package:
                stats.add("Missing Package", d['ckan_id'])
                continue

            if self._is_alread_related(package, related_url):
                stats.add("Skipping existing related", "[%s] -> [%s]" % (package.name, d['title']))
            else:
                self._add_related(package, d['title'], related_url, thumb_url)

    def _is_alread_related(self, package, related_url):
            current_related = model.Related.get_for_dataset(package)
            for current in current_related:
                if current.related.url == related_url:
                    return True
            return False

    def _add_related(self, package, app_title, app_url, image_url=''):
        stats.add("Adding related item", "[%s] -> [%s]" % (package.name, app_title))

        related = model.Related()
        related.type = 'App'
        related.title = app_title
        related.description = ""
        related.url = app_url

        related.image_url = image_url

        model.Session.add(related)
        model.Session.commit()

        related_item = model.RelatedDataset(dataset_id=package.id, related_id=related.id)
        model.Session.add(related_item)
        model.Session.commit()


    def _make_request(self):
        uname = config.get('dgu.xmlrpc_username')
        passwd = config.get('dgu.xmlrpc_password')

        r = requests.get('http://data.gov.uk/services/rest/views/dataset_referrers',
                         auth=(uname, passwd))
        if r.status_code != 200:
            self.log.error("Request to Drupal API failed")
            return None

        return json.loads(r.content)


