import os

from pylons import config
from sqlalchemy.util import OrderedDict

from ckanext.dgu.ons import importer
from ckanext.loader import PackageLoader, ResourceSeries
from ckanext.tests.test_loader import TestLoaderBase
from ckan import model
from ckan.tests import *


TEST_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_PATH = os.path.join(TEST_DIR, 'samples')
SAMPLE_FILEPATH_1 = os.path.join(SAMPLE_PATH, 'ons_hub_sample.xml')
SAMPLE_FILEPATH_2 = os.path.join(SAMPLE_PATH, 'ons_hub_sample2.xml')
SAMPLE_FILEPATH_3 = os.path.join(SAMPLE_PATH, 'ons_hub_sample3')
SAMPLE_FILEPATH_4 = os.path.join(SAMPLE_PATH, 'ons_hub_sample4.xml')
SAMPLE_FILEPATH_4a = os.path.join(SAMPLE_PATH, 'ons_hub_sample4a.xml')
SAMPLE_FILEPATH_4b = os.path.join(SAMPLE_PATH, 'ons_hub_sample4b.xml')
TEST_PKG_NAMES = ['uk_official_holdings_of_international_reserves', 'cereals_and_oilseeds_production_harvest', 'end_of_custody_licence_release_and_recalls', 'sentencing_statistics_brief_england_and_wales', 'population_in_custody_england_and_wales', 'probation_statistics_brief']


class OnsLoader(PackageLoader):
    def __init__(self, client):
        settings = ResourceSeries(
            field_keys_to_find_pkg_by=['title', 'department'],
            resource_id_prefix='hub/id/',
            field_keys_to_expect_invariant=[
                'update_frequency', 'geographical_granularity',
                'geographic_coverage', 'temporal_granularity',
                'precision', 'url', 'taxonomy_url', 'agency',
                'author', 'author_email', 'license_id'])
        super(OnsLoader, self).__init__(client, settings)

class TestOnsLoadBasic(TestLoaderBase):
    def setup(self):
        self.tsi = TestSearchIndexer()
        super(TestOnsLoadBasic, self).setup()
        importer_ = importer.OnsImporter(SAMPLE_FILEPATH_1)
        self.pkg_dicts = [pkg_dict for pkg_dict in importer_.pkg_dict()]

        loader = OnsLoader(self.testclient)
        self.tsi.index() # this needs to run during package loading too
                         # but the test copes...
        self.res = loader.load_packages(self.pkg_dicts)
        assert self.res['num_errors'] == 0, self.res
        CreateTestData.flag_for_deletion(TEST_PKG_NAMES)

    def test_fields(self):
        q = model.Session.query(model.Package)
        names = [pkg.name for pkg in q.all()]
        pkg1 = model.Package.by_name(u'uk_official_holdings_of_international_reserves')
        cereals = model.Package.by_name(u'cereals_and_oilseeds_production_harvest')
        custody = model.Package.by_name(u'end_of_custody_licence_release_and_recalls')
        probation = model.Package.by_name(u'probation_statistics_brief')
        assert pkg1, names
        assert cereals, names
        assert custody, names
        assert probation, names
        assert pkg1.title == 'UK Official Holdings of International Reserves', pkg1.title
        assert pkg1.notes.startswith("Monthly breakdown for government's net reserves, detailing gross reserves and gross liabilities."), pkg1.notes
        assert len(pkg1.resources) == 1, pkg1.resources
        assert pkg1.resources[0].url == 'http://www.hm-treasury.gov.uk/national_statistics.htm', pkg1.resources[0]
        assert pkg1.resources[0].description == 'December 2009 | hub/id/119-36345', pkg1.resources[0].description
        assert len(custody.resources) == 2, custody.resources
        assert custody.resources[0].url == 'http://www.justice.gov.uk/publications/endofcustodylicence.htm', custody.resources[0]
        assert custody.resources[0].description == 'November 2009 | hub/id/119-36836', custody.resources[0].description
        assert custody.resources[1].url == 'http://www.justice.gov.uk/publications/endofcustodylicence.htm', custody.resources[0]
        assert custody.resources[1].description == 'December 2009 | hub/id/119-36838', custody.resources[1].description
        assert pkg1.extras['date_released'] == u'2010-01-06', pkg1.extras['date_released']
        assert probation.extras['date_released'] == u'2010-01-04', probation.extras['date_released']
        assert pkg1.extras['department'] == u"Her Majesty's Treasury", pkg1.extras['department']
        assert cereals.extras['department'] == u"Department for Environment, Food and Rural Affairs", cereals.extras['department']
        assert custody.extras['department'] == u"Ministry of Justice", custody.extras['department']
        assert u"Source agency: HM Treasury" in pkg1.notes, pkg1.notes
        assert pkg1.extras['categories'] == 'Economy', pkg1.extras['category']
        assert pkg1.extras['geographic_coverage'] == '111100: United Kingdom (England, Scotland, Wales, Northern Ireland)', pkg1.extras['geographic_coverage']
        assert pkg1.extras['national_statistic'] == 'no', pkg1.extras['national_statistic']
        assert cereals.extras['national_statistic'] == 'yes', cereals.extras['national_statistic']
        assert custody.extras['national_statistic'] == 'no', custody.extras['national_statistic']
        assert 'Designation: Official Statistics not designated as National Statistics' in custody.notes
        assert pkg1.extras['geographical_granularity'] == 'UK and GB', pkg1.extras['geographical_granularity']
        assert 'Language: English' in pkg1.notes, pkg1.notes
        def check_tags(pkg, tags_list):            
            pkg_tags = [tag.name for tag in pkg.tags]
            for tag in tags_list:
                assert tag in pkg_tags, "Couldn't find tag '%s' in tags: %s" % (tag, pkg_tags)
        check_tags(pkg1, ('economics-and-finance', 'reserves', 'currency', 'assets', 'liabilities', 'gold', 'economy', 'government-receipts-and-expenditure', 'public-sector-finance'))
        check_tags(cereals, ('environment', 'farming'))
        check_tags(custody, ('public-order-justice-and-rights', 'justice-system', 'prisons'))
        assert 'Alternative title: UK Reserves' in pkg1.notes, pkg1.notes
        
        assert pkg1.extras['external_reference'] == u'ONSHUB', pkg1.extras['external_reference']
        assert 'UK Crown Copyright with data.gov.uk rights' in pkg.license.title, pkg.license.title
        assert pkg1.extras['update_frequency'] == u'monthly', pkg1.extras['update_frequency']
        assert custody.extras['update_frequency'] == u'monthly', custody.extras['update_frequency']
        assert pkg1.author == u"Her Majesty's Treasury", pkg1.author
        assert cereals.author == u'Department for Environment, Food and Rural Affairs', cereals.author
        assert custody.author == u'Ministry of Justice', custody.author

#        assert model.Group.by_name(u'ukgov') in pkg1.groups
        for pkg in (pkg1, cereals, custody):
            assert pkg.extras['import_source'].startswith('ONS'), '%s %s' % (pkg.name, pkg.extras['import_source'])


class TestOnsLoadTwice(TestLoaderBase):
    def setup(self):
        self.tsi = TestSearchIndexer()
        super(TestOnsLoadTwice, self).setup()
        # SAMPLE_FILEPATH_2 has the same packages as 1, but slightly updated
        for filepath in [SAMPLE_FILEPATH_1, SAMPLE_FILEPATH_2]:
            importer_ = importer.OnsImporter(filepath)
            pkg_dicts = [pkg_dict for pkg_dict in importer_.pkg_dict()]
            loader = OnsLoader(self.testclient)
            self.tsi.index()
            res = loader.load_packages(pkg_dicts)
            assert res['num_errors'] == 0, res
        CreateTestData.flag_for_deletion(TEST_PKG_NAMES)

    def test_packages(self):
        pkg = model.Package.by_name(u'uk_official_holdings_of_international_reserves')
        assert pkg.title == 'UK Official Holdings of International Reserves', pkg.title
        assert pkg.notes.startswith('CHANGED'), pkg.notes
        assert len(pkg.resources) == 1, pkg.resources
        assert 'CHANGED' in pkg.resources[0].description, pkg.resources


class TestOnsLoadClashTitle(TestLoaderBase):
    # two packages with the same title, both from ONS,
    # but from different departments, so must be different packages
    def setup(self):
        self.tsi = TestSearchIndexer()
        super(TestOnsLoadClashTitle, self).setup()
        # ons items have been split into 3 files, because search needs to
        # do indexing in between
        for suffix in 'abc':
            importer_ = importer.OnsImporter(SAMPLE_FILEPATH_3 + suffix + '.xml')
            pkg_dicts = [pkg_dict for pkg_dict in importer_.pkg_dict()]
            loader = OnsLoader(self.testclient)
            self.tsi.index()
            self.res = loader.load_packages(pkg_dicts)
            assert self.res['num_errors'] == 0, self.res
        CreateTestData.flag_for_deletion(TEST_PKG_NAMES)

    def test_ons_package(self):
        pkg = model.Package.by_name(u'annual_survey_of_hours_and_earnings')
        assert pkg
        assert not pkg.extras.get('department'), pkg.extras.get('department')
        assert 'Office for National Statistics' in pkg.notes, pkg.notes
        assert len(pkg.resources) == 2, pkg.resources
        assert '2007 Results Phase 3 Tables' in pkg.resources[0].description, pkg.resources
        assert '2007 Pensions Results' in pkg.resources[1].description, pkg.resources

    def test_welsh_package(self):
        pkg = model.Package.by_name(u'annual_survey_of_hours_and_earnings_')
        assert pkg
        assert pkg.extras['department'] == 'Welsh Assembly Government', pkg.extras['department']
        assert len(pkg.resources) == 1, pkg.resources
        assert '2008 Results' in pkg.resources[0].description, pkg.resources


class TestOnsLoadClashSource(TestLoaderBase):
    # two packages with the same title, and department, but one not from ONS,
    # so must be different packages
    def setup(self):
        self.tsi = TestSearchIndexer()
        super(TestOnsLoadClashSource, self).setup()

        self.clash_name = u'cereals_and_oilseeds_production_harvest'
        CreateTestData.create_arbitrary([
            {'name':self.clash_name,
             'title':'Test clash',
             'extras':{
                 'department':'Department for Environment, Food and Rural Affairs',
                 'import_source':'DECC-Jan-09',
                 },
             }
            ])
        importer_ = importer.OnsImporter(SAMPLE_FILEPATH_1)
        CreateTestData.flag_for_deletion(TEST_PKG_NAMES)
        pkg_dicts = [pkg_dict for pkg_dict in importer_.pkg_dict()]
        loader = OnsLoader(self.testclient)
        self.tsi.index()
        self.res = loader.load_packages(pkg_dicts)
        assert self.res['num_errors'] == 0, self.res

    def test_names(self):
        pkg1 = model.Package.by_name(self.clash_name)
        assert pkg1.title == u'Test clash', pkg1.title

        pkg2 = model.Package.by_name(self.clash_name + u'_')
        assert pkg2.title == u'Cereals and Oilseeds Production Harvest', pkg2.title

class TestOnsLoadSeries(TestLoaderBase):
    def setup(self):
        self.tsi = TestSearchIndexer()
        super(TestOnsLoadSeries, self).setup()
        for filepath in [SAMPLE_FILEPATH_4a, SAMPLE_FILEPATH_4b]:
            importer_ = importer.OnsImporter(filepath)
            pkg_dicts = [pkg_dict for pkg_dict in importer_.pkg_dict()]
            for pkg_dict in pkg_dicts:
                assert pkg_dict['title'] == 'Regional Labour Market Statistics', pkg_dict
                assert pkg_dict['extras']['agency'] == 'Office for National Statistics', pkg_dict
                assert not pkg_dict['extras']['department'], pkg_dict # but key must exist
            loader = OnsLoader(self.testclient)
            self.tsi.index()
            res = loader.load_packages(pkg_dicts)
            assert res['num_errors'] == 0, res
        CreateTestData.flag_for_deletion('regional_labour_market_statistics')

    def test_packages(self):
        pkg = model.Package.by_name(u'regional_labour_market_statistics')
        assert pkg
        assert pkg.title == 'Regional Labour Market Statistics', pkg.title
        assert pkg.extras['agency'] == 'Office for National Statistics', pkg.extras['agency']
        assert len(pkg.resources) == 9, pkg.resources

