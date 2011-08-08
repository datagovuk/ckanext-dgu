'''
#1135
Looks through all packages and if one is marked national statistic, but is
not from the hub, then unmark it.
'''
from collections import defaultdict

from paste.deploy.converters import asbool

from common import ScriptError
from mass_changer_cmd import MassChangerCommand
from ckanclient import CkanApiError

log = __import__("logging").getLogger(__name__)

pkgs_per_dot = 10 # progress bar

class NSFilter(object):
    def __init__(self, ckanclient, dry_run=False, force=False):
        '''
        Changes licenses of packages.
        @param ckanclient: instance of ckanclient to make the changes
        @param license_id: id of the license to change packages to
        @param force: do not stop if there is an error with one package
        '''
        self.client = ckanclient
        self.dry_run = dry_run
        self.force = force

    def filter(self):
        results = defaultdict(list)
        pkg_refs = self.client.package_register_get()
        def save_result(reason, pkg):
            log.info('%s: %s', reason, pkg['name'])
            results[reason].append(pkg['name'])
            
        # HACK
        #pkg_refs = ['local-authority-spend-over-500-london-borough-of-hackney'] + pkg_refs[:10]
        count = 0
        log.info('%i packages to process', len(pkg_refs))
        for pkg_ref in pkg_refs:
            count += 1
            if count % pkgs_per_dot == 0:
                log.debug('Processed %i packages', count)
            pkg = self.client.package_entity_get(pkg_ref)
            if asbool(pkg['extras'].get('national_statistic') or False):
                if not pkg['extras'].get('import_source', '').startswith('ONS'):
                    save_result('NS but not ONS - change', pkg)
                    if not self.dry_run:
                        pkg['extras']['national_statistic'] = 'no'
                        try:
                            self.client.package_entity_put(pkg)
                        except CkanApiError, e:
                            log.error('Could not update package %r: %r' % (pkg['name'], e.args))
                            if not self.force:
                                raise
                        log.info('Changed ok')
                else:
                    save_result('NS and ONS', pkg)
            else:
                save_result('Not NS', pkg)

        # output summary
        for reason, pkgs in results.items():
            log.info('  %i %s: %r', len(pkgs), reason, pkgs[:5])

class Command(MassChangerCommand):
    '''Looks through all packages and if one is marked national statistic, but is
not from the hub, then unmark it.
    '''
    
    def command(self):
        super(Command, self).command()

        ns_filter = NSFilter(self.client,
                             dry_run=self.options.dry_run,
                             force=self.options.force)
        ns_filter.filter()

if __name__ == '__main__':
    Command().command()
