from ckanext.api_command import ApiCommand
from ckanext.dgu.ons.downloader import OnsData
from ckanext.dgu.ons.importer import OnsImporter
from ckanext.dgu.ons.loader import OnsLoader
from ckanclient import CkanClient

class OnsLoaderCmd(ApiCommand):
    def add_options(self):
        self.parser.add_option("-d", "--days",
                               dest="days",
                               default="7",
                               help="Days to fetch data (default: 7)")
    def command(self):
        super(OnsLoaderCmd, self).command()
        
        days = int(self.options.days)

        data_filepath = OnsData.download_recent(days=days)
        importer = OnsImporter(filepath=data_filepath)
        loader = OnsLoader(self.client)

        loader.load_packages(importer.pkg_dict())

def load():
    OnsLoaderCmd().command()
