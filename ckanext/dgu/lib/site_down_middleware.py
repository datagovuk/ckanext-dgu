from ckan.plugins import toolkit


class SiteDownMiddleware(object):
    def __init__(self, app, app_conf):
        self.app = app

    def __call__(self, environ, start_response):
        # Get basic pylons going manually, so that we can render
        self.app.setup_app_env(environ, start_response)
        start_response('503 Service Unavailable', [])
        return toolkit.render('data/site_down.html')
