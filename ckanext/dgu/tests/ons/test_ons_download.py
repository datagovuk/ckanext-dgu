import os
import datetime

from nose.tools import assert_equal

from ons_data_tester import OnsDataTester
from ckanext.dgu.ons import downloader

class TestOnsData:
    def __init__(self):
        self.ons_cache_path = os.path.expanduser(downloader.ONS_DEFAULT_CACHE_PATH)
        self.ons_url_base = downloader.ONS_URL_BASE[:downloader.ONS_URL_BASE.find('?')]
        
    def test_get_url(self):
        ons_data = OnsDataTester()
        res = ons_data._get_url(31, 12, 2004, 30, 6, 2005)
        assert res[0] == self.ons_url_base + '?lday=31&lmonth=12&lyear=2004&uday=30&umonth=6&uyear=2005', res[0]
        assert res[1] == '2004-12-31_-_2005-6-30', res[1]

    def test_get_url_month(self):
        ons_data = OnsDataTester()
        res = ons_data._get_url_month(12, 2004)
        assert res[0] == self.ons_url_base + '?lday=1&lmonth=12&lyear=2004&uday=31&umonth=12&uyear=2004', res[0]
        assert res[1] == '2004-12', res[1]

    def test_get_url_recent(self):
        ons_data = OnsDataTester()
        res = ons_data._get_url_recent(days=7)
        assert res[0] == self.ons_url_base + '?lday=14&lmonth=06&lyear=2005&uday=21&umonth=06&uyear=2005', res[0]
        assert res[1] == '7_days_to_2005-06-21', res[1]

    def test_get_url_recent_via_flexible(self):
        ons_data = OnsDataTester()
        res = ons_data._get_url_flexible(days=7)
        assert res[0] == self.ons_url_base + '?lday=14&lmonth=06&lyear=2005&uday=21&umonth=06&uyear=2005', res[0]
        assert res[1] == '7_days_to_2005-06-21', res[1]

    def test_get_url_end_date(self):
        ons_data = OnsDataTester()
        res = ons_data._get_url_flexible(
            days=7, end_date=datetime.date(2005, 6, 15))
        assert_equal(res[0], self.ons_url_base + '?lday=08&lmonth=06&lyear=2005&uday=15&umonth=06&uyear=2005')
        assert_equal(res[1], '7_days_to_2005-06-15')

    def test_get_url_start_date(self):
        ons_data = OnsDataTester()
        res = ons_data._get_url_flexible(
            days=7, start_date=datetime.date(2005, 6, 7))
        assert_equal(res[0], self.ons_url_base + '?lday=07&lmonth=06&lyear=2005&uday=14&umonth=06&uyear=2005')
        assert_equal(res[1], '7_days_from_2005-06-07')

    def test_get_url_period(self):
        ons_data = OnsDataTester()
        res = ons_data._get_url_flexible(
            start_date=datetime.date(2005, 6, 7),
            end_date=datetime.date(2005, 6, 9))
        assert_equal(res[0], self.ons_url_base + '?lday=07&lmonth=06&lyear=2005&uday=09&umonth=06&uyear=2005')
        assert_equal(res[1], '2005-06-07_to_2005-06-09')

    def test_get_urls_for_all_time(self):
        ons_data = OnsDataTester()
        url_tuples = ons_data._get_urls_for_all_time(False)
        assert len(url_tuples) == 90,  len(url_tuples)
        assert url_tuples[0] == [self.ons_url_base + '?lday=1&lmonth=1&lyear=1998&uday=31&umonth=1&uyear=1998', '1998-01', False], url_tuples[0]
        assert url_tuples[-2] == [self.ons_url_base + '?lday=1&lmonth=5&lyear=2005&uday=31&umonth=5&uyear=2005', '2005-05', False], url_tuples[-2]
        assert url_tuples[-1] == [self.ons_url_base + '?lday=1&lmonth=6&lyear=2005&uday=31&umonth=6&uyear=2005', '2005-06_incomplete', True], url_tuples[-1]

    def test_get_monthly_urls_since(self):
        ons_data = OnsDataTester()
        url_tuples = ons_data._get_monthly_urls_since(1999, 11)
        assert_equal(len(url_tuples), 68)
        assert url_tuples[0] == [self.ons_url_base + '?lday=1&lmonth=11&lyear=1999&uday=31&umonth=11&uyear=1999', '1999-11', False], url_tuples[0]
        assert_equal(url_tuples[1][1], '1999-12')
        assert_equal(url_tuples[2][1], '2000-01')
        assert_equal(url_tuples[3][1], '2000-02')
        assert_equal(url_tuples[-1][1], '2005-06_incomplete')


    def test_download(self):
        url = 'testurl'
        url_name = 'UrlName'
        ons_data = OnsDataTester()
        res = ons_data.download(url, url_name, force_download=False)
        assert res == self.ons_cache_path + '/ons_data_UrlName', res
        assert ons_data.files_downloaded == {res: 'testurl'}, res.items()

    def _test_import_recent(self):
        res = OnsDataTester.import_recent(days=7)
        assert res == 5, res
