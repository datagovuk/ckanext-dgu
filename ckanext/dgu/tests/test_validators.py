from nose.tools import assert_equal, assert_raises

from ckan.lib.navl.dictization_functions import flatten_dict, unflatten, Invalid

from ckanext.dgu.validators import merge_resources, \
                                   validate_additional_resource_types, \
                                   validate_data_resource_types

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
        errors = {k:[] for k in flattened_data.keys()}
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
        errors = {k:[] for k in flattened_data.keys()}
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

        errors = {k:[] for k in flattened_data.keys()}
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
