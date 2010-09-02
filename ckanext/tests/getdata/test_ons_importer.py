import os

from pylons import config
from sqlalchemy.util import OrderedDict

from ckanext.getdata import ons_importer
from ckan.tests import *


SAMPLE_PATH = os.path.abspath(os.path.join(config['here'], '..','dgu', 'ckanext', 'tests', 'getdata', 'samples'))
SAMPLE_FILEPATH_1 = os.path.join(SAMPLE_PATH, 'ons_hub_sample.xml')


class TestOnsData1:
    def setup(self):
        records_obj = ons_importer.OnsDataRecords(SAMPLE_FILEPATH_1)
        self.records = [record for record in records_obj.records]
    
    def test_records(self):
        assert len(self.records) == 8
        record1 = self.records[0]
        assert record1.keys() == [u'title', u'link', u'description', u'pubDate', u'guid', u'hub:source-agency', u'hub:theme', u'hub:coverage', u'hub:designation', u'hub:geographic-breakdown', u'hub:language', u'hub:ipsv', u'hub:keywords', u'hub:altTitle', u'hub:nscl'], record1.keys()
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
        ons_importer_ = ons_importer.OnsImporter(filepath=SAMPLE_FILEPATH_1)
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

