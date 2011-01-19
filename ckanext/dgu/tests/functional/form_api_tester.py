import copy

from pylons import request, response
from webob.multidict import MultiDict

from ckan import model
from ckan.lib.helpers import literal, select, json
from ckan.controllers.form import FormController
from ckan.plugins import implements, SingletonPlugin
from ckan.plugins import IRoutes

class FormApiTester(SingletonPlugin):
    implements(IRoutes, inherit=True)

    test_controller = 'ckanext.dgu.tests.functional.form_api_tester:FormApiTestController'
    
    def after_map(self, map):
        ''' Create test i/f over existing api by adding to routes
        by copying the i/f mappings
        e.g. map.connect('/api/1/form/package/create', controller='form', action='package_create')
             is copied to :
             map.connect('/apitest/1/form/package/create', controller='FormApiTestController', action='package_create')
        '''
        for route in map.matchlist:
            if route.routepath.startswith('/api/') and \
               'form' in route._kargs.get('controller'):
                test_routepath = route.routepath.replace('/api/', '/apitest/')
                test_kargs = copy.deepcopy(route._kargs)
                test_kargs['controller'] = self.test_controller
                map.connect(test_routepath, **test_kargs)
        return map


class FormApiTestController(FormController):
    '''Controller that acts as a client for the form API by
    forwarding requests onto it.

    NB This plug-in must not be enabled on a live site because
    of the credentials bypass.

    Useful for manual testing:
      * Acts as a mock app passing through to the form API
      * Credentials bypass

    To activate this plugin:
      * add this to the config:  
         ckan.plugins = form_api_tester
      * ensure ckanext is installed in the ckan environment
         pip -E pyenv install ckanext

    Usage:
      Browse to form api urls replacing 'api' with 'apitest' and
      add a user parameter.
      e.g. http://127.0.0.1:5000/apitest/form/package/create
    '''

    def __init__(self):
        super(FormApiTestController, self).__init__()
        self.form_template = literal('''
<html>
  <form id="test" action="" method="post">    
    %s
    <input type="submit" name="send" />
  </form>
</html>''')
        self.success_template = literal('''
<html>
  <h1>Success %s</h1>
  <p>
    %s
  </p>
</html>''')
        self.error_template = literal('''
<html>
  <h1>Error %s</h1>
  <p>
    %s
  </p>
</html>''')
        self.default_users = ['okfn', 'tester', 'joeadmin']

    def get_user_selector(self):
        users = [user.name for user in model.Session.query(model.User)]
        for potential_default_user in self.default_users:
            if potential_default_user in users:
                default_user = potential_default_user
                break
        else:
            default_user = users[0]                
        return literal('<label for="user_name">User:</label>') + \
               select('user_name', default_user, users, 'user_name')

    def form_wrapper(self, form_function, request_params, *args):
        if request_params.has_key('user_name'):
            user_name = request_params['user_name']
            user = model.User.by_name(user_name)
            assert user, 'User not found: %s'
            request.environ['Authorization'] = user.apikey
        res_text = form_function(*args)
        if response.status.startswith('20'):
            if 'Package' in res_text:
                fields = self.get_user_selector() + '\n' + res_text
                return self.form_template % fields
            else:
                return self.success_template % (response.status, res_text)
        else:
            return self.error_template % (response.status, res_text)

    def package_form_wrapper(self, form_function, request_params, *args):
        if 'Package' in str(request.params.keys()):
            # Format request params as:
            #{ form_data: [ (FIELD-NAME, FIELD-VALUE), ... ],
            #  log_message: LOG-MESSAGE, author: AUTHOR }

            author = 'Test author: %s' % request.params.get('user_name', 'not given')
            form_params = {'form_data':{},
                           'log_message':'Test log message',
                           'author':author,
                           }
            for key, value in request.params.items():
                if '-' in key:
                    form_params['form_data'][key] = value
            self._set_request_params({json.dumps(form_params):1})
        return self.form_wrapper(form_function, request_params, *args)
        
    def _set_request_params(self, params):
        # Use request.environ['_parsed_post_vars'] because
        # request.params is immutable but derived from
        # _parsed_post_vars
        request.environ['webob._parsed_post_vars'] = (params, request.body_file)
        # check it works
        updated_params = request.POST
        assert updated_params == params, updated_params
        

    def package_create(self):
        return self.package_form_wrapper(super(FormApiTestController, self).package_create, request.params)
            
    def package_edit(self, id):
        return self.package_form_wrapper(super(FormApiTestController, self).package_edit, request.params, id)
        
