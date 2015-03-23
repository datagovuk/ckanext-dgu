import logging
import json
import os

from ckan.lib.cli import CkanCommand
# No other CKAN imports allowed until _load_config is run,
# or logging is disabled


class Schema(CkanCommand):
    """Schema/code list command

    init - initialize the database tables
    create_test_data - create some test data (idempotent)
    import_schemas <schemas.jsonl> - create/update schemas from a file
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 2
    min_args = 1

    def command(self):
        self._load_config()
        self.log = logging.getLogger(__name__)

        cmd = self.args[0]
        cmd_args = self.args[1:]
        def assert_arg_number(expected_num_args):
            if len(cmd_args) != expected_num_args:
                self.parser.error('Should be %s args not %s' %
                        (expected_num_args, len(cmd_args)))
        if cmd == 'init':
            self.init()
        elif cmd == 'create_test_data':
            self.create_test_data()
        elif cmd == 'import_schemas':
            assert_arg_number(1)
            schema_filepath = cmd_args[0]
            if not os.path.exists(schema_filepath):
                self.parser.error('File does not exist: %s' % schema_filepath)
            self.import_schemas(schema_filepath)
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
        from ckanext.dgu.model.schema_codelist import Schema, Codelist
        pt = plugins.toolkit
        context = {'model': model, 'user': 'dgu'}

        # Create schemas
        schemas = [dict(url='http://lga.org/toilet?v0.3', title='Toilet locations'),
                   dict(url='http://spend.com/25', title='25k Spend'),
                   dict(url='http://environment.data.gov.uk/def/bathing-water-quality/', title='Bathing water quality (ontology)'),
                   dict(url='http://environment.data.gov.uk/def/bathing-water/', title='Bathing water (ontology)'),
                   dict(url='http://environment.data.gov.uk/def/bwq-cc-2012/', title='Bathing water classifications'),
                   dict(url='http://location.data.gov.uk/def/ef/SamplingPoint/', title='Sampling point (environmental monitoring) ontology'),
                   dict(url='http://www.w3.org/2006/time', title='Time (OWL ontology)'),
                   dict(url='http://purl.org/linked-data/cube', title='Data cube (vocabulary)'),
                   dict(url='http://www.w3.org/2004/02/skos/core', title='Simple Knowledge Organization System (SKOS vocabulary)'),
                   dict(url='http://purl.org/dc/terms/', title='DCMI Metadata Terms (vocabulary)'),
                   dict(url='http://xmlns.com/foaf/0.1/', title='FOAF Vocabulary'),
                   dict(url='http://purl.org/linked-data/sdmx/2009/sdmx-attribute', title='Statistical Data and Metadata Exchange (SDMX)'),
                   dict(url='http://www.w3.org/2003/01/geo/wgs84_pos', title='WGS84 Geo Positioning vocabulary'),
                   dict(url='http://data.ordnancesurvey.co.uk/ontology/geometry/', title='Ordnance Survey Geometry (ontology)'),
                   ]
        for schema in schemas:
            existing_schema = Schema.by_title(schema['title'])
            if existing_schema:
                schema['id'] = existing_schema.id
                for k, v in schema.items():
                    setattr(existing_schema, k, v)
            else:
                model.Session.add(Schema(**schema))
            model.repo.commit_and_remove()

        codelists = [
            dict(url='http://environment.data.gov.uk/registry/def/water-quality/_sampling_point_types', title='Water sampling point types'),
            dict(url='http://environment.data.gov.uk/registry/def/water-quality/sampling_mechanisms', title='Water quality sampling mechanisms'),
            ]
        for codelist in codelists:
            existing_list = Codelist.by_title(codelist['title'])
            if existing_list:
                codelist['id'] = existing_list.id
                for k, v in codelist.items():
                    setattr(existing_list, k, v)
            else:
                model.Session.add(Codelist(**codelist))
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
        datasets = [
            dict(name='oxford-toilets',
                 title='Oxford toilets',
                 codelist=[],
                 schema=[Schema.by_title('Toilet locations').id]),
            dict(name='bathing-waters',
                 title='Bathing waters',
                 codelist=[Codelist.by_title(title).id for title in
                           ('Water sampling point types',
                            'Water quality sampling mechanisms')],
                 schema=[Schema.by_url(url).id for url in
                         (
                            'http://environment.data.gov.uk/def/bathing-water-quality/',
                            'http://environment.data.gov.uk/def/bathing-water/',
                            'http://environment.data.gov.uk/def/bwq-cc-2012/',
                            'http://location.data.gov.uk/def/ef/SamplingPoint/',
                            'http://www.w3.org/2006/time',
                            'http://purl.org/linked-data/cube',
                            'http://www.w3.org/2004/02/skos/core',
                            'http://purl.org/dc/terms/',
                            'http://xmlns.com/foaf/0.1/',
                            'http://purl.org/linked-data/sdmx/2009/sdmx-attribute',
                            'http://www.w3.org/2003/01/geo/wgs84_pos',
                            'http://data.ordnancesurvey.co.uk/ontology/geometry/',
                         )]
                     )]
        for dataset in datasets:
            dataset.update(defaults)
            existing_dataset = model.Package.get(dataset['name'])
            action = 'create' if not existing_dataset else 'update'
            if existing_dataset:
                dataset['id'] = existing_dataset.id
            dataset = pt.get_action('dataset_%s' % action)(context, dataset)

        print 'Datasets: ', ' '.join([dataset['name'] for dataset in datasets])

    def import_schemas(self, schema_filepath):
        from ckan import model
        from ckanext.dgu.model.schema_codelist import Schema

        # Load file with schemas
        schema_dicts = []
        with open(schema_filepath) as f:
            for line in f.readlines():
                schema_dict = json.loads(line)
                schema_dicts.append(schema_dict)

        # Create/update in the db
        for schema in schema_dicts:
            if 'id' in schema:
                existing_schema = Schema.by_title(schema['title'])
            else:
                existing_schema = Schema.by_title(schema['title'])
            if existing_schema:
                schema['id'] = existing_schema.id
                for k, v in schema.items():
                    setattr(existing_schema, k, v)
                schema_obj = existing_schema
            else:
                schema_obj = Schema(**schema)
                model.Session.add(schema_obj)
            model.Session.commit()
            # Print JSONL with ids, in case you want to save with IDs
            print json.dumps(schema_obj.as_dict())
        model.Session.remove()

