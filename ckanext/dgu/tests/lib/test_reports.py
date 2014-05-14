from datetime import datetime as dt
from nose.tools import assert_equal

from ckanext.dgu.lib.reports import get_quarter_dates

class TestQuarters(object):
    def test_may(self):
        qs = get_quarter_dates(dt(2014, 5, 10))
        assert_equal(qs['this'], (dt(2014, 4, 1), dt(2014, 5, 10)))
        assert_equal(qs['last'], (dt(2014, 1, 1), dt(2014, 3, 31)))

    def test_march(self):
        qs = get_quarter_dates(dt(2014, 3, 31))
        assert_equal(qs['this'], (dt(2014, 1, 1), dt(2014, 3, 31)))
        assert_equal(qs['last'], (dt(2013, 10, 1), dt(2013, 12, 31)))

    def test_start_of_q(self):
        qs = get_quarter_dates(dt(2014, 4, 1))
        assert_equal(qs['this'], (dt(2014, 4, 1), dt(2014, 4, 1)))
        assert_equal(qs['last'], (dt(2014, 1, 1), dt(2014, 3, 31)))


