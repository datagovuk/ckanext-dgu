class SiteDownMiddleware(object):
    def __init__(self, app, app_conf):
        pass

    def __call__(self, environ, start_response):
        start_response('503 Service Unavailable', [])
        return '<h1>Site Maintenance</h1><p>The data.gov.uk data catalogue is currently down for maintenance</p>'

