import os

from logging import getLogger

from ckan.plugins import implements, SingletonPlugin
from ckan.plugins import IRoutes
from ckan.plugins import IConfigurer
from ckan.plugins import IGenshiStreamFilter
import ckanext.dgu

from ckan.model import Session
from ckanext.harvest.model import HarvestObject

import ckanext.dgu.forms.html as html
from genshi.input import HTML
from genshi.filters import Transformer

log = getLogger(__name__)

class FormApiPlugin(SingletonPlugin):
    """
    Configures the Form API and harvesting used by Drupal.
    """

    implements(IRoutes)
    implements(IConfigurer)
    implements(IGenshiStreamFilter)

    def before_map(self, map):
        for version in ('', '1/'):
            map.connect('/api/%sform/package/create' % version, controller='ckanext.dgu.forms.formapi:FormController', action='package_create')
            map.connect('/api/%sform/package/edit/:id' % version, controller='ckanext.dgu.forms.formapi:FormController', action='package_edit')
            map.connect('/api/%sform/harvestsource/create' % version, controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_create')
            map.connect('/api/%sform/harvestsource/edit/:id' % version, controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_edit')
            map.connect('/api/%sform/harvestsource/delete/:id' % version, controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_delete')
            map.connect('/api/%srest/harvestsource/:id' % version, controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_view')
        map.connect('/api/2/form/package/create', controller='ckanext.dgu.forms.formapi:Form2Controller', action='package_create')
        map.connect('/api/2/form/package/edit/:id', controller='ckanext.dgu.forms.formapi:Form2Controller', action='package_edit')
        map.connect('/api/2/form/harvestsource/create', controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_create')
        map.connect('/api/2/form/harvestsource/edit/:id', controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_edit')
        map.connect('/api/2/form/harvestsource/delete/:id', controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_delete')
        map.connect('/api/2/rest/harvestsource', controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_list')
        map.connect('/api/2/rest/harvestsource/:id', controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_view')
        map.connect('/api/2/rest/harvestingjob', controller='ckanext.dgu.forms.formapi:FormController',
                action='harvesting_job_create',
                conditions=dict(method=['POST']))
        """
        These routes are implemented in ckanext-csw
        map.connect('/api/2/rest/harvesteddocument/:id/xml/:id2.xml', controller='ckanext.dgu.forms.formapi:FormController',
                action='harvested_document_view_format',format='xml')
        map.connect('/api/rest/harvesteddocument/:id/html', controller='ckanext.dgu.forms.formapi:FormController',
                action='harvested_document_view_format', format='html')
        """
        map.connect('/api/2/util/publisher/:id/department', controller='ckanext.dgu.forms.formapi:FormController', action='get_department_from_publisher')
        map.connect('/', controller='ckanext.dgu.controllers.catalogue:CatalogueController', action='home')
        map.connect('home', '/ckan/', controller='home', action='index')
        return map

    def after_map(self, map):
        return map

    def update_config(self, config):
        rootdir = os.path.dirname(ckanext.dgu.__file__)

        template_dir = os.path.join(rootdir, 'templates')
        public_dir = os.path.join(rootdir, 'public')

        if config.get('extra_template_paths'):
            config['extra_template_paths'] += ',' + template_dir
        else:
            config['extra_template_paths'] = template_dir
        if config.get('extra_public_paths'):
            config['extra_public_paths'] += ',' + public_dir
        else:
            config['extra_public_paths'] = public_dir

    def filter(self, stream):

        from pylons import request, tmpl_context as c
        routes = request.environ.get('pylons.routes_dict')

        if routes.get('controller') == 'package' and \
            routes.get('action') == 'read' and c.pkg.id:

            is_inspire = [v[1] for i,v in enumerate(c.pkg_extras) if v[0] == 'INSPIRE']
            if is_inspire and is_inspire[0] == 'True':
                # We need the guid from the HarvestedObject!
                doc = Session.query(HarvestObject). \
                      filter(HarvestObject.package_id==c.pkg.id). \
                      order_by(HarvestObject.created.desc()). \
                      limit(1).first()
                if doc:
                    data = {'guid': doc.guid}
                    stream = stream | Transformer('body//div[@class="resources subsection"]/table')\
                        .append(HTML(html.GEMINI_CODE % data))

        return stream
