'''
All datasets will now have an extra called last_major_modification that 
denotes when a resource was last added or deleted, or when a resource 
url was last changed.  This script will set the initial value.
'''

import datetime
from ckanclient import CkanApiError
from mass_changer_cmd import MassChangerCommand

from ckanext.importlib.loader import PackageLoader
from running_stats import StatsList

log = __import__("logging").getLogger(__name__)

class Tool:
    def __init__(self, ckanclient, dry_run=False, force=False):
        '''
        @param ckanclient: instance of ckanclient to make the changes
        @param dry_run: change nothing
        @param force: do not stop if there is an error with one package
        '''
        self.client = ckanclient
        self.dry_run = dry_run
        self.force = force
        self.loader = PackageLoader(self.client)

    def set_initial_value(self):
        '''Some ONSHUB datasets were edited manually and due to a bug, many
        of the extras got lost. Here we restore the external_reference=ONSHUB
        extra.
        '''
        stats = StatsList()

        packages = self.client.action('package_list')
        
        log.info('Processing %d packages', len(packages))

        for p in packages:
            pkg = self.loader._get_package(p)

            if 'last_major_modification' in pkg['extras'] and not self.force:
                log.info("Not adding a new date as a value of '%s' already exists: %s" % \
                    (pkg['extras']['last_major_modification'],pkg['name'],))
                continue

            # Add the extra using either metadata_modified/created 
            pkg['extras']['last_major_modification'] = pkg.get('metadata_created')
            if not self.dry_run:
                try:
                    self.client.package_entity_put(pkg)
                    log.info(stats.add('Added extra value %s' % pkg['extras']['last_major_modification'], pkg['name']))                    
                except CkanApiError:
                    log.error('Error (%s) updating package over API: %s' % \
                              (self.client.last_status,
                               self.client.last_message))
                    stats.add('Error writing to package over API %s' % self.client.last_status, pkg['name'])
                    continue
            else:
                log.info(stats.add("Pretending to add '%s' as extra" % \
                    pkg['extras']['last_major_modification'], pkg['name']))                

        print stats.report()
        if self.dry_run:
            print 'NB: No packages changed - dry run.'

            
        
class Command(MassChangerCommand):
    ''''''
    
    def command(self):
        super(Command, self).command()

        tool = Tool(self.client,
                    dry_run=self.options.dry_run,
                    force=self.options.force)
        tool.set_initial_value()

    def add_options(self):
        super(Command, self).add_options()

def command():
    Command().command()
