"""
High-level functional tests for the create/edit package form.

The new package form is being refactored so as not to use sqlalchemy.  These
are the tests for this form.  For tests based on the sqlalchemy-based form,
see 'test_package_gov3.py'.
"""
from functools import partial
import re

from nose.plugins.skip import SkipTest

from ckanext.dgu.tests import Gov3Fixtures

from ckan.lib.create_test_data import CreateTestData
from ckan.lib.field_types import DateType
from ckan.tests import WsgiAppCase, CommonFixtureMethods
from ckan.tests.html_check import HtmlCheckMethods

def url_for(**kwargs):
    """
    TODO: why isn't the real url_for picking up the correct route?
    """
    from ckan.tests import url_for as _url_for
    url = _url_for(**kwargs)
    return url.replace('dataset','package')

class TestFormRendering(WsgiAppCase, HtmlCheckMethods, CommonFixtureMethods):
    """
    Tests that the various fields are represeted correctly in the form.
    """

    # Fields we expect to see on the rendered form.
    # input name -> (Label text , input type)
    # for example:
    #   <label for="title">Title *</label>
    #   <input name="title"/>
    # if Label text is None, it's not search for
    _expected_fields = {
        # Name section
        'title':     ('Name:', 'input'),
        'name':      ('Unique identifier for this data record', 'input'),
        
        # Data section
        'package_type':                     (None, 'input'),
        'update_frequency':                 ('Update frequency', 'select'),
        'update_frequency-other':           ('Other:', 'input'),
        'resources__0__name-individual':    (None, 'input'),
        'resources__0__url-individual':     (None, 'input'),
        'resources__0__name-timeseries':    (None, 'input'),
        'resources__0__url-timeseries':     (None, 'input'),
        'resources__0__url-date':           (None, 'input'),

        # Description section
        'notes':     (None, 'textarea'),

        # Contact details section
        'published_by':         ('Published by:', 'select'),
        'publisher_email':      ('Email address:', 'input'),
        'publisher_url':        ('Link:', 'input'),
        'publisher_telephone':  ('Telephone number:', 'input'),
        'author':               ('Contact', 'input'),
        'author_email':         ('Contact email', 'input'),
        'author_url':           ('Contact link:', 'input'),
        'author_telephone':     ('Contact telephone:', 'input'),

        # Themes and tags section
        'primary_theme':        (None, 'select'),
        'secondary_theme':      (None, 'input'),
        'tag_string':           ('Tags', 'input'),
        'url':                  ('URL', 'input'),
        'taxonomy_url':         ('Taxonomy URL', 'input'),
        'mandate':              ('Mandate', 'input'),
        'license_id':           ('Licence *', 'select'),
        'national_statistic':   ('National Statistic', 'input'),

        # Additional resources section
        'resources__0__name-additional':    ('Description:', 'input'),
        'resources__0__url-additional':     ('Link:', 'input'),

        # Time & date section
        'date_released':                ('Date released', 'input'),
        'date_updated':                 ('Date updated', 'input'),
        'date_update_future':           ('Date to be published', 'input'),
        'precision':                    ('Precision', 'input'),
        'temporal_granularity':         ('Temporal granularity', 'select'),
        'temporal_granularity-other':   ('Other', 'input'),
        'temporal_coverage':            ('Temporal coverage', 'input'),

        # Geographic coverage section
        'geographic_granularity':       ('Geographic granularity', 'select'),
        'geographic_granularity-other': ('Other', 'input'),
        'geographic_coverage':          ('Geographic coverage', 'input'),
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

    @classmethod
    def setup(self):
        """
        Create standard gov3 test fixtures for this suite.

        This test class won't be editing any packages, so it's ok to only
        create these fixtures once.
        """
        self.fixtures = Gov3Fixtures()
        self.fixtures.create()

    @classmethod
    def teardown(self):
        """
        Cleanup the Gov3Fixtures
        """
        self.fixtures.delete()

    def test_new_form_has_all_fields(self):
        """
        Asserts that a form for a new package contains the various expected fields
        """
        offset = url_for(controller='package', action='new')
        response = self.app.get(offset)

        # quick check that we're checking the correct url
        assert "package" in offset

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
        response = self.app.get(offset)

        for field in self._unexpected_fields:
            match = re.search('<(input|textarea|select) [^>]* name="%s"' % field,
                              response.body)
            assert not match , '"%s" found in response: "%s"' % (field, match.group(0))

    def test_edit_form_form_has_all_fields(self):
        """
        Asserts that edit-form of a package has the fields prefilled correctly.
        """
        package = self.fixtures.pkgs[0]

        offset = url_for(controller='package', action='edit', id=package['name'])
        response = self.app.get(offset)

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
        expected_field_values['tag_string'] = package['tags']
        expected_field_values['license_id'] = package['license']

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
            expected_field_values[field_name] = _convert_date(expected_field_values[field_name])

        # TODO: fix these fields
        del expected_field_values['published_by']
        del expected_field_values['published_via']
    
        for field_name, expected_value in expected_field_values.items():
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
        response = self.app.get(offset)

        for field in self._unexpected_fields:
            match = re.search('<(input|textarea|select) [^>]* name="%s"' % field,
                              response.body)
            assert not match , '"%s" found in response: "%s"' % (field, match.group(0))

class TestFormValidation(object):
    """
    A suite of tests that check validation of the various form fields.
    """

    def __init__(self):
        self._form_client = _PackageFormClient()

    def test_title_non_empty(self):
        """Asserts that the title cannot be empty"""
        data = {'title': ''}
        response = self._form_client.post_form(data)
        assert 'Title: Missing value' in response.body

    def test_name_non_empty(self):
        """Asserts that the name (uri identifier) is non-empty"""
        data = {'name': ''}
        response = self._form_client.post_form(data)
        assert 'Name: Missing value' in response.body

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
        assert 'Notes: Missing value' in response.body

    def test_date_released_only_accepts_well_formed_dates(self):
        """
        Asserts that date_released only accepts dates.
        
        TODO: what's the granularity of this field meant to be?  Schema indicates
              it's very loose, e.g. "Dec/2011", whereas form help indicates it's
              to the day.
        TODO: are these even on the new form?
        """
        raise SkipTest('date_released field needs spec.')

    def test_date_updated_only_accepts_well_formed_dates(self):
        """
        Asserts that date_updated only accepts dates.
        
        TODO: what's the granularity of this field meant to be?  Schema indicates
              it's very loose, e.g. "Dec/2011", whereas form help indicates it's
              to the day.
        TODO: are these even on the new form?
        """
        raise SkipTest('date_updated field needs spec.')

    def test_date_update_future_only_accepts_well_formed_dates(self):
        """
        Asserts that date_update_future only accepts dates.
        
        TODO: what's the granularity of this field meant to be?  Schema indicates
              it's very loose, e.g. "Dec/2011", whereas form help indicates it's
              to the day.
        TODO: are these even on the new form?
        """
        raise SkipTest('date_update_future field needs spec.')

class TestPackageCreation(CommonFixtureMethods):
    """
    A suite of tests that check that packages are created correctly through the creation form.
    """
    
    _package_data = {
        'name': 'new_name',
        'title': 'New Package Title',
        'notes': 'The package abstract.',
        'author': 'A Job Role',
        'author_email': 'role@department.gov.uk',
        'tag_string': 'tag1, tag2, multi word tag',
        'published_by': 'A publisher',

        # resources
        'resources__0__url': 'http://www.example.com',
        'resources__0__description': 'A resource',
        'resources__1__url': 'http://www.google.com',
        'resources__1__description': 'A search engine',
    }

    def __init__(self):
        self._form_client = _PackageFormClient()

    def teardown(self):
        """
        Delete any created packages
        """
        CreateTestData.delete()

    def test_submitting_a_valid_create_form_creates_a_new_package(self):
        """Assert that submitting a valid create form does indeed create a new package"""
        # setup fixture
        package_name = self._package_data['name']
        CreateTestData.flag_for_deletion(package_name)
        assert not self.get_package_by_name(package_name),\
            'Package "%s" already exists' % package_name
        
        # create package via form
        self._form_client.post_form(self._package_data)
        
        # ensure it's correct
        pkg = self.get_package_by_name(package_name)
        assert pkg
        assert self._package_data['name'] == pkg.name
        assert self._package_data['title'] == pkg.title
        assert self._package_data['notes'] == pkg.notes
        assert self._package_data['author'] == pkg.author
        assert self._package_data['author_email'] == pkg.author_email
        assert set(['tag1', 'tag2', 'multi word tag']) ==\
               set(tag.name for tag in pkg.tags)
        assert self._package_data['published_by'] == pkg.extras['published_by']
        assert self._package_data['resources__0__url'] ==\
               pkg.resources[0].url
        assert self._package_data['resources__1__url'] ==\
               pkg.resources[1].url
        assert self._package_data['resources__0__description'] ==\
               pkg.resources[0].description
        assert self._package_data['resources__1__description'] ==\
               pkg.resources[1].description

class _PackageFormClient(WsgiAppCase):
    """
    A helper object that provides a single method for POSTing a package create form.

    It simulates form usage by first GETting the create form, pulling out the
    form fields from the form, and POSTing back the form with the provided data.
    """

    def post_form(self, data):
        """
        GETs the package-create page, fills in the given fields, and POSTs the form.
        """
        offset = url_for(controller='package', action='new')
        response = self.app.get(offset)
        
        # parse the form fields from the html
        form_field_matches = re.finditer('<(input|select|textarea) [^>]*name="(?P<field_name>[^"]+)"',
                                         response.body)

        # initialise all fields with an empty string
        form_fields = dict((match.group('field_name'), '') for match in form_field_matches)
        form_fields['save'] = 'Save'
        
        self._assert_not_posting_extra_fields(form_fields.keys(), data.keys())

        # and fill in the form with the data provided
        form_fields.update(data)
        return self.app.post(offset, params=form_fields)

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
        assert form_fields >= data_fields, str(form_fields - data_fields)

def _convert_date(datestring):
    """
    Converts a date-string to that rendered by the form.

    It does this by converting to db format, and then back to a string.
    """
    return DateType.db_to_form(datestring)
