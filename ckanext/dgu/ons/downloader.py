import os
import urllib
import datetime
import logging
import datetime

ONS_CACHE_PATH = os.path.abspath(os.path.expanduser('~/ons_data'))
if not os.path.exists(ONS_CACHE_PATH):
    os.makedirs(ONS_CACHE_PATH)
ONS_URL_BASE = 'http://www.statistics.gov.uk/hub/release-calendar/rss.xml?lday=%(lday)s&lmonth=%(lmonth)s&lyear=%(lyear)s&uday=%(uday)s&umonth=%(umonth)s&uyear=%(uyear)s'

MONTHS_PER_YEAR = 12
YEAR_ONS_DATA_STARTS = 2004

class OnsData(object):
    '''Manages download and parse of ONS data.'''
    @classmethod
    def download_recent(cls, ons_cache_dir=ONS_CACHE_PATH, log=False, days=7):
        ons = cls(ons_cache_dir, log)
        url, url_name = ons._get_url_recent(days=days)
        return ons.download(url, url_name, force_download=True)

    @classmethod
    def download_flexible(cls, ons_cache_dir=ONS_CACHE_PATH, log=False,
                          days=None, start_date=None, end_date=None):
        ons = cls(ons_cache_dir, log)
        url, url_name = ons._get_url_flexible(days=days,
                                              start_date=start_date,
                                              end_date=end_date)
        return ons.download(url, url_name, force_download=True)

    @classmethod
    def download_all(cls, ons_cache_dir=ONS_CACHE_PATH, log=False):
        ons = cls(ons_cache_dir, log)
        url_tuples = ons._get_urls_for_all_time()
        return ons.download_multiple(url_tuples)

    def __init__(self, local_cache_dir=ONS_CACHE_PATH, log=False):
        self._local_cache_dir = os.path.expanduser(local_cache_dir)
        self._url_base = ONS_URL_BASE
        self._logging = log
        
    def download_multiple(self, url_tuples):
        filepaths = []
        for url_tuple in url_tuples:
            filepaths.append(self.download(*url_tuple))
        return filepaths

    def download(self, url, url_name, force_download=False):
        local_filepath = os.path.join(self._local_cache_dir, 'ons_data_%s' % url_name)
        if force_download and os.path.exists(local_filepath):
            os.remove(local_filepath)
        if not os.path.exists(local_filepath):
            urllib.urlretrieve(url, local_filepath)
        else:
            self.log(logging.info, 'ONS Data already downloaded: %s' % url_name)
        return local_filepath
        
    def download_month(self, month, year):
        assert month <= MONTHS_PER_YEAR
        assert year > 2000
        url, url_name = _get_url_month(month, year)
        self.download(url, url_name)

    def _get_url(self, lday, lmonth, lyear, uday, umonth, uyear):
        params = { 'lday':lday, 'lmonth':lmonth, 'lyear':lyear,
                   'uday':uday, 'umonth':umonth, 'uyear':uyear, }
        url = self._url_base % params
        url_id = '%(lyear)s-%(lmonth)s-%(lday)s_-_%(uyear)s-%(umonth)s-%(uday)s' % params
        return url, url_id
    
    def _get_url_month(self, month, year):
        id = '%(lday)s-%(lmonth)s-%(lyear)s_-_%(uday)s-%(umonth)s-%(uyear)s'
        url = self._url_base % {'lday':1, 'lmonth':month, 'lyear':year,
                                'uday':31, 'umonth':month, 'uyear':year,}
        url_id = datetime.date(year, month, 1).strftime('%Y-%m')
        if year == self._get_today().year and \
               month == self._get_today().month:
            url_id += '_incomplete'
        return [url, url_id]
    
    def _get_url_recent(self, days=7):
        end_date = self._get_today()
        return self._get_url_flexible(days=days, end_date=end_date)

    def _get_url_flexible(self, days=None, start_date=None, end_date=None):
        '''If you specify just days then it defaults end_date to be today.
        Otherwise you need to specify exactly two parameters.'''
        if start_date:
            assert isinstance(start_date, datetime.date)
        if end_date:
            assert isinstance(end_date, datetime.date)
        assert (days and not (start_date or end_date)) or \
               sum((bool(days), bool(start_date), bool(end_date))) == 2, \
               (days, start_date, end_date)

        url_id = None
        if days and not (start_date or end_date):
            end_date = self._get_today()
        if not start_date:
            start_date = end_date - datetime.timedelta(days=days)
            url_id = end_date.strftime(str(days) + '_days_to_%Y-%m-%d')
        if not end_date:
            end_date = start_date + datetime.timedelta(days=days)            
            url_id = start_date.strftime(str(days) + '_days_from_%Y-%m-%d')
        url, basic_url_id = self._get_url_days_period(start_date, end_date)
        return url, url_id or basic_url_id
        
    def _get_url_days_period(self, start_date, end_date):
        assert isinstance(start_date, datetime.date)
        assert isinstance(end_date, datetime.date)
        period = end_date - start_date
        if period > datetime.timedelta(days=31):
            self.log(logging.warning, 'Period is longer than a month - you may find the ONS Hub truncates the results unexpectedly.')
        url = self._url_base % {'lday':start_date.strftime('%d'),
                                'lmonth':start_date.strftime('%m'),
                                'lyear':start_date.strftime('%Y'),
                                'uday':end_date.strftime('%d'),
                                'umonth':end_date.strftime('%m'),
                                'uyear':end_date.strftime('%Y'),
                                }
        url_id = '%s_to_%s' % (start_date.strftime('%Y-%m-%d'),
                                end_date.strftime('%Y-%m-%d'))
        return url, url_id

    def _get_urls_for_all_time(self):
        url_tuples = []
        this_year = self._get_today().year
        for year in range(YEAR_ONS_DATA_STARTS, this_year): # not including this year
            for month in range(1, MONTHS_PER_YEAR+1): # i.e. 1-12 inclusive
                url_tuples.append(self._get_url_month(month, year) + [False])
        this_month = self._get_today().month
        for month in range(1, this_month):
            url_tuples.append(self._get_url_month(month, this_year) + [False])
        url_tuples.append(self._get_url_month(this_month, this_year) + [True])
        return url_tuples

    def _get_today(self):
        return datetime.date.today()

    def log(self, log_func, msg):
        if self._logging:
            log_func(msg)
        else:
            print '%s: %s' % (log_func.func_name, msg)
