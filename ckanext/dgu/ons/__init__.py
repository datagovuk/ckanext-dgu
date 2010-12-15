from ckanext.command import Command
from ckanext.dgu.ons.downloader import OnsData
from ckanext.dgu.ons.importer import OnsImporter
from ckanext.dgu.ons.loader import OnsLoader
from ckanclient import CkanClient

class Loader(Command):
    parser = Command.StandardParser()
    parser.add_option("-d", "--days",
                      dest="days",
                      default="7",
                      help="Days to fetch data (default: 7)")
    parser.add_option("-u", "--url",
                      dest="api_url",
                      default="http://test.ckan.net/api",
                      help="API URL (default: http://test.ckan.net/api)")
    parser.add_option("-k", "--key",
                      dest="api_key",
                      help="API Key (required)")
    def command(self):
        days = int(self.options.days)
        api_url = self.options.api_url
        api_key = self.options.api_key
        if not api_key:
            self.parser.error('Please specify an API Key')

        data_filepath = OnsData.download_recent(days=days)
        importer = OnsImporter(filepath=data_filepath)
        client = CkanClient(base_location=api_url, api_key=api_key)
        loader = OnsLoader(client)

        loader.load_packages(importer.pkg_dict())

def load():
    Loader().command()
