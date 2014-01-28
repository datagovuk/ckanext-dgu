import datetime
import logging

from ckanext.importlib.api_command import ApiCommand
from ckanext.dgu.bin.running_stats import StatsList

class OnsLoaderCmd(ApiCommand):
    user_agent = 'ONS Loader'

    def add_options(self):
        ApiCommand.add_options(self)
        self.parser.add_option("-d", "--days",
                               dest="days",
                               help="Days to fetch data (e.g. 7) (period is up to today, unless start-date or end-date specified)")
        self.parser.add_option("-s", "--start-date",
                               dest="start_date",
                               help="Date of start of period to fetch data (e.g. 2008-6-25)")
        self.parser.add_option("-e", "--end-date",
                               dest="end_date",
                               help="Date of end of period to fetch data (e.g. 2008-6-25)")
        self.parser.add_option("-m", "--month",
                               dest="month",
                               help="Year and month to fetch data from (e.g. 2008-6)")
        self.parser.add_option("", "--months-since",
                               dest="months_since",
                               help="Year and month to fetch data since, in monthly chunks (e.g. 2008-6)")
        self.parser.add_option("-a", "--all-time",
                               dest="all_time",
                               action="store_true",
                               default=False,
                               help="Request all ONS updates ever, in monthly chunks")
        self.parser.add_option("-f", "--force-download",
                               dest="force_download",
                               action="store_true",
                               default=False,
                               help="Force download from ONS, even if it is cached")
        self.parser.add_option("-c", "--cache-dir",
                               dest="ons_cache_dir",
                               help="Path to store downloads from ONS Pub Hub")
        self.parser.add_option("--publisher",
                               dest="publisher",
                               help="Filter by this publisher")

    def parse_date(self, date_str):
        return datetime.date(*[int(date_chunk) for date_chunk in date_str.split('-')])

    def parse_month(self, date_str):
        return datetime.date(*[int(date_chunk) for date_chunk in date_str.split('-')] + [1])

    def command(self):
        from ckanext.dgu.ons.downloader import OnsData, ONS_DEFAULT_CACHE_PATH
        from ckanext.dgu.ons.importer import OnsImporter
        from ckanext.dgu.ons.loader import OnsLoader

        ApiCommand.command(self)
        log = logging.getLogger(__name__)

        try:
            if self.options.days:
                self.options.days = int(self.options.days)
            if self.options.start_date:
                self.options.start_date = self.parse_date(self.options.start_date)
            if self.options.end_date:
                self.options.end_date = self.parse_date(self.options.end_date)
            if self.options.month:
                self.options.month = self.parse_month(self.options.month)
            if self.options.months_since:
                self.options.months_since = self.parse_month(self.options.months_since)
            if not self.options.ons_cache_dir:
                self.options.ons_cache_dir = ONS_DEFAULT_CACHE_PATH

            if self.options.days or \
                self.options.start_date or \
                self.options.end_date:
                data_filepaths = OnsData.download_flexible(
                    days=self.options.days,
                    start_date=self.options.start_date,
                    end_date=self.options.end_date,
                    ons_cache_dir=self.options.ons_cache_dir)

            elif self.options.month:
                data_filepaths = OnsData.download_month(year=self.options.month.year,
                                                        month=self.options.month.month)
            elif self.options.months_since:
                data_filepaths = OnsData.download_months_since(
                    year=self.options.months_since.year,
                    month=self.options.months_since.month,
                    force_download=self.options.force_download)
            elif self.options.all_time:
                data_filepaths = OnsData.download_all(force_download=self.options.force_download)
            else:
                self.parser.error('Please specify a time period')

            filter_ = {}
            if self.options.publisher:
                filter_['publisher'] = self.options.publisher

            stats = StatsList()
            importer = OnsImporter(filepaths=data_filepaths,
                                   ckanclient=self.client, stats=stats,
                                   filter_=filter_)
            loader = OnsLoader(self.client, stats)

            loader.load_packages(importer.pkg_dict())
            log.info('Summary:\n' + stats.report())
        except:
            # Any problem, make sure it gets logged
            log.exception('ONS Loader exception')
            raise

def load():
    OnsLoaderCmd().command()
