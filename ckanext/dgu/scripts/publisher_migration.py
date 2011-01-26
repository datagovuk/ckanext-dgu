from collections import defaultdict
import socket
from xmlrpclib import ServerProxy, ProtocolError

from common import ScriptError, remove_readonly_fields

from ckanclient import CkanApiError

log = __import__("logging").getLogger(__name__)

class PublisherMigration:
    '''Changes department/agency fields to published_by/_via'''
    def __init__(self, ckanclient,
                 xmlrpc_domain, xmlrpc_username, xmlrpc_password,
                 dry_run=False):
        self.ckanclient = ckanclient
        self.dry_run = dry_run
        self.xmlrpc = {'username':xmlrpc_username,
                       'password':xmlrpc_password,
                       'domain':xmlrpc_domain}
        self.organisations = {}

    def get_organisation(self, dept_or_agency):
        if not self.organisations.has_key(dept_or_agency):
            if not hasattr(self, 'drupal'):
                domain = self.xmlrpc['domain']
                username = self.xmlrpc['username']
                password = self.xmlrpc['password']
                if username or password:
                    server = '%s:%s@%s' % (username, password, domain)
                else:
                    server = '%s' % domain
                xmlrpc_url = 'http://%s/services/xmlrpc' % server
                log.info('XMLRPC connection to %s', xmlrpc_url)
                self.drupal = ServerProxy(xmlrpc_url)
            try:
                org_id = self.drupal.organisation.match(dept_or_agency)
            except socket.error, e:
                raise ScriptError('Socket error connecting to %s', xmlrpc_url)
            except ProtocolError, e:
                raise ScriptError('XMLRPC error connecting to %s', xmlrpc_url)
            except ResponseError, e:
                raise ScriptError('XMLRPC response error connecting to %s for department: %r', xmlrpc_url, dept_or_agency)
            if org_id:
                try:
                    org_name = self.drupal.organisation.one(org_id)
                except socket.error, e:
                    raise ScriptError('Socket error connecting to %s', xmlrpc_url)
                except ProtocolError, e:
                    raise ScriptError('XMLRPC error connecting to %s', xmlrpc_url)
                organisation = u'%s [%s]' % (org_name, org_id)
                log.info('Found organisation: %r', organisation)
            else:
                log.error('Could not find organisation: %s', dept_or_agency)
                organisation = ''
            self.organisations[dept_or_agency] = organisation
        return self.organisations[dept_or_agency]
        
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
                except ckanclient.CkanApiError, e:
                    log.error('Could not get: %r' % e)
                    pkgs_rejected['Could not get package: %r' % e].append(pkg_ref)
                    continue
                if ('published_by' in pkg['extras'] and \
                    'published_via' in pkg['extras']):
                    log.error('...already migrated')
                    pkgs_rejected['Already migrated'].append(pkg)
                    continue

                dept = pkg['extras'].get('department')
                agency = pkg['extras'].get('agency')
                if dept:
                    pub_by = self.get_organisation(dept)                
                    pub_via = self.get_organisation(agency) if agency else ''
                else:
                    pub_by = self.get_organisation(agency) if agency else ''
                    pub_via = ''
                    if not pub_by or pub_via:
                        log.warn('No publisher for package: %s', pkg['name'])
                log.info('%s:\n  %r/%r ->\n  %r/%r', \
                         pkg['name'], dept, agency, pub_by, pub_via)
                if not self.dry_run:
                    pkg['extras']['published_by'] = pub_by
                    pkg['extras']['published_via'] = pub_via
                    if pkg['extras'].has_key('department'):
                        pkg['extras']['department'] = None
                    if pkg['extras'].has_key('agency'):
                        pkg['extras']['agency'] = None
                    remove_readonly_fields(pkg)
                    self.ckanclient.package_entity_put(pkg)
                    log.info('...done')
                pkgs_done.append(pkg)
            except ScriptError, e:
                log.error('Error during processing package %r: %r', \
                          pkg_ref, e)
                pkgs_rejected['Error: %r' % e].append(pkg_ref)
                continue
            except Exception, e:
                log.error('Exception during processing package %r: %r', \
                          pkg_ref, e)
                pkgs_rejected['Exception: %r' % e].append(pkg_ref)
                continue
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
        cmd = PublisherMigration(self.client,
                                 self.options.xmlrpc_domain,
                                 self.options.xmlrpc_username,
                                 self.options.xmlrpc_password,
                                 dry_run=self.options.dry_run)
        cmd.run()

def command():
    Command().command()

