import sys

from ckanclient import CkanClient
from ckanext.importlib.api_command import ApiCommand
from ons_analysis import OnsAnalysis

class OnsAnalysisCommand(ApiCommand):
    def add_options(self):
        super(OnsAnalysisCommand, self).add_options()
    
    def command(self):
        super(OnsAnalysisCommand, self).command()

        # now do command
        client = CkanClient(base_location=self.options.api_url,
                            api_key=self.options.api_key,
                            http_user=self.options.username,
                            http_pass=self.options.password)
        change_licenses = OnsAnalysis(client)
        change_licenses.run()

def command():
    OnsAnalysisCommand().command()

