from ckanext.importlib.loader import ResourceSeries
from ckanext.dgu.bin.transfer_url import TransferUrl
from ckanext.dgu.bin.mass_changer_cmd import MassChangerCommand
from ckanclient import CkanClient

class TransferUrlCommand(MassChangerCommand):
    def command(self):
        super(TransferUrlCommand, self).command()
        if self.options.license_id is None:
            self.parser.error("Please specify a license ID")
        if len(self.args) != 1:
            self.parser.error("Command is required")
            
        client = CkanClient(base_location=self.options.api_url,
                            api_key=self.options.api_key,
                            http_user=self.options.username,
                            http_pass=self.options.password)
        transfer_url = TransferUrl(client, dry_run=self.options.dry_run,
                                   force=self.options.force)
        transfer_url.transfer_url()

def command():
    TransferUrlCommand().command()

