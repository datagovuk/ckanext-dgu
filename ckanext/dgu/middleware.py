#
# Drupal integration code
#

import Cookie
from ckanext.dgu.drupalclient import DrupalClient, DrupalXmlRpcSetupError, \
     DrupalRequestError
from xmlrpclib import ServerProxy

def drupal_extract_cookie(cookie_string):
    cookies = Cookie.SimpleCookie()
    cookies.load(str(cookie_string))
    for cookie in cookies:
        if cookie.startswith('SESS'):
            return cookies[cookie].value
    return None

def is_ckan_signed_in(cookie_string):
    cookies = Cookie.SimpleCookie()
    cookies.load(str(cookie_string))
    if not 'auth_tkt' in cookies:
        return False
    return True

class AuthAPIMiddleware(object):

    def __init__(self, app, app_conf):
        self.app = app
        self.drupal_client = None

    def __call__(self, environ, start_response):
        if self.drupal_client is None:
            self.drupal_client = DrupalClient()
        ckan_signed_in = [False]
        drupal_signed_in = [False]

        for k, v in environ.items():
            key = k.lower()
            if key  == 'http_cookie':
                ckan_signed_in[0] = is_ckan_signed_in(v)
                drupal_signed_in[0] = drupal_extract_cookie(v)

        ckan_signed_in = ckan_signed_in[0]
        drupal_signed_in = drupal_signed_in[0]
        environ['drupal.user_id'] = None
        environ['drupal.publisher'] = None
        new_start_response = start_response
        if drupal_signed_in and not ckan_signed_in:
            user_id = self.drupal_client.get_user_id_from_session_id(drupal_signed_in)
            res = self.drupal_client.get_user_properties(user_id)
            environ['drupal.uid'] = res['uid']
            environ['drupal.publishers'] = res['publishers']
            environ['drupal.name'] = res['name']

            from ckan import model
            from ckan.model.meta import Session

            def munge(username):
                username.lower().replace(' ', '_')
                return username

            # Add the new Drupal user if they don't already exist.
            query = Session.query(model.User).filter_by(name=unicode(environ['drupal.uid']))
            if not query.count():
                user = model.User(
                    name=munge(unicode(environ['drupal.uid'])), 
                    fullname=unicode(environ['drupal.name']), 
                    about=u'Drupal auto-generated user',
                )
                Session.add(user)
                Session.commit()
            else:
                user = query.one()
            new_header = environ['repoze.who.plugins']['auth_tkt'].remember(
                environ,
                {
                    'repoze.who.userid': environ['drupal.uid'],
                    'tokens': '',
                    'userdata': '',
                }
            )

            cookie_template = new_header[0][1].split('; ')

            cookie_string = ''
            for name, value in [
                ('ckan_apikey', user.apikey),
                ('ckan_display_name', user.fullname),
                ('ckan_user', user.name),
            ]: 
                cookie_string += '; %s="%s"'%(name, value)
                new_cookie = cookie_template[:]
                new_cookie[0] = '%s="%s"'%(name, value)
                new_header.append(('Set-Cookie', str('; '.join(new_cookie))))

            # Also need these cookies to work too:

            # ckan_apikey
            # Value	"3a51edc6-6461-46b8-bfe2-57445cbdeb2b"
            # Host	catalogue.dev.dataco.coi.gov.uk
            # Path	/
            # Secure	No
            # Expires	At End Of Session
            # 
            # 
            # Name	ckan_display_name
            # Value	"James Gardner"
            # Host	catalogue.dev.dataco.coi.gov.uk
            # Path	/
            # Secure	No
            # Expires	At End Of Session
            # 
            # 
            # Name	ckan_user
            # Value	"4466"
            # Host	catalogue.dev.dataco.coi.gov.uk
            # Path	/
            # Secure	No
            # Expires	At End Of Session


            # @@@ Need to add the headers to the request too so that the rest of the stack can sign the user in.

#Cookie: __utma=217959684.178461911.1286034407.1286034407.1286178542.2; __utmz=217959684.1286178542.2.2.utmcsr=google|utmccn=(organic)|utmcmd=organic|utmctr=coi%20london; DRXtrArgs=James+Gardner; DRXtrArgs2=3e174e7f1e1d3fab5ca138c0a023e13a; SESS9854522e7c5dba5831db083c5372623c=4160a72a4d6831abec1ac57d7b5a59eb; auth_tkt="a578c4a0d21bdbde7f80cd271d60b66f4ceabc3f4466!"; ckan_apikey="3a51edc6-6461-46b8-bfe2-57445cbdeb2b"; ckan_display_name="James Gardner"; ckan_user="4466"

            # There is a bug(/feature?) in line 628 of Cookie.py that means
            # it can't load from unicode strings. This causes Beaker to fail
            # unless the value here is a string
            if not environ.get('HTTP_COOKIE'):
                environ['HTTP_COOKIE'] += str(cookie_string)
            else:
                environ['HTTP_COOKIE'] = str(cookie_string[2:])

            def cookie_setting_start_response(status, headers, exc_info=None):
                headers += new_header
                return start_response(status, headers, exc_info)
            new_start_response = cookie_setting_start_response
        return self.app(environ, new_start_response)

#    # Configure the Pylons environment
#    load_environment(global_conf, app_conf)
#
#    # The Pylons WSGI app
#    app = PylonsApp()
#
#    # Routing/Session/Cache Middleware
#    app = RoutesMiddleware(app, config['routes.map'])
#    app = SessionMiddleware(app, config)
#    app = CacheMiddleware(app, config)
#    
#    # CUSTOM MIDDLEWARE HERE (filtered by error handling middlewares)
#    #app = QueueLogMiddleware(app)
#    
#    if asbool(full_stack):
#        # Handle Python exceptions
#        app = ErrorHandler(app, global_conf, **config['pylons.errorware'])
#
#        # Display error documents for 401, 403, 404 status codes (and
#        # 500 when debug is disabled)
#        if asbool(config['debug']):
#            app = StatusCodeRedirect(app)
#        else:
#            app = StatusCodeRedirect(app, [400, 401, 403, 404, 500])
#    app = AuthAPIMiddleware(app, app_conf)
#    # Initialize repoze.who
#    who_parser = WhoConfig(global_conf['here'])
#    who_parser.parse(open(app_conf['who.config_file']))
#    app = PluggableAuthenticationMiddleware(app,
#                    who_parser.identifiers,
#                    who_parser.authenticators,
#                    who_parser.challengers,
#                    who_parser.mdproviders,
#                    who_parser.request_classifier,
#                    who_parser.challenge_decider,
#                    logging.getLogger('repoze.who'),
#                    logging.WARN, # ignored
#                    who_parser.remote_user_key,
#               )
#    
#    # Establish the Registry for this application
#    app = RegistryManager(app)
#
#    if asbool(static_files):
#        # Serve static files
#        static_app = StaticURLParser(config['pylons.paths']['static_files'])
#        static_parsers = [static_app, app]
#
#        # Configurable extra static file paths
#        extra_public_paths = config.get('extra_public_paths')
#        if extra_public_paths:
#            static_parsers = [StaticURLParser(public_path) \
#                              for public_path in \
#                              extra_public_paths.split(',')] + static_parsers
#            
#        app = Cascade(static_parsers)
#    
#    return app
