import os

from pylons import config
from sqlalchemy.util import OrderedDict
from nose.tools import assert_equal

from ckanext.dgu.ons import importer
from ckan.tests import *


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


class TestOnsImporter:
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
        ons_importer_ = importer.OnsImporter(filepath=SAMPLE_FILEPATH_1)
        package_dict = ons_importer_.record_2_package(record)
    
        expected_package_dict = [
            ('name', u'uk_official_holdings_of_international_reserves'),
            ('title', u'UK Official Holdings of International Reserves'),
            ('version', None),
            ('url', None),
            ('author', u"Her Majesty's Treasury"),
            ('author_email', None),
            ('maintainer', None),
            ('maintainer_email', None),
            ('notes', u"Monthly breakdown for government's net reserves, detailing gross reserves and gross liabilities.\n\nSource agency: HM Treasury\n\nLanguage: English\n\nAlternative title: UK Reserves"),
            ('license_id', u'ukcrown-withrights'),
            ('tags', [u'assets', u'currency', u'economics-and-finance', u'economy', u'gold', u'government-receipts-and-expenditure', u'liabilities', u'public-sector-finance', u'reserves']),
            ('groups', ['ukgov']),
            ('resources', [OrderedDict([
                ('url', u'http://www.hm-treasury.gov.uk/national_statistics.htm'),
                ('description', u'December 2009 | hub/id/119-36345'),
                ])]),
            ('extras', OrderedDict([
                ('geographic_coverage', u'111100: United Kingdom (England, Scotland, Wales, Northern Ireland)'),
                ('geographical_granularity', u'UK and GB'),
                ('external_reference', u'ONSHUB'),
                ('temporal_granularity', u''),
                ('date_updated', u''),
                ('agency', u''),
                ('precision', u''),
                ('temporal_coverage_to', u''),
                ('temporal_coverage_from', u''),
                ('national_statistic', 'no'),
                ('update_frequency', 'monthly'),
                ('department', u"Her Majesty's Treasury"),
                ('import_source', 'ONS-ons_hub_sample.xml'),
                ('date_released', '2010-01-06'),
                ('categories', u'Economy'),
                ])),
            ]
        for key, value in expected_package_dict:
            assert package_dict[key] == value, self.records[0][key].items()
        expected_keys = set([key for key, value in expected_package_dict])
        keys = set(package_dict.keys())
        key_difference = expected_keys - keys
        assert not key_difference, key_difference

