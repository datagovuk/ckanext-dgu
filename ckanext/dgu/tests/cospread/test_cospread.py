import os
import datetime

from sqlalchemy.util import OrderedDict
from pylons import config
from nose.tools import assert_equal

from ckan.tests import *
import ckan.model as model
from ckan.lib import spreadsheet_importer
from ckan.tests.wsgi_ckanclient import WsgiCkanClient
from ckan.tests.lib.test_spreadsheet_importer import CKAN_SRC_DIR, CSV_EXTENSION, XL_EXTENSION, SPREADSHEET_DATA_MAP, ExampleFiles
from ckanext.dgu.tests import PackageDictUtil
from ckanext.dgu.cospread.cospread import MultipleCospreadDataRecords, CospreadImporter

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
EXAMPLES_DIR = os.path.join(TEST_DIR, 'samples')
EXAMPLE_FILEBASE = 'cospread'

examples = ExampleFiles(EXAMPLES_DIR, EXAMPLE_FILEBASE)

# column titles for older pro forma; used in example 1
expected_titles_1 = set((
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
# titles for more recent cospread pro forma; used for clg example
expected_titles_2 = set((
    "Package name",
    "Title",
    "CO Reference",
    "Notes",
    "Date released",
    "Date updated",
    "Update frequency",
    "Geographical Granularity - Standard", "Geographical Granularity - Other",
    "Geographic coverage - England","Geographic coverage - N. Ireland","Geographic coverage - Scotland", "Geographic coverage - Wales","Geographic coverage - Overseas","Geographic coverage - Global",
    "Temporal Granularity - Standard","Temporal Granularity - Other",
    "Temporal Coverage - To\n(if needed)", "Temporal Coverage - From",
    "Download file format",
    "Download Description",
    "Precision",
    "URL",
    "Download URL",
    "Taxonomy URL",
    "Department",
    "Agency responsible",
    "Author - Permanent contact point for members of the public; not an individual.", "Author - E-mail address.",
    "Maintainer - Blank unless not the author.", "Maintainer - E-mail address, if needed.",
    "Licence", "Tags"
    ))
    
example_record = OrderedDict([
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
    ('Department', 'Department for Education'),
    ('Agency responsible', ''),
    ('Contact - Permanent contact point', 'DCSF Data Services Group'),
    ('Contact - E-mail address.', 'statistics@dcsf.gsi.gov.uk'),
    ('Maintainer - ', ''),
    ('Maintainer - E-mail address', ''),
    ('Licence', 'UK Crown Copyright'),
    ('Tags', 'dcsf england child-protection-plan-statistics referrals assessments child-protection-register'),
    ])
example_pkg_dict = OrderedDict([
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
    ('tags', ['child', 'child-protection', 'children']), 
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
        ('import_source', 'COSPREAD-cospread1.csv'),
        ('department', u'Department for Education'),
        ('update_frequency', 'Annually'),
        ('national_statistic', ''),
        ('categories', 'Health, well-being and Care'),
        ])
     ),
    ])

clg_record = OrderedDict([
    ('Package name', 'Total-number-of-dwellings-owned-by-your-local-authority'),
    ('Title', 'Total number of dwellings owned by your local authority'),
    ('CO Identifier', ''),
    ('Notes', 'The purpose % Non-Decent Homes.\n\nThe links below provide access to the Local Data Exchange (LDEx) API which can be used to discover data about this indicator.'),
    ('Date released', datetime.date(2002, 4, 1)),
    ('Date updated', ''),
    ('Update frequency', ''),
    ('Geographical Granularity', 'Local Authority (District)'),
    ('Geographic coverage - England', 'England'),
    ('Geographic coverage - N. Ireland', ''),
    ('Geographic coverage - Scotland', ''),
    ('Geographic coverage - Wales', ''),
    ('Geographic coverage - Overseas', ''),
    ('Geographic coverage - Global', ''),
    ('Temporal Granularity', ''),
    ('Temporal Coverage - From', '2002/03'),
    ('Temporal Coverage - To\n(if needed)', '2008/09'),
    ('resources', [{'File format': 'RDF',
                    'Download URL': 'http://ldexincubator.communities.gov.uk/service/ldex/housingandplanning/api/housingandplanning-indicator/A_TOAlDW/doc.rdf',
                    'Download Description': 'RDF Description',
                    },
                   {'File format': 'RDF',
                    'Download URL': 'http://doc2.rdf',
                    'Download Description': 'File 2',
                    }]),
    ('Precision', ''),
    ('URL', 'http://ldexincubator.communities.gov.uk/service/ldex/housingandplanning/doc/housingandplanning-indicator/A_TOAlDW/doc.html'),
    ('Taxonomy URL', ''),
    ('Department', 'Department for Communities and Local Government'),
    ('Agency responsible', ''),
    ('Contact - Permanent contact point', ''),
    ('Contact - E-mail address.', 'open_data@yahoo.com'),
    ('Maintainer - ', ''),
    ('Maintainer - E-mail address', ''),
    ('Licence', 'UK Crown Copyright with data.gov.uk rights'),
    ('Tags', 'Housing-and-Planning-View-Indicator-Places LDEx LDEX Local-Data-Exchange Department-for-Communities-and-Local-Government Communities Local-Government Housing-and-Planning-Indicator housing planning'),
    ])

clg_pkg_dict = OrderedDict([
    ('name', u'total-number-of-dwellings-owned-by-your-local-authority'),
    ('title', u'Total number of dwellings owned by your local authority'),
    ('version', None),
    ('url', u'http://ldexincubator.communities.gov.uk/service/ldex/housingandplanning/doc/housingandplanning-indicator/A_TOAlDW/doc.html'),
    ('author', u''),
    ('author_email', u'open_data@yahoo.com'),
    ('maintainer', u''),
    ('maintainer_email', u''),
    ('notes', u'The purpose % Non-Decent Homes.\n\nThe links below provide access to the Local Data Exchange (LDEx) API which can be used to discover data about this indicator.'),
    ('license_id', u'uk-ogl'),
    ('tags', ['communities', 'department-for-communities-and-local-government', 'housing', 'housing-and-planning-indicator', 'housing-and-planning-view-indicator-places', 'ldex', 'local-authority', 'local-data-exchange', 'local-government', 'planning']),
    ('groups', ['ukgov']),
    ('resources', [OrderedDict([
        ('url', 'http://ldexincubator.communities.gov.uk/service/ldex/housingandplanning/api/housingandplanning-indicator/A_TOAlDW/doc.rdf'),
        ('format', 'RDF'),
        ('description', 'RDF Description'),
        ]),
                   OrderedDict([
        ('url', 'http://doc2.rdf'),
        ('format', 'RDF'),
        ('description', 'File 2')
                       ]),
                   ]),
    ('extras', OrderedDict([
        ('external_reference', ''),
        ('date_released', '2002-04-01'),
        ('date_updated', ''),
        ('temporal_granularity', ''),
        ('temporal_coverage_to', '2009'),
        ('temporal_coverage_from', '2002'),
        ('geographic_coverage', '100000: England'),
        ('geographical_granularity', 'Local Authority (District)'),
        ('agency', u''),
        ('precision', ''),
        ('taxonomy_url', ''),
        ('import_source', 'COSPREAD-cospread-clg.xls'),
        ('department', u'Department for Communities and Local Government'),
        ('update_frequency', ''),
        ('national_statistic', ''),
        ('categories', ''),
        ])
     ),
    ])

class TestCospreadDataRecords:
    @classmethod
    def setup_class(self):
        self.data = examples.get_data('1', CSV_EXTENSION)
        self.data_records = MultipleCospreadDataRecords(self.data)
        
    def test_0_title_row(self):
        assert self.data_records.records_list[0].titles[0] == u'Package name', \
               self.data_records.records_list[0].titles

    def test_1_titles(self):
        titles = set(self.data_records.records_list[0].titles)
        title_difference = expected_titles_1 ^ titles
        assert not title_difference, title_difference

    def test_2_records(self):
        self.records = [record for record in self.data_records.records]
        assert len(self.records) == 3, self.records
        for key, value in example_record.items():
            assert self.records[0].has_key(key), 'Expected key %r in record: %r' % (key, self.records[0].keys())
            assert_equal(self.records[0][key], value)
        expected_keys = set([key for key, value in example_record.items()])
        keys = set(self.records[0].keys())
        key_difference = expected_keys - keys
        assert not key_difference, key_difference


class TestCospreadDataRecordsClg:
    @classmethod
    def setup_class(self):
        self.data = examples.get_data('-clg', XL_EXTENSION)
        self.data_records = MultipleCospreadDataRecords(self.data)
        
    def test_0_title_row(self):
        assert self.data_records.records_list[0].titles[0] == u'Package name', \
               self.data_records.records_list[0].titles

    def test_1_titles(self):
        titles = set(self.data_records.records_list[0].titles)
        title_difference = expected_titles_2 ^ titles
        if title_difference:
            msg = 'Titles should not have: %r' % (title_difference & titles)
            msg += '\nTitles expected but not received: %r' % (title_difference & expected_titles_2)
        assert not title_difference, msg

    def test_1_multiple_sheets(self):
        assert len(self.data_records.records_list) == 3, self.data_records.records_list

    def test_2_records(self):
        self.records = [record for record in self.data_records.records]
        assert len(self.records) == 3, '%i, %r' % (len(self.records),
                                                   self.records)
        # check record titles
        assert_equal(self.records[0]['Title'], u'Total number of dwellings owned by your local authority')
        assert_equal(self.records[1]['Title'], u'CWI Children in Need Domain')
        assert_equal(self.records[2]['Title'], u'NI 001 - Percentage of people who believe people from different backgrounds get on well together in their local area')
        
        # check first record thoroughly
        for key, value in clg_record.items():
            assert self.records[0].has_key(key), 'Expected key %r in record: %r' % (key, self.records[0].keys())
            assert_equal(self.records[0][key] or None, value or None)
        expected_keys = set([key for key, value in clg_record.items()])
        keys = set(self.records[0].keys())
        key_difference = expected_keys - keys
        assert not key_difference, key_difference


class TestImport:
    @classmethod
    def setup_class(self):
        self._filepath = examples.get_spreadsheet_filepath('1', CSV_EXTENSION)
        self.importer = CospreadImporter(include_given_tags=False, filepath=self._filepath)
        self.pkg_dicts = [pkg_dict for pkg_dict in self.importer.pkg_dict()]

    def test_0_name_munge(self):
        def test_name_munge(name, expected_munge):
            munge = self.importer.name_munge(name)
            assert munge == expected_munge, 'Got %s not %s' % (munge, expected_munge)
        test_name_munge('hesa-(1994-1995)', 'hesa-1994-1995')

        # 96 characters should be left alone
        test_name_munge('ni-198q-children-travelling-to-school-mode-of-transport-usually-used-pupils-aged-5-16-by-cycling', 'ni-198q-children-travelling-to-school-mode-of-transport-usually-used-pupils-aged-5-16-by-cycling')
        test_name_munge('a'*105, 'a'*100)

    def test_0_munge(self):
        def test_munge(name, expected_munge):
            munge = self.importer.munge(name)
            assert munge == expected_munge, 'Got %s not %s' % (munge, expected_munge)        
        test_munge('a$b cD:e f-g%  h', 'ab-cd-e-f-g-h')

    def test_1_record_2_package(self):
        pkg_dict = self.importer.record_2_package(example_record)

        log = self.importer.get_log()
        assert log[0].startswith("WARNING: Value for column 'Categories' of 'Health, well-being and Care' is not in suggestions '["), log[0]
        assert log[1].startswith("WARNING: URL doesn't start with http: test.html"), log[1]
        assert log[2].startswith("WARNING: URL doesn't start with http: test.json"), log[2]
        assert log[3].startswith("WARNING: Value for column 'Categories' of 'Health, well-being and Care' is not in suggestions '["), log[3]
        assert_equal(len(log), 4, log)

        PackageDictUtil.check_dict(pkg_dict, example_pkg_dict)
        expected_keys = set([key for key, value in example_pkg_dict.items()])
        keys = set(pkg_dict.keys())
        key_difference = expected_keys - keys
        assert not key_difference, key_difference

    def test_2_overall_import(self):
        pkg_dict = self.importer.record_2_package(example_record)
        assert_equal(self.pkg_dicts[0], pkg_dict)


class TestImportClg():
    @classmethod
    def setup_class(self):
        self._filepath = examples.get_spreadsheet_filepath('-clg', XL_EXTENSION)
        self.importer = CospreadImporter(include_given_tags=True, filepath=self._filepath)
        self.pkg_dicts = [pkg_dict for pkg_dict in self.importer.pkg_dict()]

    def test_all_sheets_found(self):
        assert len(self.pkg_dicts) == 3

    def test_include_given_tags(self):
        assert 'housing-and-planning-view-indicator-places' in self.pkg_dicts[0]['tags'], self.pkg_dicts[0]['tags']

    def test_1_record_2_package(self):
        pkg_dict = self.importer.record_2_package(clg_record)

        log = self.importer.get_log()
        assert log[0].startswith("WARNING: Value for column 'Geographical Granularity' of 'Local Authority (District)'"), log[0]
        assert log[1].startswith("WARNING: Value for column 'Geographical Granularity' of 'Super Output Area'"), log[1]
        assert log[2].startswith("WARNING: Value for column 'Geographical Granularity' of 'Local Authority District (LAD), County/Unitary Authority, Government Office Region (GOR), National'"), log[2]
        assert log[3].startswith("WARNING: Value for column 'Geographical Granularity' of 'Local Authority (District)' is not in suggestions"), log[3]
        assert_equal(len(log), 4, log)

        PackageDictUtil.check_dict(pkg_dict, clg_pkg_dict)
        expected_keys = set([key for key, value in clg_pkg_dict.items()])
        keys = set(pkg_dict.keys())
        key_difference = expected_keys - keys
        assert not key_difference, key_difference

    def test_2_overall_import(self):
        pkg_dict = self.importer.record_2_package(clg_record)
        assert_equal(self.pkg_dicts[0]['name'], pkg_dict['name'])
