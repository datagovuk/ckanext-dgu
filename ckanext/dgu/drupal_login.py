import Cookie
import logging

from zope.interface import implements
from repoze.who.interfaces import IChallenger, IIdentifier, IChallengeDecider, IAuthenticator, IMetadataProvider

from ckanext.dgu.drupalclient import DrupalClient, DrupalXmlRpcSetupError, \
     DrupalRequestError

log = logging.getLogger(__name__)

class DrupalLoginPlugin(object):
    '''Allows CKAN user to login via Drupal. It looks for the Drupal cookie
    and gets user details from Drupal using XMLRPC. It is a repoze.who plugin
    so works side-by-side with normal CKAN logins.'''
    implements(IIdentifier, IAuthenticator)

    drupal_client = None

    # IIdentifier
    def identify(self, environ):
        # check for Drupal cookie exists or not
        drupal_session_id = self.get_drupal_session_id_from_cookie(environ)
        return {'drupal_session_id': drupal_session_id} if drupal_session_id else None

    def get_drupal_session_id_from_cookie(self, environ):
        drupal_session_id = [False]
        for k, v in environ.items():
            key = k.lower()
            if key  == 'http_cookie':
                drupal_session_id[0] = self.drupal_cookie_parse(v)
        drupal_session_id = drupal_session_id[0]
        return drupal_session_id

    def drupal_cookie_parse(self, cookie_string):
        '''Returns the Drupal Session ID from the cookie string.'''
        cookies = Cookie.SimpleCookie()
        cookies.load(str(cookie_string))
        for cookie in cookies:
            if cookie.startswith('SESS'):
                log.debug('Drupal cookie found')
                return cookies[cookie].value
        return None

    def remember(self, environ, identity):
        # just using authtkt?
        rememberer = self._get_rememberer(environ)
        return rememberer.remember(environ, identity)

    def forget(self, environ, identity):
        rememberer = self._get_rememberer(environ)
        return rememberer.forget(environ, identity)

    def _get_rememberer(self, environ):
        rememberer = environ['repoze.who.plugins']['auth_tkt']
        return rememberer

    # IAuthenticator
    def authenticate(self, environ, identity):
        if not identity.get('drupal_session_id'):
            return
        
        # get info about the user from drupal
        if self.drupal_client is None:
            self.drupal_client = DrupalClient()
        drupal_user_id = self.drupal_client.get_user_id_from_session_id(identity['drupal_session_id'])
        if not drupal_user_id:
            log.info('Drupal disowned the session ID found in the cookie.')
            return None
        user_properties = self.drupal_client.get_user_properties(drupal_user_id)
        log.debug('Drupal user is: %s (%i)', user_properties.get('name'), user_properties.get('uid'))

        # Store user properties in environment (why?)
        #environ['drupal.uid'] = user_properties['uid']
        #environ['drupal.publishers'] = user_properties['publishers']
        #environ['drupal.name'] = user_properties['name']

        from ckan import model
        from ckan.model.meta import Session

        def munge_drupal_id_to_ckan_user_name(drupal_id):
            drupal_id.lower().replace(' ', '_')
            return u'drupal_%s' % drupal_id
        ckan_user_name = munge_drupal_id_to_ckan_user_name(user_properties['uid'])

        # Add the new Drupal user if they don't already exist.
        query = Session.query(model.User).filter_by(name=unicode(ckan_user_name))
        if not query.count():
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
        
        return user.name
