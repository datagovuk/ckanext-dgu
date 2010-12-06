from ckan.lib.create_test_data import CreateTestData

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
        'department':u'Department for Children, Schools and Families',
        'temporal_granularity':u'year',
        'temporal_coverage-from':u'2008-6',
        'temporal_coverage-to':u'2009-6',
        'national_statistic':u'yes',
        'precision':u'Numbers to nearest 10, percentage to nearest whole number',
        'taxonomy_url':u'',
        'agency':u'',
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
        'department':u'Department of Energy and Climate Change',
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
        'department':u'Department for Children, Schools and Families',
        'temporal_granularity':u'year',
        'temporal_coverage-from':u'2008-6-24 12:30',
        'temporal_coverage-to':u'2009-6',
        'national_statistic':u'yes',
        'precision':u'Numbers to nearest 10, percentage to nearest whole number',
        'mandate':u'http://www.legislation.gov.uk/id/ukpga/Eliz2/6-7/51/section/2',                
                'taxonomy_url':u'',
        'agency':u'',
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
        'department':u'Department of Energy and Climate Change',
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
        assert not missing_keys, 'Missing keys: %r. All unmatching keys: %r' % (extra_keys, unmatching_keys)
        extra_keys = set(dict_to_check.keys()) - set(expected_dict.keys())
        assert not extra_keys, 'Keys that should not be there: %r. All unmatching keys: %r' % (extra_keys, unmatching_keys)

def teardown_module():
    assert not CreateTestData.get_all_data(), 'A test in module %r forgot to clean-up its data: %r' % (__name__, CreateTestData.get_all_data())
