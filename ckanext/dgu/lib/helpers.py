import logging
import re
import urllib
from itertools import dropwhile
import datetime

from webhelpers.html import literal
from webhelpers.text import truncate
from pylons import tmpl_context as c

from ckan.lib.helpers import icon
import ckan.lib.helpers
from ckan.controllers.package import search_url, url_with_params
from publisher_node import PublisherNode

log = logging.getLogger(__name__)

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

def construct_publisher_tree(groups,  type='publisher', title_for_group=lambda x:x.title):
    """
        Uses the provided groups to generate a tree structure (in a dict) by
        matching up the tree relationship using the Member objects.

        We might look at using postgres CTE to build the entire tree inside
        postgres but for now this is adequate for our needs.
    """
    from ckan import model

    root = PublisherNode( "root", "root")
    tree = { root.slug : root }

    # Get all the member objects between groups.
    # For each member:
    #    .group_id is the group
    #    .table_id is the parent group
    members = model.Session.query(model.Member).\
                join(model.Group, model.Member.group_id == model.Group.id).\
                filter(model.Group.type == 'publisher').\
                filter(model.Member.table_name == 'group').\
                filter(model.Member.state == 'active').all()

    group_lookup  = dict( (g.id,g, ) for g in groups )
    group_members = dict( (g.id,[],) for g in groups )

    # Process the membership rules
    for member in members:
        if member.table_id in group_lookup and member.group_id:
            group_members[member.table_id].append( member.group_id )

    def get_groups(group):
        return [group_lookup[i] for i in group_members[group.id]]

    for group in groups:
        slug, title = group.name, title_for_group(group)
        if not slug in tree:
            tree[slug] = PublisherNode(slug, title)
        else:
            # May be updating a parent placeholder where the child was
            # encountered first.
            tree[slug].slug = slug
            tree[slug].title = title

        parent_nodes = get_groups(group)
        if len(parent_nodes) == 0:
            root.children.append( tree[slug] )
        else:
            for parent in parent_nodes:
                parent_slug, parent_title = parent.name, parent.title
                if not parent_slug in tree:
                    # Parent doesn't yet exist, add a placeholder
                    tree[parent_slug] = PublisherNode('', '')
                tree[parent_slug].children.append(tree[slug])
    return root

def render_tree(groups,  type='publisher'):
    return construct_publisher_tree(groups,type).render()

def render_mini_tree(all_groups,this_group):
    '''Render a tree, but a special case, where there is one 'parent' (optional),
    the current group and any number of subgroups under it.'''
    from ckan import model
    import ckanext.dgu.lib.publisher as publisher

    def get_root_group(group, critical_path):
        critical_path.insert(0, group)
        parent = publisher.get_parents(group)
        if parent:
            return get_root_group(parent[0],critical_path)
        return group, critical_path

    root_group, critical_path = get_root_group(this_group, [])
    def title_for_group(group):
        if group==this_group:
            return '<strong>%s</strong>' % group.title
        return group.title

    root = construct_publisher_tree(all_groups,'publisher',title_for_group)
    root.children = filter( lambda x: x.slug==root_group.name , root.children )

    return root.render()

def get_resource_wms(resource_dict):
    '''For a given resource, return the WMS url if it is a WMS data type.'''
    # plenty of WMS resources have res['format']='' so
    # also search for WMS in the url
    url = resource_dict.get('url') or ''
    format = resource_dict.get('format') or ''
    # NB This WMS detection condition must match that in ckanext-os/ckanext/os/controller.py
    if 'wms' in url.lower() or format.lower() == 'wms':
        return url

def get_resource_wfs(resource_dict):
    '''For a given resource, return the WMS url if it is a WMS data type.'''
    url = resource_dict.get('url') or ''
    format = resource_dict.get('format') or ''
    # NB This WMS detection condition must match that in ckanext-os/ckanext/os/controller.py
    if 'wfs' in url.lower() or format.lower() == 'wfs':
        return url

def get_wms_info(pkg_dict):
    '''For a given package, extracts all the urls and spatial extent.
    Returns (urls, extent) where:
    * urls is a list of tuples like ('url', 'http://geog.com?wms')
    * extent is a tuple of (N, W, E, S) representing max extent
    '''
    urls = []
    for r in pkg_dict.get('resources',[]):
        wms_url = get_resource_wms(r)
        if wms_url:
            urls.append(('url', wms_url))
        wfs_url = get_resource_wfs(r)
        if wfs_url:
            urls.append(('wfsurl', wfs_url))
            urls.append(('resid', r['id']))
    # Extent
    extras = pkg_dict['extras']
    extent = {'n': get_from_flat_dict(extras, 'bbox-north-lat', ''),
              'e': get_from_flat_dict(extras, 'bbox-east-long', ''),
              'w': get_from_flat_dict(extras, 'bbox-west-long', ''),
              's': get_from_flat_dict(extras, 'bbox-south-lat', '')}
    extent_list = []
    for direction in 'nwes':
        if extent[direction] in (None, ''):
            extent_list = []
            break
        try:
            # check it is a number
            float(extent[direction])
        except ValueError, e:
            log.error('Package %r has invalid bbox value %r: %s' %
                      (pkg_dict.get('name'), extent[direction], e))
        extent_list.append(extent[direction])
    return urllib.urlencode(urls), tuple(extent_list)

def get_from_flat_dict(list_of_dicts, key, default=None):
    '''Extract data from a list of dicts with keys 'key' and 'value'
    e.g. pkg_dict['extras'] = [{'key': 'language', 'value': '"french"'}, ... ]
    '''
    for dict_ in list_of_dicts:
        if dict_.get('key', '') == key:
            return dict_.get('value', default).strip('"')
    return default

def get_uklp_package_type(package):
    return get_from_flat_dict(package.get('extras', []), 'resource-type', '')

def is_service(package):
    res_type = get_uklp_package_type(package)
    return res_type == 'service'

# variant of core ckan method of same name
# but displays better string if no resource there
def resource_display_name(resource_dict):
    name = resource_dict.get('name')
    description = resource_dict.get('description')
    if name and name != 'None':
        return name
    elif description and description != 'None':
        return description
    else:
        noname_string = 'File'
        return '[%s] %s' % (noname_string, resource_dict['id'])

def _search_with_filter(k_search,k_replace):
    from ckan.lib.base import request
    from ckan.controllers.package import search_url
    # most search operations should reset the page counter:
    params_nopage = [(k, v) for k,v in request.params.items() if k != 'page']
    params = set(params_nopage)
    params_filtered = set()
    for (k,v) in params:
        if k==k_search: k=k_replace
        params_filtered.add((k,v))
    return search_url(params_filtered)

def search_with_subpub():
    return _search_with_filter('publisher','parent_publishers')

def search_without_subpub():
    return _search_with_filter('parent_publishers','publisher')

def predict_if_resource_will_preview(resource_dict):
    format = resource_dict.get('format')
    if not format:
        return False
    normalised_format = format.lower().split('/')[-1]
    return normalised_format in (('csv', 'xls', 'rdf+xml', 'owl+xml',
                                  'xml', 'n-triples', 'turtle', 'plain',
                                  'txt', 'atom', 'tsv', 'rss'))
    # list of formats is copied from recline js

def dgu_linked_user(user, maxlength=16):  # Overwrite h.linked_user
    from ckan import model
    from ckan.lib.base import h
    from ckanext.dgu.plugins_toolkit import c

    if user in [model.PSEUDO_USER__LOGGED_IN, model.PSEUDO_USER__VISITOR]:
        return user
    if not isinstance(user, model.User):
        user_name = unicode(user)
        user = model.User.get(user_name)
    if not user:
        # may be in the format "NHS North Staffordshire (uid 6107 )"
        match = re.match('.*\(uid (\d+)\s?\)', user_name)
        if match:
            drupal_user_id = match.groups()[0]
            user = model.User.get('user_d%s' % drupal_user_id)

    if (c.is_an_official):
        # only officials can see the actual user name
        if user:
            publisher = ', '.join([group.title for group in user.get_groups('publisher')])

            display_name = '%s (%s)' % (user.fullname, publisher)
            link_text = truncate(user.fullname or user.name, length=maxlength)
            return h.link_to(link_text,
                             h.url_for(controller='user', action='read', id=user.name))
        else:
            return truncate(user_name, length=maxlength)
    else:
        # joe public just gets a link to the user's publisher(s)
        import ckan.authz
        if user:
            groups = user.get_groups('publisher')
            if groups:
                return h.literal(' '.join([h.link_to(truncate(group.title, length=maxlength),
                                                     '/publisher/%s' % group.name) \
                                         for group in groups]))
            elif ckan.authz.Authorizer().is_sysadmin(user):
                return 'System Administrator'
            else:
                return 'Staff'
        else:
            return 'Staff'

def render_datestamp(datestamp_str, format='%d/%m/%Y'):
    # e.g. '2012-06-12T17:33:02.884649' returns '12/6/2012'
    if not datestamp_str:
        return ''
    try:
        return datetime.datetime(*map(int, re.split('[^\d]', datestamp_str)[:-1])).strftime(format)
    except Exception:
        return ''

def get_cache_url(resource_dict):
    url = resource_dict.get('cache_url')
    if not url:
        return
    url = url.strip().replace('None', '')
    # strip off the domain, in case this is running in test
    # on a machine other than data.gov.uk
    return url.replace('http://data.gov.uk/', '/')

def get_stars_aggregate(dataset_id):
    '''For a dataset, of all its resources, get details of the one with the highest QA score.
    returns a dict of details including:
      {'value': 3, 'last_updated': '2012-06-15T13:20:11.699', ...}
    '''
    from ckanext.qa.reports import dataset_five_stars
    stars_dict = dataset_five_stars(dataset_id)
    return stars_dict

def mini_stars_and_caption(num_stars):
    mini_stars = num_stars * '&#9733'
    mini_stars += '&#9734' * (5-num_stars)
    captions = [
        'Unavailable or not openly licensed',
        'Unstructured data (e.g. PDF)',
        'Structured data but proprietry format (e.g. Excel)',
        'Structured data in open format (e.g. CSV)',
        'Linkable data - served at URIs (e.g. RDF)',
        'Linked data - data URIs and linked to other data (e.g. RDF)'
        ]
    return literal('%s&nbsp; %s' % (mini_stars, captions[num_stars]))

def render_stars(stars, reason, last_updated):
    if stars==0:
        stars_html = 5 * icon('star-grey')
    else:
        stars_html = stars * icon('star')

    tooltip = literal('<div class="star-rating-reason"><b>Reason: </b>%s</div>' % reason) if reason else ''
    for i in range(5,0,-1):
        classname = 'fail' if (i > stars) else ''
        tooltip += literal('<div class="star-rating-entry %s">%s</div>' % (classname, mini_stars_and_caption(i)))

    datestamp = last_updated.strftime('%d/%m/%Y')
    tooltip += literal('<div class="star-rating-last-updated"><b>Score updated: </b>%s</div>' % datestamp)

    return literal('<span class="star-rating"><span class="tooltip">%s</span><a href="http://lab.linkeddata.deri.ie/2010/star-scheme-by-example/" target="_blank">%s</a></span>' % (tooltip, stars_html))

def scraper_icon(res, alt=None):
    if not alt:
        alt = "File link has been added automatically by scraping {url} on {date}. " \
              "Powered by scraperwiki.com.".format(url=res.get('scraper_source'), date=res.get('scraped').format("%d/%m/%Y"))
    return icon('scraperwiki_small', alt=alt)

def ga_download_tracking(resource, action='download'):
    '''Google Analytics event tracking for downloading a resource.

    Values for action: download, download-cache

    c.f. Google example:
    <a href="#" onClick="_gaq.push(['_trackEvent', 'Videos', 'Play', 'Baby\'s First Birthday']);">Play</a>

    The call here is wrapped in a timeout to give the push call time to complete as some browsers
    will complete the new http call without allowing _gaq time to complete.  This *could* be resolved
    by setting a target of _blank but this forces the download (many of them remote urls) into a new
    tab/window.
    '''
    return "var that=this;_gaq.push(['_trackEvent','resource','%s','%s',0,true]);"\
           "setTimeout(function(){location.href=that.href;},200);return false;" \
           % (action, resource.get('url'))

def render_datetime(datetime_, date_format=None, with_hours=False):
    '''Render a datetime object or timestamp string as a pretty string
    (Y-m-d H:m).
    If timestamp is badly formatted, then a blank string is returned.

    This is a wrapper on the CKAN one which has an American date_format.
    '''
    if not date_format:
        date_format = '%d %b %Y'
        if with_hours:
            date_format += ' %H:%M'
    return ckan.lib.helpers.render_datetime(datetime_, date_format)

def dgu_drill_down_url(params_to_keep, added_params, alternative_url=None):
    '''Since you must not mix spatial search with other facets,
    we need to strip off "sort=spatial+desc" from the params if it
    is there.

    params_to_keep: All the params apart from 'page' or
                    'sort=spatial+desc' (it is more efficient to calculate
                    this once and pass it in than to calculate it here).
                    List of (key, value) pairs.
    added_params: Dict of params to add, for this facet option
    '''
    params = set(params_to_keep)
    params |= set(added_params.items())
    if alternative_url:
        return url_with_params(alternative_url, params)
    return search_url(params)
