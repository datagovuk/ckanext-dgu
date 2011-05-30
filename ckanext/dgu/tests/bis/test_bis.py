import os
import datetime

from sqlalchemy.util import OrderedDict
from pylons import config

from ckan.tests import *
import ckan.model as model
from ckanext.importlib import spreadsheet_importer

from nose.plugins.skip import SkipTest
raise SkipTest('BIS importer deprecated pending use of v3 schema.')

from ckanext.dgu.bis.bis import BisImporter
from ckanext.dgu.tests import PackageDictUtil
from ckan.tests.wsgi_ckanclient import WsgiCkanClient

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLES_DIR = os.path.join(TEST_DIR, 'samples')
BIS_1_FILEBASE = os.path.abspath(os.path.join(config['here'], SAMPLES_DIR, 'bis1'))
XL_EXTENSION = '.xls'

class BasicLogger:
    def __init__(self):
        self._log = []
        
    def log(self, msg):
        self._log.append(msg)

    def get_log(self):
        return self._log

def get_example_data():
    logger = BasicLogger()
    filepath = BIS_1_FILEBASE + XL_EXTENSION
    return spreadsheet_importer.XlData(logger.log, filepath=filepath, sheet_index=0)

def get_resource_data():
    logger = BasicLogger()
    filepath = BIS_1_FILEBASE + XL_EXTENSION
    return spreadsheet_importer.XlData(logger.log, filepath=filepath, sheet_index=1)

class TestSpreadsheetDataRecords:
    @classmethod
    def setup_class(self):
        self.data = get_example_data()
        self.data_records = spreadsheet_importer.SpreadsheetDataRecords(self.data, 'Dataset Ref#')
        self.records = [record for record in self.data_records.records]
        
    def test_0_title_row(self):
        assert self.data_records.titles[0] == self.data.get_row(0)[0], \
               self.data_records.titles

    def test_1_titles(self):
        titles = set(self.data_records.titles)
        expected_titles = set((
            'Dataset Ref#', 'Dataset Status', 'Agency', 'Primary Contact',
            'Secondary Contact', 'Title', 'Abstract', 'Date Released',
            'Date Updated', 'Update Frequency', 'Tags', 'Department',
            'Wiki', 'Identifier', 'Licence', 'Version', 'Geographic Coverage',
            'Geographic Granularity', 'Temporal Granularity', 'Agency',
            'Precision', 'Taxonomy url', 'Temporal Coverage From',
            'Temporal Coverage To', 'National Statistic', 'Categories',
            'Contact information', 'Data File', 'Reference Material',
            'Information', 'Full Description', 'Unknown', 'Total'))
        title_difference = expected_titles - titles
        print self.data_records.titles
        assert not title_difference, title_difference

    def test_2_records(self):
        assert len(self.records) == 2, self.records
        expected_record = [
            (u'Dataset Ref#', u'BIS-000002'),
            (u'Dataset Status', u'Proposed'),
            (u'Agency', u'Higher Education Statistics Agency'),
            (u'Primary Contact', u'information.provision@hesa.ac.uk'),
            (u'Secondary Contact', None),
            (u'Title', u'Higher Education Statistics: All HE students by level of study, mode of study, subject of study, domicile and gender 2007/08'),
            (u'Abstract', u'This dataset provides the 2007/08 higher education statistics for all students by level of study, mode of study, subject of study, domicile and gender'),
            (u'Date Released', 2008),
            (u'Date Updated', 2008),
            (u'Update Frequency', u'Never'),
            (u'Tags', u'hesa higher-education-statistics 2007-2008'),
            (u'Department', u'Department for Business, Innovation & Skills'),
            (u'Wiki', u'-'),
            (u'Identifier', u'higher-education-statistics-all-he-students-by-level-of-study-mode-of-study-subject-of-study-domicile-and-gender-2007-2008'),
            (u'Licence', u'Higher Education Statistcs Agency Copyright with data.gov.uk rights'),
            (u'Version', u'-'),
            (u'Geographic Coverage', u'United Kingdom (England, Scotland, Wales, Northern Ireland)'),
            (u'Geographic Granularity', u'national'),
            (u'Temporal Granularity', u'years'),
            (u'Precision', u'integer to the nearest 5'),
            (u'Taxonomy url', u'-'),
            (u'Temporal Coverage From', datetime.date(2007, 8, 1)),
            (u'Temporal Coverage To', datetime.date(2008, 7, 31)),
            (u'National Statistic', u'no'),
            (u'Categories', u'-'),
            (u'Contact information', u'Higher Education Statistics Agency (HESA)\n+44 (0) 1242 211133\ninformation.provision@hesa.ac.uk'),
            (u'Data File', 1),
            (u'Reference Material', 2),
            (u'Information', 0),
            (u'Full Description', 0),
            (u'Unknown', 0),
            (u'Total', 3)
            ]
        for key, value in expected_record:
            assert self.records[0][key] == value, self.records[0][key].items()
        expected_keys = set([key for key, value in expected_record])
        keys = set(self.records[0].keys())
        key_difference = expected_keys - keys
        assert not key_difference, key_difference

class TestResourceRecords:
    @classmethod
    def setup_class(self):
        self.data = get_resource_data()
        self.data_records = spreadsheet_importer.SpreadsheetDataRecords(self.data, 'Resource Status')
        self.records = [record for record in self.data_records.records]
        
    def test_0_title_row(self):
        assert self.data_records.titles[0] == self.data.get_row(0)[0], \
               self.data_records.titles

    def test_1_titles(self):
        titles = set(self.data_records.titles)
        expected_titles = set((
            'Dataset Ref#', 'Resource Status', 'Resourse Type',
            'Resource Format', 'Resource Title', 'Resource url', 'Comments',
            'Updated', 'Licence', 'Size'
            ))
        title_difference = expected_titles - titles
        print self.data_records.titles
        assert not title_difference, title_difference

    def test_2_records(self):
        assert len(self.records) == 9, self.records
        print self.records[0].items()
        expected_record = [
            (u'Dataset Ref#', u'BIS-000001'),
            (u'Resource Status', u'Proposed'),
            (u'Resourse Type', u'Data File'),
            (u'Resource Format', u'XLS'),
            (u'Resource Title', u'Data File - XLS Format'),
            (u'Resource url', u'http://www.hesa.ac.uk/dox/dataTables/studentsAndQualifiers/download/subject0809.xls?v=1.0'),
            (u'Comments', None),
            (u'Updated', None),
            (u'Licence', None),
            (u'Size', None),
            ]
        for key, value in expected_record:
            assert self.records[0][key] == value, self.records[0][key]
        expected_keys = set([key for key, value in expected_record])
        keys = set(self.records[0].keys())
        key_difference = expected_keys - keys
        assert not key_difference, key_difference


class TestImport:
    @classmethod
    def setup_class(self):
        self._filepath = BIS_1_FILEBASE + XL_EXTENSION
        self.importer = BisImporter(filepath=self._filepath)
        self.pkg_dicts = [pkg_dict for pkg_dict in self.importer.pkg_dict()]

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()
        
    def test_0_munge(self):
        def test_munge(name, expected_munge):
            munge = self.importer.name_munge(name)
            assert munge == expected_munge, 'Got %s not %s' % (munge, expected_munge)
        test_munge('hesa-first-year-uk-domiciled-he-students-by-qualification-aim-mode-of-study-gender-and-disability-1994-1995', 'hesa-first-year-uk-domiciled-he-students-disability-1994-1995')


    def test_1_row_2_package(self):
        row_dict = OrderedDict([
            (u'Dataset Ref#', u'BIS-000002'),
            (u'Dataset Status', u'Proposed'),
            (u'Agency', u'Higher Education Statistics Agency'),
            (u'Primary Contact', u'information.provision@hesa.ac.uk'),
            (u'Secondary Contact', None),
            (u'Title', u'Higher Education Statistics: All HE students by level of study, mode of study, subject of study, domicile and gender 2007/08'),
            (u'Abstract', u'This dataset provides the 2007/08 higher education statistics for all students by level of study, mode of study, subject of study, domicile and gender'),
            (u'Date Released', 2008),
            (u'Date Updated', 2008),
            (u'Update Frequency', u'Never'),
            (u'Tags', u'hesa higher-education-statistics 2007-2008'),
            (u'Department', u'Department for Business, Innovation & Skills'),
            (u'Wiki', u'-'),
            (u'Identifier', u'higher-education-statistics-all-he-students-by-level-of-study-mode-of-study-subject-of-study-meeeeeeeeeeeeeeeeeeeeeeeeeeeega-long-name-2007-2008'),
            (u'Licence', u'Higher Education Statistcs Agency Copyright with data.gov.uk rights'),
            (u'Version', u'-'),
            (u'Geographic Coverage', u'United Kingdom (England, Scotland, Wales, Northern Ireland)'),
            (u'Geographic Granularity', u'national'),
            (u'Temporal Granularity', u'years'),
            (u'Precision', u'integer to the nearest 5'),
            (u'Taxonomy url', u'-'),
            (u'Temporal Coverage From', datetime.date(2007, 8, 1)),
            (u'Temporal Coverage To', datetime.date(2008, 7, 31)),
            (u'National Statistic', u'no'),
            (u'Categories', u'-'),
            (u'Contact information', u'Higher Education Statistics Agency (HESA)\n+44 (0) 1242 211133\ninformation.provision@hesa.ac.uk'),
            (u'Data File', 1),
            (u'Reference Material', 2),
            (u'Information', 0),
            (u'Full Description', 0),
            (u'Unknown', 0),
            (u'Total', 3)
            ])
        expected_pkg_dict = OrderedDict([
            ('name', u'hesa-all-he-students-by-level-of-study-mode-of-study-subject-of-study-meeeeeeeeeeeeee-2007-2008'),
            ('title', u'Higher Education Statistics: All HE students by level of study, mode of study, subject of study, domicile and gender 2007/08'),
            ('version', u'-'),
            ('url', None),
            ('author', u'Higher Education Statistics Agency (HESA)'),
            ('author_email', u'information.provision@hesa.ac.uk'),
            ('maintainer', u''),
            ('maintainer_email', u''),
            ('notes', u'This dataset provides the 2007/08 higher education statistics for all students by level of study, mode of study, subject of study, domicile and gender'),
            ('license_id', u'hesa-withrights'),
            ('tags', [u'2007-2008', u'education', u'hesa', \
                      u'higher-education', u'higher-education-statistics']),
            ('groups', ['ukgov']),
            ('resources', [OrderedDict([
                ('url', 'http://www.hesa.ac.uk/dox/dataTables/studentsAndQualifiers/download/subject0708.xls?v=1.0'),
                ('format', 'XLS'),
                ('description', 'Data File - XLS Format'),
                ]),
                           OrderedDict([
                               ('url', 'http://www.hesa.ac.uk/index.php/component/option,com_datatables/task,show_file/defs,1/Itemid,121/catdex,3/disp,/dld,subject0708.xls/yrStr,2007+to+2008/dfile,studefs0708.htm/area,subject/mx,0/'),
                               ('format', 'HTML'),
                               ('description', 'Reference Material - Data File Definition'),
                               ]),
                           OrderedDict([
                               ('url', 'http://www.hesa.ac.uk/index.php/component/option,com_datatables/task,show_file/defs,2/Itemid,121/catdex,3/disp,/dld,subject0708.xls/yrStr,2007+to+2008/dfile,notes0708.htm/area,subject/mx,0/'),
                               ('format', 'HTML'),
                               ('description', 'Reference Material - Notes Regarding Data File Content'),
                               ]),
                           ]),
            ('extras', OrderedDict([
                ('external_reference', 'BIS-000002'),
                ('date_released', '2008'),
                ('date_updated', '2008'),
                ('temporal_granularity', 'years'),
                ('temporal_coverage_to', '2008-07-31'),
                ('temporal_coverage_from', '2007-08-01'),
                ('geographic_coverage', '111100: United Kingdom (England, Scotland, Wales, Northern Ireland)'),
                ('geographical_granularity', 'national'),
                ('agency', u'Higher Education Statistics Agency'),
                ('precision', 'integer to the nearest 5'),
                ('taxonomy_url', '-'),
                ('import_source', 'BIS-%s' % os.path.basename(self._filepath)),
                ('department', u'Department for Business, Innovation and Skills'),
                ('update_frequency', 'Never'),
                ('national_statistic', 'no'),
                ('categories', '-'),
                ])
             ),
            ])
        pkg_dict = self.importer.row_2_package(row_dict)

        log = self.importer.get_log()
        assert not log, log

        PackageDictUtil.check_dict(pkg_dict, expected_pkg_dict)
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
