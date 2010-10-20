from ckanext.command import Command
from ckanext.loader import ResourceSeries
from ckanext.dgu.scripts.change_licenses import ChangeLicenses
from ckanclient import CkanClient

class ChangeLicenses(Command):
    parser = Command.StandardParser()
    parser.add_option("-H", "--host",
                      dest="api_url",
                      default="http://test.ckan.net/api",
                      help="API URL (default: http://test.ckan.net/api)")
    parser.add_option("-k", "--key",
                      dest="api_key",
                      help="API Key (required)")
    parser.add_option("--license-id",
                      dest="license_id",
                      help="ID of the license to change all packages to")

    def command(self):
        api_url = self.options.api_url
        api_key = self.options.api_key
        assert api_key is not None, "Please specify an API Key"
        license_id = self.options.license_id

        client = CkanClient(base_location=api_url, api_key=api_key)
        change_licenses = ChangeLicenses(client, license_id)
        change_licenses.change_all_packages
        
def command():
    ChangeLicenses().command()

