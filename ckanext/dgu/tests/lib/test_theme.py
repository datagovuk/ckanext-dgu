import os.path

from nose.tools import assert_equal

from ckan import model
from ckanext.dgu.lib.theme import (categorize_package, categorize_package2,
                                   normalize_token)
from ckanext.taxonomy.models import init_tables
from ckanext.taxonomy import lib

fish_pkg = {'name': '',
            'title': 'fishing in the river',
            'notes': 'Fish',
            'tags': '',
            'extras': {}}

fish_and_spend_pkg = {'name': '',
                      'title': 'fishing in the river spend',
                      'notes': 'Fish spend transactions',
                      'tags': '',
                      'extras': {}}

death_pkg = {'name': '',
             'title': 'Death',
             'notes': '',
             'tags': '',
             'extras': {}}


class ThemeTestBase(object):
    @classmethod
    def setup_class(cls):
        init_tables()
        themes_filepath = os.path.abspath(os.path.join(__file__,
                                                       '../../../themes.json'))
        lib.load_terms_and_extras(themes_filepath, 'dgu-themes')

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()


class TestCategorizePackage(ThemeTestBase):

    def test_basic(self):
        themes = categorize_package(fish_pkg)

        assert_equal(themes, ['Environment'])

    def test_with_secondary_theme(self):
        themes = categorize_package(fish_and_spend_pkg)

        assert_equal(themes, ['Environment', 'Government Spending'])


class TestCategorizePackage2(ThemeTestBase):

    def test_basic(self):
        themes = categorize_package2(fish_pkg)

        assert_equal(type(themes), list)
        theme = themes[0]
        assert_equal(type(theme), dict)
        assert_equal(theme['name'], 'Environment')
        # be lenient as the algorithm may change
        assert theme['score'] > 3, theme.get('score')
        assert theme['reasons'], theme.get('reasons')
        assert_equal([u'"fish" matched title',
                      u'"river" matched title',
                      u'"fish" matched description'],
                     theme['reasons'])

    def test_with_secondary_theme(self):
        themes = categorize_package2(fish_and_spend_pkg)

        assert_equal(type(themes), list)
        theme = themes[0]
        assert_equal(type(theme), dict)
        assert_equal(theme['name'], 'Environment')
        # be lenient as the algorithm may change
        assert theme['score'] > 3, theme.get('score')
        assert theme['reasons'], theme.get('reasons')
        assert_equal([u'"fish" matched title',
                      u'"river" matched title',
                      u'"fish" matched description'],
                     theme['reasons'])

        theme = themes[1]
        assert_equal(theme['name'], 'Government Spending')
        assert_equal([u'"spend" matched title',
                      u'"transact" matched description',
                      u'"spend" matched description'],
                     theme['reasons'])

    def test_topic_in_two_categories(self):
        themes = categorize_package2(death_pkg)
        theme_names = [theme['name'] for theme in themes]
        assert_equal(set(('Society', 'Health')), set(theme_names))


class TestNormalizeToken(object):
    def test_no_change(self):
        assert_equal(normalize_token('fish'), 'fish')

    def test_stem(self):
        assert_equal(normalize_token('fishes'), 'fish')

    def test_stem_exception(self):
        assert_equal(normalize_token('hospitality'), 'hospitality')
        # not hospital
