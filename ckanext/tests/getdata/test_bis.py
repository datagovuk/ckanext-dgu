import os
import datetime

from sqlalchemy.util import OrderedDict
from pylons import config

from ckan.tests import *
import ckan.model as model
from ckan.lib import importer
from ckanext.getdata.bis import BisImporter

SAMPLES_DIR = '../dgu/ckanext/tests/getdata/samples'
BIS_1_FILEBASE = os.path.abspath(os.path.join(config['here'], SAMPLES_DIR, 'bis1'))
XL_EXTENSION = '.xls'

class BasicLogger:
    def __init__(self):
        self._log = []
        
    def log(self, msg):
        self._log.append(msg)

def get_example_data():
    logger = BasicLogger()
    filepath = BIS_1_FILEBASE + XL_EXTENSION
    return importer.XlData(logger.log, filepath=filepath, sheet_index=0)

def get_resource_data():
    logger = BasicLogger()
    filepath = BIS_1_FILEBASE + XL_EXTENSION
    return importer.XlData(logger.log, filepath=filepath, sheet_index=1)

class TestDataRecords:
    @classmethod
    def setup_class(self):
        self.data = get_example_data()
        self.data_records = importer.DataRecords(self.data, 'Dataset Ref#')
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
        self.data_records = importer.DataRecords(self.data, 'Resource Status')
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

    def test_0_row_2_package(self):
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
            ])
        expected_pkg_dict = OrderedDict([
            ('name', u'hesa-all-he-students-by-level-of-study-mode-of-study-subject-of-study-domicile-and-gender-2007-2008'),
            ('title', u'Higher Education Statistics: All HE students by level of study, mode of study, subject of study, domicile and gender 2007/08'),
            ('version', u'-'),
            ('url', None),
            ('author', u'Higher Education Statistics Agency (HESA)'),
            ('author_email', u'information.provision@hesa.ac.uk'),
            ('maintainer', u''),
            ('maintainer_email', u''),
            ('notes', u'This dataset provides the 2007/08 higher education statistics for all students by level of study, mode of study, subject of study, domicile and gender'),
            ('license_id', u'hesa-withrights'),
            ('tags', set([u'higher-education', u'education'])),
            ('groups', []),
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
                ('geographic_granularity', 'national'),
                ('agency', u'Higher Education Statistics Agency'),
                ('precision', 'integer to the nearest 5'),
                ('taxonomy_url', '-'),
                ('import_source', 'BIS-%s' % os.path.basename(self._filepath)),
                ('department', u'Department for Business, Innovation & Skills'),
                ('update_frequency', 'Never'),
                ('national_statistic', 'no'),
                ('categories', '-'),
                ])
             ),
            ])
        pkg_dict = self.importer.row_2_package(row_dict)

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

class TestImporter(TestController):

    @classmethod
    def setup_class(self):
        model.repo.rebuild_db()
        CreateTestData.create()
        assert model.User.by_name(unicode(DEFAULT_USER))

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_0_index(self):
        offset = url_for(controller='importer')
        res = self.app.get(offset)
        assert 'Importer' in res, res

    def test_1_not_logged_in(self):
        res = self._submit_file(EXAMPLE_TESTFILE_FILEPATH + XL_EXTENSION, username=None, status=302)

    def test_1_not_logged_in_midway(self):
        res = self._submit_file(EXAMPLE_TESTFILE_FILEPATH + XL_EXTENSION, status=200)
        assert 'Import Preview' in res, res_
        res = self._import(res, 'test', username=None, status=302)
        pkg = model.Package.by_name(u'wikipedia')
        assert not pkg

    def test_2_import_example_testfile(self):
        res = self._submit_file(EXAMPLE_TESTFILE_FILEPATH + XL_EXTENSION, status=200)
        assert 'Import Preview' in res, res_
        assert '2 packages read' in res, res_
        assert 'wikipedia' in res_, res_
        assert 'tviv' in res_, res_
        res = self._import(res, 'test', status=200)
        assert 'Imported 2 packages' in res, self.main_div(res)

    # TODO get working: overwriting existing package
    def _test_3_import_full_testfile(self):
        res = self._submit_file(FULL_TESTFILE_FILEPATH + XL_EXTENSION, status=200)
        assert 'Import Preview' in res, res_
        assert '2 packages read' in res, res_
        assert 'name: annakarenina' in res_, res_
        assert 'name: warandpeace' in res_, res_
        res = self._import(res, 'test', status=200)
        assert 'Imported 2 packages' in res, self.main_div(res)

##    def _submit_file(self, filepath, username=DEFAULT_USER, status=None):
##        assert os.path.exists(filepath)
        
##        return res
        
##    def _import(self, res, log_message, username=DEFAULT_USER, status=None):
##        form = res.forms['import']
##        form['log_message'] = log_message
##        extra_environ = {'REMOTE_USER':username} if username else {}
##        res = form.submit('import', extra_environ=extra_environ,
##                          status=status)
##        if not status or status == 200:
##            assert 'Import Result' in res, self.main_div(res)
##        return res

