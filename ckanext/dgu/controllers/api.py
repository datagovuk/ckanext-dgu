from ckan.lib.base import model, abort, response, h, BaseController
from ckan.controllers.api import ApiController
from ckan.lib.helpers import OrderedDict
from ckanext.dgu.plugins_toolkit import get_action
import logging

log = logging.getLogger(__name__)

class DguApiController(ApiController):
    def latest_datasets(self, limit=10):
        query = model.Session.query(model.PackageRevision)
        query = query.filter(model.PackageRevision.state=='active')
        query = query.filter(model.PackageRevision.current==True)
        
        query = query.order_by(model.package_revision_table.c.revision_timestamp.desc())
        query = query.limit(min(100, limit))
        pkg_dicts = []
        for pkg_rev in query:
            pkg = pkg_rev.continuity
            publishers = pkg.get_groups('publisher')
            if publishers:
                pub_title = publishers[0].title
                pub_link = '/publisher/%s' % publishers[0].name
            else:
                pub_title = pub_link = None
            pkg_dict = OrderedDict((
                ('name', pkg.name),
                ('title', pkg.title),
                ('notes', pkg.notes),
                ('dataset_link', '/dataset/%s' % pkg.name),
                ('publisher_title', pub_title),
                ('publisher_link', pub_link),
                ('metadata_modified', pkg.metadata_modified.isoformat()),
                ))
            pkg_dicts.append(pkg_dict)
        return self._finish_ok(pkg_dicts)

    def dataset_count(self):
        from ckan.lib.search import SearchError
        try:
            # package search
            context = {'model': model, 'session': model.Session,
                       'user': 'visitor'}
            fq = 'capacity:"public"'
            data_dict = {
                'q':'',
                'fq':fq,
                'facet':'false',
                'rows':0,
                'start':0,
            }
            query = get_action('package_search')(context,data_dict)
            count = query['count']
        except SearchError, se:
            log.error('Search error: %s', se)
            count = 0

        return self._finish_ok(count)
