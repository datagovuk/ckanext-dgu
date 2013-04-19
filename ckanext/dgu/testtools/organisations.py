import os.path
import logging
import sys

from ckanext.dgu.bin.xmlrpc_command import XmlRpcCommand

from ckan.lib.helpers import json

from ckanext.dgu.schema import canonise_organisation_name
from ckanext.dgu.ons.producers import get_ons_producers
from ckanext.dgu.drupalclient import DrupalClient

log = logging.getLogger(__name__)

test_organisations = {'1': {'name': 'National Health Service',
                            'parent_department_id': '7'},
                      '2': {'name': 'Ealing PCT',
                            'parent_department_id': '7'},
                      '3': {'name': 'Department for Education',
                            'parent_department_id': '3'},
                      '4': {'name': 'Department of Energy and Climate Change',
                            'parent_department_id': '4'},
                      '5': {'name': 'Department for Business, Innovation and Skills',
                            'parent_department_id': '5'},
                      '6': {'name': 'Department for Communities and Local Government',
                            'parent_department_id': '6'},
                      '7': {'name': 'Department of Health',
                            'parent_department_id': '7'},
                      '8': {'name': 'Office for National Statistics',
                            'parent_department_id': '8'},
                      }

test_organisation_names = dict([(id, org_dict['name']) for id, org_dict in test_organisations.items()])

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
            org_name = canonise_organisation_name(org_name)
            org_id = drupal.match_organisation(org_name)
            if org_id == False:
                log.error('Could not find organisation %r', org_name)
                has_errors = True
                continue
            proper_org_name = drupal.get_organisation_name(org_id)
            parent_department_id = drupal.get_department_from_organisation(org_id)
            orgs[org_id] = {'name': proper_org_name,
                            'parent_department_id': parent_department_id}
            
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

class OrgCommand(XmlRpcCommand):
    '''Generates a list of organisations for test purposes.
    Checks all organisations to be tested against a real Drupal.
    '''
    summary = 'Generates a list of organisations for test purposes.'
    
    def command(self):
        super(OrgCommand, self).command()

        cmd = LotsOfOrganisations.generate(self.xmlrpc_settings)

def command():
    OrgCommand().command()

