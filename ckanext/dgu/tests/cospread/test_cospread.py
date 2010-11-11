import os
import datetime

from sqlalchemy.util import OrderedDict
from pylons import config
from nose.tools import assert_equal

from ckan.tests import *
import ckan.model as model
from ckan.lib import spreadsheet_importer
from ckanext.dgu.cospread.cospread import CospreadDataRecords, CospreadImporter
from ckan.tests.wsgi_ckanclient import WsgiCkanClient

SAMPLES_DIR = '../dgu/ckanext/dgu/tests/cospread/samples'
CKAN_SRC_DIR = config['here']
COSPREAD_FILEBASE = os.path.abspath(os.path.join(CKAN_SRC_DIR, SAMPLES_DIR, 'cospread'))
CSV_EXTENSION = '.csv'
XL_EXTENSION = '.xls'

class BasicLogger:
    def __init__(self):
        self._log = []
        
    def log(self, msg):
        self._log.append(msg)

    def get_log(self):
        return self._log

def get_example_filepath(index=1):
    return '%s%i%s' % (COSPREAD_FILEBASE, index, CSV_EXTENSION)

def get_example_data(index=1):
    logger = BasicLogger()
    filepath = get_example_filepath(index)
    return spreadsheet_importer.CsvData(logger.log, filepath=filepath)

class TestCospreadDataRecords:
    @classmethod
    def setup_class(self):
        self.data = get_example_data()
        self.data_records = CospreadDataRecords(self.data)
        self.records = [record for record in self.data_records.records]
        
    def test_0_title_row(self):
        assert self.data_records.titles[0] == u'Package name', \
               self.data_records.titles

    def test_1_titles(self):
        titles = set(self.data_records.titles)
        expected_titles = set((
            "Package name",
            "Title",
            "CO Identifier",
            "Notes",
            "Date released",
            "Date updated",
            "Update frequency",
            "Geographical Granularity - Standard", "Geographical Granularity - Other",
            "Geographic coverage - England","Geographic coverage - N. Ireland","Geographic coverage - Scotland", "Geographic coverage - Wales","Geographic coverage - Overseas","Geographic coverage - Global",
            "Temporal Granularity - Standard","Temporal Granularity - Other",
            "File format",
            "Categories",
            "National Statistic",
            "Precision",
            "URL",
            "Download URL",
            "Taxonomy URL",
            "Department",
            "Agency responsible",
            "Contact - Permanent contact point","Contact - E-mail address.",
            "Maintainer - ", "Maintainer - E-mail address",
            "Licence", "Tags"
            ))
        title_difference = expected_titles ^ titles
        assert not title_difference, title_difference

    def test_2_records(self):
        assert len(self.records) == 3, self.records
        expected_record = [
            ('Package name', 'child-protection-plan-england-2009'),
            ('Title', 'Child Protection Plan'),
            ('CO Identifier', 'DCSF-DCSF-0017'),
            ('Notes', 'Referrals, assessment and children and young people who are the subjects of child protection plans (on the child protection register) for year ending March 2009'),
            ('Date released', '17/09/2009'),
            ('Date updated', '17/09/09'),
            ('Update frequency', 'Annually'),
            ('Geographical Granularity', 'Local Authority'),
            ('Geographic coverage - England', 'Yes'),
            ('Geographic coverage - N. Ireland', 'No'),
            ('Geographic coverage - Scotland', 'No'),
            ('Geographic coverage - Wales', 'No'),
            ('Geographic coverage - Overseas', 'No'),
            ('Geographic coverage - Global', 'No'),
            ('Temporal Granularity', 'Years'),
            ('resources', [{'File format': 'XLS',
                            'Download URL': 'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000873/FINALAdditionalTables1to13.xls\n\nhttp://www.dcsf.gov.uk/rsgateway/DB/SFR/s000873/NationalIndicatorTables.xls'}]),
            ('Categories', 'Health, well-being and Care'),
            ('National Statistic', 'Yes'),
            ('Precision', 'Numbers rounded to nearest 100 if over 1,000, and to the nearest 10 otherwise.  Percentage to nearest whole number.'),
            ('URL', 'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000873/index.shtml'),
            ('Taxonomy URL', ''),
            ('Department', 'Department for Children, Schools and Families'),
            ('Agency responsible', ''),
            ('Contact - Permanent contact point', 'DCSF Data Services Group'),
            ('Contact - E-mail address.', 'statistics@dcsf.gsi.gov.uk'),
            ('Maintainer - ', ''),
            ('Maintainer - E-mail address', ''),
            ('Licence', 'UK Crown Copyright'),
            ('Tags', 'dcsf england child-protection-plan-statistics referrals assessments child-protection-register'),
            ]
        for key, value in expected_record:
            assert self.records[0].has_key(key), 'Expected key %r in record: %r' % (key, self.records[0].keys())
            assert_equal(self.records[0][key], value)
        expected_keys = set([key for key, value in expected_record])
        keys = set(self.records[0].keys())
        key_difference = expected_keys - keys
        assert not key_difference, key_difference


class TestImport:
    @classmethod
    def setup_class(self):
        self._filepath = get_example_filepath()
        self.importer = CospreadImporter(include_given_tags=True, filepath=self._filepath)
        self.pkg_dicts = [pkg_dict for pkg_dict in self.importer.pkg_dict()]

    def test_0_name_munge(self):
        def test_name_munge(name, expected_munge):
            munge = self.importer.name_munge(name)
            assert munge == expected_munge, 'Got %s not %s' % (munge, expected_munge)
        test_name_munge('hesa-(1994-1995)', 'hesa-1994-1995')

    def test_1_record_2_package(self):
        row_record = OrderedDict([
            ('Package name', 'child-protection-plan-england-2009'),
            ('Title', 'Child Protection Plan'),
            ('CO Identifier', 'DCSF-DCSF-0017'),
            ('Notes', 'Referrals, assessment and children and young people who are the subjects of child protection plans (on the child protection register) for year ending March 2009'),
            ('Date released', '17/09/2009'),
            ('Date updated', '17/09/09'),
            ('Update frequency', 'Annually'),
            ('Geographical Granularity', 'Local Authority'),
            ('Geographic coverage - England', 'Yes'),
            ('Geographic coverage - N. Ireland', 'No'),
            ('Geographic coverage - Scotland', 'No'),
            ('Geographic coverage - Wales', 'No'),
            ('Geographic coverage - Overseas', 'No'),
            ('Geographic coverage - Global', 'No'),
            ('Temporal Granularity', 'Years'),
            ('resources', [{'File format': 'XLS',
                            'Download URL': 'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000873/FINALAdditionalTables1to13.xls\n\nhttp://www.dcsf.gov.uk/rsgateway/DB/SFR/s000873/NationalIndicatorTables.xls'}]),
            ('Categories', 'Health, well-being and Care'),
            ('National Statistic', 'Yes'),
            ('Precision', 'Numbers rounded to nearest 100 if over 1,000, and to the nearest 10 otherwise.  Percentage to nearest whole number.'),
            ('URL', 'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000873/index.shtml'),
            ('Taxonomy URL', ''),
            ('Department', 'Department for Children, Schools and Families'),
            ('Agency responsible', ''),
            ('Contact - Permanent contact point', 'DCSF Data Services Group'),
            ('Contact - E-mail address.', 'statistics@dcsf.gsi.gov.uk'),
            ('Maintainer - ', ''),
            ('Maintainer - E-mail address', ''),
            ('Licence', 'UK Crown Copyright'),
            ('Tags', 'dcsf england child-protection-plan-statistics referrals assessments child-protection-register'),
            ])

        expected_pkg_dict = OrderedDict([
            ('name', u'child-protection-plan-england-2009'),
            ('title', u'Child Protection Plan'),
            ('version', None),
            ('url', u'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000873/index.shtml'),
            ('author', u'DCSF Data Services Group'),
            ('author_email', u'statistics@dcsf.gsi.gov.uk'),
            ('maintainer', u''),
            ('maintainer_email', u''),
            ('notes', u'Referrals, assessment and children and young people who are the subjects of child protection plans (on the child protection register) for year ending March 2009'),
            ('license_id', u'uk-ogl'),
            ('tags', ['assessments', 'child', 'child-protection', 'child-protection-plan-statistics', 'child-protection-register', 'children', 'dcsf', 'england', 'referrals']), 
            ('groups', ['ukgov']),
            ('resources', [OrderedDict([
                ('url', 'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000873/FINALAdditionalTables1to13.xls'),
                ('format', 'XLS'),
                ('description', ''),
                ]),
                           OrderedDict([
                ('url', 'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000873/NationalIndicatorTables.xls'),
                ('format', 'XLS'),
                ('description', ''),
                               ]),
                           ]),
            ('extras', OrderedDict([
                ('external_reference', 'DCSF-DCSF-0017'),
                ('date_released', '2009-09-17'),
                ('date_updated', '2009-09-17'),
                ('temporal_granularity', 'years'),
                ('temporal_coverage_to', ''),
                ('temporal_coverage_from', ''),
                ('geographic_coverage', '100000: England'),
                ('geographical_granularity', 'local authority'),
                ('agency', u''),
                ('precision', 'Numbers rounded to nearest 100 if over 1,000, and to the nearest 10 otherwise.  Percentage to nearest whole number.'),
                ('taxonomy_url', ''),
                ('import_source', 'COSPREAD-%s' % os.path.basename(self._filepath)),
                ('department', u'Department for Children, Schools and Families'),
                ('update_frequency', 'Annually'),
                ('national_statistic', ''),
                ('categories', 'Health, well-being and Care'),
                ])
             ),
            ])
        pkg_dict = self.importer.record_2_package(row_record)

        log = self.importer.get_log()
        assert not log, log

        self.check_dict(pkg_dict, expected_pkg_dict)
        expected_keys = set([key for key, value in expected_pkg_dict.items()])
        keys = set(pkg_dict.keys())
        key_difference = expected_keys - keys
        assert not key_difference, key_difference

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
