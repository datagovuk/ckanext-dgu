'''Tool for prodding various bits of code, to allow live testing of the system to take place.'''

import sys

from ckan.lib.cli import CkanCommand

class Prodder(object):
    def archiver(self, res_id):
        import ckanext.archiver.plugin
        from ckan import model
        from pylons import config

        res = model.Session.query(model.Resource).get(res_id)
        assert res, 'Could not find res: %s' % res_id
        plugin = ckanext.archiver.plugin.ArchiverPlugin()
        plugin.configure(config)
        plugin.notify(res)

    def qa(self, res_id):
        import ckanext.qa.plugin
        from ckan import model
        from pylons import config

        res = model.Session.query(model.Resource).get(res_id)
        assert res, 'Could not find res: %s' % res_id
        plugin = ckanext.qa.plugin.QAPlugin()
        plugin.configure(config)
        plugin.notify(res)

    def os(self, dataset_id):
        import ckanext.os.plugin
        from ckan import model
        from pylons import config

        res = model.Package.get(dataset_id)
        assert res, 'Could not find package: %s' % dataset_id
        plugin = ckanext.os.plugin.SpatialIngesterPlugin()
        plugin.configure(config)
        plugin.notify(res)

class ProdCommand(CkanCommand):
    '''Prodder

    paster --plugin=ckanext-dgu prod OPTIONS {archiver|qa|os} entity_id
    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__
    min_args = 1
    max_args = None
    group = 'ckanext-dgu'

    ## def add_options(self):
    ##     Command.add_options(self)
    ##     self.parser.add_option('-q', '--quiet',
    ##                            dest='is_quiet',
    ##                            action='store_true',
    ##                            default=False,
    ##                            help='Quiet mode')
    ## parser.add_option('-l', '--lots-of-organisations',
    ##                   dest='lots_of_organisations',
    ##                   action='store_true',
    ##                   default=False,
    ##                   help='Use a lot of organisations instead of a handful.')

    def command(self):
        self._load_config()
        target = self.args[0]
        if target == 'archiver':
            prodder = Prodder()
            if not len(self.args) == 2:
                print self.usage
                print 'Error: Wrong number of args'
                sys.exit(1)
            res_id = self.args[1]
            prodder.archiver(res_id)
        elif target == 'qa':
            prodder = Prodder()
            if not len(self.args) == 2:
                print self.usage
                print 'Error: Wrong number of args'
                sys.exit(1)
            res_id = self.args[1]
            prodder.qa(res_id)
        elif target == 'os':
            prodder = Prodder()
            if not len(self.args) == 2:
                print self.usage
                print 'Error: Wrong number of args'
                sys.exit(1)
            dataset_id = self.args[1]
            prodder.os(dataset_id)
        else:
            assert 0, 'Target not known: %s' % target

#def command(name):
#    ProdCommand().command()

