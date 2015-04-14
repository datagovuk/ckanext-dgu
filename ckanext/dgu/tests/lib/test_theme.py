from nose.tools import assert_equal

from ckanext.dgu.lib.theme import categorize_package, categorize_package2

fish_pkg = {'name': '',
            'title': 'fishing in the river',
            'notes': 'Fish',
            'tags': '',
            'extras': {}}

fish_and_spend_pkg = {'name': '',
                      'title': 'fishing in the river',
                      'notes': 'Fish spend transactions',
                      'tags': '',
                      'extras': {}}


class TestCategorizePackage:
    def test_basic(self):
        themes = categorize_package(fish_pkg)

        assert_equal(themes, ['Environment'])

    def test_with_secondary_theme(self):
        themes = categorize_package(fish_and_spend_pkg)

        assert_equal(themes, ['Environment', 'Spending'])


class TestCategorizePackage2:
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
        assert_equal(theme['name'], 'Spending')
        assert_equal([u'"transact" matched description',
                      u'"spend" matched description'],
                     theme['reasons'])
