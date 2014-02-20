import logging

import ckan.lib.cli

# No other CKAN imports allowed until _load_config is run, or logging disabled

class DguCreateTestDataCommand(ckan.lib.cli.CkanCommand):
    '''Create DGU test data in the database

    create-test-data - creates test data
    create-test-data users - creates test users only

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
        
        try:
            plugins.load('synchronous_search') # so packages get indexed
        except:
            pass

        self.log = logging.getLogger(__name__)

        if self.args:
            cmd = self.args[0]
        else:
            cmd = 'basic'
        if cmd == 'basic':
            DguCreateTestData.create_dgu_test_data()
        elif cmd == 'users':
            DguCreateTestData.create_dgu_test_users()
        else:
            print 'Command %s not recognized' % cmd
            raise NotImplementedError
        
        self.log.info('Created DGU test data successfully')
