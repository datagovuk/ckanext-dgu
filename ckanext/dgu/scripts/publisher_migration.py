from collections import defaultdict

from xmlrpclib import ServerProxy

from common import ScriptError, remove_readonly_fields

from ckanclient import CkanApiError

class PublisherMigration:
    '''Changes department/agency fields to published_by/_via'''
    def __init__(self, ckanclient,
                 xmlrpc_domain, xmlrpc_username, xmlrpc_password,
                 dry_run):
        self.ckanclient = ckanclient
        self.dry_run = dry_run
        self.xmlrpc = {'username':xmlrpc_username,
                       'password':xmlrpc_password,
                       'domain':xmlrpc_domain}

    def get_organisation(self, dept_or_agency):
        domain = self.xmlrpc['domain']
        username = self.xmlrpc['xmlrpc_username']
        password = self.xmlrpc['xmlrpc_password']
        if username or password:
            server = '%s:%s@%s' % (username, password, domain)
        else:
            server = '%s' % domain
        xmlrpc_url = 'http://%s/services/xmlrpc' % server
        print 'XMLRPC connection to %s' % xmlrpc_url
        drupal = ServerProxy(xmlrpc_url)
        try:
            org = drupal.organisation.match(dept_or_agency)
        except socket.error, e:
            raise ScriptError('Socket error connecting to %s', xmlrpc_url)
        print org
        import pdb; pdb.set_trace()
        org_name = org['name']
        org_id = org['id']
        return '%s [%s]' % (org_name, org_id)
        
    def run(self):
        pkgs_done = []
        pkgs_rejected = defaultdict(list) # reason: [pkgs]
        all_pkgs = self.ckanclient.package_register_get()
        for pkg_ref in all_pkgs:
            pkg = self.ckanclient.package_entity_get(pkg_ref)
            if not('department' in pkg or 'agency' in pkg or \
                   'published_by' not in pkg['extras'] or \
                   'published_via' not in pkg['extras']):
                pkgs_rejected['Already migrated'].append(pkg)
                continue

            dept = pkg['department']
            agency = pkg['agency']
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
                del pkg['department']
                del pkg['agency']
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
        self.parser.add_option("-D", "--xmlrpc-domain",
                               dest="xmlrpc_domain",
                               )
        self.parser.add_option("-U", "--xmlrpc-username",
                               dest="xmlrpc_username",
                               )
        self.parser.add_option("-U", "--xmlrpc-password",
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

