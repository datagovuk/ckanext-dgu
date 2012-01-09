from itertools import dropwhile

def _is_additional_resource(resource):
    """
    Returns true iff the given resource identifies as an additional resource.
    """
    return resource.get('resource_type', '') in ('documentation',)

def _is_timeseries_resource(resource):
    """
    Returns true iff the given resource identifies as a timeseries resource.
    """
    return not _is_additional_resource(resource) and \
           resource.get('date', None)

def _is_individual_resource(resource):
    """
    Returns true iff the given resource identifies as an individual resource.
    """
    return not _is_additional_resource(resource) and \
           not _is_timeseries_resource(resource)

def additional_resources(package):
    """Extract the additional resources from a package"""
    return filter(_is_additional_resource, package.get('resources'))

def timeseries_resources(package):
    """Extract the timeseries resources from a package"""
    return filter(_is_timeseries_resource, package.get('resources'))

def individual_resources(package):
    """Extract the individual resources from a package"""
    return filter(_is_individual_resource, package.get('resources'))

def resource_type(resource):
    """
    Returns the resource type as a string.

    Returns one of 'additional', 'timeseries', 'individual'.
    """
    fs = zip(('additional', 'timeseries', 'individual'),
             (_is_additional_resource, _is_timeseries_resource, _is_individual_resource))
    return dropwhile(lambda (_,f): not f(resource), fs).next()[0]
