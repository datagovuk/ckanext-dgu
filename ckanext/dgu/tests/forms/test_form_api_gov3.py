import re
import random

from pylons import config
from nose.tools import assert_equal

from ckan.lib.field_types import DateType
from ckan.lib.helpers import json
from ckan.lib.helpers import literal
import ckan.model as model
from ckan.lib.create_test_data import CreateTestData

from test_form_api import BaseFormsApiCase
from ckanext.dgu.tests import MockDrupalCase, Gov3Fixtures, strip_organisation_id
from ckan.tests.functional.api.base import (Api1TestCase,
                                            Api2TestCase,
                                            ApiUnversionedTestCase)


class PackageFixturesBase:
    def create(self, **kwargs):
        CreateTestData.create_arbitrary(self.pkgs,
                                        extra_user_names=[self.user_name],
                                        **kwargs)

    def delete(self):
        CreateTestData.delete()


class FormsApiTestCase(BaseFormsApiCase, MockDrupalCase):

    @classmethod
    def setup_class(cls):
        super(FormsApiTestCase, cls).setup_class()

    def setup(self):
        self.fixtures = Gov3Fixtures()
        self.fixtures.create()
        self.pkg_dict = self.fixtures.pkgs[0]
        self.package_name = self.pkg_dict['name']
        test_user = self.get_user_by_name(unicode(self.fixtures.user_name))
        self.extra_environ = {
            'Authorization' : str(test_user.apikey)
        }
        self.package_name_alt = u'formsapialt'
        self.package_fillers = {'title': 'test title',
                                'notes': 'test notes',
                                'license_id': 'mit-license',
                                }
        self.core_package_fields = set(('name', 'title', 'version',
                                       'url', 'notes',
                                       'author', 'author_email',
                                       'maintainer', 'maintainer_email',
                                       'license_id'))

    @classmethod
    def teardown_class(cls):
        super(FormsApiTestCase, cls).teardown_class()

    def teardown(self):
        model.repo.rebuild_db()

    def test_get_package_create_form(self):
        form, ret_status = self.get_package_create_form(package_form='package_gov3')
        self.assert_formfield(form, 'Package--name', '')
        self.assert_formfield(form, 'Package--title', '')
        self.assert_not_formfield(form, 'Package--version', '')
        self.assert_formfield(form, 'Package--url', '')
        self.assert_formfield(form, 'Package--notes', '')
        self.assert_formfield(form, 'Package--resources-0-url', '')
        self.assert_formfield(form, 'Package--resources-0-format', '')
        self.assert_formfield(form, 'Package--resources-0-description', '')
        self.assert_formfield(form, 'Package--resources-0-id', '')
        self.assert_formfield(form, 'Package--author', '')
        self.assert_formfield(form, 'Package--author_email', '')
        self.assert_formfield(form, 'Package--license_id', '')
        self.assert_formfield(form, 'Package--published_by', None)
        self.assert_formfield(form, 'Package--published_via', '')
        self.assert_formfield(form, 'Package--mandate', '')
        self.assert_not_formfield(form, 'Package--categories', '')
        self.assert_not_formfield(form, 'Package--maintainer', '')
        self.assert_not_formfield(form, 'Package--maintainer_email', '')
        self.assert_not_formfield(form, 'Package--newfield0-key', '')
        self.assert_not_formfield(form, 'Package--newfield0-value', '')
        self.assert_not_formfield(form, 'Package--newfield1-key', '')
        self.assert_not_formfield(form, 'Package--newfield1-value', '')
        self.assert_not_formfield(form, 'Package--newfield2-key', '')
        self.assert_not_formfield(form, 'Package--newfield2-value', '')
        self.assert_not_formfield(form, 'Package--extras-date_update_future-key', '')
        self.assert_not_formfield(form, 'Package--extras-date_update_future-value', '')

    def test_get_package_edit_form(self):
        package = self.get_package_by_name(self.package_name)
        form, ret_status = self.get_package_edit_form(package.id, package_form='package_gov3')
        prefix = 'Package-%s-' % package.id
        self.assert_formfield(form, prefix + 'name', package.name)
        expected_values = dict([(key, value) for key, value in package.extras.items()])
        expected_values['temporal_coverage-to'] = '6/2009'
        expected_values['temporal_coverage-from'] = '12:30 24/6/2008'
        expected_values['date_updated'] = '12:30 30/7/2009'
        expected_values['date_released'] = '30/7/2009'
        expected_values['date_update_future'] = '1/7/2009'
        expected_values['published_by'] = strip_organisation_id(expected_values['published_by'])
        expected_values['published_via'] = strip_organisation_id(expected_values['published_via'])
        del expected_values['national_statistic'] # restricted over form api
        del expected_values['geographic_coverage'] # don't test here
        del expected_values['external_reference']
        del expected_values['import_source']
        for key, value in expected_values.items():
            self.assert_formfield(form, prefix + key, value)

    def test_get_package_edit_form_restrict(self):
        package = self.get_package_by_name(self.package_name)
        form, ret_status = self.get_package_edit_form(package.id, package_form='package_gov3', restrict=True)
        prefix = 'Package-%s-' % package.id
        self.assert_formfield(form, prefix + 'name', package.name)
        self.assert_formfield(form, prefix + 'notes', package.notes)
        for key in ('national_statistic',):
            value = package.extras[key]
            self.assert_not_formfield(form, prefix + key, value)
        
    def test_submit_full_package_edit_form_valid(self):
        package = self.get_package_by_name(self.package_name)
        data = {
            'name':self.package_name_alt,
            'title':'test title',
            'url':'http://someurl.com/',
            'notes':'test notes',
            'tags':'sheep,goat,fish',
            'resources-0-url':'http://someurl.com/download.csv',
            'resources-0-format':'CSV',
            'resources-0-description':'A csv file',
            'author':'Brian',
            'author_email':'brian@company.com',
            'license_id':'cc-zero',
            'published_by':'Department for Education [3]',
            'published_via':'Ealing PCT [2]',
            'temporal_coverage-to':'6/2009',
            'temporal_coverage-from':'12:30 24/6/2008',
            'date_updated':'12:30 30/7/2009',
            'date_released':'30/7/2009',
            'date_update_future':'1/7/2009',
            'mandate':'Law 1996',
            }
        res = self.post_package_edit_form(package.id, **data)
        self.assert_blank_response(res)
        assert not self.get_package_by_name(self.package_name)
        pkg = self.get_package_by_name(self.package_name_alt)
        assert pkg
        for key in data.keys():
            if key.startswith('resources'):
                subkey = key.split('-')[-1]
                pkg_value = getattr(pkg.resources[0], subkey)
            elif key == 'tags':
                pkg_value = set([tag.name for tag in pkg.tags])
                data[key] = set(data[key].split(','))
            elif key in self.core_package_fields:
                pkg_value = getattr(pkg, key)
            else:
                # an extra
                pkg_value = pkg.extras[key]
                if '-' in pkg_value:
                    pkg_value = DateType.db_to_form(pkg_value)
            assert pkg_value == data[key], '%r should be %r but is %r' % (key, data[key], pkg_value)

    def test_submit_package_create_form_valid(self):
        package_name = self.package_name_alt
        assert not self.get_package_by_name(package_name)
        res = self.post_package_create_form(name=package_name,
                                            **self.package_fillers)
        self.assert_header(res, 'Location')
        self.assert_blank_response(res)
        self.assert_header(res, 'Location', 'http://localhost'+self.package_offset(package_name))
        pkg = self.get_package_by_name(package_name)
        assert pkg
        rev = pkg.revision
        assert_equal(rev.message, 'Unit-testing the Forms API...')
        assert_equal(rev.author, 'automated test suite')

    def test_submit_package_create_form_invalid(self):
        package_name = self.package_name_alt
        assert not self.get_package_by_name(package_name)
        res = self.post_package_create_form(name='',
                                            status=[400],
                                            **self.package_fillers)
        self.assert_not_header(res, 'Location')
        assert "Identifier: Please enter a value" in res.body, res.body
        assert not self.get_package_by_name(package_name)

    def test_submit_package_edit_form_valid(self):
        package = self.get_package_by_name(self.package_name)
        res = self.post_package_edit_form(package.id,
                                          name=self.package_name_alt,
                                          **self.package_fillers)
        self.assert_blank_response(res)
        assert not self.get_package_by_name(self.package_name)
        pkg = self.get_package_by_name(self.package_name_alt)
        assert pkg
        rev = pkg.revision
        assert_equal(rev.message, 'Unit-testing the Forms API...')
        assert_equal(rev.author, 'automated test suite')

    def test_submit_package_edit_form_errors(self):
        package = self.get_package_by_name(self.package_name)
        package_id = package.id
        # Nothing in name.
        invalid_name = ''
        author_email = "foo@baz.com"
        res = self.post_package_edit_form(package_id,
                                          name=invalid_name,
                                          author_email=author_email,
                                          status=[400],
                                          **self.package_fillers)
        # Check package is unchanged.
        assert self.get_package_by_name(self.package_name)
        # Check response is an error form.
        assert "class=\"field_error\"" in res
        form = self.form_from_res(res)
        name_field_name = 'Package-%s-name' % (package_id)
        author_field_name = 'Package-%s-author_email' % (package_id)
        # this test used to be 
        #   self.assert_formfield(form, field_name, invalid_name)
        # but since the formalchemy upgrade, we no longer sync data to
        # the model if the validation fails (as this would cause an
        # IntegrityError at the database level).
        # and formalchemy.fields.FieldRenderer.value renders the model
        # value if the passed in value is an empty string
        self.assert_formfield(form, name_field_name, package.name)
        # however, other fields which aren't blank should be preserved
        self.assert_formfield(form, author_field_name, author_email)

        # Whitespace in name.
        invalid_name = ' '
        res = self.post_package_edit_form(package_id,
                                          name=invalid_name,
                                          status=[400],
                                          **self.package_fillers)
        # Check package is unchanged.
        assert self.get_package_by_name(self.package_name)
        # Check response is an error form.
        assert "class=\"field_error\"" in res
        form = self.form_from_res(res)
        field_name = 'Package-%s-name' % (package_id)
        self.assert_formfield(form, field_name, invalid_name)
        # Check submitting error form with corrected values is OK.
        res = self.post_package_edit_form(package_id, form=form, name=self.package_name_alt)
        self.assert_blank_response(res)
        assert not self.get_package_by_name(self.package_name)
        assert self.get_package_by_name(self.package_name_alt)


class TestFormsApi1(Api1TestCase, FormsApiTestCase): pass

class TestFormsApi2(Api2TestCase, FormsApiTestCase): pass

class TestFormsApiUnversioned(ApiUnversionedTestCase, FormsApiTestCase): pass


class EmbeddedFormTestCase(BaseFormsApiCase, MockDrupalCase):
    '''Tests the form as it would be used embedded in dgu html.'''

    @classmethod
    def setup_class(self):
        MockDrupalCase.setup_class()
        model.repo.init_db()
        self.fixtures = Gov3Fixtures()
        self.fixtures.create()
        self.pkg_dict = self.fixtures.pkgs[0]
        self.package_name = self.pkg_dict['name']
        test_user = self.get_user_by_name(unicode(self.fixtures.user_name))
        self.apikey_header_name = config.get('apikey_header_name', 'X-CKAN-API-Key')
        self.extra_environ = {
            self.apikey_header_name : str(test_user.apikey)
        }
        

    @classmethod
    def teardown_class(self):
        MockDrupalCase.teardown_class()
        model.repo.rebuild_db()

    def _insert_into_field_tag(self, form_html, field_name, tag_name, tag_insertion):
        '''Finds the tag for a package field and inserts some html into it.'''
        form_html, num_replacements = re.subn(
            '(<%s[^>]* id="Package-.{0,36}-%s" .*) ?((value)|(name)=[^>]*>)' % \
            (tag_name, field_name),
            r'\1 class="disabled" readonly \2', form_html)
        assert num_replacements == 1, num_replacements
        return form_html

    def form_from_res(self, res):
        assert not "<html>" in str(res.body), "The response is an HTML doc, not just a form: %s" % str(res.body)

##        res.body = self._insert_into_field_tag(res.body, 'name', 'input', 'class="disabled" readonly')
##        res.body = self._insert_into_field_tag(res.body, 'department', 'select', 'disabled="disabled" readonly')
##        res.body = self._insert_into_field_tag(res.body, 'national_statistic', 'input', 'disabled="disabled" readonly')
        res.body = '''
<html>
  </body>
    <form method="post">
        %s
        <input type="submit">
    </form>
  </body>
</html>
''' % res.body

        return res.forms[0]

    def test_submit_package_create_form_valid(self):
        package_name = u'new_name'
        assert not self.get_package_by_name(package_name)
        form, ret_status = self.get_package_create_form(package_form='package_gov3')
        res = self.post_package_create_form(
            form=form, package_form='package_gov3',
            name=package_name,
            title=u'New name',
            notes=u'Notes',
            license_id=u'cc-zero',
            )
        self.assert_header(res, 'Location')
        self.assert_blank_response(res)
        self.assert_header(res, 'Location', 'http://localhost'+self.package_offset(package_name))
        pkg = self.get_package_by_name(package_name)
        assert pkg
        
    def test_submit_package_edit_form_valid(self):
        package_name = self.package_name
        pkg = self.get_package_by_name(package_name)
        new_title = u'New Title'
        form, ret_status = self.get_package_edit_form(pkg.id, package_form='package_gov3')
        res = self.post_package_edit_form(pkg.id, form=form, title=new_title, package_form='package_gov3')
        self.assert_blank_response(res)
        pkg = self.get_package_by_name(package_name)
        assert pkg.title == new_title, pkg

    def test_submit_package_edit_form_valid_restrict(self):
        package_name = self.package_name
        pkg = self.get_package_by_name(package_name)
        new_title = u'New Title 2'
        form, ret_status = self.get_package_edit_form(pkg.id, package_form='package_gov3', restrict=True)
        res = self.post_package_edit_form(pkg.id, form=form, title=new_title, package_form='package_gov3', restrict=True)
        self.assert_blank_response(res)
        pkg = self.get_package_by_name(package_name)
        assert pkg.title == new_title, pkg

    def test_create_package(self):
        res, ret_status = self.get_package_create_form()
        # TODO finish this test

    # TODO add other tests in from test_form.py

class TestEmbeddedFormApi1(Api1TestCase, EmbeddedFormTestCase): pass

class TestEmbeddedFormApi2(Api2TestCase, EmbeddedFormTestCase): pass


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

        self.package_fillers = {'title': 'test title',
                                'notes': 'test notes',
                                'license_id': 'mit-license',
                                }

    def teardown(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def check_create_package(self, username, expect_success=True):
        user = model.User.by_name(username)
        self.extra_environ={'Authorization' : str(user.apikey)}
        package_name = 'testpkg%i' % int(random.random()*100000000)
        assert not self.get_package_by_name(package_name)
        expect_status = 201 if expect_success else 403
        res = self.post_package_create_form(name=package_name,
                                            status=expect_status,
                                            **self.package_fillers)

    def check_edit_package(self, username, expect_success=True):
        user = model.User.by_name(username)
        self.extra_environ={'Authorization' : str(user.apikey)}
        package_name = u'annakarenina'
        pkg = self.get_package_by_name(package_name)
        assert pkg
        expect_status = 200 if expect_success else 403
        res = self.post_package_edit_form(pkg.id,
                                          name=package_name,
                                          status=expect_status,
                                          **self.package_fillers)

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
        
    def test_package_create(self):
        self.check_create_package('testsysadmin', expect_success=True)
        self.check_create_package('testadmin', expect_success=True)
        self.check_create_package('notadmin', expect_success=True)
        self.remove_default_rights()
        self.check_create_package('testsysadmin', expect_success=True)
        self.check_create_package('testadmin', expect_success=False)
        self.check_create_package('notadmin', expect_success=False)

    def test_package_edit(self):
        self.check_edit_package('testsysadmin', expect_success=True)
        self.check_edit_package('testadmin', expect_success=True)
        self.check_edit_package('notadmin', expect_success=True)
        self.remove_default_rights()
        self.check_edit_package('testsysadmin', expect_success=True)
        self.check_edit_package('testadmin', expect_success=False)
        self.check_edit_package('notadmin', expect_success=False)

class TestFormsApiAuthz1(Api1TestCase, FormsApiAuthzTestCase): pass

class TestFormsApiAuthz2(Api2TestCase, FormsApiAuthzTestCase): pass

class TestFormsApiAuthzUnversioned(ApiUnversionedTestCase, FormsApiAuthzTestCase): pass
