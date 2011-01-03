import datetime

from ckanext.api_command import ApiCommand
from ckanext.dgu.ons.downloader import OnsData
from ckanext.dgu.ons.importer import OnsImporter
from ckanext.dgu.ons.loader import OnsLoader
from ckanclient import CkanClient

class OnsLoaderCmd(ApiCommand):
    def add_options(self):
        self.parser.add_option("-d", "--days",
                               dest="days",
                               help="Days to fetch data (e.g. 7) (period is up to today, unless start-date or end-date specified)")
        self.parser.add_option("-s", "--start-date",
                               dest="start_date",
                               help="Date of start of period to fetch data (e.g. 2008-6-25)")
        self.parser.add_option("-e", "--end-date",
                               dest="end_date",
                               help="Date of end of period to fetch data (e.g. 2008-6-25)")
        
    def parse_date(self, date_str):
        return datetime.date(*[int(date_chunk) for date_chunk in date_str.split('-')])
    
    def command(self):
        super(OnsLoaderCmd, self).command()

        if self.options.days:
            self.options.days = int(self.options.days)
        if self.options.start_date:
            self.options.start_date = self.parse_date(self.options.start_date)
        if self.options.end_date:
            self.options.end_date = self.parse_date(self.options.end_date)
        data_filepath = OnsData.download_flexible(
            days=self.options.days,
            start_date=self.options.start_date,
            end_date=self.options.end_date)
        importer = OnsImporter(filepath=data_filepath)
        loader = OnsLoader(self.client)

        loader.load_packages(importer.pkg_dict())

def load():
    OnsLoaderCmd().command()
