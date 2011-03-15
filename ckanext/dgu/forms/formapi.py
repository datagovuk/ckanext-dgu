import logging
import sys
import traceback

from pylons import config

from ckan.plugins.core import SingletonPlugin, implements
from ckan.plugins import IRoutes
from ckan.plugins import IConfigurer
from ckan.plugins import IGenshiStreamFilter

from ckan.lib.base import *
from ckan.lib.helpers import json
import ckan.controllers.package
from ckan.lib.package_saver import WritePackageFromBoundFieldset
from ckan.lib.package_saver import ValidationException
from ckan.controllers.rest import BaseApiController, ApiVersion1, ApiVersion2

import ckanext.dgu
from ckanext.dgu.forms import harvest_source as harvest_source_form
from ckanext.dgu.drupalclient import DrupalClient, DrupalXmlRpcSetupError, \
     DrupalRequestError

from ckanext.harvest.model import HarvestSource, HarvestingJob,HarvestedDocument
log = logging.getLogger(__name__)

class FormApi(SingletonPlugin):
    """
    Add the Form API used by Drupal into the Routing system
    """

    implements(IRoutes)
    implements(IConfigurer)
    implements(IGenshiStreamFilter)

    def before_map(self, map):
        for version in ('', '1/'):
            map.connect('/api/%sform/package/create' % version, controller='ckanext.dgu.forms.formapi:FormController', action='package_create')
            map.connect('/api/%sform/package/edit/:id' % version, controller='ckanext.dgu.forms.formapi:FormController', action='package_edit')
            map.connect('/api/%sform/harvestsource/create' % version, controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_create')
            map.connect('/api/%sform/harvestsource/edit/:id' % version, controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_edit')
            map.connect('/api/%sform/harvestsource/delete/:id' % version, controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_delete')
            map.connect('/api/%srest/harvestsource/:id' % version, controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_view')
        map.connect('/api/2/form/package/create', controller='ckanext.dgu.forms.formapi:Form2Controller', action='package_create')
        map.connect('/api/2/form/package/edit/:id', controller='ckanext.dgu.forms.formapi:Form2Controller', action='package_edit')
        map.connect('/api/2/form/harvestsource/create', controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_create')
        map.connect('/api/2/form/harvestsource/edit/:id', controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_edit')
        map.connect('/api/2/form/harvestsource/delete/:id', controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_delete')
        map.connect('/api/2/rest/harvestsource', controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_list')
        map.connect('/api/2/rest/harvestsource/:id', controller='ckanext.dgu.forms.formapi:FormController', action='harvest_source_view')
        map.connect('/api/2/rest/harvestingjob', controller='ckanext.dgu.forms.formapi:FormController',
                action='harvesting_job_create', 
                conditions=dict(method=['POST']))
        """
        These routes are implemented in ckanext-csw
        map.connect('/api/2/rest/harvesteddocument/:id/xml/:id2.xml', controller='ckanext.dgu.forms.formapi:FormController', 
                action='harvested_document_view_format',format='xml')
        map.connect('/api/rest/harvesteddocument/:id/html', controller='ckanext.dgu.forms.formapi:FormController', 
                action='harvested_document_view_format', format='html')
        """
        map.connect('/api/2/util/publisher/:id/department', controller='ckanext.dgu.forms.formapi:FormController', action='get_department_from_publisher')
        map.connect('/', controller='ckanext.dgu.controllers.catalogue:CatalogueController', action='home')
        map.connect('home', '/ckan/', controller='home', action='index')
        return map

    def after_map(self, map):
        return map

    def update_config(self, config):
        rootdir = os.path.dirname(ckanext.dgu.__file__)

        template_dir = os.path.join(rootdir, 'templates')
        public_dir = os.path.join(rootdir, 'public')
        
        if config.get('extra_template_paths'):
            config['extra_template_paths'] += ','+template_dir
        else:
            config['extra_template_paths'] = template_dir
        if config.get('extra_public_paths'):
            config['extra_public_paths'] += ','+public_dir
        else:
            config['extra_public_paths'] = public_dir

    def filter(self,stream):

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

    def _get_harvest_source(self, id):
        obj = HarvestSource.get(id, default=None)
        return obj

    def harvest_source_list(self):
        objects = model.Session.query(HarvestSource).all()
        response_data = [o.id for o in objects]
        return self._finish_ok(response_data)

    def harvest_source_view(self, id):
        # Check user authorization.
        user = self._get_required_authorization_credentials()
        am_authz = self.authorizer.is_sysadmin(user.name) # simple for now
        if not am_authz:
            self._abort_not_authorized('User %r not authorized for harvesting' % user.name)

        obj = self._get_harvest_source(id)
        if obj is None:
            response.status_int = 404
            return ''            
        response_data = obj.as_dict()
        jobs = [job for job in obj.jobs]
        if not len(jobs):
            response_data['status'] = dict(msg='No jobs yet')
            return self._finish_ok(response_data)
        last_harvest_request = 'None'
        last_harvest_status = 'Not yet harvested'
        last_harvest_request = str(jobs[-1].created)[:10]
        last_harvest_statistics = 'None'
        last_harvest_errors = 'Not yet harvested'
        last_harvest_job = 'None'
        overall_statistics = {'added': 0, 'errors': 0}
        next_harvest = 'Not scheduled'
        if len(jobs):
            if len(jobs) < 2:
                last_harvest_request = 'None'
            if jobs[-1].status == u'New':
                # We need the details for the previous one
                if len(jobs) < 2:
                    last_harvest_status = 'Not yet harvested'
                else:
                    last_harvest_statistics = {'added': len(jobs[-2].report['added']), 'errors': len(jobs[-2].report['errors'])}
                    last_harvest_status = jobs[-2].status
                    last_harvest_errors = jobs[-2].report['errors']
                    last_harvest_job = jobs[-2].id
            else:
                last_harvest_status = jobs[-1].status
                last_harvest_errors = jobs[-1].report['errors']
                last_harvest_job = jobs[-1].id
                last_harvest_statistics = {'added': len(jobs[-1].report['added']), 'errors': len(jobs[-1].report['errors'])}
            for job in jobs:
                if job.status == u'New':
                    next_harvest = 'Within 15 minutes'
                overall_statistics['added'] += len(job.report['added'])
                overall_statistics['errors'] += len(job.report['errors'])
        packages = []
        for document in obj.documents:
            if not document.package.name in packages:
                packages.append(document.package.name)
        response_data['status'] = dict(
            last_harvest_status = last_harvest_status,
            last_harvest_request = last_harvest_request,
            last_harvest_statistics = last_harvest_statistics,
            overall_statistics = overall_statistics,
            next_harvest = next_harvest,
            last_harvest_errors = last_harvest_errors,
            last_harvest_job = last_harvest_job,
            packages = packages,
        )
        return self._finish_ok(response_data)

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
                    user_ref = request_data['user_ref']
                    publisher_ref = request_data['publisher_ref']
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
                    # Also create a job
                    job = HarvestingJob(source=source, user_ref=source.user_ref, status=u'New')
                    model.Session.add(job)
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
                user_ref = request_data['user_ref']
            except KeyError, error:
                self._abort_bad_request()
            
            source = HarvestSource.get(source_id, default=None)

            err_msg = None
            if not source:
                err_msg = 'Harvest source %s does not exist.' % source_id
            
            # Check if there is an already scheduled job for this source
            existing_job = HarvestingJob.filter(source_id=source_id,status=u'New').first()
            if existing_job:
                err_msg = 'There is an already scheduled job for this source'

            if err_msg:
                self.log.debug(err_msg)
                response.status_int = 400
                response.headers['Content-Type'] = self.content_type_json
                return json.dumps(err_msg)

            # Create job.
            job = HarvestingJob(source_id=source_id, user_ref=user_ref)
            model.Session.add(job)
            model.Session.commit()
            ret_dict = job.as_dict()
            return self._finish_ok(ret_dict)
            
        except Exception:
            # Log error.
            log.error("Couldn't run create harvest source form method: %s" % traceback.format_exc())
            raise

    def harvest_source_delete(self, id):
        model.repo.new_revision()
        # Check user authorization.
        user = self._get_required_authorization_credentials()
        am_authz = self.authorizer.is_sysadmin(user.name) # simple for now
        if not am_authz:
            self._abort_not_authorized('User %r not authorized for harvesting' % user.name)

        source = HarvestSource.get(id, default=None)
        jobs = HarvestingJob.filter(source=source)
        for job in jobs:
            job.delete()
        source.delete()
        model.repo.commit()        
        return self._finish_ok()

    def harvest_source_edit(self, id):
        try:
            # Find the entity.
            entity = self._get_harvest_source(id)
            self._assert_is_found(entity)

            # Check user authorization.
            user = self._get_required_authorization_credentials()
            am_authz = self.authorizer.is_sysadmin(user.name) # simple for now
            if not am_authz:
                self._abort_not_authorized('User %r not authorized for harvesting' % user.name)

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
                    user_ref = request_data['user_ref']
                    publisher_ref = request_data['publisher_ref']
                except KeyError, error:
                    self._abort_bad_request()
                if isinstance(form_data, list):
                    form_data = dict(form_data)
                # Bind form data to fieldset.
                try:
                    form_data['HarvestSource--url'] = form_data.get('HarvestSource--url', '').strip()
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

