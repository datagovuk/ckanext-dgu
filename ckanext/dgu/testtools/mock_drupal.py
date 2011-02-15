import logging
from xmlrpclib import Fault

import paste.script

from ckanext.dgu.testtools import test_publishers

def get_mock_drupal_config():
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

    mock_drupal run
    '''
    parser = paste.script.command.Command.standard_parser(verbose=True)
    default_verbosity = 1
    group_name = 'ckanext-dgu'
    summary = __doc__.split('\n')[0]
    usage = __doc__
    log = logging.getLogger(__name__)
    min_args = 1
    max_args = None

    def command(self):
        cmd = self.args[0]
        if cmd == 'run':
            self.run_mock_drupal()

    def run_mock_drupal(self):
        from SimpleXMLRPCServer import SimpleXMLRPCServer
        from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler
        from xmlrpclib import Fault

        config = get_mock_drupal_config()
        
        # Restrict to a particular path.
        class RequestHandler(SimpleXMLRPCRequestHandler):
            rpc_paths = (config['rpc_path'],)

        # Create server
        server = SimpleXMLRPCServer((config['rpc_host'], config['rpc_port']),
                                    requestHandler=RequestHandler,
                                    logRequests=False)
        server.register_introspection_functions()

        class MyFuncs:
            class user: # lower case to match Drupal definition
                @classmethod
                def get(cls, user_id):
                    # Real example:
                    # {'status': '1',
                    # 'uid': '28',
                    # 'publishers': {'11407': 'Cabinet Office',
                    #                '12022': 'Arts Council England'},
                    # 'roles': {'2': 'authenticated user'},
                    # 'pass': '5eb...',
                    # 'threshold': '0',
                    # 'timezone': '3600',
                    # 'theme': '',
                    # 'access': '1288976307',
                    # 'init': 'me@example.com',
                    # 'mail': 'me@example.com',
                    # 'sort': '0',
                    # 'picture': '',
                    # 'picture_delete': '',
                    # 'form_build_id': 'form-6236f...',
                    # 'signature_format': '0',
                    # 'data': 'a:4:{s:7:"contact";i:1;s:14:"picture_delete";s:0:"";s:14:"picture_upload";s:0:"";s:13:"form_build_id";s:37:"form-6236...";}',
                    # 'name': 'evanking',
                    # 'language': '',
                    # 'created': '1262777740',
                    # 'picture_upload': '',
                    # 'contact': 1,
                    # 'mode': '0',
                    # 'signature': '', 
                    # 'timezone_name': 'Europe/London',
                    # 'login': '1286...'}
                    try:
                        return config['test_users'][user_id]
                    except KeyError:
                        raise Fault(404, 'There is no user with such ID.')

            class organisation:
                @classmethod
                def one(cls, org_id):
                    # return org name by id
                    return test_publishers[org_id]

                @classmethod
                def match(cls, org_name):
                    # return org id by name
                    for id, name in test_publishers.items():
                        if name == org_name:
                            return id
                @classmethod
                def department(cls, org_id): 
                    # return top level parent ord id by org id
                    if org_id == '2':
                        return {'1': 'National Health Service'}
                    elif org_id in test_publishers:
                        return {org_id: test_publishers[org_id]}
                    else:
                        raise Fault(404)



        server.register_instance(MyFuncs(), allow_dotted_names=True)

        # Run the server's main loop
        self.log.info('Serving on http://%s:%s%s',
                      (config['rpc_host'], config['rpc_port'], config['rpc_path']))
        server.serve_forever()
