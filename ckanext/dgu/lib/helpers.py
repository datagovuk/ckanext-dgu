from itertools import dropwhile
from publisher_node import PublisherNode

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

def render_tree(groups, type='publisher'):
    """
        If called with some groups, maybe a hierarchy, it will write them into
        a dict and work out the relationship between them.
    """        
    root = PublisherNode( "root", "root")                    
    tree = { root.slug : root }
    
    for group in sorted(groups, key=lambda g: g.title):
        slug, title = group.name, group.title
        if not slug in tree:
            tree[slug] = PublisherNode(slug, title)
        else:
            tree[slug].slug = slug
            tree[slug].title = title
            
        parent_nodes = group.get_groups(type) # Database hit. Ow.
        if len(parent_nodes) == 0:
            root.children.append( tree[slug] )
        else:    
            for parent in parent_nodes:
                parent_slug, parent_title = parent.name, parent.title             
                if not parent_slug in tree:
                    tree[parent_slug] = PublisherNode('', '')
                tree[parent_slug].children.append(tree[slug])     

    return root.render()
