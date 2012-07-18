import os
import datetime

from ckanext.dgu.ons import downloader

class OnsDataTester(downloader.OnsData):
    '''A test version of OnsData, that uses a test harness instead of the
    real internet, to test downloading ONS data.'''

    def __init__(self, local_cache_dir=downloader.ONS_DEFAULT_CACHE_PATH, log=False, files_downloaded=None):
        self.reset(files_downloaded)
        super(OnsDataTester, self).__init__(local_cache_dir=downloader.ONS_DEFAULT_CACHE_PATH, log=self.test_log_func)

    def reset(self, files_downloaded=None):
        # test records
        self.logs = []
        self.files_downloaded = files_downloaded or {} # filepath: url

    def download(self, url, url_name, force_download=False):
        local_filepath = os.path.join(self._local_cache_dir, 'ons_data_%s' % url_name)
        if force_download and local_filepath in self.files_downloaded:
            del self.files_downloaded[local_filepath]
        if not local_filepath in self.files_downloaded:
            self.files_downloaded[local_filepath] = url
        else:
            self.log(logging.info, 'ONS Data already downloaded: %s' % url_name)
        return local_filepath
    
    def test_log_func(self, log_func, msg):
        self.logs.append((log_func, msg))

    def _get_today(self):
        return datetime.date(2005, 6, 21)
