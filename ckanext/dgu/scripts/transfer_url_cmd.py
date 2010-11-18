from ckanext.loader import ResourceSeries
from ckanext.dgu.scripts.transfer_url import TransferUrl
from ckanext.dgu.scripts.mass_changer_cmd import MassChangerCommand
from ckanclient import CkanClient

class TransferUrlCommand(MassChangerCommand):
    def add_additional_options(self):
        pass
    
    def assert_args_valid(self):
        self(TransferUrlCommand, self).assert_args_valid()
        assert self.options.license_id is not None, "Please specify a license ID"
        assert len(self.args) == 1, "Command is required"
                
    def command(self):
        super(TransferUrlCommand, self).command()
        client = CkanClient(base_location=self.options.api_url,
                            api_key=self.options.api_key,
                            http_user=self.options.username,
                            http_pass=self.options.password)
        transfer_url = TransferUrl(client, dry_run=self.options.dry_run,
                                   force=self.options.force)
        transfer_url.transfer_url()

def command():
    TransferUrlCommand().command()

