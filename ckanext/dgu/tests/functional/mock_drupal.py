from ckan.plugins.interfaces import IRoutes
from ckan.plugins.core import SingletonPlugin, implements

class MockDrupal(SingletonPlugin):
    '''Provides functionality of the DGU Drupal system, apart from
    functionality provided in form_api_tester.'''

    implements(IRoutes)

    def after_map(self, map):
        controller = 'ckanext.dgu.tests.functional.mock_drupal:MockDrupalControler'
        map.connect('/services/xmlrpc', controller=controller, action='xmlrpc')
        import pdb; pdb.set_trace()
        return map

    def before_map(self, map):
        return map


class MockDrupalController(object):
    def xmlrpc(self, *args, **kwargs):
        import pdb; pdb.set_trace()
        return
