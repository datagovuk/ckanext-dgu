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

    application = loadapp('config:%s' % config_filepath)
    from ckanext.dgu.bin.url_space_sharer import UrlSpaceSharer
    application = UrlSpaceSharer(application)

If log_as_errors is set to True, this middleware logs to the ``wsgi.errors`` log.

'''

class UrlSpaceSharer(object):
    def __init__(self, app, log_as_errors=False):
        self.app = app
        self.log_as_errors = log_as_errors

    def __call__(self, environ, start_response):
        if self.log_as_errors:
            environ['wsgi.errors'].write('Orig PATH_INFO: %r ' % environ.get('PATH_INFO'))
            environ['wsgi.errors'].write('Orig SCRIPT_NAME: %r ' % environ.get('SCRIPT_NAME'))
            
        new_path = environ['SCRIPT_NAME'] + environ['PATH_INFO']
        if new_path != '/':
            new_path = new_path.rstrip('/')
        environ['PATH_INFO'] = new_path
        environ['SCRIPT_NAME'] = ''

        if self.log_as_errors:
            environ['wsgi.errors'].write('New PATH_INFO: %r ' % environ.get('PATH_INFO'))
        return self.app(environ, start_response)

