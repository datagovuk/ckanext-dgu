from collections import defaultdict
import socket
import copy

from xmlrpclib import ServerProxy, ProtocolError
from nose.tools import assert_equal

from common import ScriptError, remove_readonly_fields
from ckanclient import CkanApiError

from ckanext.importlib.spreadsheet_importer import CsvData

log = __import__("logging").getLogger(__name__)

class OnsRemoveResources:
    '''Remove all resources from ONS packages'''
    def __init__(self, ckanclient,
                 xmlrpc_domain, xmlrpc_username, xmlrpc_password,
                 dry_run=False):
        self.ckanclient = ckanclient
        self.dry_run = dry_run
        self.xmlrpc = {'username':xmlrpc_username,
                       'password':xmlrpc_password,
                       'domain':xmlrpc_domain}

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

                if pkg['state'] != 'active':
                    msg = 'Not active (%s)' % pkg['state']
                    log.info('...%s: %r' % (msg, pkg['name']))
                    pkgs_rejected[msg].append(pkg)
                    continue             
                if pkg['extras'].get('external_reference') != 'ONSHUB':
                    msg = 'Not ONS'
                    log.info('...%s: %r' % (msg, pkg['name']))
                    pkgs_rejected[msg].append(pkg)
                    continue             
                pkg['resources'] = []
                
                if pkg == pkg_before_changes:
                    log.info('...package unchanged: %r' % pkg['name'])
                    pkgs_rejected['Package unchanged'].append(pkg)
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

from mass_changer_cmd import MassChangerCommand

class Command(MassChangerCommand):
    def add_options(self):
        super(Command, self).add_options()
        self.parser.add_option("-D", "--xmlrpc-domain",
                               dest="xmlrpc_domain",
                               )
        self.parser.add_option("-U", "--xmlrpc-username",
                               dest="xmlrpc_username",
                               )
        self.parser.add_option("-P", "--xmlrpc-password",
                               dest="xmlrpc_password",
                               )

    def command(self):
        super(Command, self).command()

        # now do command
        cmd = OnsRemoveResources(self.client,
                                 self.options.xmlrpc_domain,
                                 self.options.xmlrpc_username,
                                 self.options.xmlrpc_password,
                                 dry_run=self.options.dry_run)
        cmd.run()

def command():
    Command().command()

