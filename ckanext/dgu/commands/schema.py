import logging

from ckan.lib.cli import CkanCommand
# No other CKAN imports allowed until _load_config is run,
# or logging is disabled


class Schema(CkanCommand):
    """Schema/code list command

    init - initialize the database tables
    create_test_data - create some test data (idempotent)
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 1
    min_args = 1

    def command(self):
        self._load_config()
        self.log = logging.getLogger(__name__)

        cmd = self.args[0]
        if cmd == 'init':
            self.init()
        elif cmd == 'create_test_data':
            self.create_test_data()
        else:
            raise NotImplementedError

    def init(self):
        import ckan.model as model
        model.Session.remove()
        model.Session.configure(bind=model.meta.engine)
        self.log.info("Database access initialised")

        import ckanext.dgu.model.schema_codelist as s_model
        s_model.init_tables(model.meta.engine)
        self.log.debug("Schema/codelist tables are setup")

    def create_test_data(self):
        from ckan import plugins
        from ckan import model
        from ckanext.dgu.model.schema_codelist import Schema
        pt = plugins.toolkit
        context = {'model': model, 'user': 'admin'}

        # Create schemas
        schemas = [dict(url='http://lga.org/toilet?v0.3', title='Toilet locations'),
                   dict(url='http://spend.com/25', title='25k Spend')]
        for schema in schemas:
            existing_schema = Schema.by_title(schema['title'])
            if existing_schema:
                schema['id'] = existing_schema.id
                for k, v in schema.items():
                    setattr(existing_schema, k, v)
            else:
                model.Session.add(Schema(**schema))
            model.repo.commit_and_remove()

        # Create org
        org = dict(name='oxford', title='Oxford',
                   type='organization',
                   is_organization=True,
                   category='local-council')
        existing_org = model.Group.get(org['name'])
        action = 'create' if not existing_org else 'update'
        if existing_org:
            org['id'] = existing_org.id
        org = pt.get_action('organization_%s' % action)(context, org)

        # Create datasets
        defaults = dict(license_id='uk-ogl',
                        owner_org=org['id'],
                        notes='This is a test')
        datasets = [dict(name='oxford-toilets',
                         title='Oxford toilets',
                         schemas='["%s"]' % Schema.by_title('Toilet locations').id)
                    ]
        for dataset in datasets:
            dataset.update(defaults)
            existing_dataset = model.Package.get(dataset['name'])
            action = 'create' if not existing_dataset else 'update'
            if existing_dataset:
                dataset['id'] = existing_dataset.id
            dataset = pt.get_action('dataset_%s' % action)(context, dataset)

        print 'Datasets: ', ' '.join([dataset['name'] for dataset in datasets])
