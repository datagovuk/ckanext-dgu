import logging
import sys
import traceback
import socket
from xmlrpclib import ServerProxy, Fault

from pylons import config

from ckan.plugins.core import SingletonPlugin, implements
from ckan.plugins.interfaces import IRoutes
from ckan.lib.base import *
from ckan.lib.helpers import json
from ckanext.dgu.forms import harvest_source as harvest_source_form
import ckan.controllers.package
from ckan.lib.package_saver import WritePackageFromBoundFieldset
from ckan.lib.package_saver import ValidationException
from ckan.controllers.rest import BaseApiController, ApiVersion1, ApiVersion2

log = logging.getLogger(__name__)

class DrupalXmlRpcSetupError(Exception): pass
class DrupalRequestError(Exception): pass

class FormApi(SingletonPlugin):
    """
    Add the Form API used by Drupal into the Routing system
    """

    implements(IRoutes)

    def after_map(self, map):
        for version in ('', '1/'):
            map.connect('/api/%sform/package/create' % version,           controller='ckanext.dgu.forms.formapi:FormController', action='package_create')
            map.connect('/api/%sform/package/edit/:id' % version,         controller='ckanext.dgu.forms.formapi:FormController', action='package_edit')
            map.connect('/api/%sform/harvestsource/create' % version,     controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_create')
            map.connect('/api/%sform/harvestsource/edit/:id' % version,   controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_edit')
        map.connect('/api/2/form/harvestsource/create',   controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_create')
        map.connect('/api/2/form/harvestsource/edit/:id', controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_edit')
        map.connect('/api/2/form/package/create',         controller='ckanext.dgu.forms.formapi:Form2Controller', action='package_create')
        map.connect('/api/2/form/package/edit/:id',       controller='ckanext.dgu.forms.formapi:Form2Controller', action='package_edit')
        return map

    def before_map(self, map):
        return map

class ApiError(Exception):
    def __init__(self, status_int, msg):
        super(ApiError, self).__init__(msg)
        self.msg = msg
        self.status_int = status_int

# Todo: Refactor package form logic (to have more common functionality package_create and package_edit)

class BaseFormController(BaseApiController):
    """Implements the CKAN Forms API."""

    error_content_type = 'json'

    @classmethod
    def _abort_bad_request(cls, msg=None):
        error_msg = 'Bad request'
        if msg:
            error_msg += ': %s' % msg
        raise ApiError, (400, error_msg)
        
    @classmethod
    def _abort_not_authorized(cls):
        raise ApiError, (403, 'Not authorized')
        
    @classmethod
    def _abort_not_found(cls):
        raise ApiError, (404, 'Not found')
                    
    @classmethod
    def _assert_is_found(cls, entity):
        if entity is None:
            cls._abort_not_found()

    def _assert_authorization_credentials(self, entity=None):
        user = self._get_user_for_apikey()
        if not user:
            log.info('User did not supply authorization credentials when required.')
            self._abort_not_authorized()

    @classmethod
    def _get_drupal_xmlrpc_url(cls):
        if not hasattr(cls, '_xmlrpc_url'):
            domain = config.get('dgu.xmlrpc_domain')
            if not domain:
                raise DrupalXmlRpcSetupError('Drupal XMLRPC not configured.')
            username = config.get('dgu.xmlrpc_username')
            password = config.get('dgu.xmlrpc_password')
            if username or password:
                server = '%s:%s@%s' % (username, password, domain)
            else:
                server = '%s' % domain
            cls._xmlrpc_url = 'http://%s/services/xmlrpc' % server
            log.info('XMLRPC connection to %s', cls._xmlrpc_url)
        return cls._xmlrpc_url

    @classmethod
    def _get_drupal_user_properties(cls, user_id):
        '''Requests dict of properties of the Drupal user in the request.
        If no user is supplied in the request then the request is aborted.
        If the Drupal server is not configured then it raises.'''
        try:
            xmlrpc_url = cls._get_drupal_xmlrpc_url()
        except DrupalXmlRpcSetupError, e:
            raise DrupalRequestError('Cannot get user properties from Drupal: %r' % e)

        try:
            user_id_int = int(user_id)
        except ValueError, e:
            cls._abort_bad_request('user_id parameter must be an integer')
        drupal = ServerProxy(xmlrpc_url)
        try:
            user = drupal.user.get(user_id)
        except socket.error, e:
            raise DrupalRequestError('Socket error with url \'%s\': %r' % (xmlrpc_url, e))
        except Fault, e:
            raise DrupalRequestError('Drupal returned error for user_id %r: %r' % (user_id, e))
        log.info('Obtained Drupal user: %r' % user)
        return user

    @classmethod
    def _get_package_fieldset(cls):
        # Get user properties for the fieldset creation
        try:
            user_id = request.params['user_id']
        except KeyError, e:
            cls._abort_bad_request('Please supply a user_id parameter in the request parameters.')
        try:
            user = cls._get_drupal_user_properties(user_id)
        except DrupalRequestError, e:
            raise DrupalRequestError('Cannot get user properties (for publishers in the form): %s' % e)
        else:
            fieldset_params = {
                'user_name': unicode(user['name']),
                'publishers': user['publishers'],
                # At some point we can hard code restrict, but not until
                # we are fully onto gov3 form.
                #'restrict': True,
                }
        return super(BaseFormController, cls)._get_package_fieldset(**fieldset_params)

    def package_create(self):
        try:
            api_url = config.get('ckan.api_url', '/').rstrip('/')
            c.package_create_slug_api_url = \
                   api_url + h.url_for(controller='apiv2/package',
                                       action='create_slug')
            # Get the fieldset.
            fieldset = self._get_package_fieldset()
            if request.method == 'GET':
                # Render the fields.
                fieldset_html = fieldset.render()
                return self._finish_ok(fieldset_html, content_type='html')
            if request.method == 'POST':
                # Check user authorization.
                self._assert_authorization_credentials()
                # Read request.
                try:
                    request_data = self._get_request_data()
                except ValueError, error:
                    self._abort_bad_request('Extracting request data: %r' % error.args)                
                try:
                    form_data = request_data['form_data']
                except KeyError, error:
                    self._abort_bad_request('Missing \'form_data\' in request data.')
                # Bind form data to fieldset.
                try:
                    bound_fieldset = fieldset.bind(model.Package, data=form_data, session=model.Session)
                except Exception, error:
                    log.error('Package create - problem binding data. data=%r fieldset=%r', form_data, fields)
                    self._abort_bad_request('Form data incomplete')
                # Validate and save form data.
                log_message = request_data.get('log_message', 'Form API')
                author = request_data.get('author', '')
                user = self._get_user_for_apikey()
                if not author:
                    if user:
                        author = user.name
                try:
                    WritePackageFromBoundFieldset(
                        fieldset=bound_fieldset,
                        log_message=log_message, 
                        author=author,
                        client=c, 
                    )
                except ValidationException, exception:
                    # Get the errorful fieldset.
                    errorful_fieldset = exception.args[0]
                    # Render the fields.
                    fieldset_html = errorful_fieldset.render()
                    log.info('Package create - data did not validate. api_user=%r author=%r data=%r error=%r', user.name, author, form_data, errorful_fieldset.errors)
                    return self._finish(400, fieldset_html, content_type='html')
                else:
                    # Retrieve created pacakge.
                    package = bound_fieldset.model
                    # Construct access control entities.
                    self._create_permissions(package, user)
                    log.info('Package create successful. user=%r author=%r data=%r', user.name, author, form_data)
                    location = self._make_package_201_location(package)
                    return self._finish_ok(\
                        newly_created_resource_location=location)
        except ApiError, api_error:
            log.info('Package create - ApiError. user=%r author=%r data=%r error=%r',
                     user.name if 'user' in dir() else None,
                     author if 'author' in dir() else None,
                     form_data if 'form_data' in dir() else None,
                     api_error)
            return self._finish(api_error.status_int, str(api_error.msg),
                                content_type=self.error_content_type)
        except Exception:
            # Log error.
            log.error('Package create - unhandled exception: exception=%r', traceback.format_exc())
            raise

    @classmethod
    def _make_package_201_location(cls, package):
        location = '/api'
        location += cls._make_version_part()
        package_ref = cls._ref_package(package)
        location += '/rest/package/%s' % package_ref
        return location

    @classmethod
    def _make_harvest_source_201_location(cls, harvest_source):
        location = '/api'
        location += cls._make_version_part()
        source_ref = cls._ref_harvest_source(harvest_source)
        location += '/rest/harvestsource/%s' % source_ref
        return location

    @classmethod
    def _make_version_part(cls):
        part = ''
        is_version_in_path = False
        path_parts = request.path.split('/')
        if path_parts[2] == cls.api_version:
            is_version_in_path = True
        if is_version_in_path:
            part = '/%s' % cls.api_version
        return part

    def package_edit(self, id):
        try:
            # Find the entity.
            pkg = self._get_pkg(id)
            self._assert_is_found(pkg)
            # Get the fieldset.
            fieldset = self._get_package_fieldset()
            if request.method == 'GET':
                # Bind entity to fieldset.
                bound_fieldset = fieldset.bind(pkg)
                # Render the fields.
                fieldset_html = bound_fieldset.render()
                return self._finish_ok(fieldset_html, content_type='html')
            if request.method == 'POST':
                # Check user authorization.
                self._assert_authorization_credentials()
                # Read request.
                try:
                    request_data = self._get_request_data()
                except ValueError, error:
                    self._abort_bad_request('Extracting request data: %r' % error.args)
                try:
                    form_data = request_data['form_data']
                except KeyError, error:
                    self._abort_bad_request('Missing \'form_data\' in request data.')
                # Bind form data to fieldset.
                try:
                    bound_fieldset = fieldset.bind(pkg, data=form_data)
                    # Todo: Replace 'Exception' with bind error.
                except Exception, error:
                    log.error('Package edit - problem binding data. data=%r fieldset=%r', form_data, fields)
                    self._abort_bad_request('Form data incomplete')
                # Validate and save form data.
                log_message = request_data.get('log_message', 'Form API')
                author = request_data.get('author', '')
                user = self._get_user_for_apikey()
                if not author:
                    if user:
                        author = user.name
                try:
                    WritePackageFromBoundFieldset(
                        fieldset=bound_fieldset,
                        log_message=log_message, 
                        author=author,
                        client=c,
                    )
                except ValidationException, exception:
                    # Get the errorful fieldset.
                    errorful_fieldset = exception.args[0]
                    # Render the fields.
                    fieldset_html = errorful_fieldset.render()
                    log.info('Package edit - data did not validate. user=%r author=%r data=%r error=%r', user.name, author, form_data, errorful_fieldset.errors)
                    return self._finish(400, fieldset_html, content_type='html')
                else:
                    log.info('Package edit successful. user=%r author=%r data=%r', user.name, author, form_data)
                    return self._finish_ok()
        except ApiError, api_error:
            log.info('Package edit - ApiError. user=%r author=%r data=%r error=%r',
                     user.name if 'user' in dir() else None,
                     author if 'author' in dir() else None,
                     form_data if 'form_data' in dir() else None,
                     api_error)
            return self._finish(api_error.status_int, str(api_error.msg),
                                content_type=self.error_content_type)
        except Exception:
            # Log error.
            log.error('Package edit - unhandled exception: exception=%r', traceback.format_exc())
            raise

    @classmethod
    def _create_harvest_source_entity(cls, bound_fieldset, user_ref=None, publisher_ref=None):
        bound_fieldset.validate()
        if bound_fieldset.errors:
            raise ValidationException(bound_fieldset)
        bound_fieldset.sync()
        model.Session.commit()

    @classmethod
    def _create_permissions(cls, package, user):
        model.setup_default_user_roles(package, [user])
        model.repo.commit_and_remove()

    @classmethod
    def _update_harvest_source_entity(cls, id, bound_fieldset, user_ref, publisher_ref):
        bound_fieldset.validate()
        if bound_fieldset.errors:
            raise ValidationException(bound_fieldset)
        bound_fieldset.sync()
        model.Session.commit()

    def package_create_example(self):
        client_user = self._get_user(u'tester')
        api_key = client_user.apikey
        self.ckan_client = self._start_ckan_client(api_key=api_key)
        if request.method == 'GET':
            fieldset_html = self.ckan_client.package_create_form_get()
            if fieldset_html == None:
                raise Exception, "Can't read package create form??"
            form_html = '<form action="" method="post">' + fieldset_html + '<input type="submit"></form>'
        else:
            form_data = request.params.items()
            request_data = {
                'form_data': form_data,
                'log_message': 'Package create example...',
                'author': 'automated test suite',
            }
            form_html = self.ckan_client.package_create_form_post(request_data)
            if form_html == '""':
                form_html = "Submitted OK"
        page_html = '<html><head><title>My Package Create Page</title></head><body><h1>My Package Create Form</h1>%s</html>' % form_html
        return page_html

    def package_edit_example(self, id):
        client_user = self._get_user(u'tester')
        api_key = client_user.apikey
        self.ckan_client = self._start_ckan_client(api_key=api_key)
        if request.method == 'GET':
            fieldset_html = self.ckan_client.package_edit_form_get(id)
            if fieldset_html == None:
                raise Exception, "Can't read package edit form??"
            form_html = '<form action="" method="post">' + fieldset_html + '<input type="submit"></form>'
        else:
            form_data = request.params.items()
            request_data = {
                'form_data': form_data,
                'log_message': 'Package edit example...',
                'author': 'automated test suite',
            }
            form_html = self.ckan_client.package_edit_form_post(id, request_data)
            if form_html == '""':
                form_html = "Submitted OK"
        page_html = '<html><head><title>My Package Edit Page</title></head><body><h1>My Package Edit Form</h1>%s</html>' % form_html
        return page_html

    @classmethod
    def _start_ckan_client(cls, api_key, base_location='http://127.0.0.1:5000/api'):
        import ckanclient
        return ckanclient.CkanClient(base_location=base_location, api_key=api_key)

    def harvest_source_create(self):
        try:
            # Get the fieldset.
            fieldset = harvest_source_form.get_harvest_source_fieldset()
            if request.method == 'GET':
                # Render the fields.
                fieldset_html = fieldset.render()
                return self._finish_ok(fieldset_html, content_type='html')
            if request.method == 'POST':
                # Check user authorization.
                self._assert_authorization_credentials()
                # Read request.
                try:
                    request_data = self._get_request_data()
                except ValueError, error:
                    self._abort_bad_request('Extracting request data: %r' % error.args)                                    
                try:
                    form_data = request_data['form_data']
                    user_ref = request_data['user_ref']
                    publisher_ref = request_data['publisher_ref']
                except KeyError, error:
                    self._abort_bad_request()
                # Bind form data to fieldset.
                try:
                    bound_fieldset = fieldset.bind(model.HarvestSource, data=form_data, session=model.Session)
                except Exception, error:
                    # Todo: Replace 'Exception' with bind error.
                    self._abort_bad_request()
                # Validate and save form data.
                try:
                    self._create_harvest_source_entity(bound_fieldset, user_ref=user_ref, publisher_ref=publisher_ref)
                except ValidationException, exception:
                    # Get the errorful fieldset.
                    errorful_fieldset = exception.args[0]
                    # Render the fields.
                    fieldset_html = errorful_fieldset.render()
                    return self._finish(400, fieldset_html)
                else:
                    # Retrieve created harvest source entity.
                    source = bound_fieldset.model
                    # Set and store the non-form object attributes.
                    source.user_ref = user_ref
                    source.publisher_ref = publisher_ref
                    model.Session.add(source)
                    model.Session.commit()
                    # Set the response's Location header.
                    location = self._make_harvest_source_201_location(source)
                    return self._finish_ok(\
                        newly_created_resource_location=location)
        except ApiError, api_error:
            return self._finish(api_error.status_int, str(api_error.msg))
        except Exception:
            # Log error.
            log.error("Couldn't run create harvest source form method: %s" % traceback.format_exc())
            raise
        
    def harvest_source_edit(self, id):
        try:
            # Find the entity.
            entity = self._get_harvest_source(id)
            self._assert_is_found(entity)
            # Get the fieldset.
            fieldset = harvest_source_form.get_harvest_source_fieldset()
            if request.method == 'GET':
                # Bind entity to fieldset.
                bound_fieldset = fieldset.bind(entity)
                # Render the fields.
                fieldset_html = bound_fieldset.render()
                return self._finish_ok(fieldset_html, content_type='html')
            if request.method == 'POST':
                # Check user authorization.
                self._assert_authorization_credentials()
                # Read request.
                try:
                    request_data = self._get_request_data()
                except ValueError, error:
                    self._abort_bad_request('Extracting request data: %r' % error.args)                                    
                try:
                    form_data = request_data['form_data']
                    user_ref = request_data['user_ref']
                    publisher_ref = request_data['publisher_ref']
                except KeyError, error:
                    self._abort_bad_request()
                # Bind form data to fieldset.
                try:
                    bound_fieldset = fieldset.bind(entity, data=form_data)
                    # Todo: Replace 'Exception' with bind error.
                except Exception, error:
                    self._abort_bad_request()
                # Validate and save form data.
                log_message = request_data.get('log_message', 'Form API')
                author = request_data.get('author', '')
                if not author:
                    user = self._get_user_for_apikey()
                    if user:
                        author = user.name
                try:
                    self._update_harvest_source_entity(id, bound_fieldset, user_ref=user_ref, publisher_ref=publisher_ref)
                except ValidationException, exception:
                    # Get the errorful fieldset.
                    errorful_fieldset = exception.args[0]
                    # Render the fields.
                    fieldset_html = errorful_fieldset.render()
                    return self._finish(400, fieldset_html)
                else:
                    # Retrieve created harvest source entity.
                    source = bound_fieldset.model
                    # Set and store the non-form object attributes.
                    source.user_ref = user_ref
                    source.publisher_ref = publisher_ref
                    model.Session.add(source)
                    model.Session.commit()
                    return self._finish_ok()
        except ApiError, api_error:
            return self._finish(api_error.status_int, str(api_error.msg))
        except Exception:
            # Log error.
            log.error("Couldn't update harvest source: %s" % traceback.format_exc())
            raise

class FormController(ApiVersion1, BaseFormController):
    pass

class Form2Controller(ApiVersion2, BaseFormController):
    pass

