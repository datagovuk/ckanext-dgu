'''Derived from auth_tkt.py from repoze.who.plugins
DGU modifications:
* requests to remember() from repoze.who are ignored if we are logged
  in to Drupal

'''
import sys
import logging

from repoze.who.plugins.auth_tkt import AuthTktCookiePlugin

log = logging.getLogger(__name__)

class DGUAuthTktCookiePlugin(AuthTktCookiePlugin):
    # IIdentifier
    def remember(self, environ, identity):
        log.warn('WHO CALLED %r', self.who_called_me(1))
        log.warn('IDENTITY %r', identity)
        AuthTktCookiePlugin.remember(environ, identity)

    def who_called_me(self, n=0):
        frame = sys._getframe(n)
        c = frame.f_code
        return c.co_filename, c.co_name
