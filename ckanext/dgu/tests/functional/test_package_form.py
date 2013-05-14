"""
High-level functional tests for the create/edit package form.

TODO:
[ ] Sub-themes

"""
from functools import partial
import json
import re

from nose.tools import assert_equal, assert_raises
from nose.plugins.skip import SkipTest

import paste.fixture

from ckanext.dgu.tests import Gov3Fixtures
import ckanext.dgu.lib.helpers

import ckan
from ckan.lib.create_test_data import CreateTestData
from ckan.lib.field_types import DateType
import ckan.model as model
from ckan.tests import WsgiAppCase, CommonFixtureMethods, url_for, assert_in, assert_not_in
from ckan.tests.html_check import HtmlCheckMethods
from ckanext.dgu.plugins_toolkit import get_action
from ckanext.dgu.testtools.create_test_data import DguCreateTestData


class ResourceHelper(object):
    def get_additional_resources(self, package):
        """Extract the additional resources from a package"""
        return filter(self._is_additional_resource, package.get('resources'))

    def get_timeseries_resources(self, package):
        """Extract the timeseries resources from a package"""
        return filter(self._is_timeseries_resource, package.get('resources'))

    def _is_individual_resource(self,resource):
        """
        Returns true iff the given resource identifies as an individual resource.
        """
        return not self._is_additional_resource(resource) and \
               not self._is_timeseries_resource(resource)

    def get_individual_resources(self, package):
        """Extract the individual resources from a package"""
        return filter(self._is_individual_resource, package.get('resources'))

    def _is_additional_resource(self, resource):
        """
        Returns true iff the given resource identifies as an additional resource.
        """
        return resource.get('resource_type', '') in ('documentation',)

    def _is_timeseries_resource(self, resource):
        """
        Returns true iff the given resource identifies as a timeseries resource.
        """
        return not self._is_additional_resource(resource) and \
               resource.get('date', None)




class TestFormRendering(WsgiAppCase, HtmlCheckMethods, CommonFixtureMethods):
    """
    Test that the various fields are represented correctly in the form.
    """

    # Fields we expect to see on the rendered form.
    # input name -> (Label text , input type)
    # for example:
    #   <label for="title">Title *</label>
    #   <input name="title"/>
    # if Label text is None, it's not searched for
    _expected_fields = {
        # Name section
        'title':     ('Name:', 'input'),
        'name':      ('Unique identifier for this data record', 'input'),

        # Data section
        'package_type':                         (None, 'input'),
        'update_frequency':                     ('Update frequency', 'select'),
        'update_frequency-other':               ('Other:', 'input'),
        'individual_resources__0__description': (None, 'input'),
        'individual_resources__0__url':         (None, 'input'),
        'individual_resources__0__format':      (None, 'input'),
        'timeseries_resources__0__description': (None, 'input'),
        'timeseries_resources__0__url':         (None, 'input'),
        'timeseries_resources__0__date':        (None, 'input'),
        'timeseries_resources__0__format':      (None, 'input'),

        # Description section
        'notes':     (None, 'textarea'),

        # Contact details section
        'groups__0__name':          ('Published by: ', 'select'),
        'contact-name':             (None, 'input'),
        'contact-email':            (None, 'input'),
        'contact-phone':            (None, 'input'),
        'foi-name':                 (None, 'input'),
        'foi-email':                (None, 'input'),
        'foi-phone':                (None, 'input'),
        'foi-web':                (None, 'input'),

        # Themes and tags section
        'theme-primary':        (None, 'select'),
        'theme-secondary':      (None, 'input'),
        'tag_string':           ('Tags', 'input'),
        'mandate':              ('Mandate', 'input'),
        'license_id':           ('Licence:', 'select'),
        'access_constraints':   (None, 'textarea'),

        # Additional resources section
        'additional_resources__0__description': (None, 'input'),
        'additional_resources__0__url':         (None, 'input'),
        'additional_resources__0__format':      (None, 'input'),

        # Time & date section
        'temporal_coverage':            ('Temporal coverage', 'input'),

        # Geographic coverage section
        'geographic_coverage':          (None, 'input'),
    }

    # Fields that shouldn't appear in the form
    _unexpected_fields = (
        'external_reference',
        'import_source',
        'version',
        'maintainer',
        'maintainer_email',
        'newfield0-key',
        'newfield0-value',
    )

    # Fields that are still part of the package, but we only
    # expect them to appear on an edit-form, and only then if they
    # have a non-empty value
    _deprecated_fields = (
        'url',
        'taxonomy_url',
        'date_released',
        'date_updated',
        'date_update_future',
        'precision',
        'temporal_granularity',
        'temporal_granularity-other',
        'geographic_granularity',
        'geographic_granularity-other',
    )

    @classmethod
    def setup(self):
        """
        Create standard gov3 test fixtures for this suite.

        This test class won't be editing any packages, so it's ok to only
        create these fixtures once.
        """
        CreateTestData.create_groups(_EXAMPLE_GROUPS, auth_profile='publisher')
        CreateTestData.flag_for_deletion(group_names=[g['name'] for g in _EXAMPLE_GROUPS])
        self.fixtures = Gov3Fixtures()
        self.fixtures.create()
        self.admin = _create_sysadmin()

    @classmethod
    def teardown(self):
        """
        Cleanup the Gov3Fixtures
        """
        self.fixtures.delete()
        _drop_sysadmin()
        CreateTestData.delete()

    def test_new_form_has_all_fields(self):
        """
        Asserts that a form for a new package contains the various expected fields
        """
        offset = url_for(controller='package', action='new')
        response = self.app.get(offset, extra_environ={'REMOTE_USER': self.admin})

        for field, (label_text, input_type) in self._expected_fields.items():

            # e.g. <label for="title">Title *</label>
            if label_text is not None:
                self.check_named_element(response.body,
                                        'label',
                                        'for="%s"' % field,
                                        label_text)

            # e.g. <input name="title">
            self.check_named_element(response.body,
                                     input_type,
                                     'name="%s' % field)

    def test_new_form_does_not_contain_unexpected_fields(self):
        """
        Asserts that the fields named in self._unexpected_fields do not appear in the form.

        There are a set of fields that are on the normal package form that we don't
        want appearing in the dgu form.
        """
        offset = url_for(controller='package', action='new')
        response = self.app.get(offset, extra_environ={'REMOTE_USER': self.admin})

        for field in self._unexpected_fields:
            match = re.search('<(input|textarea|select) [^>]* name="%s"' % field,
                              response.body)
            assert not match , '"%s" found in response: "%s"' % (field, match.group(0))

    def test_failed_new_form_maintains_previously_entered_field_values(self):
        """
        Asserts that the user does not lose form data when attempting to submit an incorrect form.

        By removing the required name field from the submission, we get a failed
        submission, and then check each of the field values in the returned html.
        """
        package_data = _EXAMPLE_TIMESERIES_DATA.copy()
        del package_data['name']

        form_client = _PackageFormClient()
        response = form_client.post_form(package_data)

        # Sanity check that the form failed to submit due to the name being missing.
        assert 'Missing value' in response, response

        # Check the notes field separately as it contains a newline character
        # in its value.  And the `self.check_named_element()` method doesn't
        # use multi-line regular expressions.
        self.check_named_element(response.body.replace('\n', '__newline__'),
                                 'textarea',
                                 'name="notes"',
                                 package_data['notes'].replace('\n', '__newline__'))
        del package_data['notes']

        # Assert that the rest of the fields appear unaltered in the form
        for field_name, expected_value in package_data.items():
            self.check_named_element(response.body,
                                     '(input|textarea|select)',
                                     'name="%s"' % field_name,
                                     expected_value)

    def test_edit_form_form_has_all_fields(self):
        """
        Asserts that edit-form of a package has the fields prefilled correctly.
        """
        package = self.fixtures.pkgs[0]

        offset = url_for(controller='package', action='edit', id=package['name'])
        response = self.app.get(offset, extra_environ={'REMOTE_USER': self.admin})

        # form field name -> expected form field value
        expected_field_values = {}

        # populate expected_field_values with the simple fields first
        for field_name in self._expected_fields:
            try:
                expected_value = package[field_name]
                if isinstance(expected_value, basestring):
                    expected_field_values[field_name] = expected_value
            except KeyError:
                pass

        # populate expected_field_values for tag_string and license_id
        # by hand, as the field names in the package dict don't follow the
        # same naming scheme as the form fields.
        expected_field_values['license_id'] = package['license']

        # tags may be re-ordered, so test them manually
        expected_tags = set(map(lambda s: s.strip(), package['tags'].split()))
        tag_string_form_value = re.finditer(r'<input [^>]*id="tag_string" name="tag_string" [^>]*value="([^"]+)" />', response.body).next().group(1)
        actual_tags = set(map(lambda s: s.strip(), tag_string_form_value.split(',')))
        assert_equal(expected_tags, actual_tags)

        # Promote the key-value pairs stored in 'extras' to form fields.
        expected_field_values.update((k,v) for (k,v) in package['extras'].items()\
                                           if k not in self._unexpected_fields)

        # Some of the data isn't in the format as rendered on the form, so
        # overwrite it by hand for now.
        expected_field_values['geographic_coverage'] = 'england'
        date_fields = ('date_update_future',
                       'date_released',
                       'date_updated',
                       'temporal_coverage-from',
                       'temporal_coverage-to',
                       )
        for field_name in date_fields:
            expected_field_values[field_name] = DateType.db_to_form(expected_field_values[field_name])

        # TODO: fix these fields
        del expected_field_values['published_by']
        del expected_field_values['published_via']

        helper = ResourceHelper()
        # Ensure the resources have been un-merged correctly.
        for resource_type in 'additional timeseries individual'.split():
            resource_type += '_resources'

            fields = []
            for field_name in [f for f in self._expected_fields if f.startswith(resource_type)]:
                fields.append(field_name.split('__')[-1])


            resources = getattr(helper, "get_%s" % resource_type)(package)
            for index, resource in enumerate(resources):
                for field in fields:
                    # eg. additional_resources__0__url
                    full_field_name = '__'.join([resource_type,
                                                 str(index),
                                                 field])
                    try:
                        expected_field_values[full_field_name] = resource[field]
                    except KeyError:
                        expected_field_values[full_field_name] = resource.get('extras',{}).get(field)

        for field_name, expected_value in expected_field_values.items():

            if field_name not in self._deprecated_fields or expected_value:
                self.check_named_element(response.body,
                                        '(input|textarea|select)',
                                        'name="%s"' % field_name,
                                        expected_value)



    def test_a_full_timeseries_dataset_edit_form(self):
        """
        Creates a new package and then checks the edit form is filled correctly.
        """
        form_client = _PackageFormClient()
        package_data = _EXAMPLE_TIMESERIES_DATA.copy()
        package_name = package_data['name']
        CreateTestData.flag_for_deletion(package_name)
        assert not self.get_package_by_name(package_name),\
            'Package "%s" already exists' % package_name

        # create package via form
        response = form_client.post_form(package_data)

        # GET the edit form
        offset = url_for(controller='package', action='edit', id=package_name)
        response = self.app.get(offset, extra_environ={'REMOTE_USER': self.admin})

        # tags may be re-ordered, so test them manually
        expected_tags = set(map(lambda s: s.strip(), package_data['tag_string'].split(',')))
        tag_string_form_value = re.finditer(r'<input [^>]*id="tag_string" name="tag_string" [^>]*value="([^"]+)" />', response.body).next().group(1)
        actual_tags = set(map(lambda s: s.strip(), tag_string_form_value.split(',')))
        assert_equal(expected_tags, actual_tags)
        del package_data['tag_string']

        # Check the notes fiels separately as it contains a newline character
        # in its value.  And the `self.check_named_element()` method doesn't
        # use multi-line regular expressions.
        self.check_named_element(response.body.replace('\n', '__newline__'),
                                 'textarea',
                                 'name="notes"',
                                 package_data['notes'].replace('\n', '__newline__'))
        del package_data['notes']

        # Assert that the rest of the fields appear unaltered in the form
        for field_name, expected_value in package_data.items():
            self.check_named_element(response.body,
                                     '(input|textarea|select)',
                                     'name="%s"' % field_name,
                                     expected_value)


    def test_edit_form_does_not_contain_unexpected_fields(self):
        """
        Asserts that the fields named in self._unexpected_fields do not appear in the form.

        There are a set of fields that are on the normal package form that we don't
        want appearing in the dgu form.
        """
        package = self.fixtures.pkgs[0]
        offset = url_for(controller='package', action='edit', id=package['name'])
        response = self.app.get(offset, extra_environ={'REMOTE_USER': self.admin})

        for field in self._unexpected_fields:
            match = re.search('<(input|textarea|select) [^>]* name="%s"' % field,
                              response.body)
            assert not match , '"%s" found in response: "%s"' % (field, match.group(0))

class TestFormValidation(object):
    """
    A suite of tests that check validation of the various form fields.
    """

    @classmethod
    def setup_class(cls):
        cls._form_client = _PackageFormClient()
        DguCreateTestData.create_dgu_test_data()

    @classmethod
    def teardown_class(cls):
        _drop_sysadmin()

    def test_title_non_empty(self):
        """Asserts that the title cannot be empty"""
        data = {'title': ''}
        response = self._form_client.post_form(data)
        assert 'Name:</b> Missing value' in response.body, response.body

    def test_name_non_empty(self):
        """Asserts that the name (uri identifier) is non-empty"""
        data = {'name': ''}
        response = self._form_client.post_form(data)
        assert 'Unique identifier:</b> Missing value' in response.body, response.body

    def test_name_rejects_non_alphanumeric_names(self):
        """Asserts that the name (uri identifier) does not allow punctuation"""
        bad_names = ('fullstop.',
                     'exclamation!',
                     'quotes"',
                     'hash#',
                     'unicode%E3%82%A1', # u'unicode\u30a1' url-encoded
                     )
        for name in bad_names:
            data = {'name': name}
            response = self._form_client.post_form(data)
            assert 'Url must be purely lowercase alphanumeric (ascii) characters and these symbols: -_'\
                in response.body, '"%s" allowed as url identifier' % name

    def test_name_must_be_at_least_2_characters(self):
        """Asserts that 1-length names are not allowed"""
        data = {'name': 'a'}
        response = self._form_client.post_form(data)
        assert 'Name must be at least 2 characters long' in response.body

    def test_notes_non_empty(self):
        """Asserts that the abstract cannot be empty"""
        data = {'notes': ''}
        response = self._form_client.post_form(data)
        assert 'Description:</b> Missing value' in response.body, response.body

    def test_individual_resource_url_non_empty(self):
        """Asserts that individual resources must have url defined"""
        data = {'individual_resources__0__description': 'description with no url',
                'individual_resources__0__format': 'format with no url'}
        response = self._form_client.post_form(data)
        assert 'URL:</b> Missing value' in response.body, response.body

    def test_timeseries_resource_url_non_empty(self):
        """Asserts that timeseries resources must have url defined"""
        data = {'timeseries_resources__0__description': 'description with no url',
                'timeseries_resources__0__date': 'date with no url',
                'timeseries_resources__0__format': 'format with no url'}
        response = self._form_client.post_form(data)
        assert 'URL:</b> Missing value' in response.body, response.body

    def test_additional_resource_url_non_empty(self):
        """Asserts that additional resources must have url defined"""
        data = {'additional_resources__0__description': 'description with no url',
                'additional_resources__0__format': 'format with no url'}
        response = self._form_client.post_form(data)
        assert 'URL:</b> Missing value' in response.body, response.body

    def test_individual_resource_description_non_empty(self):
        """Asserts that individual resources must have description defined"""
        data = {'individual_resources__0__url': 'url with no description',
                'individual_resources__0__format': 'format with no description'}
        response = self._form_client.post_form(data)
        assert 'Title:</b> Missing value' in response.body, response.body

    def test_timeseries_resource_description_non_empty(self):
        """Asserts that timeseries resources must have description defined"""
        data = {'timeseries_resources__0__url': 'url with no description',
                'timeseries_resources__0__date': 'date with no description',
                'timeseries_resources__0__format': 'format with no description'}
        response = self._form_client.post_form(data)
        assert 'Title:</b> Missing value' in response.body, response.body

    def test_additional_resource_description_non_empty(self):
        """Asserts that additional resources must have description defined"""
        data = {'additional_resources__0__url': 'url with no description',
                'additional_resources__0__format': 'format with no description'}
        response = self._form_client.post_form(data)
        assert 'Title:</b> Missing value' in response.body, response.body
        assert 'Row(s) partially filled' in response.body, response.body

    def test_timeseries_resource_date_non_empty(self):
        """Asserts that timeseries resources must have date defined"""
        data = {'timeseries_resources__0__description': 'description with no date',
                'timeseries_resources__0__url': 'url with no date',
                'timeseries_resources__0__format': 'format with no date',}
        response = self._form_client.post_form(data)
        assert 'Date:</b> Missing value' in response.body, response.body

    def assert_accepts_date(self, field_name, date_str):
        data = {field_name: date_str}
        response = self._form_client.post_form(data, id=DguCreateTestData.old_form_package().id)
        assert not ("Cannot parse form date" in response.body or\
                    "Date error reading in format" in response.body), response.body

    def assert_rejects_date(self, field_name, date_str):
        data = {field_name: date_str}
        response = self._form_client.post_form(data, id=DguCreateTestData.old_form_package().id)
        assert "Cannot parse form date" in response.body or \
               "Date error reading in format" in response.body, response.body

    def test_date_updated_only_accepts_well_formed_dates(self):
        """
        Asserts that date_updated only accepts dates.
        """
        self.assert_accepts_date('date_updated', '30/12/12')
        self.assert_accepts_date('date_updated', '12/2012')
        self.assert_accepts_date('date_updated', '20-12-2012')

        self.assert_rejects_date('date_updated', '2012/12/30')
        self.assert_rejects_date('date_updated', '2012-12-30')
        self.assert_rejects_date('date_updated', '2012-12')

    def test_date_update_future_only_accepts_well_formed_dates(self):
        """
        Asserts that date_update_future only accepts dates.
        """
        self.assert_accepts_date('date_update_future', '30/12/12')
        self.assert_rejects_date('date_update_future', '2012/12/30')

    def test_both_timeseries_and_individual_resources_cannot_be_specified(self):
        """
        Asserts that it's not possible to enter both timeseries and individual resources
        """
        data = {
            'timeseries_resources__0__description': 'Timeseries description',
            'timeseries_resources__0__url':         'http://example.com/timeseries',
            'timeseries_resources__0__date':        'December 2011',
            'individual_resources__0__description': 'Individual description',
            'individual_resources__0__url':         'http://example.com/individual',
        }
        response = self._form_client.post_form(data)
        assert 'Only define timeseries or individual resources, not both' in response.body

    def test_additional_resources_disallows_non_documentation_resource_types(self):
        """
        Asserts that non-documentation resource types are not allowed for additional resources.
        """
        for resource_type in ["bad", "api", "file"]:
            data = {
                'additional_resources__0__description':   'Additional resource 1',
                'additional_resources__0__url':           'http://example.com/doc1',
                'additional_resources__0__resource_type': resource_type,
            }
            response = self._form_client.post_form(data)
            assert_in("Invalid resource type: %s" % resource_type,
                      response.body)

    def test_data_resources_disallows_non_file_or_api_resource_types(self):
        """
        Asserts that non-{file,api} resource types are not allowed for data resources.
        """
        for resource_type in ["bad", "documentation"]:
            data = {
                'timeseries_resources__0__description':   'Timeseries resource 1',
                'timeseries_resources__0__url':           'http://example.com/data1',
                'timeseries_resources__0__date':          'Summer',
                'timeseries_resources__0__resource_type': resource_type,
            }
            response = self._form_client.post_form(data)
            assert_in("Invalid resource type: %s" % resource_type,
                      response.body)

            data = {
                'individual_resources__0__description':   'Individual resource 1',
                'individual_resources__0__url':           'http://example.com/data1',
                'individual_resources__0__resource_type': resource_type,
            }
            response = self._form_client.post_form(data)
            assert_in("Invalid resource type: %s" % resource_type,
                      response.body)

    def test_cannot_create_a_non_ogl_dataset_without_specifying_license_name(self):
        """
        Asserts that the user specify a license name if the license is non-OGL
        """
        data = {'license_id': ""}
        response = self._form_client.post_form(data)
        assert_in('Licence:</b> Please enter the access constraints.', response.body)

    def test_cannot_name_another_license_if_declaring_the_dataset_to_be_ogl_licensed(self):
        """
        Asserts that if specifying an ogl license, then the user cannot fill the license id themselves
        """
        data = {'license_id': 'uk-ogl', 'access_constraints': 'A difference license'}
        response = self._form_client.post_form(data)
        assert 'Licence:</b> Leave the "Access Constraints" box empty if selecting a license from the list' in response, response

    def test_publisher_required_as_sysadmin(self):
        '''
        You must specify a publisher.
        '''
        data = {}
        response = self._form_client.post_form(data)
        assert 'Publisher:' in response, response
        assert 'Unique identifier:</b> Missing value' in response
        assert '<p class="field_error">Please select a publisher.</p>' in response

    def test_publisher_required(self):
        '''
        You must specify a publisher. Check the authorization is correct
        to let the validation through when you are not a sysadmin.
        '''
        data = {}
        response = self._form_client.post_form(data, user_name='nhseditor')
        assert 'Publisher:' in response, response
        assert 'Unique identifier:</b> Missing value' in response
        assert '<p class="field_error">Please select a publisher.</p>' in response


class TestPackageCreation(CommonFixtureMethods):
    """
    A suite of tests that check that packages are created correctly through the creation form.
    """

    def setup(self):
        self._form_client = _PackageFormClient()
        CreateTestData.create_groups(_EXAMPLE_GROUPS, auth_profile='publisher')
        CreateTestData.flag_for_deletion(group_names=[g['name'] for g in _EXAMPLE_GROUPS])

    def teardown(self):
        """
        Delete any created packages
        """
        _drop_sysadmin()
        CreateTestData.delete()

    def test_submitting_a_valid_create_form_creates_a_new_package(self):
        """Assert that submitting a valid create form does indeed create a new package"""
        # setup fixture
        package_data = _EXAMPLE_INDIVIDUAL_DATA
        package_name = package_data['name']
        CreateTestData.flag_for_deletion(package_name)
        assert not self.get_package_by_name(package_name),\
            'Package "%s" already exists' % package_name

        # create package via form
        self._form_client.post_form(package_data)

        # ensure it's correct
        pkg = self.get_package_by_name(package_name)
        assert pkg
        assert package_data['name'] == pkg.name

    def test_a_full_timeseries_dataset(self):
        """
        Tests the submission of a fully-completed timeseries dataset.
        """
        package_data = _EXAMPLE_TIMESERIES_DATA
        package_name = package_data['name']
        CreateTestData.flag_for_deletion(package_name)
        assert not self.get_package_by_name(package_name),\
            'Package "%s" already exists' % package_name

        # create package via form
        response = self._form_client.post_form(package_data)

        # ensure it's correct
        pkg = self.get_package_by_name(package_name)
        assert pkg, response.body
        assert_equal(package_data['title'], pkg.title)
        assert_equal(package_data['notes'], pkg.notes)

        publisher = pkg.as_dict()['groups'][0]
        assert_equal(package_data['groups__0__name'], publisher)

        # Extra data
        # Timeseries data
        helper = ResourceHelper()
        expected_timeseries_keys = filter(lambda k: k.startswith('timeseries_resources'),
                                          package_data.keys())
        timeseries_resources = helper.get_timeseries_resources(pkg.as_dict())
        assert_equal(len(timeseries_resources), 4)
        for key in expected_timeseries_keys:
            index, field = key.split('__')[1:]
            index = int(index)
            assert_equal(package_data[key],
                         timeseries_resources[index][field])

        # Publisher / contact details
        # The contact-email should not be an extra-field on the dataset as it's the
        # same as the publisher group's contact-email.  ie - it hasn't been overridden.
        # The resof the information should be in the extras fields
        assert_not_in('contact-email', pkg.extras)
        assert_equal(package_data['contact-name'], pkg.extras['contact-name'])
        assert_equal(package_data['contact-phone'], pkg.extras['contact-phone'])
        assert_equal(package_data['foi-name'], pkg.extras['foi-name'])
        assert_equal(package_data['foi-web'], pkg.extras['foi-web'])
        assert_equal(package_data['foi-email'], pkg.extras['foi-email'])
        assert_equal(package_data['foi-phone'], pkg.extras['foi-phone'])

        # Themes and tags
        assert_equal(package_data['theme-primary'], pkg.extras['theme-primary'])

        assert_equal(set(package_data['theme-secondary']),
                     set(pkg.extras['theme-secondary']))

        # Health and Education are from the primary and secondary themes, which
        # end up in the tags
        assert_equal(set(['tag1', 'tag2', 'a multi word tag', 'Health', 'Education']),
                     set(tag.name for tag in pkg.get_tags()))

        # Additional resources
        helper = ResourceHelper()
        expected_additional_keys = filter(lambda k: k.startswith('additional_resources'),
                                          package_data.keys())
        additional_resources = helper.get_additional_resources(pkg.as_dict())
        assert_equal(len(additional_resources), 2)
        for key in expected_additional_keys:
            index, field = key.split('__')[1:]
            index = int(index)
            assert_equal(package_data[key],
                         additional_resources[index][field])

        assert_equal(package_data['mandate'], pkg.extras['mandate'])
        assert_equal(package_data['access_constraints'], pkg.license_id)

        assert_equal(package_data['temporal_coverage-from'], DateType.db_to_form(pkg.extras['temporal_coverage-from']))
        assert_equal(package_data['temporal_coverage-to'], DateType.db_to_form(pkg.extras['temporal_coverage-to']))
        assert_in('England', pkg.extras['geographic_coverage'])

class TestEditingHarvestedDatasets(CommonFixtureMethods, WsgiAppCase):
    """
    Tests based around a sysadmin editing and saving a harvested dataset.
    """

    def setup(self):
        """
        Creates a harvested UKLP dataset.
        """
        _drop_sysadmin()
        self.admin = _create_sysadmin()

        CreateTestData.create_test_user()
        self.tester = 'tester'

        CreateTestData.create_groups(_EXAMPLE_GROUPS, admin_user_name=self.tester, auth_profile='publisher')
        CreateTestData.flag_for_deletion(group_names=[g['name'] for g in _EXAMPLE_GROUPS])

        context = {
            'model': ckan.model,
            'session': ckan.model.Session,
            'user': self.admin,
            'api_version': 2,
            'schema': ckan.logic.schema.default_package_schema(),
        }
        package_dict = _UKLP_DATASET.copy()

        self.uklp_dataset = get_action('package_create_rest')(context, package_dict)

        CreateTestData.flag_for_deletion(pkg_names=[self.uklp_dataset['name']])

    def teardown(self):
        CreateTestData.delete()
        _drop_sysadmin()

    def test_sysadmin_can_edit_UKLP_dataset(self):
        """Test that a sysadmin can access the edit page of a UKLP dataset"""
        offset = url_for(controller='package', action='edit', id=self.uklp_dataset['id'])
        response = self.app.get(offset, extra_environ={'REMOTE_USER': self.admin})
        assert_equal(response.status, 200)

    def test_publisher_cannot_edit_a_UKLP_dataset(self):
        """Test that a publisher cannot access the edit page of a UKLP dataset"""
        offset = url_for(controller='package', action='edit', id=self.uklp_dataset['id'])

        response = None
        try:
            response = self.app.get(offset, extra_environ={'REMOTE_USER': self.tester})
        except paste.fixture.AppError, e:
            assert_in('401 Unauthorized', str(e))
        assert not response

    def test_sysadmin_can_save_a_UKLP_harvested_dataset(self):
        """Test sysadmin can save a UKLP dataset.

        The thing to test here is that saving works even when the following
        form-fields may be invalid or missing (as they cannot easily be populated
        when harvesting):

        * theme-primary
        * resource formats
        * temporal_coverage-{from,to}
        """
        client = _PackageFormClient()
        response = client.post_form({}, id=self.uklp_dataset['id'])

        assert_not_in('Errors in form', response.body)
        assert_equal(response.response.status_int, 302)

    def test_when_sysadmin_saves_that_no_harvested_data_is_dropped(self):
        """Test that we don't accidently drop any data that has been harvested."""

        offset = url_for(controller='api',
                         register='package',
                         action='show',
                         id=self.uklp_dataset['id'],
                         ver='2')

        pkg_before = json.loads(self.app.get(offset).body)

        # GET and POST the form, without entering any new details.
        client = _PackageFormClient()
        client.post_form({'license_id': '__other__'}, id=self.uklp_dataset['id'])

        pkg_after = json.loads(self.app.get(offset).body)

        # The form may add new fields to the package, such as 'mandate'.
        # But shouldn't change any existing fields.
        ignored_fields = ['metadata_modified']
        new_values = dict( (k, pkg_after.get(k,None)) for k in pkg_before.keys()
                                                      if k not in ignored_fields )
        for k in new_values.keys():
            assert_equal(new_values[k], pkg_before[k])

class TestAuthorization(WsgiAppCase):
    @classmethod
    def setup_class(cls):
        cls._form_client = _PackageFormClient()
        DguCreateTestData.create_dgu_test_data()

    @classmethod
    def teardown_class(cls):
        _drop_sysadmin()

    def assert_create_or_edit(self, create_or_edit, user_name, allowed=True):
        if create_or_edit == 'create':
            package_data = _EXAMPLE_TIMESERIES_DATA.copy()
            package_data['name'] = 'tstcreate' + user_name
            package_data['groups__0__name'] = 'national-health-service'
            package_name = package_data['name']
            package_id = None
        else:
            package_data = {}
            package_id = DguCreateTestData.form_package().id
            package_name = DguCreateTestData.form_package().name
        response = self._form_client.post_form(package_data, id=package_id, user_name=user_name, use_sysadmin_to_get_form=True, abort_on_bad_status=False)
        redirect = response.header_dict.get('Location', '')
        dataset_read_path = '/dataset/%s' % package_name
        if allowed:
            # 200 means there are form errors
            assert response.status != 200, response.body
            # 302 is what is wanted - a redirect to the package read page
            assert_equal(response.status, 302)
            assert dataset_read_path in redirect, redirect
        else:
            assert_equal(response.status, 401)
            assert dataset_read_path not in redirect, redirect
            # also assert that you couldn't get the form in the first place
            assert_raises(paste.fixture.AppError, self._form_client.post_form, package_data, user_name=user_name, use_sysadmin_to_get_form=False, abort_on_bad_status=False)

    def assert_create(self, user_name, allowed=True):
        self.assert_create_or_edit('create', user_name, allowed)
    def assert_edit(self, user_name, allowed=True):
        self.assert_create_or_edit('edit', user_name, allowed)

    def test_create_by_sysadmin(self):
        self.assert_create('sysadmin', allowed=True)
    def test_create_by_nhsadmin(self):
        if model.engine_is_sqlite():
            raise SkipTest
        self.assert_create('nhsadmin', allowed=True)
    def test_create_by_nhseditor(self):
        self.assert_create('nhseditor', allowed=True)
    def test_create_by_user(self):
        self.assert_create('user', allowed=False)

    def test_edit_by_sysadmin(self):
        self.assert_edit('sysadmin', allowed=True)
    def test_edit_by_nhsadmin(self):
        self.assert_edit('nhsadmin', allowed=True)
    def test_edit_by_nhseditor(self):
        self.assert_edit('nhseditor', allowed=True)
    def test_edit_by_user(self):
        self.assert_edit('user', allowed=False)

class _PackageFormClient(WsgiAppCase):
    """
    A helper object that provides a single method for POSTing a package create form.

    It simulates form usage by first GETting the create form, pulling out the
    form fields from the form, and POSTing back the form with the provided data.
    """

    def __init__(self):
        _drop_sysadmin()
        self.admin = _create_sysadmin()

    def post_form(self, data, id=None, user_name=None, use_sysadmin_to_get_form=False,
                  abort_on_bad_status=True):
        """
        GETs the package-create or package-edit page, fills in the given fields, and POSTs the form.
        id - package id if you want to edit (otherwise it will create)
        user_name - of the user you want to do this as (default = sysadmin)
        abort_on_bad_status - you may not want this, to check the error response details
        """
        if id:
            offset = url_for(controller='package', action='edit', id=id)
        else:
            offset = url_for(controller='package', action='new')

        response = self.app.get(offset,
                                extra_environ={'REMOTE_USER': self.admin if use_sysadmin_to_get_form else (user_name or self.admin)},
                                )

        # get the form fields and values from the html
        form = response.forms['package-edit']
        form_fields = {}
        for field_name, field_value_obj in form.fields.items():
            if not field_name:
                continue
            form_fields[field_name] = field_value_obj[0].value

        self._assert_not_posting_extra_fields(form_fields.keys(), data.keys())

        # and fill in the form with the data provided
        form_fields.update(data)

        self._add_generated_fields(form_fields, data.keys())

        allowed_status = [200, 201, 302]
        if not abort_on_bad_status:
            allowed_status.append(401)

        return self.app.post(offset, params=form_fields,
                             extra_environ={'REMOTE_USER': user_name or self.admin},
                             status=allowed_status)

    def _add_generated_fields(self, form_fields, keys):
        """
        Additional resource fields are created dynamically client-side.  This
        method ensures that these fields are created if necessary.

         - form_fields is the dict that is modified to include any generated fields

         - keys is the iterable of field names being submitted.  This is used to work
           out which fields need generating.
        """

        def _index(k):
            """
            Returns the index specified in the given key

            >>> _index('additional_resources__2__url')
            2

            """
            return int(k.split('__')[1])

        resource_types = 'additional individual timeseries'.split()
        resource_counts = {}
        for resource_type in resource_types:
            resource_keys = filter(lambda k: k.startswith(resource_type+'_resources'), keys)
            resource_counts[resource_type] = max([0] + map(_index, resource_keys))

        # populate the form_fields dict with the generated fields up to the
        # given index.  If the field already exists, then leave it alone, as
        # it may contain pre-filled data already.
        for resource_type in resource_types:
            max_index = resource_counts[resource_type]
            for i in xrange(max_index+1):
                for field in ('resource_type',):    # TODO there are other fields too
                    key = '__'.join((resource_type+'_resources', str(i), field))
                    if not form_fields.has_key(key):
                        form_fields[key] = ''

    def _assert_not_posting_extra_fields(self, form_fields, data_fields):
        """
        Asserts that we're not posting data for fields that don't exist on the form

        Takes care of the one-to-many fields, eg. 'resources__0__url': an
        arbitrary number of these may be added client-side using javascript,
        so we only check that that the 0 index exists on the form.  This works
        by mapping fields like 'resources__0__url' to 'resources__num__url'.
        """
        one_to_many_re = re.compile('(resources)__\d+__(.+)$')
        sub = partial(one_to_many_re.sub,
                      lambda m: '%s__num__%s' % (m.group(1), m.group(2)))

        form_fields = set(map(sub, form_fields))
        data_fields = set(map(sub, data_fields))
        assert form_fields >= data_fields, str(data_fields - form_fields)

#### Helper methods ###

def _flatten_resource_dict(d):
    to_return = d.copy()
    for resource_type in 'additional timeseries individual'.split():
        resource_type = resource_type + '_resources'
        for index, resource in enumerate(to_return.get(resource_type,[])):
            for field, value in resource.items():
                form_field_name = '__'.join((resource_type, str(index), field))
                to_return[form_field_name] = value
        try:
            del to_return[resource_type]
        except:
            pass
    return to_return

def _create_sysadmin():
    model.repo.new_revision()
    sysadmin_user = model.User(name='sysadmin')
    model.Session.add(sysadmin_user)
    model.add_user_to_role(sysadmin_user, model.Role.ADMIN, model.System())
    model.repo.commit_and_remove()
    return 'sysadmin'

def _drop_sysadmin():
    if model.User.get('sysadmin'):
        model.repo.new_revision()
        model.User.get('sysadmin').delete()
        model.repo.commit_and_remove()

### Form data used in this module ###

_EXAMPLE_FORM_DATA = {
        # Dataset info
        'name'                  : 'new_name',
        'title'                 : 'New Package Title',
        'notes'                 : 'A multi-line\ndescription',

        # Publisher / contact details
        'groups__0__name'        : 'publisher-1',
        'contact-name'           : 'Publisher custom name',
        'contact-email'          : 'Publisher 1 contact email', # not custom: same as the group
        'contact-phone'          : 'Publisher custom phone',
        'foi-name'               : 'FOI custom name',
        'foi-email'              : 'FOI custom email',
        'foi-phone'              : 'FOI custom phone',
        'foi-web'                : 'FOI custom web',

        # additional resources
        'additional_resources'  : [
            {'url'              : 'http://www.example.com/additiona_resource',
             'description'      : 'An additional resource',
             'format'           : 'csv'},
            {'url'              : 'http://www.example.com/additiona_resource_2',
             'description'      : 'Another additional resource',
             'format'           : 'xml'}
        ],

        # Themes and tags
        'theme-primary'         : 'Health',
        'theme-secondary'       : 'Education', # TODO: check multiple boxes
        'tag_string'            : 'tag1, tag2, a multi word tag',

        # The rest
        'mandate'               : 'http://example.com/mandate',
        'access_constraints'    : 'Free-from license',
        'license_id'            : '',
        'temporal_coverage-from': '1/1/2010',
        'temporal_coverage-to'  : '1/1/2012',
        'geographic_coverage'   : 'england', # TODO: check multiple boxes
}

# An example of data for creating an individual dataset
_EXAMPLE_INDIVIDUAL_DATA = _EXAMPLE_FORM_DATA.copy()
_EXAMPLE_INDIVIDUAL_DATA.update({
        # individual resources
        'individual_resources'     : [
            {'url'                 : 'http://www.example.com',
             'description'         : 'A resource',
             'format'              : 'xml'},
            {'url'                 : 'http://www.google.com',
             'description'         : 'A search engine',
             'format'              : 'sdmx'}
        ]
})

# An example of data for creating an timeseries dataset
_EXAMPLE_TIMESERIES_DATA = _EXAMPLE_FORM_DATA.copy()
_EXAMPLE_TIMESERIES_DATA.update({
            # Timeseries data
            'update_frequency'      : 'other',
            'update_frequency-other': 'solstices',
            'timeseries_resources'  : [
                {'description'      : 'Summer solstice 2010',
                 'url'              : 'http://example.com/data/S2010',
                 'date'             : 'Summer 2010',
                 'format'           : 'xml'},

                {'description'      : 'Winter solstice 2010',
                 'url'              : 'http://example.com/data/W2010',
                 'date'             : 'Winter 2010',
                 'format'           : 'rdf'},

                {'description'      : 'Summer solstice 2011',
                 'url'              : 'http://example.com/data/S2011',
                 'date'             : 'Summer 2011',
                 'format'           : 'csv'},

                {'description'      : 'Winter solstice 2011',
                 'url'              : 'http://example.com/data/W2011',
                 'date'             : 'Winter 2011',
                 'format'           : 'xls'}
            ],
})

_EXAMPLE_FORM_DATA       = _flatten_resource_dict(_EXAMPLE_FORM_DATA)
_EXAMPLE_INDIVIDUAL_DATA = _flatten_resource_dict(_EXAMPLE_INDIVIDUAL_DATA)
_EXAMPLE_TIMESERIES_DATA = _flatten_resource_dict(_EXAMPLE_TIMESERIES_DATA)

_EXAMPLE_GROUPS = [
    {'name': 'publisher-1',
     'title': 'Publisher One',
     'contact-email': 'Publisher 1 contact email'},
    {'name': 'publisher-2',
     'title': 'Publisher Two'},
]

_UKLP_DATASET = json.loads('{"maintainer": null, "maintainer_email": null, "metadata_created": "2011-06-03T12:17:54.351438", "relationships": [], "metadata_modified": "2011-12-22T16:40:15.831307", "author": null, "author_email": null, "state": "active", "version": null, "license_id": null, "type": null, "resources": [], "tags": ["Climate change", "Geological mapping", "Geology", "NERC_DDC"], "groups": [], "name": "1-1-5m-scale-geology-through-climate-change-map-covering-uk-mainland-northern-ireland-and-eire", "isopen": false, "license": null, "notes_rendered": "<p>1:1.5M scale \'Geology Through Climate Change\' map covering UK mainland, Northern Ireland and Eire. This poster map shows the rocks of Britain and Ireland in a new way, grouped and coloured according to the environment under which they were formed. Photographs illustrate modern-day environments, alongside images of the typical rock types which are formed in them. The ages of the rocks are shown in a timeline, which also shows global temperatures and sea levels changing through time. The changing positions of Britain and Ireland as they drifted northwards through geological time are illustrated too. It was jointly produced by the BGS, the Geological Survey of Northern Ireland and the Geological Survey of Ireland. It has been endorsed by a range of teaching organisations including WJEC, OCR, The Association of Teaching Organisations of Ireland and the Earth Science Teachers Association. Although primarily intended as a teaching resource, the poster map will be of interest to anyone seeking to understand the imprint geological time has left in the rocks of our islands. This poster map is free, all you pay is the postage and packing.\\n</p>", "url": null, "ckan_url": "http://releasetest.ckan.org/dataset/1-1-5m-scale-geology-through-climate-change-map-covering-uk-mainland-northern-ireland-and-eire", "notes": "1:1.5M scale \'Geology Through Climate Change\' map covering UK mainland, Northern Ireland and Eire. This poster map shows the rocks of Britain and Ireland in a new way, grouped and coloured according to the environment under which they were formed. Photographs illustrate modern-day environments, alongside images of the typical rock types which are formed in them. The ages of the rocks are shown in a timeline, which also shows global temperatures and sea levels changing through time. The changing positions of Britain and Ireland as they drifted northwards through geological time are illustrated too. It was jointly produced by the BGS, the Geological Survey of Northern Ireland and the Geological Survey of Ireland. It has been endorsed by a range of teaching organisations including WJEC, OCR, The Association of Teaching Organisations of Ireland and the Earth Science Teachers Association. Although primarily intended as a teaching resource, the poster map will be of interest to anyone seeking to understand the imprint geological time has left in the rocks of our islands. This poster map is free, all you pay is the postage and packing.", "license_title": null, "ratings_average": null, "extras": {"bbox-east-long": "180.0000", "temporal_coverage-from": "[]", "resource-type": "dataset", "bbox-north-lat": "90.0000", "coupled-resource": "[]", "guid": "9df8df53-2a24-37a8-e044-0003ba9b0d98", "bbox-south-lat": "-90.0000", "temporal_coverage-to": "[\\"2008\\"]", "spatial-reference-system": "urn:ogc:def:crs:EPSG::4326", "spatial": "{\\"type\\":\\"Polygon\\",\\"coordinates\\":[[[180.0000, -90.0000],[180.0000, 90.0000], [-180.0000, 90.0000], [-180.0000, -90.0000], [180.0000, -90.0000]]]}", "access_constraints": "[\\"copyright: The dataset is made freely available for access, e.g. via the Internet. Either no third party data / information is contained in the dataset or BGS has secured written permission from the owner(s) of any third party data / information contained in the dataset to make the dataset freely accessible.\\", \\"The poster is copyright of NERC, copyright of Geological Survey of Ireland and copyright of Geological Survey of Northern Ireland.\\"]", "contact-email": "enquiries@bgs.ac.uk", "bbox-west-long": "-180.0000", "metadata-date": "2011-12-16T17:19:00", "dataset-reference-date": "[{\\"type\\": \\"publication\\", \\"value\\": \\"2008\\"}]", "published_by": 15004, "frequency-of-update": "asNeeded", "licence": "[]", "harvest_object_id": "56b36936-a369-4991-bd44-9e65e0ae146e", "responsible-party": "British Geological Survey (distributor)", "UKLP": "True", "spatial-data-service-type": "", "metadata-language": "eng"}, "ratings_count": 0, "title": "1:1.5M scale \'Geology Through Climate Change\' Map Covering UK mainland, Northern Ireland and Eire.", "revision_id": "37dfbc09-9d70-4839-86a0-7e33cde8299a"}')


