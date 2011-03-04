import re

from pylons import config

from ckan.lib.helpers import json
from ckan.lib.helpers import literal
import ckan.model as model
from ckan.lib.create_test_data import CreateTestData
from test_form_api import BaseFormsApiCase, Api1TestCase, Api2TestCase
from ckanext.dgu.tests import MockDrupalCase, Gov3Fixtures, strip_organisation_id


class PackageFixturesBase:
    def create(self, **kwargs):
        CreateTestData.create_arbitrary(self.pkgs,
                                        extra_user_names=[self.user_name],
                                        **kwargs)

    def delete(self):
        CreateTestData.delete()


class FormsApiTestCase(BaseFormsApiCase, MockDrupalCase):

    @classmethod
    def setup_class(self):
        super(FormsApiTestCase, self).setup_class()
        self.fixtures = Gov3Fixtures()
        self.fixtures.create()
        self.pkg_dict = self.fixtures.pkgs[0]
        self.package_name = self.pkg_dict['name']

    @classmethod
    def teardown_class(self):
        super(FormsApiTestCase, self).teardown_class()
        self.fixtures.delete()

    def test_get_package_create_form(self):
        form = self.get_package_create_form(package_form='package_gov3')
        self.assert_formfield(form, 'Package--name', '')
        self.assert_formfield(form, 'Package--title', '')
        self.assert_not_formfield(form, 'Package--version', '')
        self.assert_formfield(form, 'Package--url', '')
        self.assert_formfield(form, 'Package--notes', '')
        self.assert_formfield(form, 'Package--resources-0-url', '')
        self.assert_formfield(form, 'Package--resources-0-format', '')
        self.assert_formfield(form, 'Package--resources-0-description', '')
        self.assert_formfield(form, 'Package--resources-0-hash', '')
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
        form = self.get_package_edit_form(package.id, package_form='package_gov3')
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
        form = self.get_package_edit_form(package.id, package_form='package_gov3', restrict=True)
        prefix = 'Package-%s-' % package.id
        self.assert_formfield(form, prefix + 'name', package.name)
        self.assert_formfield(form, prefix + 'notes', package.notes)
        for key in ('national_statistic',):
            value = package.extras[key]
            self.assert_not_formfield(form, prefix + key, value)
        

class TestFormsApi1(Api1TestCase, FormsApiTestCase): pass

class TestFormsApi2(Api2TestCase, FormsApiTestCase): pass


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
        model.repo.clean_db()

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
        form = self.get_package_create_form(package_form='package_gov3')
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
        form = self.get_package_edit_form(pkg.id, package_form='package_gov3')
        res = self.post_package_edit_form(pkg.id, form=form, title=new_title, package_form='package_gov3')
        self.assert_blank_response(res)
        pkg = self.get_package_by_name(package_name)
        assert pkg.title == new_title, pkg

    def test_submit_package_edit_form_valid_restrict(self):
        package_name = self.package_name
        pkg = self.get_package_by_name(package_name)
        new_title = u'New Title 2'
        form = self.get_package_edit_form(pkg.id, package_form='package_gov3', restrict=True)
        res = self.post_package_edit_form(pkg.id, form=form, title=new_title, package_form='package_gov3', restrict=True)
        self.assert_blank_response(res)
        pkg = self.get_package_by_name(package_name)
        assert pkg.title == new_title, pkg

    def test_create_package(self):
        res = self.get_package_create_form()
        # TODO finish this test

    # TODO add other tests in from test_form.py

class TestEmbeddedFormApi1(Api1TestCase, EmbeddedFormTestCase): pass

class TestEmbeddedFormApi2(Api2TestCase, EmbeddedFormTestCase): pass
