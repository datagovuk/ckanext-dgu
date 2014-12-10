from nose.tools import assert_equal

from ckanext.dgu.lib.theme import categorize_package, categorize_package2

fish_pkg = {'name': 'river fishing',
            'title': 'fish in the river',
            'notes':'',
            'tags':'',
            'extras':{}}


class TestCategorizePackage:
    def test_basic(self):
        themes = categorize_package(fish_pkg)

        assert_equal(themes, ['Environment'])


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
