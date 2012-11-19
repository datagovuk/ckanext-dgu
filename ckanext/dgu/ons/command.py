import datetime

from ckanclient import CkanClient
from ckanext.importlib.api_command import ApiCommand

from ckanext.dgu.bin.xmlrpc_command import XmlRpcCommand

class OnsLoaderCmd(ApiCommand, XmlRpcCommand):
    def add_options(self):
        ApiCommand.add_options(self)
        XmlRpcCommand.add_options(self)
        self.parser.add_option("-d", "--days",
                               dest="days",
                               help="Days to fetch data (e.g. 7) (period is up to today, unless start-date or end-date specified)")
        self.parser.add_option("-s", "--start-date",
                               dest="start_date",
                               help="Date of start of period to fetch data (e.g. 2008-6-25)")
        self.parser.add_option("-e", "--end-date",
                               dest="end_date",
                               help="Date of end of period to fetch data (e.g. 2008-6-25)")
        self.parser.add_option("-a", "--all-time",
                               dest="all_time",
                               action="store_true",
                               default=False,
                               help="Request all ONS updates ever")
        self.parser.add_option("-c", "--cache-dir",
                               dest="ons_cache_dir",
                               help="Path to store downloads from ONS Pub Hub")
        
    def parse_date(self, date_str):
        return datetime.date(*[int(date_chunk) for date_chunk in date_str.split('-')])
    
    def command(self):
        from ckanext.dgu.ons.downloader import OnsData, ONS_DEFAULT_CACHE_PATH
        from ckanext.dgu.ons.importer import OnsImporter
        from ckanext.dgu.ons.loader import OnsLoader

        ApiCommand.command(self)
        XmlRpcCommand.command(self)

        if self.options.days:
            self.options.days = int(self.options.days)
        if self.options.start_date:
            self.options.start_date = self.parse_date(self.options.start_date)
        if self.options.end_date:
            self.options.end_date = self.parse_date(self.options.end_date)
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

        elif self.options.all_time:
            data_filepaths = OnsData.download_all()
        else:
            self.parser.error('Please specify a time period')

        importer = OnsImporter(filepaths=data_filepaths,
                               xmlrpc_settings=self.xmlrpc_settings)
        loader = OnsLoader(self.client)

        loader.load_packages(importer.pkg_dict())

def load():
    OnsLoaderCmd().command()
