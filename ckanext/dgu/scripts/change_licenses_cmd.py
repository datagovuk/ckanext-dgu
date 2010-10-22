import sys

from ckanext.command import Command
from ckanext.loader import ResourceSeries
from ckanext.dgu.scripts.change_licenses import ChangeLicenses
from ckanclient import CkanClient

class ChangeLicensesCommand(Command):
    commands = ['all', 'oct10']
    parser = Command.StandardParser(usage=("%%prog [options] {%s}" % '|'.join(commands)))
    parser.add_option("-H", "--host",
                      dest="api_url",
                      default="http://test.ckan.net/api",
                      help="API URL (default: http://test.ckan.net/api)")
    parser.add_option("-k", "--key",
                      dest="api_key",
                      help="API Key (required)")
    parser.add_option("-d", "--dry-run",
                      dest="dry_run",
                      action="store_true",
                      default=False,
                      help="Write no changes")
    parser.add_option("-f", "--force",
                      dest="force",
                      action="store_true",
                      default=False,
                      help="Don't abort rest of packages on an error")
    parser.add_option("--license-id",
                      dest="license_id",
                      help="ID of the license to change all packages to")

    def command(self):
        try:
            assert self.options.api_key is not None, "Please specify an API Key"
            assert len(self.args) == 1, "Command is required"
        except AssertionError, e:
            print 'ERROR', e.args
            self.parser.print_help()
            sys.exit(1)
        getattr(self, self.args[0])()

    def all(self):
        client = CkanClient(base_location=self.options.api_url,
                            api_key=self.options.api_key)
        change_licenses = ChangeLicenses(client, dry_run=self.options.dry_run, force=self.options.force)
        change_licenses.change_all_packages(self.options.license_id)

    def oct10(self):
        client = CkanClient(base_location=self.options.api_url,
                            api_key=self.options.api_key)
        change_licenses = ChangeLicenses(client, dry_run=self.options.dry_run, force=self.options.force)
        change_licenses.change_oct_2010(self.options.license_id)

def command():
    ChangeLicensesCommand().command()

