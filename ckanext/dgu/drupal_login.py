#repoze.who plugin

from repoze.who.interfaces import IChallenger, IIdentifier, IChallengeDecider, IAuthenticator, IMetadataProvider


class DrupalLoginPlugin(object):
    '''Allows CKAN user to login via Drupal. It looks for the Drupal cookie
    and gets user details from Drupal using XMLRPC. It is a repoze.who plugin
    so works side-by-side with normal CKAN logins.'''
    implements(IIdentifier, IAuthenticator)

    def __init__(self, app, app_conf):
        self.app = app
        self.drupal_client = None

    # IIdentifier
    def identify(environ):
        # check for Drupal cookie exists or not
        drupal_session_id = self.get_drupal_session_id_from_cookie()
        return {'drupal': True} if drupal_session_id else None

    def get_drupal_session_id_from_cookie(self):
        drupal_session_id = [False]
        for k, v in environ.items():
            key = k.lower()
            if key  == 'http_cookie':
                drupal_session_id[0] = drupal_cookie_parse(v)
        drupal_session_id = drupal_session_id[0]
        return drupal_session_id

    def drupal_cookie_parse(self, cookie_string):
        '''Returns the Drupal Session ID from the cookie string.'''
        cookies = Cookie.SimpleCookie()
        cookies.load(str(cookie_string))
        for cookie in cookies:
            if cookie.startswith('SESS'):
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
        rememberer = environ['repoze.who.plugins'][self.rememberer_name]
        return rememberer

    # IAuthenticator
    def authenticate(environ, identity):
        if not identity.get('drupal'):
            return
        
        # get info about the user from drupal
        if self.drupal_client is None:
            self.drupal_client = DrupalClient()
        drupal_user_id = self.drupal_client.get_user_id_from_session_id(drupal_session_id)
        if not drupal_user_id:
            return None
        user_properties = self.drupal_client.get_user_properties(drupal_user_id)

        # Store user properties in environment (why?)
        #environ['drupal.uid'] = user_properties['uid']
        #environ['drupal.publishers'] = user_properties['publishers']
        #environ['drupal.name'] = user_properties['name']

        from ckan import model
        from ckan.model.meta import Session

        def munge(username):
            username.lower().replace(' ', '_')
            return username

        # Add the new Drupal user if they don't already exist.
        query = Session.query(model.User).filter_by(name=unicode(user_properties['uid']))
        if not query.count():
            user = model.User(
                name=munge(unicode(user_properties['drupal.uid'])), 
                fullname=unicode(user_properties['drupal.name']), 
                about=u'Drupal auto-generated user',
                #email too would be good
            )
            Session.add(user)
            Session.commit()
        else:
            user = query.one()
        
        return user.name
