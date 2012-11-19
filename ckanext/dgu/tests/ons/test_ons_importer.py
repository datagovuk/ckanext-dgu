import os

from pylons import config
from sqlalchemy.util import OrderedDict
from nose.tools import assert_equal

from ckan.tests import *
from ckanext.dgu.ons import importer
from ckanext.dgu.ons.producers import get_ons_producers
from ckanext.dgu.schema import DrupalHelper
from ckanext.dgu.tests import MockDrupalCase, strip_organisation_id, PackageDictUtil

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_PATH = os.path.join(TEST_DIR, 'samples')
SAMPLE_FILEPATH_1 = os.path.join(SAMPLE_PATH, 'ons_hub_sample.xml')


class TestOnsData1:
    def setup(self):
        records_obj = importer.OnsDataRecords(SAMPLE_FILEPATH_1)
        self.records = [record for record in records_obj]
 
    def test_records(self):
        assert len(self.records) == 8
        record1 = self.records[0]
        r1_keys = record1.keys()
        r1_expected_keys = [u'title', u'link', u'description', u'pubDate', u'guid', u'hub:source-agency', u'hub:theme', u'hub:coverage', u'hub:designation', u'hub:geographic-breakdown', u'hub:language', u'hub:ipsv', u'hub:keywords', u'hub:altTitle', u'hub:nscl']
        r1_keys.sort(), r1_expected_keys.sort()
        assert r1_keys == r1_expected_keys

        expected_items = [
            (u'title', u'UK Official Holdings of International Reserves - December 2009'),
            (u'link', u'http://www.hm-treasury.gov.uk/national_statistics.htm'),
            (u'description', u"Monthly breakdown for government's net reserves, detailing gross reserves and gross liabilities."),
            (u'pubDate', u'Wed, 06 Jan 2010 09:30:00 GMT'),
            (u'guid', u'http://www.statistics.gov.uk/hub/id/119-36345'),
            (u'hub:source-agency', u'HM Treasury'),
            (u'hub:theme', u'Economy'),
            (u'hub:coverage', u'UK'),
            (u'hub:designation', u''),
            (u'hub:geographic-breakdown', u'UK and GB'),
            (u'hub:language', u'English'),
            (u'hub:ipsv', u'Economics and finance'),
            (u'hub:keywords', u'reserves;currency;assets;liabilities;gold;reserves;currency;assets;liabilities;gold'),
            (u'hub:altTitle', u'UK Reserves'),
            (u'hub:nscl', u'Economy;Government Receipts and Expenditure;Public Sector Finance;Economy;Government Receipts and Expenditure;Public Sector Finance')]
        for key, value in expected_items:
            assert record1[key] == value, 'Key %s: got %r but should be %r' % (key, record1[key], value)
        expected_keys = set([key for key, value in expected_items])
        keys = set(record1.keys())
        key_difference = expected_keys - keys
        assert not key_difference, key_difference


class TestOnsImporter(MockDrupalCase):
    lots_of_publishers = True
    
    def test_split_title(self):
        expected_data = [
            (u'UK Official Holdings of International Reserves - December 2009',
             u'UK Official Holdings of International Reserves', u'December 2009'),
            (u'Probation statistics brief - July - September 2009',
             u'Probation statistics brief', u'July - September 2009'),
            (u'National Park, Parliamentary Constituency and Ward level mid-year population estimates (experimental) - Mid-2008',
             u'National Park, Parliamentary Constituency and Ward level mid-year population estimates (experimental)', u'Mid-2008'),
            ]
        for xml_title, title, date in expected_data:
            res_title, res_date = importer.OnsImporter._split_title(xml_title)
            assert_equal(title, res_title)
            assert_equal(date, res_date)

    def test_geo_coverage(self):
        coverage_tests = [
            ('UK', '111100: United Kingdom (England, Scotland, Wales, Northern Ireland)'),
            ('GB', '111000: Great Britain (England, Scotland, Wales)'),
            ('England and Wales', '101000: England, Wales'),
            ('England', '100000: England'),
            ('Wales', '001000: Wales'),
            ('Scotland', '010000: Scotland'),
            ('Northern Ireland', '000100: Northern Ireland'),
            ('International', '000001: Global'),
            ]
        for coverage_str, expected_coverage_db in coverage_tests:
            coverage_db = importer.OnsImporter._parse_geographic_coverage(coverage_str)
            assert_equal(coverage_db, expected_coverage_db)

    def test_publishers(self):
        expected_results = [
            # (hub:source-agency value, published_by, published_via)
            ('HM Treasury', 'Her Majesty\'s Treasury [some_number]', ''),
            ('Information Centre for Health and Social Care', 'NHS Information Centre for Health and Social Care [some_number]', ''),
            ('Environment (Northern Ireland)', 'Northern Ireland Executive [some_number]', 'Department of the Environment [some_number]'),
            ('Office for National Statistics', 'Office for National Statistics [some_number]', ''),
            ]
        for source_agency, expected_published_by, expected_published_via in expected_results:
            department, agency, published_by, published_via = importer.OnsImporter._source_to_organisations(source_agency)
            assert published_by is not None, source_agency
            assert published_via is not None, source_agency
            published_by = strip_organisation_id(published_by)
            published_via = strip_organisation_id(published_via)
            assert_equal(published_by, expected_published_by or u'')
            assert_equal(published_via, expected_published_via or u'')

    def test_dept_to_organisation(self):
        for source_agency in get_ons_producers():
            publisher = DrupalHelper.department_or_agency_to_organisation(source_agency)
            assert publisher, source_agency
            publisher = strip_organisation_id(publisher)
            assert '[some_number]' in publisher, publisher

    def test_record_2_package(self):
        record = OrderedDict([
            (u'title', u'UK Official Holdings of International Reserves - December 2009'),
            (u'link', u'http://www.hm-treasury.gov.uk/national_statistics.htm'),
            (u'description', u"Monthly breakdown for government's net reserves, detailing gross reserves and gross liabilities."),
            (u'pubDate', u'Wed, 06 Jan 2010 09:30:00 GMT'),
            (u'guid', u'http://www.statistics.gov.uk/hub/id/119-36345'),
            (u'hub:source-agency', u'HM Treasury'),
            (u'hub:theme', u'Economy'),
            (u'hub:coverage', u'UK'),
            (u'hub:designation', u''),
            (u'hub:geographic-breakdown', u'UK and GB'),
            (u'hub:language', u'English'),
            (u'hub:ipsv', u'Economics and finance'),
            (u'hub:keywords', u'reserves;currency;assets;liabilities;gold;reserves;currency;assets;liabilities;gold'),
            (u'hub:altTitle', u'UK Reserves'),
            (u'hub:nscl', u'Economy;Government Receipts and Expenditure;Public Sector Finance;Economy;Government Receipts and Expenditure;Public Sector Finance')])
        ons_importer_ = importer.OnsImporter(filepaths=SAMPLE_FILEPATH_1)
        package_dict = ons_importer_.record_2_package(record)
    
        expected_package_dict = OrderedDict([
            ('name', u'uk_official_holdings_of_international_reserves'),
            ('title', u'UK Official Holdings of International Reserves'),
            ('version', None),
            ('url', None),
            ('author', u"Her Majesty's Treasury"),
            ('author_email', None),
            ('maintainer', None),
            ('maintainer_email', None),
            ('notes', u"Monthly breakdown for government's net reserves, detailing gross reserves and gross liabilities.\n\nSource agency: HM Treasury\n\nLanguage: English\n\nAlternative title: UK Reserves"),
            ('license_id', u'uk-ogl'),
            ('tags', [u'assets', u'currency', u'economics-and-finance', u'economy', u'gold', u'government-receipts-and-expenditure', u'liabilities', u'public-sector-finance', u'reserves']),
            ('groups', []),
            ('resources', [OrderedDict([
                ('url', u'http://www.hm-treasury.gov.uk/national_statistics.htm'),
                ('description', u'December 2009'),
                ('hub-id', u'119-36345'),
                ])]),
            ('extras', OrderedDict([
                ('geographic_coverage', u'111100: United Kingdom (England, Scotland, Wales, Northern Ireland)'),
                ('geographic_granularity', u'UK and GB'),
                ('external_reference', u'ONSHUB'),
                ('temporal_granularity', u''),
                ('date_updated', u''),
                ('precision', u''),
                ('temporal_coverage-to', u''),
                ('temporal_coverage-from', u''),
                ('national_statistic', 'no'),
                ('update_frequency', 'monthly'),
                ('import_source', 'ONS-ons_hub_sample.xml'),
                ('date_released', '2010-01-06'),
                ('categories', u'Economy'),
                ('series', u'UK Official Holdings of International Reserves'),
                ('published_by', u"Her Majesty's Treasury [some_number]"),
                ('published_via', u''),
                ])),
            ])
        for extra_key in ('published_by', 'published_via'):
            package_dict['extras'][extra_key] = strip_organisation_id(package_dict['extras'][extra_key])
        PackageDictUtil.check_dict(package_dict, expected_package_dict)
