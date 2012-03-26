'''
URL Space Sharer

WSGI middleware to enabled CKAN to share Apache config with another
application. You can specify which URL paths get directed to CKAN and the
remainder can be picked up by another application, such as Drupal.

i.e. allows requests to /dataset and /publishers to be sent to CKAN, while
those to /index.html go to Drupal, say.

This is different to mounting CKAN at a sub-URL, where all CKAN urls have to
have a specific prefix (e.g. /data) so that you get datasets at /data/datasets.

To use this middleware:

1. In your Apache you specify WSGIScriptAlias for all
URLs you want directed to CKAN::

  WSGIScriptAlias /dataset ckan.py
  WSGIScriptAlias /publisher ckan.py
  WSGIScriptAlias /css ckan.py
  
2. Enable this middleware in ``ckan.py`` by wrapping your ``application``
object like this::

    application = UrlSpaceSharer(application)

This middleware logs to the ``wsgi.errors`` log.

'''

class UrlSpaceSharer(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        #environ['wsgi.errors'].write('Orig PATH_INFO: %s' % environ.get('PATH_INFO'))
        #environ['wsgi.errors'].write('Orig SCRIPT_NAME: %s' % environ.get('SCRIPT_NAME'))
        environ['PATH_INFO'] = environ['SCRIPT_NAME'] + environ['PATH_INFO']
        environ['SCRIPT_NAME'] = ''
        #environ['wsgi.errors'].write('New PATH_INFO: %s' % environ.get('PATH_INFO'))
        return self.app(environ, start_response)

