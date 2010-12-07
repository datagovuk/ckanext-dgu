from ckanext.dgu.schema import *
from nose.tools import assert_equal

class TestGeoCoverageType:
    @classmethod
    def setup_class(cls):
        cls.expected_data = [
            # str, form, db
            ('England', ['england'], u'100000: England'),
            ('England and Wales', ['england', 'wales'], u'101000: England, Wales'),
            ('Scotland', ['scotland'], u'010000: Scotland'),
            ('Northern Ireland', ['northern_ireland'], u'000100: Northern Ireland'),
            ('GB', ['england', 'scotland', 'wales'], u'111000: Great Britain (England, Scotland, Wales)'),
            ('UK', ['england', 'scotland', 'wales', 'northern_ireland'], u'111100: United Kingdom (England, Scotland, Wales, Northern Ireland)'),
            ('Sub-National', None, u'000000: '),
            ]
            
    def test_str_to_db(self):
        for str_, form, db in self.expected_data:
            if str_ is None or db is None:
                continue
            result_db = GeoCoverageType.get_instance().str_to_db(str_)
            assert_equal(result_db, db)

    def test_form_to_db(self):
        for str_, form, db in self.expected_data:
            if form is None or db is None:
                continue
            result_db = GeoCoverageType.get_instance().form_to_db(form)
            assert_equal(result_db, db)

    def test_db_to_form(self):
        for str_, form, db in self.expected_data:
            if form is None or db is None:
                continue
            result_form = GeoCoverageType.get_instance().db_to_form(db)
            assert_equal(result_form, form)

class TestAbbreviations:
    def test_basic(self):
        res = expand_abbreviations('MFA')
        assert_equal(res, 'Marine and Fisheries Agency')

class TestTags:
    def test_parse(self):
        expected_data = [
            ('pollution fish', ['pollution', 'fish']),
            ('dosh$money', ['doshmoney']),
            ('ordnance survey', ['ordnance-survey']),
            ]
        for str_, tags in expected_data:
            result_tags = tags_parse(str_)
            assert_equal(result_tags, tags)

    def test_munge(self):
        expected_data = [
            ('pollution', 'pollution'),
            ('fish pollution', 'fish-pollution'),
            ('dosh$money', 'doshmoney'),
            ('under_score', 'under-score'),
            ]
        for str_, tag in expected_data:
            result_tag = tag_munge(str_)
            assert_equal(result_tag, tag)

    def test_suggester(self):
        expected_data = [
            ({'name':'road-traffic-accident'}, ['road', 'traffic', 'accident']),
            ({'name':'road',
              'title':'Traffic accidents'}, ['road', 'traffic', 'accident']),
            ({'name':'road',
              'agency':'Traffic accidents'}, ['road', 'traffic', 'accident']),
            ({'name':'road',
              'extras':{'agency':'Traffic accidents'}}, ['road', 'traffic', 'accident']),
            ]
        for pkg_dict, tags in expected_data:
            result_tags = suggest_tags(pkg_dict)
            assert_equal(result_tags, set(tags))

class TestName:
    def test_parse(self):
        expected_data = [
            ('Annual Report', 'annual_report'),
            ('Annual Report: 2006', 'annual_report-2006'),
            ]
        for str_, name in expected_data:
            result_name = name_munge(str_)
            assert_equal(result_name, name)
    
