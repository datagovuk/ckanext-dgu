import os

import paste.fixture
from paste.deploy import appconfig
from pylons import config

from ckan import __file__ as ckan_file
from ckan.config.middleware import make_app
from ckan.lib.create_test_data import CreateTestData

def apply_fixture_config(config_):
    local_config = [
        ('dgu.xmlrpc_username', 'testuser'),
        ('dgu.xmlrpc_password', 'testpassword'),
        ('dgu.xmlrpc_domain', 'localhost:8000'), # must match MockDrupal
        ]
    config_.update(local_config)    

class WsgiAppCase(object):
    ckan_config_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(ckan_file)), '..'))
    config_ = appconfig('config:test.ini', relative_to=ckan_config_dir)
    local_config = [('ckan.plugins', 'dgu_form_api form_api_tester'),]
    config_.local_conf.update(local_config)
    config_.local_conf['ckan.plugins'] = 'dgu_form_api form_api_tester'
    # set test config for dgu_form_api - it is imported before the test modules
    apply_fixture_config(config_.local_conf)
    wsgiapp = make_app(config_.global_conf, **config_.local_conf)
    app = paste.fixture.TestApp(wsgiapp)

class BaseCase(object):
    @staticmethod
    def _system(cmd):
        import commands
        (status, output) = commands.getstatusoutput(cmd)
        if status:
            raise Exception, "Couldn't execute cmd: %s: %s" % (cmd, output)

    @classmethod
    def _paster(cls, cmd, config_path_rel):
        cls._system('paster --plugin ckanext-dgu %s' % cmd)


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
                  'format':u'XLS',
                  'description':u'December 2009 | http://www.statistics.gov.uk/hub/id/119-36345'},
                  {'url':u'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000860/SFR17_2009_key.doc',
                  'format':u'DOC',
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
        'geographic_coverage':u'100000: England',
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
     'resources':[{'url':u'', 'format':u'XLS', 'description':u''}],
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
        'geographic_coverage':u'111100: United Kingdom (England, Scotland, Wales, Northern Ireland)',
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
                  'format':u'XLS',
                  'description':u'December 2009 | http://www.statistics.gov.uk/hub/id/119-36345'},
                  {'url':u'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000860/SFR17_2009_key.doc',
                  'format':u'DOC',
                  'description':u'http://www.statistics.gov.uk/hub/id/119-34565'}],
     'url':u'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000859/index.shtml',
     'author':u'DCSF Data Services Group',
     'author_email':u'statistics@dcsf.gsi.gov.uk',
     'license':u'uk-ogl',
     'tags':u'children fostering',
     'extras':{
        'external_reference':u'DCSF-DCSF-0024',
        'date_released':u'2009-07-30',
        'date_updated':u'2009-07-30 12:30',
        'date_update_future':u'2009-07-01',
        'update_frequency':u'annual',
        'geographic_granularity':u'regional',
        'geographic_coverage':u'100000: England',
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
     'resources':[{'url':u'', 'format':u'XLS', 'description':u''}],
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
        'geographic_granularity':u'national',
        'geographic_coverage':u'111100: United Kingdom (England, Scotland, Wales, Northern Ireland)',
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

test_publishers = {'1': 'National Health Service',
                   '2': 'Ealing PCT',
                   '3': 'Department for Education',
                   '4': 'Department of Energy and Climate Change',
                   }

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
        assert not missing_keys, 'Missing keys: %r. All unmatching keys: %r' % (extra_keys, unmatching_keys)
        extra_keys = set(dict_to_check.keys()) - set(expected_dict.keys())
        assert not extra_keys, 'Keys that should not be there: %r. All unmatching keys: %r' % (extra_keys, unmatching_keys)


class MockDrupalCase(BaseCase):
    @classmethod
    def setup_class(cls):
        cls.process = cls._mock_drupal_start()
        cls._wait_for_drupal_to_start()

    @classmethod
    def teardown_class(cls):
        cls._mock_drupal_stop(cls.process)

    @classmethod
    def _mock_drupal_start(self):
        import subprocess
        process = subprocess.Popen(['paster', 'mock_drupal', 'run'])
        return process

    @staticmethod
    def _wait_for_drupal_to_start(url='http://localhost:8000/services/xmlrpc',
                                  timeout=15):
        import xmlrpclib
        import socket
        import time

        drupal = xmlrpclib.ServerProxy(url)
        for i in range(int(timeout)*100):
            try:
                response = drupal.system.listMethods()
            except socket.error, e:
                time.sleep(0.01)
            else:
                break

    @classmethod
    def _mock_drupal_stop(cls, process):
        pid = process.pid
        pid = int(pid)
        if os.system("kill -9 %d" % pid):
            raise Exception, "Can't kill foreign Mock Drupal instance (pid: %d)." % pid
