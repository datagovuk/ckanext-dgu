import Cookie
import logging

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
        self._user_name_prefix = 'drupal_'

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

    def __call__(self, environ, start_response):
        is_ckan_cookie, drupal_session_id = self._parse_cookies()

        new_start_response = start_response
        # only think about doing this Drupal login if CKAN is not already
        # logged in (i.e. presence of an auth_tkt cookie, which indicates
        # user has logged in either normally or from this function already)
        if drupal_session_id and not is_ckan_cookie:
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

                    user = model.User(
                        name=ckan_user_name, 
                        fullname=unicode(user_properties['name']), 
                        about=u'Drupal auto-generated user',
                        #email too would be good but is not provided
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
                identity = {'repoze.who.userid': environ['drupal.uid'],
                            'tokens': '',
                            'userdata': ''}
                new_header = environ['repoze.who.plugins']['auth_tkt'].remember(environ, identity)
                # e.g. new_header = [('Set-Cookie', 'bob=ab48fe; Path=/;')]
                cookie_template = new_header[0][1].split('; ')

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
            else:
                log.info('Drupal disowned the session ID found in the cookie.')

        # The case when we were logged in with Drupal and the cookie was
        # deleted (probably because Drupal logged out)
        if not drupal_session_id and is_ckan_cookie:
            # Is the logged in user a Drupal user?
            user_name = request.environ.get('REMOTE_USER', '')
            if user_name.startswith(self._user_name_prefix):
                # don't progress the user info for this request
                request['REMOTE_USER'] = None
                # tell auth_tkt to logout whilst adding the header to tell
                # the browser to delete the cookie
                identity = {'repoze.who.userid': environ['drupal.uid'],
                            'tokens': '',
                            'userdata': ''}
                new_header = environ['repoze.who.plugins']['auth_tkt'].forget(environ, identity)
                def cookie_setting_start_response(status, headers, exc_info=None):
                    headers += new_header
                    return start_response(status, headers, exc_info)
                new_start_response = cookie_setting_start_response
                
        return self.app(environ, new_start_response)

