from ckanext.dgu.publishers import sync
from ckanext.dgu.bin.xmlrpc_command import XmlRpcCommand

class OrgCommand(XmlRpcCommand):
    '''Syncs organisations from Drupal into CKAN groups.
    '''
    summary = 'Syncs organisations from Drupal into CKAN groups.'
    
    def command(self):
        super(OrgCommand, self).command()

        sync.sync(self.xmlrpc_settings)

def command():
    OrgCommand().command()

