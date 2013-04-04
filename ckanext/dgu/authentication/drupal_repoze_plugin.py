from zope.interface import implements
from webob import Request, Response

from repoze.who.interfaces import IChallenger
from ckanext.dgu.plugins_toolkit import render

class DrupalLoginPlugin(object):

    implements(IChallenger)

    # Catches 401 redirects and sends user to Drupal log-in form
    def challenge(self, environ, status, app_headers, forget_headers):
        # redirect to login_form
        res = Response()
        res.status = 401
        res.unicode_body = render('not_authorized.html')
        #res.location = '/data/not_authorized' #self.login_form_url+"?%s=%s" %(self.came_from_field, request.url)
        return res
