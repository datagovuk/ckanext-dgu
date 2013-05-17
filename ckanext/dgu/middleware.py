from pylons.controllers.util import abort

class BlockedUAMiddleware(object):
    """ Allows blocking of access based on partial user-agent strings 
        defined in config.

        dgu.blocked_ua = Firefox,Safari 
    """
    def __init__(self, app, config):
        self.app = app
        self.blocked = [s.strip() for s in config.get('dgu.blocked_ua','').split(',')]

    def __call__(self, environ, start_response):
        if self.blocked:
            ua = environ.get("HTTP_USER_AGENT")
            if ua:
                vals = filter(lambda x: x in ua, self.blocked)
                if any(vals):
                    abort(403)

        return self.app(environ, start_response)