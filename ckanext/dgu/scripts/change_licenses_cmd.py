import sys

from ckanext.loader import ResourceSeries
from ckanext.dgu.scripts.change_licenses import ChangeLicenses
from ckanext.dgu.scripts.mass_changer_cmd import MassChangerCommand
from ckanclient import CkanClient

class ChangeLicensesCommand(MassChangerCommand):
    def __init__(self):
        commands = ('all', 'oct10')
        super(ChangeLicensesCommand, self).__init__(commands)

    def add_additional_options(self):
        self.parser.add_option("--license-id",
                               dest="license_id",
                               help="ID of the license to change all packages to")
    def assert_args_valid(self):
        super(ChangeLicensesCommand, self).assert_args_valid()
        assert self.options.license_id is not None, "Please specify a license ID"
        assert len(self.args) == 1, "Command is required"
                
    def command(self):
        super(ChangeLicensesCommand, self).command()
        getattr(self, self.args[0])()

    def all(self):
        client = CkanClient(base_location=self.options.api_url,
                            api_key=self.options.api_key,
                            http_user=self.options.username,
                            http_pass=self.options.password)
        change_licenses = ChangeLicenses(client, dry_run=self.options.dry_run, force=self.options.force)
        change_licenses.change_all_packages(self.options.license_id)

    def oct10(self):
        client = CkanClient(base_location=self.options.api_url,
                            api_key=self.options.api_key)
        change_licenses = ChangeLicenses(client, dry_run=self.options.dry_run, force=self.options.force)
        change_licenses.change_oct_2010(self.options.license_id)

def command():
    ChangeLicensesCommand().command()

