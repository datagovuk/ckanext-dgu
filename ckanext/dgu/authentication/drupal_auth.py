import Cookie
import logging
import datetime

from ckanext.dgu.drupalclient import DrupalClient, DrupalXmlRpcSetupError, \
     DrupalRequestError
from xmlrpclib import ServerProxy

log = logging.getLogger(__name__)

class DrupalAuthMiddleware(object):
    '''Allows CKAN user to login via Drupal. It looks for the Drupal cookie
    and gets user details from Drupal using XMLRPC. 
    so works side-by-side with normal CKAN logins.'''

    def __init__(self, app, app_conf):
        self.app = app
        self.drupal_client = None
        self._user_name_prefix = 'user_d'

    def _parse_cookies(self, environ):
        is_ckan_cookie = [False]
        drupal_session_id = [False]
        for k, v in environ.items():
            key = k.lower()
            if key  == 'http_cookie':
                is_ckan_cookie[0] = self._is_this_a_ckan_cookie(v)
                drupal_session_id[0] = self._drupal_cookie_parse(v)
        is_ckan_cookie = is_ckan_cookie[0]
        drupal_session_id = drupal_session_id[0]
        return is_ckan_cookie, drupal_session_id

    def _drupal_cookie_parse(self, cookie_string):
        '''Returns the Drupal Session ID from the cookie string.'''
        cookies = Cookie.SimpleCookie()
        cookies.load(str(cookie_string))
        for cookie in cookies:
            if cookie.startswith('SESS'):
                log.debug('Drupal cookie found')
                return cookies[cookie].value
        return None

    def _is_this_a_ckan_cookie(self, cookie_string):
        cookies = Cookie.SimpleCookie()
        cookies.load(str(cookie_string))
        if not 'auth_tkt' in cookies:
            return False
        return True

    def _munge_drupal_id_to_ckan_user_name(self, drupal_id):
        drupal_id.lower().replace(' ', '_')
        return u'%s%s' % (self._user_name_prefix, drupal_id)

    def _log_out(self, environ, new_headers):
        # don't progress the user info for this request
        environ['REMOTE_USER'] = None
        environ['repoze.who.identity'] = None
        # tell auth_tkt to logout whilst adding the header to tell
        # the browser to delete the cookie
        identity = {}
        headers = environ['repoze.who.plugins']['dgu_auth_tkt'].forget(environ, identity)
        if headers:
            new_headers.extend(headers)
        # Remove cookie from request, so that if we are doing a login again in this request then
        # it is aware of the cookie removal
        log.debug('Removing cookies from request: %r', environ.get('HTTP_COOKIE', ''))
        cookies = environ.get('HTTP_COOKIE', '').split('; ')
        cookies = '; '.join([cookie for cookie in cookies if not cookie.startswith('auth_tkt=')])
        environ['HTTP_COOKIE'] = cookies
        log.debug('Cookies in request now: %r', environ['HTTP_COOKIE'])

        log.debug('Logged out Drupal user')

    def __call__(self, environ, start_response):
        new_headers = []

        self.do_drupal_login_logout(environ, new_headers)
       
	log.debug('New headers: %r', new_headers) 
        def cookie_setting_start_response(status, headers, exc_info=None):
            if headers:
                headers.extend(new_headers)
            else:
                headers = new_headers
            return start_response(status, headers, exc_info)
        new_start_response = cookie_setting_start_response
                
        return self.app(environ, new_start_response)

    def do_drupal_login_logout(self, environ, new_headers):
        '''Looks at cookies and auth_tkt and may tell auth_tkt to log-in or log-out
        to a Drupal user.'''
        is_ckan_cookie, drupal_session_id = self._parse_cookies(environ)

        # Is there a Drupal cookie? We may want to do a log-in for it.
        if drupal_session_id:
            # Look at any authtkt logged in user details
            authtkt_identity = environ.get('repoze.who.identity')
            if authtkt_identity:
                authtkt_user_name = authtkt_identity['repoze.who.userid'] #same as environ.get('REMOTE_USER', '')
                authtkt_drupal_session_id = authtkt_identity['userdata']
            else:
                authtkt_user_name = ''
                authtkt_drupal_session_id = ''

            if not authtkt_user_name:
                # authtkt not logged in, so log-in with the Drupal cookie
                self._do_drupal_login(environ, drupal_session_id, new_headers)
                return
            elif authtkt_user_name.startswith(self._user_name_prefix):
                # A drupal user is logged in with authtkt.
                # See if that the authtkt matches the drupal cookie's session
                if authtkt_drupal_session_id != drupal_session_id:
                    # Drupal cookie session has changed, so tell authkit to forget the old one
                    # before we do the new login
                    log.debug('Drupal cookie session has changed from %r to %r.', authtkt_drupal_session_id, drupal_session_id)
                    self._log_out(environ, new_headers)
		    # since we are about to login again, we need to get rid of the headers like
                    # ('Set-Cookie', 'auth_tkt="INVALID"...' since we are about to set them again in this
                    # same request.)
                    new_headers[:] = [(key, value) for (key, value) in new_headers \
                                   if (not (key=='Set-Cookie' and value.startswith('auth_tkt="INVALID"')))]
                    log.debug('Headers reduced to: %r', new_headers)                    
                    self._do_drupal_login(environ, drupal_session_id, new_headers)
                    log.debug('Headers on log-out log-in result: %r', new_headers)
                    return
                else:
	            log.debug('Drupal cookie session stayed as %r.', authtkt_drupal_session_id)
                    # Drupal cookie session matches the authtkt - leave user logged in
                    return
            else:
                # There's a Drupal cookie, but user is logged in as a normal CKAN user.
                # Ignore the Drupal cookie.
                return
        elif not drupal_session_id and is_ckan_cookie:
            # Deal with the case where user is logged out of Drupal
            # i.e. user WAS were logged in with Drupal and the cookie was
            # deleted (probably because Drupal logged out)
            
            # Is the logged in user a Drupal user?
            user_name = environ.get('REMOTE_USER', '')
            if user_name and user_name.startswith(self._user_name_prefix):
                log.debug('Was logged in as Drupal user %r but Drupal cookie no longer there.', user_name)
                self._log_out(environ, new_headers)

                
    def _do_drupal_login(self, environ, drupal_session_id, new_headers):
        if self.drupal_client is None:
            self.drupal_client = DrupalClient()
        # ask drupal for the drupal_user_id for this session
        drupal_user_id = self.drupal_client.get_user_id_from_session_id(drupal_session_id)
        if drupal_user_id:
            # see if user already exists in CKAN
            ckan_user_name = self._munge_drupal_id_to_ckan_user_name(drupal_user_id)
            from ckan import model
            from ckan.model.meta import Session
            query = Session.query(model.User).filter_by(name=unicode(ckan_user_name))
            if not query.count():
                # need to add this user to CKAN

                # ask drupal about this user
                user_properties = self.drupal_client.get_user_properties(drupal_user_id)
                date_created = datetime.datetime.fromtimestamp(int(user_properties['created']))
                user = model.User(
                    name=ckan_user_name, 
                    fullname=unicode(user_properties['name']),  # NB may change in Drupal db
                    about=u'User account imported from Drupal system.',
                    email=user_properties['mail'], # NB may change in Drupal db
                    created=date_created,
                )
                Session.add(user)
                Session.commit()
                log.debug('Drupal user added to CKAN as: %s', user.name)
            else:
                user = query.one()
                log.debug('Drupal user found in CKAN: %s', user.name)

            # Ask auth_tkt to remember this user so that subsequent requests
            # will be authenticated by auth_tkt.
            # auth_tkt cookie template needs to also go in the response.
            identity = {'repoze.who.userid': str(ckan_user_name),
                        'tokens': '',
                        'userdata': drupal_session_id}
            headers = environ['repoze.who.plugins']['dgu_auth_tkt'].remember(environ, identity)
            if headers:
                new_headers.extend(headers)

	    # Tell app during this request that the user is logged in
	    environ['REMOTE_USER'] = user.name
            log.debug('Set REMOTE_USER = %r', user.name)

            # e.g. new_header = [('Set-Cookie', 'bob=ab48fe; Path=/;')]
            #cookie_template = new_header[0][1].split('; ')

            # @@@ Need to add the headers to the request too so that the rest of the stack can sign the user in.

#Cookie: __utma=217959684.178461911.1286034407.1286034407.1286178542.2; __utmz=217959684.1286178542.2.2.utmcsr=google|utmccn=(organic)|utmcmd=organic|utmctr=coi%20london; DRXtrArgs=James+Gardner; DRXtrArgs2=3e174e7f1e1d3fab5ca138c0a023e13a; SESS9854522e7c5dba5831db083c5372623c=4160a72a4d6831abec1ac57d7b5a59eb; auth_tkt="a578c4a0d21bdbde7f80cd271d60b66f4ceabc3f4466!"; ckan_apikey="3a51edc6-6461-46b8-bfe2-57445cbdeb2b"; ckan_display_name="James Gardner"; ckan_user="4466"

            # There is a bug(/feature?) in line 628 of Cookie.py that means
            # it can't load from unicode strings. This causes Beaker to fail
            # unless the value here is a string
            #if not environ.get('HTTP_COOKIE'):
            #    environ['HTTP_COOKIE'] += str(cookie_string)
            #else:
            #    environ['HTTP_COOKIE'] = str(cookie_string[2:])

        else:
            log.info('Drupal disowned the session ID found in the cookie.')
