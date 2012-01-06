"""
navl validators for the DGU package schema.
"""

from itertools import chain, groupby

def validate_resources(key, data, errors, context):
    """
    Validates that the timeseries_resources and individual_resources.

    At most one of them should contain resources.
    """
    timeseries_resources = _extract_resources('timeseries', data)
    individual_resources = _extract_resources('individual', data)

    if len(timeseries_resources) and len(individual_resources):
        errors[('validate_resources',)] = ['Only define timeseries or individual '
                                               'resources, not both']

def merge_resources(key, data, errors, context):
    """
    Merges additional resources and data resources into a single entry in the data dict.

    And removes the '{additional,timeseries,individual}_resources' entries.

    This post-processing only occurs if there have been no validation errors.
    This prevents us losing the user's input.
    """
    if key != ('__after',):
        raise Exception('The merge_resources function should only be '
                        'called as a post-processing function.  '
                        'Called with "%s"' % key)
    
    for value in errors.values():
        if value:
            return

    additional_resources = _extract_resources('additional', data)
    timeseries_resources = _extract_resources('timeseries', data)
    individual_resources = _extract_resources('individual', data)
    resources = sorted(chain(additional_resources,
                             timeseries_resources,
                             individual_resources))

    # group by the first two items in the flattened key
    #  - num : from enumerate.
    #  - resource : key we've grouped on, e.g. ('additional_resource', 0)
    #  - values : iterator over the resource keys,, e.g.
    #             [ ('additional_resource', 0, 'url'),
    #               ('additional_resource', 0, 'description') ]
    for (num, (resource, values)) in enumerate(groupby(resources, lambda t: t[:2])):
        resource_type, original_index = resource
        for (_,_,field) in values:
            data[('resources', num, field)] = data[(resource_type, original_index, field)]

            # delete the original key from the data, e.g. 
            del data[(resource_type, original_index, field)]
        
    # Update the errors dict
    additional_errors = _extract_resources('additional', errors)
    timeseries_errors = _extract_resources('timeseries', errors)
    individual_errors = _extract_resources('individual', errors)
    all_errors = sorted(chain(additional_errors,
                              timeseries_errors,
                              individual_errors))

    for (num, (resource, values)) in enumerate(groupby(all_errors, lambda t: t[:2])):
        resource_type, original_index = resource
        for (_,_,field) in values:
            errors[('resources', num, field)] = []  # safe since we know everthing has validated correctly
            del errors[(resource_type, original_index, field)]


def _validate_resource_types(allowed_types, default=None):
    """
    Returns a function that validates the given resource_type is allowed.

    If a resource_type is False-like, then it returns a default value when
    available.
    """
    
    def _converter(value):
        if not value and default:
            return default
        elif value not in allowed_types:
            raise Invalid(_('Invalid resource type: %s' % value))
        return value
    return _converter

validate_additional_resource_types = _validate_resource_types(
                                         ('documentation',),
                                         default='documentation')

validate_data_resource_types = _validate_resource_types(
                                   ('api','file'),
                                   default='file')

def _extract_resources(name, data):
    """
    Extracts the flattened resources with the given name from the flattened data dict
    """
    return [ key for key in data.keys() if key[0] == name+'_resources' ]
