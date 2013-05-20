import ckan.plugins.toolkit as t

from ckan.lib.base import BaseController, abort
c = t.c
from ckanext.dgu.lib import reports

class ReportsController(BaseController):
    ##def index(self):
    ##    return t.render('reports/index.html')

    def resources(self, id=None):
        try:
            c.include_sub_publishers = t.asbool(t.request.params.get('include_sub_publishers') or False)
        except ValueError:
            abort(400, 'include_sub_publishers parameter value must be boolean')
        c.publisher_name = id or 'department-for-culture-media-and-sport'
        c.query = reports.organisation_resources
        c.data = c.query(organisation_name=c.publisher_name,
                         include_sub_organisations=c.include_sub_publishers)
        return t.render('reports/resources.html')
