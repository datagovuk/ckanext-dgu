import os
import re
import signal
from paste.script.appinstall import SetupCommand
from pylons import config

from ckan import model
from ckan.lib.create_test_data import CreateTestData
from ckan.tests import WsgiAppCase, BaseCase
from ckanext.dgu.testtools.mock_drupal import MOCK_DRUPAL_URL
from ckanext.harvest.model import HarvestSource, HarvestJob, HarvestObject
from ckanext.harvest.model import setup as harvest_setup

# Invoke websetup with the current config file
SetupCommand('setup-app').run([config['__file__']])


class PackageFixturesBase:
    def create(self, **kwargs):
        CreateTestData.create_arbitrary(self.pkgs,
                                        extra_user_names=[self.user_name],
                                        **kwargs)

    def delete(self):
        CreateTestData.delete()

class GovFixtures(PackageFixturesBase):
    user_name = 'tester'

    @property
    def pkgs(self):
        if not hasattr(self, '_pkgs'):
            self._pkgs = [
    {
     'name':u'private-fostering-england-2009',
     'title':u'Private Fostering',
     'notes':u'Figures on children cared for and accommodated in private fostering arrangements, England, Year ending 31 March 2009',
     'resources':[{'url':u'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000859/SFR17_2009_tables.xls',
                  'format':u'xls',
                  'description':u'December 2009 | http://www.statistics.gov.uk/hub/id/119-36345'},
                  {'url':u'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000860/SFR17_2009_key.doc',
                  'format':u'doc',
                  'description':u'http://www.statistics.gov.uk/hub/id/119-34565'}],
     'url':u'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000859/index.shtml',
     'author':u'DCSF Data Services Group',
     'author_email':u'statistics@dcsf.gsi.gov.uk',
     'license':u'ukcrown',
     'tags':u'children fostering',
     'extras':{
        'external_reference':u'DCSF-DCSF-0024',
        'date_released':u'2009-07-30',
        'date_updated':u'2009-07-30',
        'update_frequency':u'annual',
        'geographic_granularity':u'regional',
        'geographic_coverage':u'1000000: England',
        'department':u'Department for Education',
        'agency':u'',
        'temporal_granularity':u'year',
        'temporal_coverage-from':u'2008-6',
        'temporal_coverage-to':u'2009-6',
        'national_statistic':u'yes',
        'precision':u'Numbers to nearest 10, percentage to nearest whole number',
        'taxonomy_url':u'',
        'import_source':u'ONS-Jan-09',
        }
     },
    {'name':u'weekly-fuel-prices',
     'title':u'Weekly fuel prices',
     'notes':u'Latest price as at start of week of unleaded petrol and diesel.',
     'resources':[{'url':u'', 'format':u'xls', 'description':u''}],
     'url':u'http://www.decc.gov.uk/en/content/cms/statistics/source/prices/prices.aspx',
     'author':u'DECC Energy Statistics Team',
     'author_email':u'energy.stats@decc.gsi.gov.uk',
     'license':u'ukcrown',
     'tags':u'fuel prices',
     'extras':{
        'external_reference':u'DECC-DECC-0001',
        'date_released':u'2009-11-24',
        'date_updated':u'2009-11-24',
        'update_frequency':u'weekly',
        'department':u'Department of Energy and Climate Change',
        'agency':u'',
        'geographic_granularity':u'national',
        'geographic_coverage':u'1111000: United Kingdom (England, Scotland, Wales, Northern Ireland)',
        'temporal_granularity':u'weeks',
        'temporal_coverage-from':u'2008-11-24',
        'temporal_coverage-to':u'2009-11-24',
        'national_statistic':u'yes',
        'import_source':u'DECC-Jan-09',
        }
     }
                ]
        return self._pkgs

class Gov3Fixtures(PackageFixturesBase):
    user_name = 'tester'

    @property
    def pkgs(self):
        if not hasattr(self, '_pkgs'):
            self._pkgs = [
    {
     'name':u'private-fostering-england-2009',
     'title':u'Private Fostering',
     'notes':u'Figures on children cared for and accommodated in private fostering arrangements, England, Year ending 31 March 2009',
     'resources':[{'url':u'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000859/SFR17_2009_tables.xls',
                  'format':u'xls',
                  'description':u'December 2009 | http://www.statistics.gov.uk/hub/id/119-36345',
                  'resource_type': u'file',
                  'name':u''},
                  {'url':u'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000860/SFR17_2009_key.doc',
                  'format':u'doc',
                  'description':u'http://www.statistics.gov.uk/hub/id/119-34565',
                  'resource_type': u'documentation',
                  'name':u''}],
     'url':u'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000859/index.shtml',
     'author':u'DCSF Data Services Group',
     'author_email':u'statistics@dcsf.gsi.gov.uk',
     'license':u'uk-ogl',
     'tags':u'children fostering',
     'groups':['publisher-1'],
     'extras':{
        'external_reference':u'DCSF-DCSF-0024',
        'date_released':u'2009-07-30',
        'date_updated':u'2009-07-30 12:30',
        'date_update_future':u'2009-07-01',
        'update_frequency':u'annual',
        'geographic_granularity':u'regional',
        'geographic_coverage':u'1000000: England',
        'published_by':u'Department for Education [3]',
        'published_via':u'',
        'temporal_granularity':u'year',
        'temporal_coverage-from':u'2008-6-24 12:30',
        'temporal_coverage-to':u'2009-6',
        'national_statistic':u'yes',
        'precision':u'Numbers to nearest 10, percentage to nearest whole number',
        'mandate':u'http://www.legislation.gov.uk/id/ukpga/Eliz2/6-7/51/section/2',
                'taxonomy_url':u'',
        'import_source':u'ONS-Jan-09',
        }
     },
    {'name':u'weekly-fuel-prices',
     'title':u'Weekly fuel prices',
     'notes':u'Latest price as at start of week of unleaded petrol and diesel.',
     'resources':[{'url':u'', 'format':u'xls', 'description':u'', 'name':u''}],
     'url':u'http://www.decc.gov.uk/en/content/cms/statistics/source/prices/prices.aspx',
     'author':u'DECC Energy Statistics Team',
     'author_email':u'energy.stats@decc.gsi.gov.uk',
     'license':u'ukcrown',
     'tags':u'fuel prices',
     'groups':['publisher-1'],
     'extras':{
        'external_reference':u'DECC-DECC-0001',
        'date_released':u'2009-11-24',
        'date_updated':u'2009-11-24',
        'update_frequency':u'weekly',
        'geographic_granularity':u'national',
        'geographic_coverage':u'1111000: United Kingdom (England, Scotland, Wales, Northern Ireland)',
        'published_by':u'Department of Energy and Climate Change [4]',
        'published_via':u'',
        'temporal_granularity':u'weeks',
        'temporal_coverage-from':u'2008-11-24',
        'temporal_coverage-to':u'2009-11-24',
        'national_statistic':u'yes',
        'import_source':u'DECC-Jan-09',
        }
     }
                ]
        return self._pkgs


class PackageDictUtil(object):
    @classmethod
    def check_dict(cls, dict_to_check, expected_dict):
        for key, value in expected_dict.items():
            if key == 'extras':
                cls.check_dict(dict_to_check['extras'], value)
            else:
                if value:
                    assert dict_to_check[key] == value, 'Key \'%s\' should be %r not: %r' % (key, value, dict_to_check[key])
                else:
                    assert not dict_to_check.get(key), 'Key \'%s\' should have no value, not: %s' % (key, dict_to_check[key])
        unmatching_keys = set(dict_to_check.keys()) ^ set(expected_dict.keys())
        missing_keys = set(expected_dict.keys()) - set(dict_to_check.keys())
        assert not missing_keys, 'Missing keys: %r. All unmatching keys: %r' % (missing_keys, unmatching_keys)
        extra_keys = set(dict_to_check.keys()) - set(expected_dict.keys())
        assert not extra_keys, 'Keys that should not be there: %r. All unmatching keys: %r' % (extra_keys, unmatching_keys)

    @classmethod
    def assert_subset(cls, dict_to_check, expected_dict):
        '''Takes a package dict_to_check and an expected package dict(expected_dict).
        Returns ok if the items in the expected_dict are in the dict_to_check. If there
        are other keys in the dict_to_check then these are ignored.

        '''
        for key, value in expected_dict.items():
            if key == 'extras':
                cls.assert_subset(dict_to_check['extras'], value)
            else:
                if value:
                    assert dict_to_check[key] == value, 'Key \'%s\' should be %r not: %r' % (key, value, dict_to_check[key])
                else:
                    assert not dict_to_check.get(key), 'Key \'%s\' should have no value, not: %s' % (key, dict_to_check[key])
        missing_keys = set(expected_dict.keys()) - set(dict_to_check.keys())
        assert not missing_keys, 'Missing keys: %r' % (missing_keys)

class DrupalSetupError(Exception):
    pass

class MockDrupalCase(BaseCase):
    xmlrpc_url = MOCK_DRUPAL_URL
    xmlrpc_settings = {'xmlrpc_url': xmlrpc_url}

    @classmethod
    def setup_class(cls):
        cls._check_drupal_not_already_running()
        MockDrupalCase.process = cls._mock_drupal_start()
        cls._wait_for_drupal_to_start()

    @classmethod
    def teardown_class(cls):
        cls._mock_drupal_stop(MockDrupalCase.process)

    @classmethod
    def _mock_drupal_start(cls):
        import subprocess
        options = ['-q']
        if hasattr(cls, 'lots_of_publishers') and cls.lots_of_publishers:
            options.append('-l')
        process = subprocess.Popen(['paster', '--plugin=ckanext-dgu', 'mock_drupal', 'run'] + options)
        return process

    @classmethod
    def _check_drupal_not_already_running(cls,
                                          url=None):
        import xmlrpclib
        import socket
        import time

        url = url or cls.xmlrpc_url
        drupal = xmlrpclib.ServerProxy(url)
        try:
            response = drupal.system.listMethods()
        except socket.error, e:
            return

        raise DrupalSetupError('MockDrupal already seems to be running: %s.\n'
                               'Kill its process (paster) first.' % url)

    @classmethod
    def _wait_for_drupal_to_start(cls,
                                  url=None,
                                  timeout=15):
        import xmlrpclib
        import socket
        import time

        url = url or cls.xmlrpc_url
        drupal = xmlrpclib.ServerProxy(url)
        for i in range(int(timeout)*100):
            try:
                response = drupal.system.listMethods()
            except socket.error, e:
                time.sleep(0.01)
            else:
                return
        raise DrupalSetupError('Time-out while waiting for Drupal to start up.')

    @classmethod
    def _mock_drupal_stop(cls, process):
      process.terminate()

def strip_organisation_id(org_name_with_id):
    # e.g. 'NHS [54]' becomes 'NHS [some_number]'
    return re.sub('\[\d+\]', '[some_number]', org_name_with_id)

class HarvestFixture(object):
    '''Base class, useful for several tests relating to harvesting.'''
    @classmethod
    def setup_class(cls):
        # Create package and its harvest object
        CreateTestData.create()
        harvest_setup()
        source = HarvestSource(url=u'http://test-source.org',type='test')
        source.save()

        job = HarvestJob(source=source)
        job.save()

        ho = HarvestObject(package=model.Package.by_name(u'annakarenina'),
                           job=job,
                           guid=u'test-guid',
                           content=u'<xml>test content</xml>')
        ho.save()

        # Save a reference to the harvest object in the package
        rev = model.repo.new_revision()
        pkg = model.Package.by_name(u'annakarenina')
        pkg.extras['harvest_object_id'] = ho.id
        pkg.save()

        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

def assert_solr_schema_is_the_dgu_variant():
    '''
        Checks if the schema version of the SOLR server is compatible
        with DGU.

        Based on ckan.lib.search.check_solr_schema_version
    '''

    import urllib2
    from ckan.lib.search.common import is_available, SolrSettings
    from ckan.lib.search import SOLR_SCHEMA_FILE_OFFSET

    if not is_available():
        # Something is wrong with the SOLR server
        log.warn('Problems were found while connecting to the SOLR server')
        return False

    # Request the schema XML file to extract the version
    solr_url, solr_user, solr_password = SolrSettings.get()
    http_auth = None
    if solr_user is not None and solr_password is not None:
        http_auth = solr_user + ':' + solr_password
        http_auth = 'Basic ' + http_auth.encode('base64').strip()

    url = solr_url.strip('/') + SOLR_SCHEMA_FILE_OFFSET

    req = urllib2.Request(url=url)
    if http_auth:
        req.add_header('Authorization', http_auth)

    solr_schema = urllib2.urlopen(req).read()
    assert 'DGU variant' in solr_schema, 'Change your development.ini to use the DGU schema.'
