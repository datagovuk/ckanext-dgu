import logging
import socket
from xmlrpclib import ServerProxy, Fault

from pylons import config
from webhelpers.text import truncate

log = logging.getLogger(__name__)

class DrupalXmlRpcSetupError(Exception): pass
class DrupalRequestError(Exception): pass
class DrupalKeyError(Exception): pass

class DrupalClient(object):
    def __init__(self, xmlrpc_settings=None):
        '''If you do not supply xmlrpc settings then it looks them
        up in the pylons config.'''
        self.xmlrpc_url = DrupalClient.get_xmlrpc_url(xmlrpc_settings)
        self.drupal = ServerProxy(self.xmlrpc_url)

    @staticmethod
    def get_xmlrpc_url(xmlrpc_settings=None):
        '''
        xmlrpc_settings is a dict. Either specify xmlrpc_url or
        xmlrpc_domain (and optionally xmlrpc_username and xmlrpc_password).
        If you do not supply xmlrpc settings then it looks them
        up in the pylons config.'''
        if xmlrpc_settings and xmlrpc_settings.get('xmlrpc_url'):
            xmlrpc_url = xmlrpc_settings['xmlrpc_url']
        else:
            if xmlrpc_settings:
                domain = xmlrpc_settings.get('xmlrpc_domain')
                username = xmlrpc_settings.get('xmlrpc_username')
                password = xmlrpc_settings.get('xmlrpc_password')
            else:
                domain = config.get('dgu.xmlrpc_domain')
                username = config.get('dgu.xmlrpc_username')
                password = config.get('dgu.xmlrpc_password')
            if not domain:
                raise DrupalXmlRpcSetupError('Drupal XMLRPC not configured.')
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
        log.info('Obtained Drupal user: %r', truncate(unicode(user), 200))
        return user

    def get_department_from_publisher(self, id):
        try:
            department = self.drupal.organisation.department(str(id))
        except socket.error, e:
            raise DrupalRequestError('Socket error with url \'%s\': %r' % (self.xmlrpc_url, e))
        except Fault, e:
            raise DrupalRequestError('Drupal returned error for user_id %r: %r' % (id, e))
        log.info('Obtained Drupal department %r from publisher %r', department, id)
        return department

    def get_organisation_name(self, id):
        try:
            organisation_name = self.drupal.organisation.one(str(id))
        except socket.error, e:
            raise DrupalRequestError('Socket error with url \'%s\': %r' % (self.xmlrpc_url, e))
        except Fault, e:
            if e.faultCode == 404:
                raise DrupalKeyError(id)
            else:
                raise DrupalRequestError('Drupal returned error for user_id %r: %r' % (id, e))
        log.info('Obtained Drupal department %r from id %r', organisation_name, id)
        return organisation_name

    def match_organisation(self, organisation_name):
        try:
            organisation_id = self.drupal.organisation.match(organisation_name or u'')
        except socket.error, e:
            raise DrupalRequestError('Socket error with url \'%s\': %r' % (self.xmlrpc_url, e))
        except Fault, e:
            if e.faultCode == 404:
                raise DrupalKeyError(id)
            else:
                raise DrupalRequestError('Drupal returned error for user_id %r: %r' % (id, e))
        log.info('Obtained organisation id %r from name %r', organisation_id, organisation_name)
        return organisation_id
