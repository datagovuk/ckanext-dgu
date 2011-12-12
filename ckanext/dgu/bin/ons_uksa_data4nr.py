'''
DGU#1236
Looks for data4nr packages with published_by UKSA and published_via ONS and
change to just published_by ONS
'''
from collections import defaultdict

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
        pkg_refs = sorted(self.client.package_register_get())
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
            is_uksa = str(pkg['extras'].get('published_by', '')).startswith('UK Statistics Authority')
            if not is_uksa:
                save_result('Not UKSA', pkg)
            else:
                is_data4nr = pkg['extras'].get('external_referance', '').startswith('DATA4NR') or pkg['extras'].get('import_source', '').startswith('DATA4NR')
                if not is_data4nr:
                    save_result('UKSA but not DATA4NR', pkg)
                else:
                    save_result('UKSA and DATA4NR - change', pkg)
                    if not self.dry_run:
                        pkg['extras']['published_by'] = 'Office for National Statistics [11606]'
                        pkg['extras']['published_via'] = ''
                        try:
                            self.client.package_entity_put(pkg)
                        except CkanApiError, e:
                            log.error('...Could not update package %r: %r' % (pkg['name'], e.args))
                            if not self.force:
                                raise
                        log.info('...Changed ok')
                    else:
                        log.info('Would have updated: %r', pkg['name'])
                        
        # output summary
        log.info('Out of %i packages:', len(pkg_refs))
        for reason, pkgs in results.items():
            log.info('  %i %s: %r', len(pkgs), reason, pkgs[:5])

    def clear_ns_flag(self, pkg):
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
            log.info('Would have updated: %r', pkg['name'])
            

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

    def add_options(self):
        super(Command, self).add_options()

if __name__ == '__main__':
    Command().command()
def command():
    Command().command()
