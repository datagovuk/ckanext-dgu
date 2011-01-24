from collections import defaultdict
import socket
from xmlrpclib import ServerProxy, ProtocolError

from common import ScriptError, remove_readonly_fields

from ckanclient import CkanApiError

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
                print 'XMLRPC connection to %s' % xmlrpc_url
                self.drupal = ServerProxy(xmlrpc_url)
            try:
                org_id = self.drupal.organisation.match(dept_or_agency)
            except socket.error, e:
                raise ScriptError('Socket error connecting to %s', xmlrpc_url)
            except ProtocolError, e:
                raise ScriptError('XMLRPC error connecting to %s', xmlrpc_url)
            try:
                org_name = self.drupal.organisation.one(org_id)
            except socket.error, e:
                raise ScriptError('Socket error connecting to %s', xmlrpc_url)
            except ProtocolError, e:
                raise ScriptError('XMLRPC error connecting to %s', xmlrpc_url)
            organisation = u'%s [%s]' % (org_name, org_id)
            print organisation
            self.organisations[dept_or_agency] = organisation
        return self.organisations[dept_or_agency]
        
    def run(self):
        pkgs_done = []
        pkgs_rejected = defaultdict(list) # reason: [pkgs]
        all_pkgs = self.ckanclient.package_register_get()
        print 'Working on %i packages' % len(all_pkgs)
        for pkg_ref in all_pkgs:
            try:
                pkg = self.ckanclient.package_entity_get(pkg_ref)
            except ckanclient.CkanApiError, e:
                pkgs_rejected['Could not get package: %r' % e].append(pkg_ref)
                continue
            if not('department' in pkg['extras'] or 'agency' in pkg['extras'] or \
                   'published_by' not in pkg['extras'] or \
                   'published_via' not in pkg['extras']):
                pkgs_rejected['Already migrated'].append(pkg)
                continue

            dept = pkg['extras'].get('department')
            agency = pkg['extras'].get('agency')
            if dept:
                pub_by = self.get_organisation(dept)                
                pub_via = self.get_organisation(agency) if agency else None
            else:
                pub_by = self.get_organisation(agency) if agency else None
                pub_via = None
                if not pub_by or pub_via:
                    print 'Warning: No publisher for package: %s' % pkg['name']
            print '%r/%r -> %r/%r' % (dept, agency,
                                      pub_by, pub_via)
            if not self.dry_run:
                pkg['extras']['published_by'] = pub_by
                pkg['extras']['published_via'] = pub_via
                if pkg['extras'].has_key('department'):
                    del pkg['extras']['department']
                if pkg['extras'].has_key('agency'):
                    del pkg['extras']['agency']
                remove_readonly_fields(pkg)
                self.ckanclient.package_entity_put(pkg)
                print '...done'
            pkgs_done.append(pkg)
        print 'Processed %i packages' % len(pkgs_done)
        print 'Rejected packages:'
        for reason, pkgs in pkgs_rejected.items():
            print '  %i: %s' % (len(pkgs), reason)

import sys

#from ckanext.api_command import ApiCommand
from mass_changer_cmd import MassChangerCommand
from ofsted_fix import OfstedFix

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

