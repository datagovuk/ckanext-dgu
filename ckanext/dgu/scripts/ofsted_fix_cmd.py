import sys

#from ckanext.api_command import ApiCommand
from mass_changer_cmd import MassChangerCommand
from ofsted_fix import OfstedFix

class OfstedFixCmd(MassChangerCommand):
    def command(self):
        super(OfstedFixCmd, self).command()

        # now do command
        cmd = OfstedFix(self.client, dry_run=self.options.dry_run)
        cmd.run()

def command():
    OfstedFixCmd().command()

