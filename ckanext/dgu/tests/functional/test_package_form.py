import re
import uuid

import lxml.html
from nose.tools import assert_equal
from routes import url_for

import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories
import ckan.model as model
from ckanext.dgu.tests.functional.base import DguFunctionalTestBase

assert_in = helpers.assert_in
webtest_submit = helpers.webtest_submit
submit_and_follow = helpers.submit_and_follow


# Tests inspired by:
# * ckan/new_tests/controllers/test_package.py
# * ckan/ckanext/example_idatasetform/tests/test_example_idatasetform.py

def _get_package_new_page(app, user=None):
    if user is None:
        user = factories.User()
    env = {'REMOTE_USER': user['name'].encode('ascii')}
    response = app.get(
        url=url_for(controller='package', action='new'),
        extra_environ=env,
    )
    return env, response


def _setup_user_and_org():
    user = factories.User()
    user['capacity'] = 'editor'
    org = factories.Organization(category='local-council', users=[user])
    env = {'REMOTE_USER': user['name'].encode('ascii')}
    reqd_fields = {'title': 'Test',
                   'notes': 'Test',
                   'owner_org': org['id'],
                   'license_id': 'uk-ogl'}
    return env, reqd_fields


def _get_package_edit_page(app, env, package_name):
    response = app.get(
        url=url_for(controller='package', action='edit', id=package_name),
        extra_environ=env,
    )
    return response


def _get_errors(response):
    '''Returns the validation error text, extracted from the webtest
    response.'''
    doc = lxml.html.fromstring(response.body)
    strings = doc.xpath('//div[@id="errors"]//text()')
    # join strings and get rid of excess spaces & newlines
    return re.sub(r"(\s)+", ' ', ' '.join(strings))


def reqd_dataset_fields(org):
    '''Returns a dict with the required params for creating a dataset'''
    return {'title': 'Test',
            'notes': 'Test',
            'owner_org': org['id'],
            'license_id': 'uk-ogl'}


class TestPackageController(DguFunctionalTestBase):

    def test_form_renders(self):
        app = self._get_test_app()
        env, response = _get_package_new_page(app)
        assert_in('dataset-edit', response.forms)

    def test_required_fields(self):
        app = self._get_test_app()
        env, response = _get_package_new_page(app)
        form = response.forms['dataset-edit']

        response = webtest_submit(form, 'save', status=200, extra_environ=env)
        assert_in('dataset-edit', response.forms)
        errors = _get_errors(response)
        assert_in('Name: Missing value', errors)
        assert_in('Unique identifier: Missing value', errors)
        assert_in('Description: Missing value', errors)
        assert_in('Owner org: Organization does not exist', errors)

    def _new_dataset(self):
        user = factories.User()
        user['capacity'] = 'editor'
        org = factories.Organization(category='local-council', users=[user])
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        name = 'test_dataset_{n}'.format(n=str(uuid.uuid4())[:6])
        app = self._get_test_app()
        response = app.get(
            url=url_for(controller='package', action='new'),
            extra_environ=env,
        )
        form = response.forms['dataset-edit']
        form['title'] = name.capitalize().replace('_', ' ')
        form['name'] = name
        form['notes'] = 'Test'
        form['owner_org'] = org['id']
        return form, env, app, name

    def _submit_with_validation_error(self, form, env,
                                      validation_error_field='notes'):
        form[validation_error_field] = ''  # to force validation error
        response = webtest_submit(form, 'save', status=200, extra_environ=env)
        assert_in('dataset-edit', response.forms)
        form = response.forms['dataset-edit']
        return form

    def _submit_to_save(self, form, name, app, env,
                        validation_error_field='notes',
                        validation_error_original_value='test'):
        # clear validation error
        form[validation_error_field] = validation_error_original_value
        response = submit_and_follow(app, form, env, 'save')
        # just check it has finished the edit, rather than being sent on to the
        # resource create/edit form.
        assert_equal(response.req.path, '/dataset/%s' % name)
        pkg = model.Package.by_name(name)
        return pkg

    def _edit_dataset(self, env, app, name):
        response = _get_package_edit_page(app, env, name)
        form = response.forms['dataset-edit']
        return form

    ## Each field in the form is tested using the standard 4 methods.
    ## Use test_edit_title as the template for new fields.

    def test_edit_title(self):
        form, env, app, name = self._new_dataset()
        form_field_id = 'title'
        value = 'Test Title'
        form[form_field_id] = value

        form = self._submit_with_validation_error(form, env)
        assert_equal(form[form_field_id].value, value)

        pkg = self._submit_to_save(form, name, app, env)
        assert_equal(pkg.title, value)

        form = self._edit_dataset(env, app, name)
        assert_equal(form[form_field_id].value, value)

    def test_edit_name(self):
        form, env, app, name = self._new_dataset()
        form_field_id = 'name'
        value = 'test-name'
        form[form_field_id] = value

        form = self._submit_with_validation_error(form, env)
        assert_equal(form[form_field_id].value, value)

        name = value  # specific to name field
        pkg = self._submit_to_save(form, name, app, env)
        assert_equal(pkg.name, value)

        form = self._edit_dataset(env, app, name)
        assert_equal(form[form_field_id].value, value)

    def test_edit_update_frequency(self):
        form, env, app, name = self._new_dataset()
        form_field_id = 'update_frequency'
        value = 'annual'
        form[form_field_id] = value

        form = self._submit_with_validation_error(form, env)
        assert_equal(form[form_field_id].value, value)

        pkg = self._submit_to_save(form, name, app, env)
        assert_equal(pkg.extras['update_frequency'], value)

        form = self._edit_dataset(env, app, name)
        assert_equal(form[form_field_id].value, value)

    def test_edit_update_frequency_other(self):
        form, env, app, name = self._new_dataset()
        form_field_id = 'update_frequency-other'
        value = 'custom'
        form[form_field_id] = value

        form = self._submit_with_validation_error(form, env)
        assert_equal(form[form_field_id].value, value)

        pkg = self._submit_to_save(form, name, app, env)
        assert_equal(pkg.extras['update_frequency'], value)

        form = self._edit_dataset(env, app, name)
        assert_equal(form[form_field_id].value, value)

    def test_edit_resource(self):
        form, env, app, name = self._new_dataset()
        form['individual_resources__0__description'] = 'Desc'
        form['individual_resources__0__url'] = 'http://url.com'
        form['individual_resources__0__format'] = 'XLS'

        form = self._submit_with_validation_error(form, env)
        assert_equal(form['individual_resources__0__description'].value, 'Desc')
        assert_equal(form['individual_resources__0__url'].value, 'http://url.com')
        assert_equal(form['individual_resources__0__format'].value, 'XLS')

        pkg = self._submit_to_save(form, name, app, env)
        assert_equal(pkg.resources[0].description, 'Desc')
        assert_equal(pkg.resources[0].url, 'http://url.com')
        assert_equal(pkg.resources[0].format, 'XLS')

        form = self._edit_dataset(env, app, name)
        assert_equal(form['individual_resources__0__description'].value, 'Desc')
        assert_equal(form['individual_resources__0__url'].value, 'http://url.com')
        assert_equal(form['individual_resources__0__format'].value, 'XLS')

    def test_edit_timeseries_resource(self):
        form, env, app, name = self._new_dataset()
        form['timeseries_resources__0__date'] = '13/1/2015'
        form['timeseries_resources__0__description'] = 'Desc'
        form['timeseries_resources__0__url'] = 'http://url.com'
        form['timeseries_resources__0__format'] = 'XLS'

        form = self._submit_with_validation_error(form, env)
        assert_equal(form['timeseries_resources__0__date'].value, '13/1/2015')
        assert_equal(form['timeseries_resources__0__description'].value, 'Desc')
        assert_equal(form['timeseries_resources__0__url'].value, 'http://url.com')
        assert_equal(form['timeseries_resources__0__format'].value, 'XLS')

        pkg = self._submit_to_save(form, name, app, env)
        assert_equal(pkg.resources[0].extras['date'], '2015-01-13')
        assert_equal(pkg.resources[0].description, 'Desc')
        assert_equal(pkg.resources[0].url, 'http://url.com')
        assert_equal(pkg.resources[0].format, 'XLS')

        form = self._edit_dataset(env, app, name)
        assert_equal(form['timeseries_resources__0__date'].value, '13/1/2015')
        assert_equal(form['timeseries_resources__0__description'].value, 'Desc')
        assert_equal(form['timeseries_resources__0__url'].value, 'http://url.com')
        assert_equal(form['timeseries_resources__0__format'].value, 'XLS')

    def test_edit_notes(self):
        form, env, app, name = self._new_dataset()
        form_field_id = 'notes'
        value = 'Test Notes'
        form[form_field_id] = value

        form = self._submit_with_validation_error(form, env, 'license_id')
        assert_equal(form[form_field_id].value, value)

        pkg = self._submit_to_save(form, name, app, env, 'license_id', 'uk-ogl')
        assert_equal(pkg.notes, value)

        form = self._edit_dataset(env, app, name)
        assert_equal(form[form_field_id].value, value)

    def test_edit_license(self):
        form, env, app, name = self._new_dataset()
        form_field_id = 'license_id'
        value = 'cc-by'
        form[form_field_id] = value

        form = self._submit_with_validation_error(form, env)
        assert_equal(form[form_field_id].value, value)

        pkg = self._submit_to_save(form, name, app, env)
        assert_equal(pkg.license_id, value)

        form = self._edit_dataset(env, app, name)
        assert_equal(form[form_field_id].value, value)

    def test_edit_license_other(self):
        form, env, app, name = self._new_dataset()
        form_field_id = 'access_constraints'
        value = 'My Licence'
        form[form_field_id] = value
        form['license_id'] = ''

        form = self._submit_with_validation_error(form, env)
        assert_equal(form[form_field_id].value, value)

        pkg = self._submit_to_save(form, name, app, env)
        assert_equal(pkg.license_id, value)

        form = self._edit_dataset(env, app, name)
        assert_equal(form[form_field_id].value, value)

    def test_edit_license_harvested(self):
        # need to create the licence extra before the form will display it
        env, fields = _setup_user_and_org()
        fields['extras'] = [{'key': 'licence', 'value': '["Harvest licence"]'}]
        dataset = factories.Dataset(**fields)
        name = dataset['name']
        app = self._get_test_app()
        form = self._edit_dataset(env, app, name)
        form_field_id = 'license_extra'
        value = '["Harvest licence"]'  # changing it in the form doesn't work
        form[form_field_id] = value
        form['license_id'] = '__extra__'

        form = self._submit_with_validation_error(form, env)
        assert_equal(form[form_field_id].value, value)

        pkg = self._submit_to_save(form, name, app, env)
        assert_equal(pkg.extras['licence'], value)

        form = self._edit_dataset(env, app, name)
        assert_equal(form[form_field_id].value, value)

    def test_edit_publisher(self):
        form, env, app, name = self._new_dataset()
        # get the org id via the user
        user = model.User.get(env['REMOTE_USER'])
        member = model.Session.query(model.Member) \
            .filter(model.Member.table_name == 'user') \
            .filter(model.Member.state == 'active') \
            .filter(model.Member.table_id == user.id) \
            .filter(model.Member.capacity == 'editor') \
            .first()
        org = member.group
        form_field_id = 'owner_org'
        value = org.id
        form[form_field_id] = value

        form = self._submit_with_validation_error(form, env)
        assert_equal(form[form_field_id].value, value)

        pkg = self._submit_to_save(form, name, app, env)
        assert_equal(pkg.owner_org, value)

        form = self._edit_dataset(env, app, name)
        assert_equal(form[form_field_id].value, value)

    def test_edit_contact(self):
        form, env, app, name = self._new_dataset()
        form['contact-name'] = 'Name'
        form['contact-email'] = 'a@b.com'
        form['contact-phone'] = '123'
        form['foi-name'] = 'FName'
        form['foi-email'] = 'Fa@b.com'
        form['foi-phone'] = 'F123'
        form['foi-web'] = 'http://foi.com'

        form = self._submit_with_validation_error(form, env)
        assert_equal(form['contact-name'].value, 'Name')
        assert_equal(form['contact-email'].value, 'a@b.com')
        assert_equal(form['contact-phone'].value, '123')
        assert_equal(form['foi-name'].value, 'FName')
        assert_equal(form['foi-email'].value, 'Fa@b.com')
        assert_equal(form['foi-phone'].value, 'F123')
        assert_equal(form['foi-web'].value, 'http://foi.com')

        pkg = self._submit_to_save(form, name, app, env)
        assert_equal(pkg.extras['contact-name'], 'Name')
        assert_equal(pkg.extras['contact-email'], 'a@b.com')
        assert_equal(pkg.extras['contact-phone'], '123')
        assert_equal(pkg.extras['foi-name'], 'FName')
        assert_equal(pkg.extras['foi-email'], 'Fa@b.com')
        assert_equal(pkg.extras['foi-phone'], 'F123')
        assert_equal(pkg.extras['foi-web'], 'http://foi.com')

        form = self._edit_dataset(env, app, name)
        assert_equal(form['contact-name'].value, 'Name')
        assert_equal(form['contact-email'].value, 'a@b.com')
        assert_equal(form['contact-phone'].value, '123')
        assert_equal(form['foi-name'].value, 'FName')
        assert_equal(form['foi-email'].value, 'Fa@b.com')
        assert_equal(form['foi-phone'].value, 'F123')
        assert_equal(form['foi-web'].value, 'http://foi.com')

    def test_edit_theme_primary(self):
        form, env, app, name = self._new_dataset()
        form_field_id = 'theme-primary'
        value = 'Crime'
        form[form_field_id] = value

        form = self._submit_with_validation_error(form, env)
        assert_equal(form[form_field_id].value, value)

        pkg = self._submit_to_save(form, name, app, env)
        assert_equal(pkg.extras['theme-primary'], value)

        form = self._edit_dataset(env, app, name)
        assert_equal(form[form_field_id].value, value)

    def test_edit_theme_secondary(self):
        form, env, app, name = self._new_dataset()
        form.get('theme-secondary', index=1).value__set(True)
        form.get('theme-secondary', index=2).value__set(True)

        form = self._submit_with_validation_error(form, env)
        assert_equal(form.get('theme-secondary', index=0).checked, False)
        assert_equal(form.get('theme-secondary', index=1).checked, True)
        assert_equal(form.get('theme-secondary', index=2).checked, True)

        pkg = self._submit_to_save(form, name, app, env)
        assert_equal(pkg.extras.get('theme-secondary'), u'["Defence", "Economy"]')

        form = self._edit_dataset(env, app, name)
        assert_equal(form.get('theme-secondary', index=0).checked, False)
        assert_equal(form.get('theme-secondary', index=1).checked, True)
        assert_equal(form.get('theme-secondary', index=2).checked, True)

    def test_edit_tags(self):
        form, env, app, name = self._new_dataset()
        form_field_id = 'tag_string'
        value = 'Smoke, air pollution'
        form[form_field_id] = value

        form = self._submit_with_validation_error(form, env)
        assert_equal(form[form_field_id].value, value)

        pkg = self._submit_to_save(form, name, app, env)
        assert_equal(set(tag.name for tag in pkg.get_tags()),
                     set(('air pollution', 'Smoke')))

        form = self._edit_dataset(env, app, name)
        assert_equal(form[form_field_id].value, value)

    def test_edit_additional_resource(self):
        form, env, app, name = self._new_dataset()
        form['additional_resources__0__description'] = 'Desc'
        form['additional_resources__0__url'] = 'http://url.com'
        form['additional_resources__0__format'] = 'PDF'

        form = self._submit_with_validation_error(form, env)
        assert_equal(form['additional_resources__0__description'].value, 'Desc')
        assert_equal(form['additional_resources__0__url'].value, 'http://url.com')
        assert_equal(form['additional_resources__0__format'].value, 'PDF')

        pkg = self._submit_to_save(form, name, app, env)
        assert_equal(pkg.resources[0].description, 'Desc')
        assert_equal(pkg.resources[0].url, 'http://url.com')
        assert_equal(pkg.resources[0].format, 'PDF')

        form = self._edit_dataset(env, app, name)
        assert_equal(form['additional_resources__0__description'].value, 'Desc')
        assert_equal(form['additional_resources__0__url'].value, 'http://url.com')
        assert_equal(form['additional_resources__0__format'].value, 'PDF')

    def test_edit_mandate(self):
        form, env, app, name = self._new_dataset()
        form_field_id = 'mandate'
        value = ['http://link.com']
        form[form_field_id] = value

        form = self._submit_with_validation_error(form, env)
        assert_equal(form[form_field_id].value, value)

        pkg = self._submit_to_save(form, name, app, env)
        assert_equal(pkg.extras['mandate'], value)

        form = self._edit_dataset(env, app, name)
        assert_equal(form[form_field_id].value, value)

    def test_edit_temporal_coverage(self):
        form, env, app, name = self._new_dataset()
        form['temporal_coverage-from'] = u'21/3/2007'
        form['temporal_coverage-to'] = u'3/10/2009'

        form = self._submit_with_validation_error(form, env)
        assert_equal(form['temporal_coverage-from'].value, u'21/3/2007')
        assert_equal(form['temporal_coverage-to'].value, u'3/10/2009')

        pkg = self._submit_to_save(form, name, app, env)
        assert_equal(pkg.extras['temporal_coverage-from'], u'2007-03-21')
        assert_equal(pkg.extras['temporal_coverage-to'], u'2009-10-03')

        form = self._edit_dataset(env, app, name)
        assert_equal(form['temporal_coverage-from'].value, u'21/3/2007')
        assert_equal(form['temporal_coverage-to'].value, u'3/10/2009')
