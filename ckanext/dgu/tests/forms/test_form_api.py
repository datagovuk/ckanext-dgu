import re

from pylons import config
import webhelpers
from nose.tools import assert_equal
from nose.plugins.skip import SkipTest;

from ckan.tests import *
from ckan.tests import search_related
from ckan.tests.functional.api.base import (ApiTestCase,
                                            Api1TestCase,
                                            Api2TestCase,
                                            ApiUnversionedTestCase)

from ckanext.harvest.lib import get_harvest_source, create_harvest_source

import ckan.model as model
import ckan.authz as authz
from ckan.lib.helpers import url_for
from ckan.lib.helpers import json
from ckan.lib.create_test_data import CreateTestData

from ckanext.dgu.forms.formapi import FormController
from ckanext.dgu.tests import WsgiAppCase, MockDrupalCase, strip_organisation_id
from ckanext.dgu.testtools import test_publishers


ACCESS_DENIED = [403]

# Todo: Test for access control setup. Just checking an object exists in the model doesn't mean it will be presented through the WebUI.


class BaseFormsApiCase(ModelMethods, ApiTestCase, WsgiAppCase, CommonFixtureMethods, CheckMethods, MockDrupalCase):
    '''Utilities and pythonic wrapper for the Forms API for testing it.'''
    
    api_version = ''
    def split_form_args(self, kwargs):
        '''Splits form keyword arguments into those for the form url
        and those for the fields in the form.'''
        form_url_args = {}
        form_values_args = {}
        # allow user_id in calling fieldset only for tests
        possible_url_params = ['package_form', 'restrict', 'user_id']
        for k, v, in kwargs.items():
            if k in possible_url_params:
                form_url_args[k] = v
            else:
                form_values_args[k] = v
        return form_url_args, form_values_args

    @staticmethod
    def get_harvest_source_by_url(source_url, default=Exception):
        return get_harvest_source(source_url,attr='url',default=default)

    def create_harvest_source(self, **kwds):
        source = create_harvest_source(kwds)
        return source
   
    def delete_harvest_source(self, url):
        source = self.get_harvest_source_by_url(url, None)
        if source:
            self.delete_commit(source)

    def offset_package_create_form(self, **kwargs):
        self.set_drupal_user(kwargs)
        url_args, ignore = self.split_form_args(kwargs)
        return  url_for(self.offset('/form/package/create'), **url_args)

    def offset_package_edit_form(self, ref, **kwargs):
        self.set_drupal_user(kwargs)
        url_args, ignore = self.split_form_args(kwargs)
        return  url_for(self.offset('/form/package/edit/%s' % str(ref)), **url_args)

    def offset_harvest_source_create_form(self):
        return self.offset('/form/harvestsource/create')

    def offset_harvest_source_edit_form(self, ref):
        return self.offset('/form/harvestsource/edit/%s' % ref)

    def set_drupal_user(self, form_url_args):
        if not form_url_args.has_key('user_id'):
            # not logged into Drupal, so set user_id for testing
            form_url_args['user_id'] = '62'
    
    def get_package_create_form(self, status=[200], **form_url_args):
        offset = self.offset_package_create_form(**form_url_args)
        res = self.get(offset, status=status)
        return self.form_from_res(res), res.status

    def get_package_edit_form(self, package_ref, status=[200], **kwargs):
        offset = self.offset_package_edit_form(package_ref, **kwargs)
        res = self.get(offset, status=status)
        return self.form_from_res(res), res.status

    def get_harvest_source_create_form(self, status=[200]):
        offset = self.offset_harvest_source_create_form()
        res = self.get(offset, status=status)
        return self.form_from_res(res)

    def get_harvest_source_edit_form(self, harvest_source_id, status=[200]):
        offset = self.offset_harvest_source_edit_form(harvest_source_id)
        res = self.get(offset, status=status)
        return self.form_from_res(res)

    def form_from_res(self, res):
        '''Pass in a resource containing the form and this method returns
        the paster form, which is more easily tested.'''
        assert not "<html>" in str(res.body), "The response is an HTML doc, not just a form: %s" % str(res.body)
        # Arrange 'form fixture' from fieldsets string (helps testing Form API).
        res.body = "<html><form id=\"test\" action=\"\" method=\"post\">" + res.body + "<input type=\"submit\" name=\"send\"></form></html>"
        return res.forms['test']

    def post_package_create_form(self, form=None, status=[201], **kwargs):
        form_url_args, form_field_args = self.split_form_args(kwargs)
        if form == None:
            if not isinstance(status, list):
                status = [status]
            get_status = status + [200]
            form, return_status = self.get_package_create_form(status=get_status, **form_url_args)
            if return_status != 200:
                return
        for key, field_value in form_field_args.items():
            field_name = 'Package--%s' % key
            form[field_name] = field_value
        form_data = form.submit_fields()
        data = {
            'form_data': form_data,
            'log_message': 'Unit-testing the Forms API...',
            'author': 'automated test suite',
        }
        offset = self.offset_package_create_form(**form_url_args)
        return self.post(offset, data, status=status)

    def post_harvest_source_create_form(self, form=None, status=[201], **field_args):
        if form == None:
            form = self.get_harvest_source_create_form()
        for key,field_value in field_args.items():
            field_name = 'HarvestSource--%s' % key
            form[field_name] = field_value
        form_data = form.submit_fields()
        data = {
            'form_data': form_data,
            'user_id': 'example publisher user',
            'publisher_id': 'example publisher',
        }
        offset = self.offset_harvest_source_create_form()
        return self.post(offset, data, status=status)

    def package_id_from_ref(self, package_ref):
        if self.ref_package_by == 'id':
            return package_ref
        elif self.ref_package_by == 'name':
            package = model.Package.get(package_ref)
            return package.id
        else:
            raise Exception, "Unsupported value for ref_package_by: %s" % self.ref_package_by

    def post_package_edit_form(self, package_ref, form=None, status=[200], **offset_and_field_args):
        offset_kwargs, field_args = self.split_form_args(offset_and_field_args)
        if form == None:
            if not isinstance(status, list):
                status = [status]
            get_status = status + [200]
            form, return_status = self.get_package_edit_form(package_ref, status=get_status, **offset_kwargs)
            if return_status != 200:
                return
        package_id = self.package_id_from_ref(package_ref)
        for key,field_value in field_args.items():
            field_name = 'Package-%s-%s' % (package_id, key)
            self.set_formfield(form, field_name, field_value)
        form_data = form.submit_fields()
        data = {
            'form_data': form_data,
            'log_message': 'Unit-testing the Forms API...',
            'author': 'automated test suite',
        }
        offset = self.offset_package_edit_form(package_ref, **offset_kwargs)
        return self.post(offset, data, status=status)
        
    def post_harvest_source_edit_form(self, harvest_source_id, form=None, status=[200], **field_args):
        if form == None:
            form = self.get_harvest_source_edit_form(harvest_source_id)
        for key,field_value in field_args.items():
            field_name = 'HarvestSource-%s-%s' % (harvest_source_id, key)
            self.set_formfield(form, field_name, field_value)
        form_data = form.submit_fields()
        data = {
            'form_data': form_data,
            'user_id': 'example publisher user',
            'publisher_id': 'example publisher',
        }
        offset = self.offset_harvest_source_edit_form(harvest_source_id)
        return self.post(offset, data, status=status)
        
    def set_formfield(self, form, field_name, field_value):
        form[field_name] = field_value

    def assert_not_header(self, res, name):
        headers = self.get_headers(res)
        assert not name in headers, "Found header '%s' in response: %s" % (name, res)

    def assert_header(self, res, name, value=None):
        headers = self.get_headers(res)
        assert name in headers, "Couldn't find header '%s' in response: %s" % (name, res)
        if value != None:
            assert_equal(headers[name], value)

    def get_header_keys(self, res):
        return [h[0] for h in res.headers]

    def get_headers(self, res):
        headers = {}
        for h in res.headers:
            name = h[0]
            value = h[1]
            headers[name] = value
        return headers

    def assert_formfield(self, form, name, expected):
        '''
        Checks a specified form field exists, and if you
        give a non-None expected value, then it checks that too.
        '''
        assert name in form.fields, 'No field named %r out of:\n%s' % \
               (name, '\n'.join(sorted(form.fields)))
        if expected is not None:
            field = form[name]
            value = field.value
            value = strip_organisation_id(value)
            assert value == expected, 'Field %r: %r != %r' % \
                   (field.name, value, expected)

    def assert_not_formfield(self, form, name, expected=None):
        '''
        Checks a specified field does not exist in the form.
        @param expected: ignored (allows for same interface as
                         assert_formfield).
        '''
        assert name not in form.fields, name

    def assert_blank_response(self, response):
        assert (not response.body) or (not json.loads(response.body))


class FormsApiTestCase(BaseFormsApiCase):

    @classmethod
    def setup_class(cls):
        model.repo.rebuild_db()
        super(FormsApiTestCase, cls).setup_class()
        from ckanext.harvest.model import setup as harvest_setup
        harvest_setup()

    def setup(self):
        model.repo.init_db()
        CreateTestData.create()
        self.package_name = u'formsapi'
        self.package_name_alt = u'formsapialt'
        self.package_name_alt2 = u'formsapialt2'
        self.apikey_header_name = config.get('apikey_header_name', 'X-CKAN-API-Key')

        self.user = self.get_user_by_name(u'tester')
        if not self.user:
            self.user = self.create_user(name=u'tester')
        self.user = self.get_user_by_name(u'tester')
        model.add_user_to_role(self.user, model.Role.ADMIN, model.System())
        model.repo.commit_and_remove()
        self.extra_environ = {
            self.apikey_header_name : str(self.user.apikey)
        }
        self.create_package(name=self.package_name)
        self.harvest_source = None

    def teardown(self):
        model.repo.rebuild_db()
        model.Session.connection().invalidate()

    @classmethod
    def teardown_class(cls):
        super(FormsApiTestCase, cls).teardown_class()        

    def get_field_names(self, form):
        return form.fields.keys()

    def test_get_package_edit_form(self):
        package = self.get_package_by_name(self.package_name)
        form, return_status = self.get_package_edit_form(package.id)
        field_name = 'Package-%s-name' % (package.id)
        self.assert_formfield(form, field_name, package.name)

    def test_get_harvest_source_create_form(self):
        raise SkipTest('These tests should be moved to ckanext-harvest.')

        form = self.get_harvest_source_create_form()
        self.assert_formfield(form, 'HarvestSource--url', '')
        self.assert_formfield(form, 'HarvestSource--type', 'CSW Server')
        self.assert_formfield(form, 'HarvestSource--description', '')

    def test_submit_harvest_source_create_form_valid(self):
        raise SkipTest('These tests should be moved to ckanext-harvest.')

        source_url = u'http://localhost/'
        source_type= u'CSW Server'
        source_description = u'My harvest source.'
        assert not self.get_harvest_source_by_url(source_url, None)
        res = self.post_harvest_source_create_form(url=source_url,type=source_type,description=source_description)
        self.assert_header(res, 'Location')
        # Todo: Check the Location looks promising (extract and check given ID).
        self.assert_blank_response(res)
        source = self.get_harvest_source_by_url(source_url) # Todo: Use extracted ID.
        assert_equal(source['user_id'], 'example publisher user')
        assert_equal(source['publisher_id'], 'example publisher')

    def test_submit_harvest_source_create_form_invalid(self):
        raise SkipTest('These tests should be moved to ckanext-harvest.')

        source_url = u'' # Blank URL.
        source_type= u'CSW Server'
        assert not self.get_harvest_source_by_url(source_url, None)
        res = self.post_harvest_source_create_form(url=source_url, status=[400])
        self.assert_not_header(res, 'Location')
        assert "URL for source of metadata: Please enter a value" in res.body, res.body
        assert not self.get_harvest_source_by_url(source_url, None)

        source_url = u'something' # Not '^http://'
        source_type= u'CSW Server'
        assert not self.get_harvest_source_by_url(source_url, None)
        res = self.post_harvest_source_create_form(url=source_url, status=[400])
        self.assert_not_header(res, 'Location')
        assert "URL for source of metadata: Harvest source URL is invalid" in res.body, res.body
        assert not self.get_harvest_source_by_url(source_url, None)


    def test_get_harvest_source_edit_form(self):
        raise SkipTest('These tests should be moved to ckanext-harvest.')

        source_url = u'http://'
        source_type = u'CSW Server'
        source_description = u'An example harvest source.'
        self.harvest_source = self.create_harvest_source(url=source_url,type=source_type,description=source_description)
        form = self.get_harvest_source_edit_form(self.harvest_source['id'])
        self.assert_formfield(form, 'HarvestSource-%s-url' % self.harvest_source['id'], source_url)
        self.assert_formfield(form, 'HarvestSource-%s-type' % self.harvest_source['id'], source_type)
        self.assert_formfield(form, 'HarvestSource-%s-description' % self.harvest_source['id'], source_description)
 
    def test_submit_harvest_source_edit_form_valid(self):
        raise SkipTest('These tests should be moved to ckanext-harvest.')

        source_url = u'http://'
        source_type = u'CSW Server'
        source_description = u'An example harvest source.'
        alt_source_url = u'http://a'
        alt_source_type = u'Web Accessible Folder (WAF)'
        alt_source_description = u'An old example harvest source.'
        self.harvest_source = self.create_harvest_source(url=source_url, type=source_type,description=source_description)
        assert self.get_harvest_source_by_url(source_url, None)
        assert not self.get_harvest_source_by_url(alt_source_url, None)
        res = self.post_harvest_source_edit_form(self.harvest_source['id'], url=alt_source_url, type=alt_source_type,description=alt_source_description)
        self.assert_not_header(res, 'Location')
        # Todo: Check the Location looks promising (extract and check given ID).
        self.assert_blank_response(res)
        assert not self.get_harvest_source_by_url(source_url, None)
        source = self.get_harvest_source_by_url(alt_source_url) # Todo: Use extracted ID.
        assert source
        assert_equal(source['user_id'], 'example publisher user')
        assert_equal(source['publisher_id'], 'example publisher')

    def test_submit_harvest_source_edit_form_invalid(self):
        raise SkipTest('These tests should be moved to ckanext-harvest.')

        source_url = u'http://'
        source_type = u'CSW Server'
        source_description = u'An example harvest source.'
        alt_source_url = u''
        self.harvest_source = self.create_harvest_source(url=source_url, type=source_type,description=source_description)
        assert self.get_harvest_source_by_url(source_url, None)
        res = self.post_harvest_source_edit_form(self.harvest_source['id'], url=alt_source_url, status=[400])
        assert self.get_harvest_source_by_url(source_url, None)
        self.assert_not_header(res, 'Location')
        assert "URL for source of metadata: Please enter a value" in res.body, res.body

class FormsApiAuthzTestCase(BaseFormsApiCase):
    def setup(self):
        # need to do this for every test since we mess with System rights
        CreateTestData.create()
        model.repo.new_revision()
        model.Session.add(model.User(name=u'testadmin'))

        ## testsysadmin is already created by CreateTestData.create()
        # model.Session.add(model.User(name=u'testsysadmin'))

        model.Session.add(model.User(name=u'notadmin'))
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(u'annakarenina')
        admin = model.User.by_name(u'testadmin')
        sysadmin = model.User.by_name(u'testsysadmin')
        model.add_user_to_role(admin, model.Role.ADMIN, pkg)
        model.add_user_to_role(sysadmin, model.Role.ADMIN, model.System())
        model.repo.commit_and_remove()

        self.pkg = model.Package.by_name(u'annakarenina')
        self.admin = model.User.by_name(u'testadmin')
        self.sysadmin = model.User.by_name(u'testsysadmin')
        self.notadmin = model.User.by_name(u'notadmin')

    def teardown(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def check_create_harvest_source(self, username, expect_success=True):
        user = model.User.by_name(username)
        self.extra_environ={'Authorization' : str(user.apikey)}
        expect_status = 200 if expect_success else 403
        
        form = self.get_harvest_source_create_form(status=expect_status)

    def check_edit_harvest_source(self, username, expect_success=True):
        # create a harvest source
        source_url = u'http://localhost/'
        source_type = u'CSW Server'
        source_description = u'My harvest source.'
        sysadmin = model.User.by_name(u'testsysadmin')
        self.extra_environ={'Authorization' : str(sysadmin.apikey)}
        if not self.get_harvest_source_by_url(source_url, None):
            res = self.post_harvest_source_create_form(url=source_url, type=source_type,description=source_description)
        harvest_source = self.get_harvest_source_by_url(source_url, None)
        assert harvest_source

        user = model.User.by_name(username)
        self.extra_environ={'Authorization' : str(user.apikey)}
        expect_status = 200 if expect_success else 403
        
        form = self.get_harvest_source_edit_form(harvest_source['id'], status=expect_status)

    def remove_default_rights(self):
        roles = []
        system_role_query = model.Session.query(model.SystemRole)
        package_role_query = model.Session.query(model.PackageRole)
        for pseudo_user in (u'logged_in', u'visitor'):
            roles.extend(system_role_query.join('user').\
                         filter_by(name=pseudo_user).all())
            roles.extend(package_role_query.join('package').\
                         filter_by(name='annakarenina').\
                         join('user').filter_by(name=pseudo_user).all())
        for role in roles:
            role.delete()
        model.repo.commit_and_remove()
        
    def test_harvest_source_create(self):
        raise SkipTest('These tests should be moved to ckanext-harvest.')

        self.check_create_harvest_source('testsysadmin', expect_success=True)
        self.check_create_harvest_source('testadmin', expect_success=False)
        self.check_create_harvest_source('notadmin', expect_success=False)
        self.remove_default_rights()
        self.check_create_harvest_source('testsysadmin', expect_success=True)
        self.check_create_harvest_source('testadmin', expect_success=False)
        self.check_create_harvest_source('notadmin', expect_success=False)

    def test_harvest_source_edit(self):
        raise SkipTest('These tests should be moved to ckanext-harvest.')

        self.check_edit_harvest_source('testsysadmin', expect_success=True)
        self.check_edit_harvest_source('testadmin', expect_success=False)
        self.check_edit_harvest_source('notadmin', expect_success=False)
        self.remove_default_rights()
        self.check_edit_harvest_source('testsysadmin', expect_success=True)
        self.check_edit_harvest_source('testadmin', expect_success=False)
        self.check_edit_harvest_source('notadmin', expect_success=False)

class TestFormsApi1(Api1TestCase, FormsApiTestCase): pass

class TestFormsApi2(Api2TestCase, FormsApiTestCase): pass

class TestFormsApiUnversioned(ApiUnversionedTestCase, FormsApiTestCase): pass

class WithOrigKeyHeader(FormsApiTestCase):
    apikey_header_name = 'Authorization'

class TestFormsApi1WithOrigKeyHeader(WithOrigKeyHeader, TestFormsApi1): pass

class TestFormsApi2WithOrigKeyHeader(WithOrigKeyHeader, TestFormsApi2): pass

class TestFormsApiUnversionedWithOrigKeyHeader(TestFormsApiUnversioned): pass

class TestFormsApiAuthz1(Api1TestCase, FormsApiAuthzTestCase): pass

class TestFormsApiAuthz2(Api2TestCase, FormsApiAuthzTestCase): pass

class TestFormsApiAuthzUnversioned(ApiUnversionedTestCase, FormsApiAuthzTestCase): pass
