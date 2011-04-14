import logging
import sys
import traceback

from pylons import config

from ckan.lib.base import *
from ckan.lib.helpers import json
import ckan.controllers.package
from ckan.lib.package_saver import WritePackageFromBoundFieldset
from ckan.lib.package_saver import ValidationException
from ckan.controllers.rest import BaseApiController, ApiVersion1, ApiVersion2

from ckanext.dgu.forms import harvest_source as harvest_source_form
from ckanext.dgu.drupalclient import DrupalClient, DrupalXmlRpcSetupError, \
     DrupalRequestError

from ckanext.harvest.model import HarvestSource
from ckanext.harvest.lib import get_harvest_sources, get_harvest_source, \
                                remove_harvest_source,create_harvest_job

import html
from genshi.input import HTML
from genshi.filters import Transformer

log = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(self, status_int, msg):
        super(ApiError, self).__init__(msg)
        self.msg = msg
        self.status_int = status_int

class BaseFormController(BaseApiController):
    """Implements the CKAN Forms API."""

    error_content_type = 'json'
    authorizer = ckan.authz.Authorizer()

    @classmethod
    def _abort_bad_request(cls, msg=None):
        error_msg = 'Bad request'
        if msg:
            error_msg += ': %s' % msg
        raise ApiError, (400, error_msg)

    @classmethod
    def _abort_not_authorized(cls, msg=None):
        error_msg = 'Not authorized'
        if msg:
            error_msg += ': %s' % msg
        raise ApiError, (403, error_msg)

    @classmethod
    def _abort_not_found(cls):
        raise ApiError, (404, 'Not found')

    @classmethod
    def _assert_is_found(cls, entity):
        if entity is None:
            cls._abort_not_found()

    def _get_required_authorization_credentials(self, entity=None):
        user = self._get_user_for_apikey()
        if not user:
            log.info('User did not supply authorization credentials when required.')
            self._abort_not_authorized()
        return user

    @classmethod
    def _drupal_client(cls):
        if not hasattr(cls, '_drupal_client_cache'):
            cls._drupal_client_cache = DrupalClient()
        return cls._drupal_client_cache

    @classmethod
    def _get_package_fieldset(cls):
        # Get user properties for the fieldset creation
        try:
            user_id = request.params['user_id']
        except KeyError, e:
            cls._abort_bad_request('Please supply a user_id parameter in the request parameters.')
        try:
            user = cls._drupal_client().get_user_properties(user_id)
        except DrupalRequestError, e:
            raise DrupalRequestError('Cannot get user properties (for publishers in the form): %s' % e)
        else:
            fieldset_params = {
                'user_name': unicode(user['name']),
                'publishers': user['publishers'],
                # restrict national_statistic field - only for edit on ckan
                'restrict': True,
                }
        return super(BaseFormController, cls)._get_package_fieldset(**fieldset_params)

    @classmethod
    def _ref_harvest_source(cls, harvest_source):
        return getattr(harvest_source, 'id')

    # Todo: Refactor package form logic (to have more common functionality
    # between package_create and package_edit)
    def package_create(self):
        try:
            # Check user authorization.
            user = self._get_required_authorization_credentials()
            am_authz = self.authorizer.is_authorized(user.name, model.Action.PACKAGE_CREATE, model.System())
            if not am_authz:
                self._abort_not_authorized('User %r not authorized to create packages' % user.name)

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
        except DrupalRequestError, e:
            log.error('Package create - DrupalRequestError: exception=%r', traceback.format_exc())
            raise
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

            # Check user authorization.
            user = self._get_required_authorization_credentials()
            am_authz = self.authorizer.is_authorized(user.name, model.Action.EDIT, pkg)
            if not am_authz:
                self._abort_not_authorized('User %r not authorized to edit %r' % (user.name, pkg.name))

            # Get the fieldset.
            fieldset = self._get_package_fieldset()
            if request.method == 'GET':
                # Bind entity to fieldset.
                bound_fieldset = fieldset.bind(pkg)
                # Render the fields.
                fieldset_html = bound_fieldset.render()
                return self._finish_ok(fieldset_html, content_type='html')
            if request.method == 'POST':
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
        except DrupalRequestError, e:
            log.error('Package edit - DrupalRequestError: exception=%r', traceback.format_exc())
            raise
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
    def _create_harvest_source_entity(cls, bound_fieldset, user_id=None, publisher_id=None):
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
    def _update_harvest_source_entity(cls, id, bound_fieldset, user_id=None, publisher_id=None):
        bound_fieldset.validate()
        if bound_fieldset.errors:
            raise ValidationException(bound_fieldset)
        bound_fieldset.sync()
        model.Session.commit()

    def _get_harvest_source(self, id):
        obj = HarvestSource.get(id, default=None)
        return obj

    def harvest_source_list(self):
        try:
            # Check user authorization.
            user = self._get_required_authorization_credentials()
            am_authz = self.authorizer.is_sysadmin(user.name) # simple for now
            if not am_authz:
                self._abort_not_authorized('User %r not authorized for harvesting' % user.name)
            
            objects = get_harvest_sources()
            response_data = [o['id'] for o in objects]
            return self._finish_ok(response_data)
        except ApiError, api_error:
            return self._finish(api_error.status_int, str(api_error.msg))
        except Exception:
            # Log error.
            log.error("Couldn't run list harvest source form method: %s" % traceback.format_exc())
            raise

    def harvest_source_view(self, id):
        try:
            # Check user authorization.
            user = self._get_required_authorization_credentials()
            am_authz = self.authorizer.is_sysadmin(user.name) # simple for now
            if not am_authz:
                self._abort_not_authorized('User %r not authorized for harvesting' % user.name)

            source = get_harvest_source(id,default=None)
            if source is None:
                response.status_int = 404
                return 'Not found'

            return self._finish_ok(source)
        except ApiError, api_error:
            return self._finish(api_error.status_int, str(api_error.msg))
        except Exception:
            # Log error.
            log.error("Couldn't run view harvest source form method: %s" % traceback.format_exc())
            raise

    def harvest_source_create(self):
        try:
            # Check user authorization.
            user = self._get_required_authorization_credentials()
            am_authz = self.authorizer.is_sysadmin(user.name) # simple for now
            if not am_authz:
                self._abort_not_authorized('User %r not authorized for harvesting' % user.name)

            # Get the fieldset.
            fieldset = harvest_source_form.get_harvest_source_fieldset()
            if request.method == 'GET':
                # Render the fields.
                fieldset_html = fieldset.render()
                return self._finish_ok(fieldset_html, content_type='html')
            if request.method == 'POST':
                # Read request.
                try:
                    request_data = self._get_request_data()
                except ValueError, error:
                    self._abort_bad_request('Extracting request data: %r' % error.args)
                try:
                    form_data = request_data['form_data']
                    user_id = request_data['user_id']
                    publisher_id = request_data['publisher_id']
                except KeyError, error:
                    self._abort_bad_request()
                if isinstance(form_data, list):
                    form_data = dict(form_data)
                # Bind form data to fieldset.
                try:
                    form_data['HarvestSource--url'] = form_data.get('HarvestSource--url', '').strip()
                    bound_fieldset = fieldset.bind(HarvestSource, data=form_data, session=model.Session)
                except Exception, error:
                    # Todo: Replace 'Exception' with bind error.
                    self._abort_bad_request()
                # Validate and save form data.
                try:
                    self._create_harvest_source_entity(bound_fieldset, user_id=user_id, publisher_id=publisher_id)
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
                    source.user_id = user_id
                    source.publisher_id = publisher_id
                    model.Session.add(source)

                    # Also create a job
                    job = create_harvest_job(source.id)

                    # Save changes
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

    def harvesting_job_create(self):
        try:
            # Check user authorization.
            user = self._get_required_authorization_credentials()
            am_authz = self.authorizer.is_sysadmin(user.name) # simple for now
            if not am_authz:
                self._abort_not_authorized('User %r not authorized for harvesting' % user.name)

            # Read request.
            try:
                request_data = self._get_request_data()
            except ValueError, error:
                self._abort_bad_request('Extracting request data: %r' % error.args)
            try:
                source_id = request_data['source_id']
            except KeyError, error:
                self._abort_bad_request()

            err_msg = None
            try:
                job = create_harvest_job(source_id)
            except Exception, e:
                err_msg = str(e)

            if err_msg:
                self.log.debug(err_msg)
                response.status_int = 400
                response.headers['Content-Type'] = self.content_type_json
                return json.dumps(err_msg)
            else:
                return self._finish_ok(job)
        except ApiError, api_error:
            return self._finish(api_error.status_int, str(api_error.msg))
        except Exception:
            # Log error.
            log.error("Couldn't run create harvesting job form method: %s" % traceback.format_exc())
            raise

    def harvest_source_delete(self, id):
        try:
            model.repo.new_revision()
            # Check user authorization.
            user = self._get_required_authorization_credentials()
            am_authz = self.authorizer.is_sysadmin(user.name) # simple for now
            if not am_authz:
                self._abort_not_authorized('User %r not authorized for harvesting' % user.name)
            
            # Sources are not longer deleted, just inactivated
            err_msg = None
            try:
                remove_harvest_source(id)
            except Exception,e:
                err_msg = str(e)

            if err_msg:
                self.log.debug(err_msg)
                response.status_int = 400
                response.headers['Content-Type'] = self.content_type_json
                return json.dumps(err_msg)
            else:
                return self._finish_ok()

        except ApiError, api_error:
            return self._finish(api_error.status_int, str(api_error.msg))
        except Exception:
            # Log error.
            log.error("Couldn't run delete harvest source form method: %s" % traceback.format_exc())
            raise

    def harvest_source_edit(self, id):
        try:
            # Check user authorization.
            user = self._get_required_authorization_credentials()
            am_authz = self.authorizer.is_sysadmin(user.name) # simple for now
            if not am_authz:
                self._abort_not_authorized('User %r not authorized for harvesting' % user.name)

            # Find the entity.
            entity = self._get_harvest_source(id)
            if entity is None:
                self._abort_not_found()


            # Get the fieldset.
            fieldset = harvest_source_form.get_harvest_source_fieldset()
            if request.method == 'GET':
                # Bind entity to fieldset.
                bound_fieldset = fieldset.bind(entity)
                # Render the fields.
                fieldset_html = bound_fieldset.render()
                return self._finish_ok(fieldset_html, content_type='html')
            if request.method == 'POST':
                # Read request.
                try:
                    request_data = self._get_request_data()
                except ValueError, error:
                    self._abort_bad_request('Extracting request data: %r' % error.args)
                try:
                    form_data = request_data['form_data']
                    user_id = request_data['user_id']
                    publisher_id = request_data['publisher_id']
                except KeyError, error:
                    self._abort_bad_request()
                if isinstance(form_data, list):
                    form_data = dict(form_data)
                # Bind form data to fieldset.
                try:
                    form_data['HarvestSource--url'] = form_data.get('HarvestSource--url', '').strip()
                    form_data['HarvestSource--type'] = form_data.get('HarvestSource--type', '').strip()
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
                    self._update_harvest_source_entity(id, bound_fieldset, user_id=user_id, publisher_id=publisher_id)
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
                    source.user_id = user_id
                    source.publisher_id = publisher_id
                    source.save()
                    return self._finish_ok()
        except ApiError, api_error:
            return self._finish(api_error.status_int, str(api_error.msg))
        except Exception:
            # Log error.
            log.error("Couldn't update harvest source: %s" % traceback.format_exc())
            raise

    def get_department_from_publisher(self, id):
        try:
            department = BaseFormController._drupal_client().get_department_from_publisher(id)
        except DrupalRequestError, e:
            abort(500, 'Error making internal request: %r' % e)
        return self._finish_ok(department)


class FormController(ApiVersion1, BaseFormController):
    pass

class Form2Controller(ApiVersion2, BaseFormController):
    pass

