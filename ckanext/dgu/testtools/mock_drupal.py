import logging
from xmlrpclib import Fault
import signal
import paste.script

from ckanext.dgu.testtools.organisations import test_organisations, \
     test_organisation_names, LotsOfOrganisations

# NB Mock drupal details must match those in ckanext-dgu/test-core.ini
MOCK_DRUPAL_PATH = '/services/xmlrpc'
MOCK_DRUPAL_PORT = 8051
MOCK_DRUPAL_URL = 'http://localhost:%s%s' % \
                  (MOCK_DRUPAL_PORT, MOCK_DRUPAL_PATH)

def get_mock_drupal_config():
    return {
        'rpc_path': MOCK_DRUPAL_PATH,
        'rpc_host': 'localhost',
        'rpc_port': MOCK_DRUPAL_PORT,
        'test_users': {'62': {'name': 'testname',
                              'uid': '62',
                              'publishers': test_organisation_names,
                              'created': '1319119762', #(2011, 10, 20, 15, 9, 22)
                              'mail': 'joe@dept.gov.uk',
                              'roles': {'14': 'publishing user'}}
                       },
        'test_sessions': {'4160a72a4d6831abec1ac57d7b5a59eb': '62'}
        }

class Command(paste.script.command.Command):
    '''Dgu commands

    mock_drupal run OPTIONS
    '''
    parser = paste.script.command.Command.standard_parser(verbose=True)
    default_verbosity = 1
    group_name = 'ckanext-dgu'
    summary = __doc__.split('\n')[0]
    usage = __doc__
    min_args = 1
    max_args = None
    parser.add_option('-q', '--quiet',
                      dest='is_quiet',
                      action='store_true',
                      default=False,
                      help='Quiet mode')
    parser.add_option('-l', '--lots-of-organisations',
                      dest='lots_of_organisations',
                      action='store_true',
                      default=False,
                      help='Use a lot of organisations instead of a handful.')

    def command(self):
        cmd = self.args[0]
        if cmd == 'run':
            drupal = MockDrupal(self.options.lots_of_organisations)
            if not self.options.is_quiet:
                drupal.log.setLevel(logging.DEBUG)
                formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
                handler = logging.StreamHandler()
                handler.setFormatter(formatter)
                drupal.log.addHandler(handler)
            drupal.run()

class MockDrupal(object):

    quit_flag = False

    def __init__(self, lots_of_organisations=False):
        self.log = logging.getLogger(__name__)
        if lots_of_organisations:
            self.organisations = LotsOfOrganisations.get()
        else:
            self.organisations = test_organisations
        self.register_signal(signal.SIGQUIT)

    def register_signal(self, signum):
        signal.signal(signum, self.signal_handler)

    def signal_handler(self, signum, frame):
        print "Caught signal", signum
        self.quit_flag = True

    def run(self):
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
                    # Example response:
                    #   "Arts Council England"
                    try:
                        return self.organisations[org_id]['name']
                    except KeyError:
                        raise Fault(404, 'There is no organisation with such ID.')                    

                @classmethod
                def match(cls, org_name):
                    # return org id by name
                    # Example response:
                    #   "12022"
                    for id, org_dict in self.organisations.items():
                        if org_name == org_dict['name']:
                            return id
                    raise Fault(404, 'Cannot find organisation %r.' % org_name)
                
                @classmethod
                def department(cls, org_id): 
                    # return top level parent org id by org id
                    # Example response:
                    #   {'11419': 'Department for Culture, Media and Sport'}
                    if org_id in self.organisations:
                        parent_org_id = self.organisations[org_id]['parent_department_id']
                        return {parent_org_id: self.organisations[parent_org_id]['name']}
                    else:
                        raise Fault(404, 'No department for organisation ID %r' % org_id)

            class session:
                @classmethod
                def get(cls, session_id):
                    # return user_id given a session_id
                    # Example response:
                    #   62
                    try:
                        return config['test_sessions'][session_id]
                    except KeyError:
                        raise Fault(404, 'There is no session with such ID.')                    
        server.register_instance(MyFuncs(), allow_dotted_names=True)

        # Run the server's main loop
        self.log.debug('Serving on http://%s:%s%s',
                      config['rpc_host'], config['rpc_port'], config['rpc_path'])
        ckan_opts = '''
dgu.xmlrpc_username = 
dgu.xmlrpc_password = 
dgu.xmlrpc_domain = %(rpc_host)s:%(rpc_port)s
''' % config
        self.log.debug('CKAN options: %s',
                      ckan_opts)
        self.log.debug('%i organisations' % len(self.organisations))
        while not self.quit_flag:
            server.handle_request()        
