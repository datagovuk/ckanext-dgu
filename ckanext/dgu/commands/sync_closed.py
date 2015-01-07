import json
import logging
import sys
import os

import requests
try:
    import requests_cache
except:
    print "Please install requests_cache - pip install requests_cache"
    sys.exit(1)

from ckan.lib.cli import CkanCommand

log = logging.getLogger('ckanext')


class SyncClosedPublishers(CkanCommand):
    """
    Checks opennames for close publishers and then marks them as closed on DGU.

    TODO: Check for closed on DGU and mark as closed on OpenNames
    """
    summary = __doc__.strip().split('\n')[0]
    usage = '\n' + __doc__
    max_args = 0
    min_args = 0

    def __init__(self, name):
        super(SyncClosedPublishers, self).__init__(name)

    def command(self):
        self._load_config()

        import ckan.model as model

        # Cache all HTTP requests for 24 hours
        requests_cache.install_cache('opennames_cache', expire_after=86400)

        rev = model.repo.new_revision()
        for entities in self.opennames_entity_generator():
            for entity in self.closed_generator(entities):
                group = model.Group.get(entity)
                if not group:
                    print "Group {} does not exist".format(entity)
                    continue

                print "Updating {}".format(entity)
                group.extras['closed'] = True
                model.Session.add(group)
                model.Session.commit()
        model.repo.commit_and_remove()

    def closed_generator(self, items):
        for item in items:
            if item['attributes'].get('dgu-name') and \
                    item['attributes'].get('status', '') == 'closed' and \
                    item['invalid'] == False and item['reviewed'] == True:
                yield item['attributes']['dgu-name']

    def opennames_entity_generator(self):
        def get_json(url):
            r = requests.get(url)
            return r.json()

        d = get_json('http://opennames.org/api/2/entities?limit=1000&offset=0&dataset=public-bodies-uk')
        yield d['results']

        while d.get('next'):
            d = get_json(d['next'])
            yield d['results']


