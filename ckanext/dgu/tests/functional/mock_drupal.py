import paste.script

def get_mock_drupal_config():
    from ckanext.dgu.tests import test_publishers
    return {
        'rpc_path': '/services/xmlrpc',
        'rpc_host': 'localhost',
        'rpc_port': 8000,
        'test_users': {'62': {'name': 'testname',
                              'publishers': test_publishers}
                       },
        }

class Command(paste.script.command.Command):
    '''Dgu commands

    run
    '''
    parser = paste.script.command.Command.standard_parser(verbose=True)
    default_verbosity = 1
    group_name = 'ckanext-dgu'
    summary = __doc__.split('\n')[0]

    def command(self):
        cmd = self.args[0]
        if cmd == 'run':
            self.run_mock_drupal()

    def run_mock_drupal(self):
        from SimpleXMLRPCServer import SimpleXMLRPCServer
        from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler

        config = get_mock_drupal_config()
        
        # Restrict to a particular path.
        class RequestHandler(SimpleXMLRPCRequestHandler):
            rpc_paths = (config['rpc_path'],)

        # Create server
        server = SimpleXMLRPCServer((config['rpc_host'], config['rpc_port']),
                                    requestHandler=RequestHandler)
        server.register_introspection_functions()

        class MyFuncs:
            class user: # lower case to match Drupal definition
                @classmethod
                def get(cls, user_id):
                    return config['test_users'][user_id]

        server.register_instance(MyFuncs(), allow_dotted_names=True)

        # Run the server's main loop
        print 'Serving on http://%s:%s%s' % (config['rpc_host'],
                                             config['rpc_port'],
                                             config['rpc_path'])
        server.serve_forever()
