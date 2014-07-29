import json
import logging
from urlparse import urljoin

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

            found = False
            current_related = model.Related.get_for_dataset(package)
            for current in current_related:
                if current.related.url == related_url:
                    stats.add("Skipping existing related", "[%s] -> [%s]" % (package.name, d['title']))
                    found = True

            if not found:
                self._add_related(package, d['title'], related_url, thumb_url)

        print stats.report()


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
            print r.status_code
            return None

        return json.loads(r.content)
