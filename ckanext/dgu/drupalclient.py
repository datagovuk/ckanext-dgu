import logging
import socket
from xmlrpclib import ServerProxy, Fault

from pylons import config

log = logging.getLogger(__name__)

class DrupalXmlRpcSetupError(Exception): pass
class DrupalRequestError(Exception): pass

class DrupalClient(object):
    def __init__(self):
        self.xmlrpc_url = DrupalClient.get_xmlrpc_url()
        self.drupal = ServerProxy(self.xmlrpc_url)

    @staticmethod
    def get_xmlrpc_url():
        domain = config.get('dgu.xmlrpc_domain')
        if not domain:
            raise DrupalXmlRpcSetupError('Drupal XMLRPC not configured.')
        username = config.get('dgu.xmlrpc_username')
        password = config.get('dgu.xmlrpc_password')
        if username or password:
            server = '%s:%s@%s' % (username, password, domain)
        else:
            server = '%s' % domain
        xmlrpc_url = 'http://%s/services/xmlrpc' % server
        log.info('XMLRPC connection to %s', xmlrpc_url)
        return xmlrpc_url

    def get_user_properties(self, user_id):
        '''Requests dict of properties of the Drupal user in the request.
        If no user is supplied in the request then the request is aborted.
        If the Drupal server is not configured then it raises.'''
        try:
            user_id_int = int(user_id)
        except ValueError, e:
            cls._abort_bad_request('user_id parameter must be an integer')
        try:
            user = self.drupal.user.get(user_id)
        except socket.error, e:
            raise DrupalRequestError('Socket error with url \'%s\': %r' % (self.xmlrpc_url, e))
        except Fault, e:
            raise DrupalRequestError('Drupal returned error for user_id %r: %r' % (user_id, e))
        log.info('Obtained Drupal user: %r' % user)
        return user

    def get_department_from_publisher(self, id):
        try:
            department = self.drupal.organisation.department(id)
        except socket.error, e:
            raise DrupalRequestError('Socket error with url \'%s\': %r' % (self.xmlrpc_url, e))
        except Fault, e:
            raise DrupalRequestError('Drupal returned error for user_id %r: %r' % (id, e))
        log.info('Obtained Drupal department %r from publisher %r', department, id)
        return department
