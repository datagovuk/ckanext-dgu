from nose.tools import assert_equal, assert_raises

from ckan.lib.navl.dictization_functions import flatten_dict, unflatten, Invalid

from ckanext.dgu.forms.validators import merge_resources, unmerge_resources, \
     validate_additional_resource_types, \
     validate_data_resource_types, \
     remove_blank_resources, \
     validate_license

class TestMergeResources(object):
    """
    Tests ckanaext.dgu.validators.merge_resources()
    """

    def test_simple_case(self):
        """
        Tests with just one set of resources defined.
        """
        data = {
            'additional_resources': [
                {'description': 'Description 1', 'url': 'Url 1'},
                {'description': 'Description 2', 'url': 'Url 2'},
            ]
        }

        flattened_data = flatten_dict(data)

        ignored = {}
        errors = dict([(k, []) for k in flattened_data.keys()])
        merge_resources(('__after',), flattened_data, errors, ignored)
        result_data = unflatten(flattened_data)

        expected_data = {
            'resources': [
                {'description': 'Description 1', 'url': 'Url 1'},
                {'description': 'Description 2', 'url': 'Url 2'},
            ]
        }

        assert_equal(result_data, expected_data)

    def test_with_two_resource_types_defined(self):
        """
        Tests with two resource types defined.
        """
        data = {
            'additional_resources': [
                {'description': 'Additional 1', 'url': 'A_Url 1'},
                {'description': 'Additional 2', 'url': 'A_Url 2'},
            ],
            'timeseries_resources': [
                {'description': 'Timeseries 1', 'url': 'T_Url 1', 'date': 'T_Date 1'},
                {'description': 'Timeseries 2', 'url': 'T_Url 2', 'date': 'T_Date 2'},
                {'description': 'Timeseries 3', 'url': 'T_Url 3', 'date': 'T_Date 3'},
            ]
        }

        flattened_data = flatten_dict(data)

        ignored = {}
        errors = dict([(k, []) for k in flattened_data.keys()])
        merge_resources(('__after',), flattened_data, errors, ignored)
        result_data = unflatten(flattened_data)

        expected_data = {
            'resources': [
                {'description': 'Additional 1', 'url': 'A_Url 1'},
                {'description': 'Additional 2', 'url': 'A_Url 2'},
                {'description': 'Timeseries 1', 'url': 'T_Url 1', 'date': 'T_Date 1'},
                {'description': 'Timeseries 2', 'url': 'T_Url 2', 'date': 'T_Date 2'},
                {'description': 'Timeseries 3', 'url': 'T_Url 3', 'date': 'T_Date 3'},
            ]
        }

        assert_equal(result_data, expected_data)

    def test_merging_does_not_occur_when_there_have_been_validation_errors(self):
        """
        Test resources aren't merged when there have been other validation errors.

        This is so that we don't throw out the user's original input.
        """
        data = {
            'additional_resources': [
                {'description': 'Description 1', 'url': 'Url 1'},
                {'description': 'Description 2', 'url': 'Url 2'},
            ]
        }

        flattened_data = flatten_dict(data)
        errors = {('some_error',): ['Oh dear, you did something wrong!']}
        ignored = {}
        merge_resources(('__after',), flattened_data, errors, ignored)
        result_data = unflatten(flattened_data)

        assert_equal(data, result_data)

    def test_merging_only_occurs_after_other_validation(self):
        """
        Test merge_resources checks that it's only called as a post-processor
        """
        assert_raises(Exception,
                      merge_resources, 'not__after', {}, {}, {})

    def test_error_keys_are_merged_over(self):
        """
        Test that the items in errors are merged over correctly too.

        Note - errors may contain key values not present in the data
        """
        data = {
            'additional_resources': [
                {'description': 'Additional 1', 'url': 'A_Url 1'},
                {'description': 'Additional 2', 'url': 'A_Url 2'},
            ],
            'timeseries_resources': [
                {'description': 'Timeseries 1', 'url': 'T_Url 1', 'date': 'T_Date 1'},
                {'description': 'Timeseries 2', 'url': 'T_Url 2', 'date': 'T_Date 2'},
                {'description': 'Timeseries 3', 'url': 'T_Url 3', 'date': 'T_Date 3'},
            ]
        }
        flattened_data = flatten_dict(data)

        errors = dict([(k, []) for k in flattened_data.keys()])
        # Add some extra fields into errors
        errors[('additional_resources', 0, 'resource_type')] = []
        errors[('additional_resources', 1, 'resource_type')] = []
        errors[('timeseries_resources', 0, 'resource_type')] = []
        errors[('timeseries_resources', 1, 'resource_type')] = []
        errors[('timeseries_resources', 2, 'resource_type')] = []

        ignored = {}
        merge_resources(('__after',), flattened_data, errors, ignored)
        result_errors = unflatten(errors)

        expected_errors = {
            'resources': [
                {'description': [], 'url': [], 'resource_type': []},
                {'description': [], 'url': [], 'resource_type': []},
                {'description': [], 'url': [], 'date': [], 'resource_type': []},
                {'description': [], 'url': [], 'date': [], 'resource_type': []},
                {'description': [], 'url': [], 'date': [], 'resource_type': []},
            ]
        }

        assert_equal(result_errors, expected_errors)

class TestUnmergeResources(object):
    """
    Tests ckanaext.dgu.validators.merge_resources()
    """

    def test_just_additional_resources(self):
        """
        Tests with just one set of additional resources defined.
        """
        data = {
            'resources': [
                {'description': 'Description 1', 'url': 'Url1', 'resource_type': 'documentation'},
                {'description': 'Description 2', 'url': 'Url2', 'resource_type': 'documentation'}
            ]
        }

        flattened_data = flatten_dict(data)

        ignored = {}
        errors = dict([(k, []) for k in flattened_data.keys()])
        unmerge_resources(('__after',), flattened_data, errors, ignored)
        result_data = unflatten(flattened_data)

        expected_data = {
            'additional_resources': [
                {'description': 'Description 1', 'url': 'Url1', 'resource_type': 'documentation'},
                {'description': 'Description 2', 'url': 'Url2', 'resource_type': 'documentation'}
            ]
        }
        expected_data.update(data)

        assert_equal(result_data, expected_data)

    def test_just_timeseries_resources(self):
        """
        Tests with just one set of timeseries resources defined.
        """
        data = {
            'resources': [
                {'description': 'Description 1',
                 'url': 'Url1',
                 'resource_type': 'api',
                 'date': '2011-12-25',},
                {'description': 'Description 2',
                 'url': 'Url2',
                 'resource_type': 'api',
                 'date': '2011-11-25'},
            ]
        }

        flattened_data = flatten_dict(data)

        ignored = {}
        errors = dict([(k, []) for k in flattened_data.keys()])
        unmerge_resources(('__after',), flattened_data, errors, ignored)
        result_data = unflatten(flattened_data)

        expected_data = {
            'timeseries_resources': [
                {'description': 'Description 1',
                 'url': 'Url1',
                 'resource_type': 'api',
                 'date': '2011-12-25'},
                {'description': 'Description 2',
                 'url': 'Url2',
                 'resource_type': 'api',
                 'date': '2011-11-25'}
            ]
        }
        expected_data.update(data)

        assert_equal(result_data, expected_data)

    def test_just_individual_resources(self):
        """
        Tests with just one set of individual resources defined.
        """
        data = {
            'resources': [
                {'description': 'Description 1',
                 'url': 'Url1',
                 'resource_type': 'api',
                 'date': ''},
                {'description': 'Description 2',
                 'url': 'Url2',
                 'resource_type': 'api',},
            ]
        }

        flattened_data = flatten_dict(data)

        ignored = {}
        errors = dict([(k, []) for k in flattened_data.keys()])
        unmerge_resources(('__after',), flattened_data, errors, ignored)
        result_data = unflatten(flattened_data)

        expected_data = {
            'individual_resources': [
                {'description': 'Description 1',
                 'url': 'Url1',
                 'resource_type': 'api',
                 'date': ''},
                {'description': 'Description 2',
                 'url': 'Url2',
                 'resource_type': 'api'},
            ]
        }
        expected_data.update(data)

        assert_equal(result_data, expected_data)

    def test_mixture_of_resource_types(self):
        """
        Test with a mixture of additional and individual resources
        """
        data = {
            'resources': [
                {'description': 'Description 1', 'url': 'Url1', 'resource_type': 'documentation'},
                {'description': 'Description 2', 'url': 'Url2', 'resource_type': 'api'},
                {'description': 'Description 3', 'url': 'Url3', 'resource_type': 'file'},
                {'description': 'Description 4', 'url': 'Url4', 'resource_type': 'documentation'}
            ]
        }

        flattened_data = flatten_dict(data)

        ignored = {}
        errors = dict([(k, []) for k in flattened_data.keys()])
        unmerge_resources(('__after',), flattened_data, errors, ignored)
        result_data = unflatten(flattened_data)

        expected_data = {
            'additional_resources': [
                {'description': 'Description 1', 'url': 'Url1', 'resource_type': 'documentation'},
                {'description': 'Description 4', 'url': 'Url4', 'resource_type': 'documentation'}
            ],
            'individual_resources': [
                {'description': 'Description 2', 'url': 'Url2', 'resource_type': 'api'},
                {'description': 'Description 3', 'url': 'Url3', 'resource_type': 'file'},
            ]
        }
        expected_data.update(data)

        assert_equal(result_data, expected_data)

    def test_error_keys_are_unmerged(self):
        """
        Test that the items in errors are unmerged too.

        Note - errors may contain key values not present in the data
        """
        data = {
            'resources': [
                # additional resources
                {'description': 'Additional 1', 'url': 'A_Url 1', 'resource_type': 'documentation'},
                {'description': 'Additional 2', 'url': 'A_Url 2', 'resource_type': 'documentation'},

                # individual resources
                {'description': 'Individual 1', 'url': 'I_Url 1', 'resource_type': 'api'},
                {'description': 'Individual 2', 'url': 'I_Url 2', 'resource_type': 'api'},
                {'description': 'Individual 3', 'url': 'I_Url 3', 'resource_type': 'api'},
            ],
        }
        flattened_data = flatten_dict(data)

        errors = dict([(k, []) for k in flattened_data.keys()])
        # Add some extra fields into errors
        errors[('resources', 0, 'foo')] = []
        errors[('resources', 1, 'foo')] = []
        errors[('resources', 2, 'foo')] = []
        errors[('resources', 3, 'foo')] = []
        errors[('resources', 4, 'foo')] = []

        ignored = {}
        unmerge_resources(('__after',), flattened_data, errors, ignored)
        result_errors = unflatten(errors)

        expected_errors = {
            'additional_resources': [
                {'description': [], 'url': [], 'resource_type': [], 'foo': []},
                {'description': [], 'url': [], 'resource_type': [], 'foo': []},
            ],
            'individual_resources': [
                {'description': [], 'url': [], 'resource_type': [], 'foo': []},
                {'description': [], 'url': [], 'resource_type': [], 'foo': []},
                {'description': [], 'url': [], 'resource_type': [], 'foo': []},
            ]
        }

        assert_equal(result_errors, expected_errors)

class TestResourceTypeValidators(object):
    """
    Tests the validate_additional_resource_types and validate_data_resource_types functions.
    """

    def test_validate_additional_resource_validation(self):
        """
        Test validate_addition_resource_types only allows 'documentation'.
        """
        f = validate_additional_resource_types
        _ = None

        # allows 'documentation'
        assert_equal (f('documentation'), 'documentation')

        # disallows 'docs'
        assert_raises(Invalid, f, 'docs')

    def test_validate_additional_resource_provides_a_default_value(self):
        """
        Test validate_additional_resource_types provides 'documentation' as a default value
        """
        f = validate_additional_resource_types

        assert_equal (f(''), 'documentation')
        assert_equal (f(None), 'documentation')

    def test_validate_data_resource_validation(self):
        """
        Test validate_data_resource_types only allows 'file' or 'api'.
        """
        f = validate_data_resource_types

        # allows 'file' and 'api;
        assert_equal (f('api'), 'api')
        assert_equal (f('file'), 'file')

        # disallows 'docs'
        assert_raises(Invalid, f, 'docs')

    def test_validate_data_resource_provides_a_default_value(self):
        """
        Test validate_data_resource_types provides 'file' as a default value
        """
        f = validate_data_resource_types

        assert_equal (f(''), 'file')
        assert_equal (f(None), 'file')

class TestRemoveBlankResources:
    def test_remove_blank_resources(self):
        """
        Blank rows occur as a result of switching to/from timeseries resource
        or deleting a resource in a table (you can't remove the row itself).
        Therefore remove blank rows.
        """
        import nose
        nose.tools.maxDiff = 2000
        data = {
            'additional_resources': [
                {'id': '1', 'description': 'Additional 1', 'url': 'A_Url 1', 'resource_type': 'documentation'},
                {'id': '2', 'description': '', 'url': '', 'resource_type': 'documentation'},
                {'id': '3', 'description': 'Additional 3', 'url': 'A_Url 3', 'resource_type': 'documentation'},
            ],
            'timeseries_resources': [
                {'id': '4', 'description': 'Timeseries 1', 'url': 'T_Url 1', 'date': 'T_Date 1', 'resource_type': 'file'},
                {'id': '5', 'description': '', 'url': '', 'date': '', 'resource_type': 'file'},
                {'id': '6', 'description': 'Timeseries 3', 'url': '', 'date': 'T_Date 3', 'resource_type': 'file'},
            ]
        }

        flattened_data = flatten_dict(data)

        ignored = {}
        errors = {}
        # Add errors that validation would pick up for the blank resources
        errors[('additional_resources', 1, 'url')] = ['not empty']
        errors[('timeseries_resources', 1, 'url')] = ['not empty']
        # Add a real validation error
        errors[('timeseries_resources', 2, 'url')] = ['not empty']
        remove_blank_resources(('__after',), flattened_data, errors, ignored)
        result_data = unflatten(flattened_data)

        expected_data = {
            'additional_resources': [
                {'id': '1', 'description': 'Additional 1', 'url': 'A_Url 1', 'resource_type': 'documentation'},
                {'id': '3', 'description': 'Additional 3', 'url': 'A_Url 3', 'resource_type': 'documentation'},
            ],
            'timeseries_resources': [
                {'id': '4', 'description': 'Timeseries 1', 'url': 'T_Url 1', 'date': 'T_Date 1', 'resource_type': 'file'},
                {'id': '6', 'description': 'Timeseries 3', 'url': '', 'date': 'T_Date 3', 'resource_type': 'file'},
            ]
        }
        expected_errors = {('timeseries_resources', 2, 'url'): ['not empty']}

        assert_equal(result_data, expected_data)
        assert_equal(errors, expected_errors)


class TestValidateLicense:
    def check(self, license_id, licence, in_form,
              expected_data, expected_errors):
        errors = {}
        # The form submits a different key for the licence extra to that which
        # you'd supply when using the API (e.g. doing package_update during
        # harvesting). This is because the validation wants to know whether you
        # are using the form or not since it uses slightly different validation.
        licence_key = 'licence_in_form' if in_form else 'licence'
        data = {('license_id',): license_id,
                (licence_key,): licence}
        errors = {('license_id',): None}
        validate_license(key=None, data=data, errors=errors, context=None)
        assert_equal(data, expected_data)
        assert_equal(errors, expected_errors)

    def test_form_dropdown(self):
        self.check('uk-ogl', '', True,
                   {('license_id',): 'uk-ogl', ('licence',): ''},
                   {('license_id',): None, })

    def test_form_free_text(self):
        self.check('__other__', 'Free form', True,
                   {('license_id',): None,
                    ('extras', 99, 'key'): 'licence',
                    ('extras', 99, 'value'): 'Free form'},
                   {('license_id',): None})

    def test_form_ogl_detected_as_part(self):
        self.check('__other__', 'OGL and other terms', True,
                   {('license_id',): 'uk-ogl',
                    ('extras', 99, 'key'): 'licence',
                    ('extras', 99, 'value'): 'OGL and other terms'},
                   {('license_id',): None})

    def test_form_ogl_detected_in_whole(self):
        self.check('__other__', 'OGL', True,
                   {('license_id',): 'uk-ogl', ('licence',): ''},
                   {('license_id',): None, })

    def test_form_blank(self):
        self.check('', '', True,
                   {('license_id',): None, ('licence',): ''},
                   {('license_id',): ['Please provide a licence.']})

    def test_api_license_id(self):
        self.check('uk-ogl', '', False,
                   {('license_id',): 'uk-ogl', ('licence',): ''},
                   {('license_id',): None, })

    def test_api_free_text(self):
        # With the API, if you specify a licence then license_id gets ignored
        self.check('ignored', 'Free form', False,
                   {('license_id',): None,
                    ('extras', 99, 'key'): 'licence',
                    ('extras', 99, 'value'): 'Free form'},
                   {('license_id',): None})
