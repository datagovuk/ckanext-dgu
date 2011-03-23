from collections import defaultdict
import socket
import copy

from nose.tools import assert_equal

from common import ScriptError, remove_readonly_fields
from ckanclient import CkanApiError

from ckanext.importlib.spreadsheet_importer import CsvData

log = __import__("logging").getLogger(__name__)

mapped_attributes = {
    'temporal_granularity': dict(zip(['years', 'quarters', 'months', 'weeks', 'days', 'hours', 'points'],
                                     ['year', 'quarter', 'month', 'week', 'day', 'hour', 'point'])),

    'update_frequency': dict(zip(('annually', 'quarterly', 'monthly', 'never'),
                                 ('annual', 'quarterly', 'monthly', 'never'))), #'discontinued'
    }

class MetadataV3Migration:
    '''Changes department/agency fields to published_by/_via'''
    def __init__(self, ckanclient,
                 dry_run=False):
        self.ckanclient = ckanclient
        self.dry_run = dry_run
        
    def run(self):
        pkgs_done = []
        pkgs_rejected = defaultdict(list) # reason: [pkgs]
        all_pkgs = self.ckanclient.package_register_get()
        log.info('Working on %i packages', len(all_pkgs))
        for pkg_ref in all_pkgs:
            log.info('Package: %s', pkg_ref)
            try:
                try:
                    pkg = self.ckanclient.package_entity_get(pkg_ref)
                except CkanApiError, e:
                    log.error('Could not get: %r' % e)
                    pkgs_rejected['Could not get package: %r' % e].append(pkg_ref)
                    continue
                pkg_before_changes = copy.deepcopy(pkg)

                for attribute in mapped_attributes:
                    orig_value = pkg['extras'].get(attribute)
                    if not orig_value:
                        continue
                    mapped_value = mapped_attributes[attribute].get(orig_value)
                    if mapped_value:
                        pkg['extras'][attribute] = mapped_value
                        log.info('%s: %r -> %r', \
                                 attribute, orig_value, mapped_value)
                    else:
                        log.warn('Invalid value for %r: %r', \
                                 attribute, orig_value)

                if pkg == pkg_before_changes:
                    log.info('...package unchanged: %r' % pkg['name'])
                    pkgs_rejected['Package unchanged: %r' % pkg['name']].append(pkg)
                    continue                    
                if not self.dry_run:
                    remove_readonly_fields(pkg)
                    try:
                        self.ckanclient.package_entity_put(pkg)
                    except CkanApiError, e:
                        log.error('Could not put: %r' % e)
                        pkgs_rejected['Could not put package: %r' % e].append(pkg_ref)
                        continue
                    log.info('...done')
                pkgs_done.append(pkg)
            except ScriptError, e:
                log.error('Error during processing package %r: %r', \
                          pkg_ref, e)
                pkgs_rejected['Error: %r' % e].append(pkg_ref)
                continue
            except Exception, e:
                log.error('Uncaught exception during processing package %r: %r', \
                          pkg_ref, e)
                pkgs_rejected['Exception: %r' % e].append(pkg_ref)
                raise
        log.info('-- Finished --')
        log.info('Processed %i packages', len(pkgs_done))
        rejected_pkgs = []
        for reason, pkgs in pkgs_rejected.items():
            rejected_pkgs.append('\n  %i: %s' % (len(pkgs), reason))
        log.info('Rejected packages: %s', rejected_pkgs)

import sys

#from ckanext.api_command import ApiCommand
from mass_changer_cmd import MassChangerCommand

class Command(MassChangerCommand):
    def add_options(self):
        super(Command, self).add_options()

    def command(self):
        super(Command, self).command()

        # now do command
        cmd = MetadataV3Migration(self.client,
                                 dry_run=self.options.dry_run)
        cmd.run()

def command():
    Command().command()

