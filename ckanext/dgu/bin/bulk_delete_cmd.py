from ckanext.dgu.bin.mass_changer_cmd import MassChangerCommand
from ckanext.dgu.bin.bulk_delete import BulkDelete
from ckanclient import CkanClient

class BulkDeleteCommand(MassChangerCommand):
    def add_options(self):
        super(BulkDeleteCommand, self).add_options()
        self.parser.add_option("--package-csv",
                               dest="package_csv",
                               help="File containing a list of packages to delete",
                               default=None)

    def command(self):
        super(BulkDeleteCommand, self).command()
        if self.options.package_csv is None:
            self.parser.error("Please specify a package CSV file")

        client = CkanClient(base_location=self.options.api_url,
                            api_key=self.options.api_key,
                            http_user=self.options.username,
                            http_pass=self.options.password)

        bulk_delete = BulkDelete(client, dry_run=self.options.dry_run, force=self.options.force)
        with open(self.options.package_csv) as csv_file:
            packages = [line.strip() for line in csv_file.readlines()]
            bulk_delete.delete_package_list(packages)

def command():
    BulkDeleteCommand().command()
