"""
High-level functional tests for the create/edit package form.

The new package form is being refactored so as not to use sqlalchemy.  These
are the tests for this form.  For tests based on the sqlalchemy-based form,
see 'test_package_gov3.py'.

TODO:

[X] Assert all fields are being filled with data correctly
[X] Test validation of the resource_types: disallow 'docs' for example.
[ ] Sub-themes

"""
from functools import partial
import re

from nose.tools import assert_equal, assert_in
from nose.plugins.skip import SkipTest

from ckanext.dgu.tests import Gov3Fixtures
import ckanext.dgu.lib.helpers

from ckan.lib.create_test_data import CreateTestData
from ckan.lib.field_types import DateType
from ckan.tests import WsgiAppCase, CommonFixtureMethods, url_for
from ckan.tests.html_check import HtmlCheckMethods

class TestFormRendering(WsgiAppCase, HtmlCheckMethods, CommonFixtureMethods):
    """
    Tests that the various fields are represeted correctly in the form.
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
        'timeseries_resources__0__description': (None, 'input'),
        'timeseries_resources__0__url':         (None, 'input'),
        'timeseries_resources__0__date':        (None, 'input'),

        # Description section
        'notes':     (None, 'textarea'),

        # Contact details section
        'published_by':             ('Published by:', 'select'),
        'published_by-email':       (None, 'input'),
        'published_by-url':         (None, 'input'),
        'published_by-telephone':   (None, 'input'),
        'author':                   ('FOI Contact:', 'input'),
        'author_email':             (None, 'input'),
        'author_url':               (None, 'input'),
        'author_telephone':         (None, 'input'),

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
        'additional_resources__0__description': (None, 'input'),
        'additional_resources__0__url':         (None, 'input'),

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
        assert_in('Name: Missing value', response)

        # TODO: re-instate these fields
        del package_data['secondary_theme']

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
            expected_field_values[field_name] = _convert_date(expected_field_values[field_name])

        # TODO: fix these fields
        del expected_field_values['published_by']
        del expected_field_values['published_via']
    
        # Ensure the resources have been un-merged correctly.
        for resource_type in 'additional timeseries individual'.split():
            resource_type += '_resources'

            fields = []
            for field_name in [f for f in self._expected_fields if f.startswith(resource_type)]:
                fields.append(field_name.split('__')[-1])

            resources = getattr(ckanext.dgu.lib.helpers, resource_type)(package)
            for index, resource in enumerate(resources):
                for field in fields:
                    # eg. additional_resources__0__url
                    full_field_name = '__'.join([resource_type,
                                                 str(index),
                                                 field])
                    try:
                        expected_field_values[full_field_name] = resource[field]
                    except KeyError:
                        expected_field_values[full_field_name] = resource['extras'][field]

        for field_name, expected_value in expected_field_values.items():
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
        response = self.app.get(offset)

        # TODO: test secondary theme
        del package_data['secondary_theme']

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
            assert_in("'Invalid resource type: %s']" % resource_type,
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
            assert_in("'Invalid resource type: %s']" % resource_type,
                      response.body)

            data = {
                'individual_resources__0__description':   'Individual resource 1',
                'individual_resources__0__url':           'http://example.com/data1',
                'individual_resources__0__resource_type': resource_type,
            }
            response = self._form_client.post_form(data)
            assert_in("'Invalid resource type: %s']" % resource_type,
                      response.body)

class TestPackageCreation(CommonFixtureMethods):
    """
    A suite of tests that check that packages are created correctly through the creation form.
    """
    
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
        assert_equal(package_data['author'], pkg.author)
        assert_equal(package_data['author_email'], pkg.author_email)
        assert_equal(package_data['published_by'], pkg.extras['published_by'])

        # Extra data
        # Timeseries data
        expected_timeseries_keys = filter(lambda k: k.startswith('timeseries_resources'),
                                          package_data.keys())
        timeseries_resources = ckanext.dgu.lib.helpers.timeseries_resources(pkg.as_dict())
        assert_equal(len(timeseries_resources), 4)
        for key in expected_timeseries_keys:
            index, field = key.split('__')[1:]
            index = int(index)
            assert_equal(package_data[key],
                         timeseries_resources[index][field])

        # Publisher / contact details
        assert_equal(package_data['published_by'], pkg.extras['published_by'])
        assert_equal(package_data['published_by-email'], pkg.extras['published_by-email'])
        assert_equal(package_data['published_by-url'], pkg.extras['published_by-url'])
        assert_equal(package_data['published_by-telephone'], pkg.extras['published_by-telephone'])
        assert_equal(package_data['author'], pkg.author)
        assert_equal(package_data['author_email'], pkg.author_email)
        assert_equal(package_data['author_url'], pkg.extras['author_url'])
        assert_equal(package_data['author_telephone'], pkg.extras['author_telephone'])

        # Themes and tags
        assert_equal(package_data['primary_theme'], pkg.extras['primary_theme'])

        # TODO clarification on sub-themes needed:
        #       - equality of sub-themes regardless of parent theme?
        #       - searchable?
        #
        #      And from that, need to decide how they should be stored.
        #      Until then, we skip this assertion.
        # assert_equal(set(package_data['secondary_theme']),
        #              set(pkg.extras['secondary_theme']))

        assert_equal(set(['tag1', 'tag2', 'a multi word tag']),
                     set(tag.name for tag in pkg.tags))

        # Additional resources
        expected_additional_keys = filter(lambda k: k.startswith('additional_resources'),
                                          package_data.keys())
        additional_resources = ckanext.dgu.lib.helpers.additional_resources(pkg.as_dict())
        assert_equal(len(additional_resources), 2)
        for key in expected_additional_keys:
            index, field = key.split('__')[1:]
            index = int(index)
            assert_equal(package_data[key],
                         additional_resources[index][field])

        assert_equal(package_data['url'], pkg.url)
        assert_equal(package_data['taxonomy_url'], pkg.extras['taxonomy_url'])
        assert_equal(package_data['mandate'], pkg.extras['mandate'])
        assert_equal(package_data['license_id'], pkg.license_id)

        assert_equal(package_data['date_released'], _convert_date(pkg.extras['date_released']))
        assert_equal(package_data['date_updated'], _convert_date(pkg.extras['date_updated']))
        assert_equal(package_data['date_update_future'], _convert_date(pkg.extras['date_update_future']))
        assert_equal(package_data['precision'], pkg.extras['precision'])
        assert_equal(package_data['temporal_granularity-other'], pkg.extras['temporal_granularity'])
        assert_equal(package_data['temporal_coverage-from'], _convert_date(pkg.extras['temporal_coverage-from']))
        assert_equal(package_data['temporal_coverage-to'], _convert_date(pkg.extras['temporal_coverage-to']))
        assert_equal(package_data['geographic_granularity-other'], pkg.extras['geographic_granularity'])
        assert_in('England', pkg.extras['geographic_coverage'])

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
        # TODO: there's an obvious deficiency: this will only pick up field
        #       values if they are declared *after* the field name.
        form_field_matches = re.finditer('<(input|select|textarea) [^>]*'
                                         'name="(?P<field_name>[^"]+)"'
                                         '( [^>]*value="(?P<field_value>[^"]+)")?',
                                         response.body)

        # initialise all fields with an empty string, or with the form's pre-filled value
        form_fields = dict( (match.group('field_name'), match.groupdict('').get('field_value')) \
                                for match in form_field_matches)
        
        self._assert_not_posting_extra_fields(form_fields.keys(), data.keys())

        # and fill in the form with the data provided
        form_fields.update(data)
        self._add_generated_fields(form_fields, data.keys())
        return self.app.post(offset, params=form_fields)

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


#### Helper methods ###

def _convert_date(datestring):
    """
    Converts a date-string to that rendered by the form.

    It does this by converting to db format, and then back to a string.
    """
    return DateType.db_to_form(datestring)

### Form data used in this module ###

_EXAMPLE_FORM_DATA = {
        # Dataset info
        'name'                  : 'new_name',
        'title'                 : 'New Package Title',
        'notes'                 : 'A multi-line\ndescription',
        'author'                : 'A Job Role',
        'author_email'          : 'role@department.gov.uk',
            
        # Publisher / contact details
        'published_by'          : 'pub2',
        'published_by-email'    : 'pub2@example.com',
        'published_by-url'      : 'http://example.com/publishers/pub2',
        'published_by-telephone': '01234 567890',
        'author'                : 'A. Person',
        'author_email'          : 'a.person@example.com',
        'author_telephone'      : '09876 543210',
        'author_url'            : 'http://example.com/people/A-Person',


        # additional resources
        'additional_resources'  : [
            {'url'              : 'http://www.example.com/additiona_resource',
             'description'      : 'An additional resource'},
            {'url'              : 'http://www.example.com/additiona_resource_2',
             'description'      : 'Another additional resource'}
        ],

        # Themes and tags
        'primary_theme'         : 'Health',
        'secondary_theme'       : ['Education', 'Transportation', 'Government'],
        'tag_string'            : 'tag1, tag2, a multi word tag',

        # The rest
        'url'                   : 'http://example.com/another_url',
        'taxonomy_url'          : 'http://example.com/taxonomy',
        'mandate'               : 'http://example.com/mandate',
        'license_id'            : 'odc-pddl',
        'date_released'         : '1/1/2011',
        'date_updated'          : '1/1/2012',
        'date_update_future'    : '1/9/2012',
        'precision'             : 'As supplied',
        'temporal_granularity'  : 'other',
        'temporal_granularity-other': 'lunar month',
        'temporal_coverage-from': '1/1/2010',
        'temporal_coverage-to'  : '1/1/2012',
        'geographic_granularity': 'other',
        'geographic_granularity-other': 'postcode',
        'geographic_coverage'   : 'england', # TODO: check multiple boxes
}

# An example of data for creating an individual dataset
_EXAMPLE_INDIVIDUAL_DATA = _EXAMPLE_FORM_DATA.copy()
_EXAMPLE_INDIVIDUAL_DATA.update({
        # individual resources
        'individual_resources'     : [
            {'url'                 : 'http://www.example.com',
             'description'         : 'A resource'},
            {'url'                 : 'http://www.google.com',
             'description'         : 'A search engine'}
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
                 'date'             : 'Summer 2010'},

                {'description'      : 'Winter solstice 2010',
                 'url'              : 'http://example.com/data/W2010',
                 'date'             : 'Winter 2010'},

                {'description'      : 'Summer solstice 2011',
                 'url'              : 'http://example.com/data/S2011',
                 'date'             : 'Summer 2011'},

                {'description'      : 'Winter solstice 2011',
                 'url'              : 'http://example.com/data/W2011',
                 'date'             : 'Winter 2011'}
            ],
})

_EXAMPLE_FORM_DATA       = _flatten_resource_dict(_EXAMPLE_FORM_DATA)
_EXAMPLE_INDIVIDUAL_DATA = _flatten_resource_dict(_EXAMPLE_INDIVIDUAL_DATA)
_EXAMPLE_TIMESERIES_DATA = _flatten_resource_dict(_EXAMPLE_TIMESERIES_DATA)

