from collections import defaultdict
import socket
import copy

from xmlrpclib import ServerProxy, ProtocolError, ResponseError
from nose.tools import assert_equal

from common import ScriptError, remove_readonly_fields
from ckanclient import CkanApiError

from ckanext.importlib.spreadsheet_importer import CsvData
from ckanext.dgu import schema

log = __import__("logging").getLogger(__name__)

mapped_attributes = {
    'temporal_granularity': dict(zip(['years', 'quarters', 'months', 'weeks', 'days', 'hours', 'points'],
                                     ['year', 'quarter', 'month', 'week', 'day', 'hour', 'point'])),

    'update_frequency': dict(zip(('annually', 'quarterly', 'monthly', 'never'),
                                 ('annual', 'quarterly', 'monthly', 'never'))), #'discontinued'
    }

class PublisherMigration:
    '''Changes department/agency fields to published_by/_via'''
    def __init__(self, ckanclient,
                 xmlrpc_domain, xmlrpc_username, xmlrpc_password,
                 publisher_map_filepath,
                 update_all,
                 dry_run=False):
        self.ckanclient = ckanclient
        self.dry_run = dry_run
        self.xmlrpc = {'username':xmlrpc_username,
                       'password':xmlrpc_password,
                       'domain':xmlrpc_domain}
        self.publisher_map = self.read_publisher_map(publisher_map_filepath) \
                             if publisher_map_filepath else {}
        self.update_all = update_all
        self.organisations = {}

    def read_publisher_map(self, publisher_map_filepath):
        logger = None
        publisher_map = {}
        data = CsvData(logger, filepath=publisher_map_filepath)
        header = data.get_row(0)
        assert_equal(header[:2], ['Agency text', 'Corrected name'])
        for row_index in range(data.get_num_rows())[1:]:
            row = data.get_row(row_index)
            if len(row) < 2:
                continue
            agency, publisher = row[:2]
            agency = agency.strip()
            publisher = publisher.strip()
            if agency and publisher:
                publisher_map[agency] = publisher
        return publisher_map
        
    def get_organisation(self, dept_or_agency):
        if not self.organisations.has_key(dept_or_agency):
            # check for name mapping
            mapped_publisher = self.publisher_map.get(dept_or_agency.strip())
            if mapped_publisher:
                log.info('Mapping %r to %r', dept_or_agency, mapped_publisher)
                dept_or_agency = mapped_publisher

            # try canonical name
            dept_or_agency = schema.canonise_organisation_name(dept_or_agency)

            # look up with Drupal
            if not hasattr(self, 'drupal'):
                domain = self.xmlrpc['domain']
                username = self.xmlrpc['username']
                password = self.xmlrpc['password']
                if username or password:
                    server = '%s:%s@%s' % (username, password, domain)
                else:
                    server = '%s' % domain
                self.xmlrpc_url = 'http://%s/services/xmlrpc' % server
                log.info('XMLRPC connection to %s', self.xmlrpc_url)
                self.drupal = ServerProxy(self.xmlrpc_url)
            try:
                org_id = self.drupal.organisation.match(dept_or_agency)
            except socket.error, e:
                raise ScriptError('Socket error connecting to %s', self.xmlrpc_url)
            except ProtocolError, e:
                raise ScriptError('XMLRPC error connecting to %s', self.xmlrpc_url)
            except ResponseError, e:
                raise ScriptError('XMLRPC response error connecting to %s for department: %r', self.xmlrpc_url, dept_or_agency)
            if org_id:
                try:
                    org_name = self.drupal.organisation.one(org_id)
                except socket.error, e:
                    raise ScriptError('Socket error connecting to %s', self.xmlrpc_url)
                except ProtocolError, e:
                    raise ScriptError('XMLRPC error connecting to %s', self.xmlrpc_url)
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
                except CkanApiError, e:
                    log.error('Could not get: %r' % e)
                    pkgs_rejected['Could not get package: %r' % e].append(pkg_ref)
                    continue
                pkg_before_changes = copy.deepcopy(pkg)

                # mapped attributes
                for attribute in mapped_attributes:
                    orig_value = pkg['extras'].get(attribute)
                    if not orig_value:
                        continue
                    mapped_value = mapped_attributes[attribute].get(orig_value)
                    if not mapped_value:
                        mapped_value = mapped_attributes[attribute].get(orig_value.lower().strip())
                        if not mapped_value:
                            if orig_value.lower() in mapped_attributes[attribute].values():
                                mapped_value = orig_value.lower()
                    if mapped_value and orig_value != mapped_value:
                        pkg['extras'][attribute] = mapped_value
                        log.info('%s: %r -> %r', \
                                 attribute, orig_value, mapped_value)
                    else:
                        log.warn('Invalid value for %r: %r', \
                                 attribute, orig_value)

                # create publisher fields
                if self.update_all or not pkg['extras'].get('published_by'):
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
                    pkg['extras']['published_by'] = pub_by
                    pkg['extras']['published_via'] = pub_via
                
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
        self.parser.add_option("-m", "--publisher-map",
                               dest="publisher_map_csv",
                               )
        self.parser.add_option("--update-all",
                               dest="update_all",
                               )

    def command(self):
        super(Command, self).command()

        # now do command
        cmd = PublisherMigration(self.client,
                                 self.options.xmlrpc_domain,
                                 self.options.xmlrpc_username,
                                 self.options.xmlrpc_password,
                                 self.options.publisher_map_csv,
                                 self.options.update_all,
                                 dry_run=self.options.dry_run)
        cmd.run()

def command():
    Command().command()

