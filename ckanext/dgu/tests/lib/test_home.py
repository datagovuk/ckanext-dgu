import os

from nose.tools import assert_equal

from ckanext.dgu.lib.home import get_themes
from ckanext.taxonomy.models import init_tables as init_taxonomy_tables
from ckanext.taxonomy import lib as taxonomy_lib


class TestHome(object):
    @classmethod
    def setup_class(cls):
        init_taxonomy_tables()
        themes_filepath = os.path.abspath(os.path.join(__file__,
                                                       '../../../themes.json'))
        taxonomy_lib.load_terms_and_extras(themes_filepath, 'dgu-themes')

    def test_get_themes(self):
        themes = get_themes()

        assert_equal(len(themes), 12)
        assert_equal(themes[0][0], 'Business and economy')
        assert_equal(themes[0][1], 'Small businesses, industry, imports, exports and trade')
