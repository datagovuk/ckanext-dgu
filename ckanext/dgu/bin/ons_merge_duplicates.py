'''
Some ONSHUB datasets are in data.gov.uk twice for an unknown reason - they
have the same title and publisher, which is the search criteria.
e.g. aerospace_and_electronic_cost_indices_ and aerospace_and_electronic_cost_indices
This script merges these pairs together.

Some ONSHUB datasets have no publisher because their 'source agency' was not
recognised but the importer for a while.
e.g. provisional_monthly_patient_reported_outcome_measures_proms_in_england
This script adds the publisher for these, using the latest mapping of
source agencies.
'''

from pprint import pprint
import re

from ckanclient import CkanApiError
from mass_changer_cmd import MassChangerCommand

from ckanext.importlib.loader import PackageLoader
from ckanext.dgu.ons.importer import OnsImporter
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

    def add_missing_onshub_extra(self):
        '''Some ONSHUB datasets were edited manually and due to a bug, many
        of the extras got lost. Here we restore the external_reference=ONSHUB
        extra.
        '''
        stats = StatsList()

        res = self.client.action('package_search', q='!external_reference:ONSHUB \"Source agency\"', sort='name asc', fq=' +site_id:"dgu" +state:active', wt='json', rows=100, escape_q=False)
        
        log.info('ONSHUB datasets missing extras: %i', res['count'])
        source_agency_re = re.compile('^Source agency: (.*)$', re.MULTILINE)

        for pkg in res['results']:
            # solr data_dict is not the correct sort of pkg dictionary so
            # get it via the API
            pkg = self.loader._get_package(pkg['name'])
            match = source_agency_re.search(pkg['notes'])
            if not match:
                log.error(stats.add('Could not find "Source agency: " line after all', pkg['name']))
                continue

            # Add the extra
            pkg['extras']['external_reference'] = 'ONSHUB'
            if not self.dry_run:
                try:
                    self.client.package_entity_put(pkg)
                except CkanApiError:
                    log.error('Error (%s) adding publisher over API: %s' % \
                              (self.client.last_status,
                               self.client.last_message))
                    stats.add('Error writing to publisher over API %s' % self.client.last_status, pkg['name'])
                    continue
            log.info(stats.add('Added extra', pkg['name']))

        print stats.report()
        if self.dry_run:
            print 'NB: No packages changed - dry run.'

    def correct_home_office_titles(self):
        '''Home Office edited their ONSHUB titles to be prefixed with
        "UK National Statistics Publication Hub: ". These cannot be added
        to by the ons_loader in the future because of this title change so
        remove the prefix.
        e.g. scientific_procedures_on_living_animals_great_britain
        '''
        stats = StatsList()
        prefix = 'UK National Statistics Publication Hub: '
        
        res = self.client.action('package_search', q='external_reference:ONSHUB \"%s\"' % prefix, sort='name asc', fq=' +site_id:"dgu" +state:active', wt='json', rows=100, escape_q=False)
        
        log.info('ONSHUB datasets with HOME_OFFICE prefix: %i', res['count'])

        for pkg in res['results']:
            # solr data_dict is not the correct sort of pkg dictionary so
            # get it via the API
            pkg = self.loader._get_package(pkg['name'])
            if not pkg['title'].startswith(prefix):
                log.error(stats.add('Prefix not there after all', pkg['name']))
                continue

            # Remove the prefix
            pkg['title'] = pkg['title'][len(prefix):]
            if not self.dry_run:
                try:
                    self.client.package_entity_put(pkg)
                except CkanApiError:
                    log.error('Error (%s) adding publisher over API: %s' % \
                              (self.client.last_status,
                               self.client.last_message))
                    stats.add('Error writing to publisher over API %s' % self.client.last_status, pkg['name'])
                    continue
            log.info(stats.add('Remove prefix', pkg['name']))

        print stats.report()
        if self.dry_run:
            print 'NB: No packages changed - dry run.'

    def add_missing_publisher(self):
        stats = StatsList()

        res = self.client.action('package_search', q='external_reference:ONSHUB !groups:["" TO *]', sort='name asc', fq=' +site_id:"dgu" +state:active', wt='json', rows=100, escape_q=False)
        
        log.info('ONSHUB datasets missing publisher: %i', res['count'])
        source_agency_re = re.compile('^Source agency: (.*)$', re.MULTILINE)

        for pkg in res['results']:
            # solr data_dict is not the correct sort of pkg dictionary so
            # get it via the API
            pkg = self.loader._get_package(pkg['name'])
            if pkg['groups']:
                log.error(stats.add('Package had a publisher', pkg['name']))
                continue
            match = source_agency_re.search(pkg['notes'])
            if not match:
                log.error(stats.add('Could not match source agency', pkg['name']))
                continue
            # Find equivalent publisher
            source_agency = match.groups()[0]
            publisher_name = OnsImporter._source_to_publisher_(source_agency, self.client)
            if not publisher_name:
                log.error(stats.add('Could not map source agency %s' % source_agency, pkg['name']))
                continue
            pkg['groups'] = [publisher_name]
            if not self.dry_run:
                try:
                    self.client.package_entity_put(pkg)
                except CkanApiError:
                    log.error('Error (%s) adding publisher over API: %s' % \
                              (self.client.last_status,
                               self.client.last_message))
                    stats.add('Error writing to publisher over API %s' % self.client.last_status, pkg['name'])
                    continue
            stats.add('Added publisher %s' % publisher_name, pkg['name'])

        print stats.report()
        if self.dry_run:
            print 'NB: No packages changed - dry run.'

    def merge_duplicates(self):
        merge_stats = StatsList()

        onshub_packages_search_options = {'external_reference': 'ONSHUB',
                                          'state': 'active'}
        res = self.loader._package_search(onshub_packages_search_options)
        log.info('ONSHUB records: %i', res['count'])
        pkgs_already_merged = set()
        for pkg_ref in res['results']:
            pkg = self.loader._get_package(pkg_ref)
            if pkg['name'] in pkgs_already_merged:
                log.info(merge_stats.add('Already merged', pkg['name']))
                continue                
            if not self.loader._pkg_matches_search_options(pkg, onshub_packages_search_options):
                log.error(merge_stats.add('Did not match ONSHUB search after all', pkg['name']))
                continue
            # look for duplicates
            dupe_search_options = {'title': pkg['title'],
                                   'groups': pkg['groups'][0] if pkg['groups'] else '',
                                   'external_reference': 'ONSHUB',
                                   'state': 'active'}
            res = self.loader._package_search(dupe_search_options)
            if not res['count']:
                log.error(merge_stats.add('Could not find itself', pkg['name']))
                continue
            dupe_pkgs = []
            for dupe_pkg_ref in res['results']:
                dupe_pkg = self.loader._get_package(dupe_pkg_ref)
                if dupe_pkg['name'] == pkg['name']:
                    continue
                if not self.loader._pkg_matches_search_options(dupe_pkg, dupe_search_options):
                    log.warn('Did not match duplicate search after all %s %s', pkg['name'], dupe_pkg['name'])
                    continue
                dupe_pkgs.append(dupe_pkg)
            if dupe_pkgs:
                log.info('Found duplicates for %s: %r',
                         pkg['name'],
                         [pkg_['name'] for pkg_ in dupe_pkgs])
                # Fix duplicates
                merge_stats.add('%i duplicates found and merged' % len(dupe_pkgs), pkg['name'])
                for dupe_pkg in dupe_pkgs:
                    pkgs_already_merged.add(dupe_pkg['name'])
                self.do_merge(pkg, dupe_pkgs)
            else:
                log.info(merge_stats.add('No duplicates', pkg['name']))
                

        print merge_stats.report()
        if self.dry_run:
            print 'NB: No packages changed - dry run.'

    def do_merge(self, pkg, dupe_pkgs):
        '''Does the merge. Returns any error message or None if successful.'''
        # Select the package with the least _ in the name to keep
        pkgs_scored = sorted([pkg] + dupe_pkgs, key=lambda p: p['name'].count('_'))
        pkg = pkgs_scored[0]
        dupe_pkgs = pkgs_scored[1:]
        log.info('Keeping %s and merging in %r', pkg['name'],
                 [p['name'] for p in dupe_pkgs])
        copy_keys = ('description', 'url', 'format', 'hub-id', 'size', 'cache_filepath', 'last_modified', 'hash', 'mimetype', 'cache_url')
        for dupe_pkg in dupe_pkgs:
            for res in dupe_pkg['resources']:
                res_copy = dict([(key, res.get(key)) for key in copy_keys])
                pkg['resources'].append(res_copy)
        if not self.dry_run:
            # Write the package
            try:
                self.client.package_entity_put(pkg)
            except CkanApiError:
                log.error('Error (%s) editing package over API: %s' % \
                          (self.client.last_status,
                           self.client.last_message))
                return 'Could not edit package: %s' % self.client.last_status
            # Delete the duplicates
            for dupe_pkg in dupe_pkgs:
                try:
                    self.client.package_entity_delete(dupe_pkg['name'])
                except CkanApiError:
                    log.error('Error (%s) deleting over API: %s' % \
                              (self.client.last_status,
                               self.client.last_message))
                    return 'Could not delete package: %s' % self.client.last_status
                
        return True

            
        
class Command(MassChangerCommand):
    '''Merges duplicate ONSHUB datasets. And adds a publisher to a dataset
    if it is missing.
    '''
    
    def command(self):
        super(Command, self).command()

        tool = Tool(self.client,
                    dry_run=self.options.dry_run,
                    force=self.options.force)
        tool.add_missing_onshub_extra()
        tool.correct_home_office_titles()
        tool.add_missing_publisher()
        tool.merge_duplicates()

    def add_options(self):
        super(Command, self).add_options()

def command():
    Command().command()
