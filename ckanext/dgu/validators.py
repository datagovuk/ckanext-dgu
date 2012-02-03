"""
navl validators for the DGU package schema.
"""

from itertools import chain, groupby

from pylons.i18n import _

from ckan.lib.navl.dictization_functions import unflatten, Invalid

from ckanext.dgu.lib.helpers import resource_type as categorise_resource

def validate_license(key, data, errors, context):
    """
    Validates the selected license options.

    Validation rules must be true to validate:

     license_id == '' => license_id-other != ''
     license_id != '' => license_id-other == ''

    Additional transformations occur:

     license_id-other != '' => license_id ~> license_id-other
     license_id-other is DROPPED

    """

    license_id = bool(data[('license_id',)])
    license_id_other = bool(data[('license_id-other',)])

    if not (license_id ^ license_id_other):
        if license_id:
            errors[('license_id',)] = ['Leave the "other" box empty if '
                                       'selecting a license from the list']
        else:
            errors[('license_id',)] = ['Please enter the name of the license']

    if not license_id:
        data[('license_id',)] = data[('license_id-other',)] 
    del data[('license_id-other',)]
    del errors[('license_id-other',)]

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

    _merge_dict(data)
    _merge_dict(errors)
            
def _merge_dict(d):
    """
    Helper function that performs a resource merge on the given dict.

    A resource merge takes a flattened dictionary, with keys (tuples) of the
    form `('additional_resource', 0, 'url')` and `('timeseries_resource', 0, 'url')`.
    And transforms it into a dict with the above keys merged into ones of the
    form `('resources', 0, 'url')`.

    d is the dict to perform the merge on.
    """
    additional_resources = _extract_resources('additional', d)
    timeseries_resources = _extract_resources('timeseries', d)
    individual_resources = _extract_resources('individual', d)
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
            d[('resources', num, field)] = d[(resource_type, original_index, field)]

            # delete the original key from the d, e.g. 
            del d[(resource_type, original_index, field)]

def unmerge_resources(key, data, errors, context):
    """
    Splits the merged resources back into their respective resource types.

    And removes the 'resources' entry.

    This post-processing only occurs if there have been no validation errors.
    """
    if key != ('__after',):
        raise Exception('The unmerge_resources function should only be '
                        'called as a post-processing function.  '
                        'Called with "%s"' % key)
    
    for value in errors.values():
        if value:
            return

    # data[('resources', '0', 'url')]

    # Categorise each resource, and add it to the respective entry
    unflattened_resources = unflatten(data).get('resources', [])
    error_resources = unflatten(errors).get('resources', [])
    resources = zip(unflattened_resources,
                    map(categorise_resource, unflattened_resources),
                    error_resources)

    for resource_type in ('additional', 'timeseries', 'individual'):
        match = lambda (r,t,e): t == resource_type # match resources of this resource_type
        for index, (resource,_,error_resource) in enumerate(filter(match, resources)):
            for field in resource.keys():
                data_key = ('%s_resources'%resource_type, index, field)
                data[data_key] = resource[field]
            for field in error_resource.keys():
                error_key = ('%s_resources'%resource_type, index, field)
                errors[error_key] = []
    
    for d in (data, errors):
        for key in ( key for key in d.keys() if key[0] == 'resources' ):
            del d[key]

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
