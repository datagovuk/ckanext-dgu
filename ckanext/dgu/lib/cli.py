import logging

import ckan.lib.cli

# No other CKAN imports allowed until _load_config is run, or logging disabled

class DguCreateTestDataCommand(ckan.lib.cli.CkanCommand):
    '''Create DGU test data in the database

    create-test-data - creates test data

    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 1
    min_args = 0

    def command(self):
        self._load_config()
        self._setup_app()

        # Now we can import
        from ckan import plugins
        from ckanext.dgu.testtools.create_test_data import DguCreateTestData
        
        plugins.load('synchronous_search') # so packages get indexed
        self.log = logging.getLogger(__name__)

        DguCreateTestData.create_dgu_test_data()
        self.log.info('Created DGU test data successfully')
