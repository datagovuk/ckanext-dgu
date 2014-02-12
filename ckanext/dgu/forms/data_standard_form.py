import ckan.plugins as p
import ckan.logic.schema as default_schema

from dataset_form import DatasetForm 

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

    def read_template(self):
        return 'data_standard/read.html'

    def show_package_schema(self):
        return DatasetForm.db_to_form_schema()

    # We don't customize the schema here - instead it is done in the validate
    # function, because there it has the context.
    #def create_package_schema(self):
    #def update_package_schema(self):

    # Override the form validation to be able to vary the schema by the type of
    # package and user
    def validate(self, context, data_dict, schema, action):
        if action in ('package_update', 'package_create'):
            # If the caller to package_update specified a schema (e.g.
            # harvesters specify the default schema) then we don't want to
            # override that.
            if not context.get('schema'):
                if 'api_version' in context:
                    # When accessed by the API, just use the default schemas.
                    # It's only the forms that are customized to make it easier
                    # for humans.
                    if action == 'package_create':
                        schema = default_schema.default_create_package_schema()
                    else:
                        schema = default_schema.default_update_package_schema()
                else:
                    # Customized schema for DGU form - leave as for dataset for now
                    schema = DatasetForm.form_to_db_schema(context)
        return p.toolkit.navl_validate(data_dict, schema, context)

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

