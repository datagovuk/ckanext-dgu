from ckanext.dgu.bin.command import Command

class XmlRpcCommand(Command):
    '''Derive from this to use the xmlrpc setting options.
    '''
    def __init__(self, usage=None):
        super(XmlRpcCommand, self).__init__()

    def add_options(self):
        super(XmlRpcCommand, self).add_options()
        self.parser.add_option("-X", "--xmlrpc-url",
                               dest="xmlrpc_url",
                               )
        self.parser.add_option("-D", "--xmlrpc-domain",
                               dest="xmlrpc_domain",
                               )
        self.parser.add_option("-U", "--xmlrpc-username",
                               dest="xmlrpc_username",
                               )
        self.parser.add_option("-P", "--xmlrpc-password",
                               dest="xmlrpc_password",
                               )

    def command(self):
        if not (self.options.xmlrpc_domain or self.options.xmlrpc_url):
            self.parser.error('Please specify an XML RPC domain or URL')

        self.xmlrpc_settings = {
            'xmlrpc_url':self.options.xmlrpc_url,
            'xmlrpc_domain':self.options.xmlrpc_domain,
            'xmlrpc_username':self.options.xmlrpc_username,
            'xmlrpc_password':self.options.xmlrpc_password}

        # now do command
        
