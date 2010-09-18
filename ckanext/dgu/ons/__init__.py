from ckanext.command import Command
from ckanext.loader import PackageLoader, ResourceSeries
from ckanext.dgu.ons.downloader import OnsData
from ckanext.dgu.ons.importer import OnsImporter
from ckanclient import CkanClient

class Loader(Command):
    parser = Command.StandardParser()
    parser.add_option("-d", "--days",
                      dest="days",
                      default="7",
                      help="Days to fetch data (default: 7)")
    parser.add_option("-u", "--url",
                      dest="api_url",
                      default="http://ckan.net/api",
                      help="API URL (default: http://ckan.net/api")
    parser.add_option("-k", "--key",
                      dest="api_key",
                      help="API Key (required)")
    def command(self):
        days = int(self.options.days)
        api_url = self.options.api_url
        api_key = self.options.api_key
        assert api_key is not None, "Please specify an API Key"

        ons_data = OnsData()

        url, url_name = ons_data._get_url_recent(days=days)
        data_filepath = ons_data.download(url, url_name, force_download=True)
        importer = OnsImporter(filepath=data_filepath)

        client = CkanClient(base_location=api_url, api_key=api_key)
        settings = ResourceSeries(
            field_keys_to_find_pkg_by=['title', 'department'],
            resource_id_prefix='hub/id/',
            field_keys_to_expect_invariant=[
                'update_frequency', 'geographical_granularity',
                'geographic_coverage', 'temporal_granularity',
                'precision', 'url', 'taxonomy_url', 'agency',
                'author', 'author_email', 'license_id'])
        loader = PackageLoader(client, settings)

        loader.load_packages(importer.pkg_dict())

def load():
    Loader().command()
