import re
import logging
import socket
from xmlrpclib import ServerProxy, Fault, ProtocolError
from xml.parsers.expat import ExpatError
from httplib import BadStatusLine

log = logging.getLogger(__name__)

class DrupalXmlRpcSetupError(Exception): pass
class DrupalRequestError(Exception): pass
class DrupalKeyError(Exception): pass

class DrupalClient(object):
    def __init__(self, xmlrpc_settings=None):
        '''If you do not supply xmlrpc settings then it looks them
        up in the pylons config.'''
        self.xmlrpc_url, self.xmlrpc_url_log_safe = DrupalClient.get_xmlrpc_url(xmlrpc_settings)
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
            xmlrpc_url_log_safe = re.sub(':([^@])[^@]*@', r':\1xxx@',
                                         xmlrpc_url)

        else:
            if xmlrpc_settings:
                domain = xmlrpc_settings.get('xmlrpc_domain')
                username = xmlrpc_settings.get('xmlrpc_username')
                password = xmlrpc_settings.get('xmlrpc_password')
            else:
                try:
                    from pylons import config
                except ImportError:
                    assert 0, 'Either supply XML RPC parameters or install pylons to try the Pylons config for it.'
                domain = config.get('dgu.xmlrpc_domain')
                username = config.get('dgu.xmlrpc_username')
                password = config.get('dgu.xmlrpc_password')
            if not domain:
                raise DrupalXmlRpcSetupError('Drupal XMLRPC not configured.')
            if username or password:
                server = '%s:%s@%s' % (username, password, domain)
                server_log_safe = '%s:%s%s@%s' % (username, password[:1], 'x' * (len(password)-1), domain)
            else:
                server = '%s' % domain
                server_log_safe = server
            xmlrpc_url_template = 'http://%s/services/xmlrpc'
            xmlrpc_url = xmlrpc_url_template % server
            xmlrpc_url_log_safe = xmlrpc_url_template % server_log_safe
        log.info('XMLRPC connection to %s', xmlrpc_url_log_safe)
        return xmlrpc_url, xmlrpc_url_log_safe

    def get_user_properties(self, user_id):
        '''Requests dict of properties of the Drupal user in the request.
        If no user is supplied in the request then the request is aborted.
        If the Drupal server is not configured then it raises.'''
        try:
            user_id_int = int(user_id)
        except ValueError, e:
            cls._abort_bad_request('user_id parameter must be an integer')
        try:
            user = self.drupal.user.retrieve(str(user_id))
        except socket.error, e:
            raise DrupalRequestError('Socket error with url \'%s\': %r' % (self.xmlrpc_url_log_safe, e))
        except Fault, e:
            raise DrupalRequestError('Drupal returned error for user_id %r: %r' % (user_id, e))
        except ProtocolError, e:
            raise DrupalRequestError('Drupal returned protocol error for user_id %r: %r' % (user_id, e))
        log.info('Obtained Drupal user: %r', unicode(user)[:200])
        return user

    def get_user_id_from_session_id(self, session_id):
        try:
            user_id = self.drupal.session.retrieve(session_id)
        except socket.error, e:
            raise DrupalRequestError('Socket error with url \'%s\': %r' % (self.xmlrpc_url_log_safe, e))
        except Fault, e:
            raise DrupalRequestError('Drupal returned error for session_id %r: %r' % (session_id, e))
        except ProtocolError, e:
            raise DrupalRequestError('Drupal returned protocol error for session_id %r: %r' % (session_id, e))
        except BadStatusLine, e:
            raise DrupalRequestError('Drupal returned bad status for session_id %r: %r' % (session_id, e))
        except ExpatError, e:
            raise DrupalRequestError('Drupal return value not XML for session_id %r: %r' % (session_id, e))
        log.info('Obtained Drupal user_id for session ID %r...: %r', session_id[:4], user_id)
        if str(user_id) == '0':
            # This is what Drupal (now) returns when the session_id is not valid
            return None
        return user_id

    def get_department_from_organisation(self, id):
        try:
            # Example response:
            #   {'11419': 'Department for Culture, Media and Sport'}
            dept_dict = self.drupal.organisation.department(str(id))
        except socket.error, e:
            raise DrupalRequestError('Socket error with url \'%s\': %r' % (self.xmlrpc_url_log_safe, e))
        except Fault, e:
            if e.faultCode == 404:
                raise DrupalKeyError(id)
            else:
                raise DrupalRequestError('Drupal returned error for organisation_id %r: %r' % (id, e))
        except ProtocolError, e:
            raise DrupalRequestError('Drupal returned protocol error for organisation_id %r: %r' % (id, e))
        if len(dept_dict) == 0:
            raise DrupalKeyError('No parent department for organisation_id %r' % id)
        if len(dept_dict) > 1:
            raise DrupalKeyError('Multiple parent departments for organisation_id %r: %r' % (id, dept_dict))
        department_id, department_name = dept_dict.items()[0]
        log.info('Obtained Drupal parent department %r (%s) from organisation %r', department_name, department_id, id)
        return department_id

    def get_organisation_name(self, id):
        try:
            organisation_name = self.drupal.organisation.one(str(id))
        except socket.error, e:
            raise DrupalRequestError('Socket error with url \'%s\': %r' % (self.xmlrpc_url_log_safe, e))
        except Fault, e:
            if e.faultCode == 404:
                raise DrupalKeyError(id)
            else:
                raise DrupalRequestError('Drupal returned error for organisation_id %r: %r' % (id, e))
        except ProtocolError, e:
            if e.errcode == 404:
                raise DrupalKeyError(id)
            else:
                raise DrupalRequestError('Drupal returned protocol error for organisation_id %r: %r' % (id, e))
        log.info('Obtained Drupal department %r from id %r', organisation_name, id)
        return organisation_name

    def match_organisation(self, organisation_name):
        try:
            organisation_id = self.drupal.organisation.match(organisation_name or u'')
        except socket.error, e:
            raise DrupalRequestError('Socket error with url \'%s\': %r' % (self.xmlrpc_url_log_safe, e))
        except Fault, e:
            if e.faultCode == 404:
                raise DrupalKeyError(organisation_name)
            else:
                raise DrupalRequestError('Drupal returned error for organisation_name %r: %r' % (organisation_name, e))
        except ProtocolError, e:
            if e.errcode == 404:
                raise DrupalKeyError(organisation_name)
            else:
                raise DrupalRequestError('Drupal returned protocol error for organisation_name %r: %r' % (organisation_name, e))
        log.info('Obtained organisation id %r from name %r', organisation_id, organisation_name)
        return organisation_id

    def get_organisation_list(self):
        try:
            organisations = self.drupal.publisher.list()
        except socket.error, e:
            raise DrupalRequestError('Socket error with url \'%s\': %r' % (self.xmlrpc_url_log_safe, e))
        except Fault, e:
            raise DrupalRequestError('Drupal returned error: %r' % (e))
        except ProtocolError, e:
            raise DrupalRequestError('Drupal returned protocol error: %r' % (e))
        log.info('Obtained organisation list %r', organisations)
        return organisations

    def get_organisation_details(self, organisation_id):
        try:
            organisation = self.drupal.publisher.details(organisation_id or u'')
        except socket.error, e:
            raise DrupalRequestError('Socket error with url \'%s\': %r' % (self.xmlrpc_url_log_safe, e))
        except Fault, e:
            if e.faultCode == 404:
                raise DrupalKeyError(organisation_id)
            else:
                raise DrupalRequestError('Drupal returned error for organisation_id %r: %r' % (organisation_id, e))
        except ProtocolError, e:
            if e.errcode == 404:
                raise DrupalKeyError(organisation_id)
            else:
                raise DrupalRequestError('Drupal returned protocol error for organisation_id %r: %r' % (organisation_id, e))
        log.info('Obtained organisation details %r from name %r', organisation, organisation_id)
        return organisation
