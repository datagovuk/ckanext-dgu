import os.path
import logging
import sys

from ckanext.command import Command

from ckan.lib.helpers import json

from ckanext.dgu import schema
from ckanext.dgu.ons.producers import get_ons_producers
from ckanext.dgu.drupalclient import DrupalClient

log = logging.getLogger(__name__)

test_organisations = {'1': 'National Health Service',
                      '2': 'Ealing PCT',
                      '3': 'Department for Education',
                      '4': 'Department of Energy and Climate Change',
                      '5': 'Department for Business, Innovation and Skills',
                      }

class LotsOfOrganisations(object):
    orgs_cache = {}
    lots_of_orgs_filepath = os.path.join(os.path.dirname(__file__),
                                         'lots_of_orgs.json')

    @classmethod
    def get(cls):
        if not cls.orgs_cache:
            f = open(cls.lots_of_orgs_filepath, 'r')
            cls.orgs_cache = json.loads(f.read())
        return cls.orgs_cache

    @classmethod
    def generate(cls, xmlrpc_settings):
        drupal = DrupalClient(xmlrpc_settings)
        orgs = {}
        has_errors = False
        orgs_to_lookup = set()
        orgs_to_lookup.add('Northern Ireland Executive')
        orgs_to_lookup |= set(get_ons_producers())
        for org_name in orgs_to_lookup:
            org_name = schema.canonise_organisation_name(org_name)
            org_id = drupal.match_organisation(org_name)
            if org_id == False:
                log.error('Could not find organisation %r', org_name)
                has_errors = True
                continue
            proper_org_name = drupal.get_organisation_name(org_id)
            orgs[org_id] = proper_org_name
            
        f = open(cls.lots_of_orgs_filepath, 'w')
        try:
            f.write(json.dumps(orgs))
        finally:
            f.close()

        if has_errors:
            print 'Finished with ERRORS'
            sys.exit(1)
        else:
            print 'Finished with SUCCESS'

class OrgCommand(Command):
    '''Generates a list of organisations for test purposes.
    Checks all organisations to be tested against a real Drupal.
    '''
    summary = 'Generates a list of organisations for test purposes.'
    
    def __init__(self, usage=None):
        self.parser = Command.StandardParser(usage=usage)
        self.parser.add_option("-X", "--xmlrpc-url",
                               dest="xmlrpc_url",
                               )
        self.parser.add_option("-D", "--xmlrpc-domain",
                               dest="xmlrpc_domain",
                               )
        self.parser.add_option("-U", "--xmlrpc-username",
                               dest="xmlrpc_username",
                               )
        self.parser.add_option("-P", "--xmlrpc-password",
                               dest="xmlrpc_password",
                               )
        super(OrgCommand, self).__init__()

    def command(self):
        if not (self.options.xmlrpc_domain or self.options.xmlrpc_url):
            self.parser.error('Please specify an XML RPC domain or URL')

        xmlrpc_settings = {
            'xmlrpc_url':self.options.xmlrpc_url,
            'xmlrpc_domain':self.options.xmlrpc_domain,
            'xmlrpc_username':self.options.xmlrpc_username,
            'xmlrpc_password':self.options.xmlrpc_password}

        cmd = LotsOfOrganisations.generate(xmlrpc_settings)

def command():
    OrgCommand().command()

