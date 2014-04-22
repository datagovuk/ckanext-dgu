'''Derived from auth_tkt.py from repoze.who.plugins
DGU modifications:
* requests to remember() from repoze.who are ignored if we are logged
  in to Drupal

'''
import sys
import logging
import os

from repoze.who.plugins.auth_tkt import AuthTktCookiePlugin, _bool

log = logging.getLogger(__name__)

class DGUAuthTktCookiePlugin(AuthTktCookiePlugin):
    # IIdentifier
    def remember(self, environ, identity):
        from pylons import config
        if 'dgu_drupal_auth' in config['ckan.plugins']:
            caller = self.who_called_me(2)
            if caller == ('drupal_auth.py', '_do_drupal_login'):
                # Remember Drupal logins
                log.info('Remembering Drupal identity')
                return super(DGUAuthTktCookiePlugin, self).remember(environ, identity)
            elif caller == ('middleware.py', '__call__'):
                user_id = dict(identity)['repoze.who.userid']
                if user_id.startswith('user_d'):
                    log.debug('Ignoring middleware request to remember Drupal login: %r', user_id)
                else:
                    log.info('Remembering non-Drupal identity %r', user_id)
                    return super(DGUAuthTktCookiePlugin, self).remember(environ, identity)
            else:
                log.error('I do not recognise the caller %r, so not remembering identity', caller)
        else:
            #log.debug('Drupal auth disabled')
            return super(DGUAuthTktCookiePlugin, self).remember(environ, identity)

    def who_called_me(self, n=0):
        frame = sys._getframe(n)
        c = frame.f_code
        return os.path.basename(c.co_filename), c.co_name

def make_plugin(secret=None,
                secretfile=None,
                cookie_name='auth_tkt',
                secure=False,
                include_ip=False,
                timeout=None,
                reissue_time=None,
                userid_checker=None,
               ):
    from repoze.who.utils import resolveDotted
    if (secret is None and secretfile is None):
        raise ValueError("One of 'secret' or 'secretfile' must not be None.")
    if (secret is not None and secretfile is not None):
        raise ValueError("Specify only one of 'secret' or 'secretfile'.")
    if secretfile:
        secretfile = os.path.abspath(os.path.expanduser(secretfile))
        if not os.path.exists(secretfile):
            raise ValueError("No such 'secretfile': %s" % secretfile)
        secret = open(secretfile).read().strip()
    if timeout:
        timeout = int(timeout)
    if reissue_time:
        reissue_time = int(reissue_time)
    if userid_checker is not None:
        userid_checker = resolveDotted(userid_checker)
    plugin = DGUAuthTktCookiePlugin(secret,
                                 cookie_name,
                                 _bool(secure),
                                 _bool(include_ip),
                                 timeout,
                                 reissue_time,
                                 userid_checker,
                                 )
    return plugin
