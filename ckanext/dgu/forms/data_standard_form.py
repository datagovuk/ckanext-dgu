import ckan.plugins as p
#import ckan.plugins.toolkit as toolkit

class DataStandardForm(p.toolkit.DefaultDatasetForm, p.SingletonPlugin):

    p.implements(p.IDatasetForm, inherit=True)
    p.implements(p.IRoutes, inherit=True)

    # IDatasetForm

    def package_types(self):
        return ('data-standard',)
        #return ('Code list', 'Ontology', 'Controlled list')

    def search_template(self):
        return 'data_standard/search.html'

    def new_template(self):
        return 'data_standard/new.html'

    def edit_template(self):
        return 'data_standard/edit.html'

    def package_form(self):
        return 'data_standard/edit_form.html'

    # IRoutes

    def before_map(self, map):
        #controller = 'ckanext.dgu.controllers.package:PackageController'
        controller = 'package'
        map.connect('/data-standard/new', controller=controller, action='new')
        map.connect('/data-standard/edit/{id}', controller=controller, action='edit')
        map.connect('/data-standard/delete/{id}', controller=controller, action='delete')
        map.connect('/data-standard/history/{id}', controller=controller, action='history')
        map.connect('/data-standard/{id}.{format}', controller=controller, action='read')
        map.connect('/data-standard/{id}', controller=controller, action='read')
        map.connect('/data-standard/{id}/resource/{resource_id}', controller=controller, action='resource_read')

        return map

