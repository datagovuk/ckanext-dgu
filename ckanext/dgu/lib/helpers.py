"""
These helper functions are made available via the h variable which
is given to every template for rendering.  To simplify the loading
of helpers all functions *that do not start with _* will be added
to the helper functions, so if you don't want your function available
make sure you prefix the function name with _
"""

import logging
import re
import urllib
from urlparse import urljoin
from itertools import dropwhile
import itertools
import datetime
import random
import types
import json

import ckan.plugins.toolkit as t
c = t.c
from webhelpers.text import truncate
from webhelpers.html import escape
from jinja2 import Markup
from pylons import config
from pylons import request

from ckan.lib.helpers import (icon, icon_html, json, unselected_facet_items,
                              get_pkg_dict_extra, organizations_available)
import ckan.lib.helpers

# not importing ckan.controllers here, since we need to monkey patch it in plugin.py
from ckanext.dgu.lib import formats

log = logging.getLogger(__name__)

def groupby(*args, **kwargs):
    return itertools.groupby(*args, **kwargs)

def resource_as_json(resource):
    return json.dumps(resource)

def is_resource_broken(resource_id):
    from ckanext.archiver.model import Archival

    archival = Archival.get_for_resource(resource_id)
    return archival and archival.is_broken==True

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

# NB these 3 functions are overwritten by the other function of the same name,
# but we should probably use these ones in preference
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

def organization_list(top=False):
    from ckan import model
    if top:
        organizations = model.Group.get_top_level_groups(type='organization')
    else:
        organizations = model.Session.query(model.Group).\
            filter(model.Group.type=='organization').\
            filter(model.Group.state=='active').order_by('title')
    for organization in organizations:
        yield (organization.name, organization.title)

def publisher_hierarchy():
    from ckan.logic import get_action
    from ckan import model
    import json
    context = {'model': model, 'session': model.Session}
    top_nodes = get_action('group_tree')(context=context,
            data_dict={'type': 'organization'})
    out = [ _publisher_hierarchy_recur(node) for node in top_nodes ]
    return out

def _publisher_hierarchy_recur(node):
    title = node['title']
    name  = node['name']
    children = [ _publisher_hierarchy_recur(child) for child in (node['children'] or []) ]
    return {
            'id': node['id'],
            'title':title,
            'name':name,
            'children':children,
            }

def publisher_hierarchy_mini(group_name_or_id):
    '''Returns HTML for a hierarchy of SOME publishers - the ones which
    are under the same top-level publisher as the given one.'''
    from ckan.logic import get_action
    from ckan import model
    context = {'model': model, 'session': model.Session}
    my_root_node = get_action('group_tree_section')(context=context,
            data_dict={'id': group_name_or_id, 'type': 'organization'})
    return _publisher_hierarchy_recur(my_root_node)

def publisher_abbreviations():
    from ckan import model
    abbrevs = model.Session.query(model.GroupExtra) \
                   .filter_by(key='abbreviation') \
                   .filter_by(state='active') \
                   .all()
    return dict(((abbrev.group_id, abbrev.value) for abbrev in abbrevs))

def is_wms(resource):
    from ckanext.dgu.lib.helpers import get_resource_wms
    return bool(get_resource_wms(resource))


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
    wfs_service = resource_dict.get('wfs_service') or ''
    format_ = resource_dict.get('format') or ''
    # NB This WMS detection condition must match that in ckanext-os/ckanext/os/controller.py
    if wfs_service == 'ckanext_os' or format_.lower() == 'wfs':
        return urljoin(config['ckan.site_url'], '/data/wfs')

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
            resname = pkg_dict['title']
            if r['description']:
                resname += ' - %s' % r['description']
            urls.append(('resname', resname.encode('utf8')))
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
            return (dict_.get('value', default) or '').strip('"')
    return default

def extras_list_to_dict(extras_list):
    if not extras_list:
        return {}
    extras = dict((extra['key'], extra['value']) for extra in extras_list)
    return extras

def get_uklp_package_type(package):
    return get_from_flat_dict(package.get('extras', []), 'resource-type', '')

def get_primary_theme(package):
    return get_from_flat_dict(package.get('extras', []), 'theme-primary', '')

def get_secondary_themes(package):
    secondary_themes_raw = get_from_flat_dict(package.get('extras', []), 'theme-secondary', '')
    return secondary_themes({'theme-secondary':secondary_themes_raw})

def is_service(package):
    res_type = get_uklp_package_type(package)
    return res_type == 'service'

# variant of core ckan method of same name
# but displays better string if no resource there
def resource_display_name(resource_dict):
    # Gemini resources special case
    if resource_dict.get('gemini',False):
        return resource_dict.get('title')
    name = resource_dict.get('name')
    description = resource_dict.get('description')
    if name and name != 'None':
        return name
    elif description and description != 'None':
        return description
    else:
        noname_string = 'File'
        return '[%s] %s' % (noname_string, resource_dict['id'])


def predict_if_resource_will_preview(resource_dict):
    format = resource_dict.get('format')
    if not format:
        return False
    normalised_format = format.lower().split('/')[-1]
    return normalised_format in (('csv', 'xls', 'rdf+xml', 'owl+xml',
                                  'xml', 'n-triples', 'turtle', 'plain',
                                  'txt', 'atom', 'tsv', 'rss', 'ods'))
    # list of formats is copied from recline js

def userobj_from_username(username):
    from ckan import model
    return model.User.get(username)


def drupal_user_id_from_username(username):
    return username.split('user_d')[-1]


def user_properties(user):
    '''
    Given a user, returns the user object and whether they are a system user or
    an official (requiring some anonymity).

    `user` parameter can be any of:
    * CKAN user.name e.g. 'user_d845'
    * user object
    * Drupal user name e.g. 'davidread'
    * Old Drupal user ID as stored in revisions e.g. 'NHS North Staffordshire (uid 6107 )'

    Returns: (user_name, user, type, this_is_me)
    where:
    * user might be None if there isn't an object for the user_name
    * type is in (None, 'system', 'official')
    '''
    from ckan import model
    is_system = False
    if user in [model.PSEUDO_USER__LOGGED_IN, model.PSEUDO_USER__VISITOR]:
        # These values occur in tests only?
        user_name = user
        is_system = True
    if not isinstance(user, model.User):
        user_name = unicode(user)
        user = model.User.get(user_name) or model.Session.query(model.User).filter_by(fullname=user_name).first()
    else:
        user_name = user.name

    # Check if this is the site_user
    site_user_name = config.get('ckan.site_id', 'ckan_site_user')
    if user and user.name == site_user_name:
        user_name = 'Site user'
        is_system = True

    if not user:
        # Up til Jun 2012, CKAN saved Drupal users in this format:
        # "NHS North Staffordshire (uid 6107 )"
        match = re.match('.*\(uid (\d+)\s?\)', user_name)
        if match:
            drupal_user_id = match.groups()[0]
            user = model.User.get('user_d%s' % drupal_user_id)

    this_is_me = user and (c.user in (user.name, user.fullname))

    is_official = (user_name and not user) or \
                  (user and (user.get_groups('organization') or user.sysadmin))
    if user and user.name.startswith('user_d'):
        user_drupal_id = user.name.split('user_d')[-1]
    else:
        user_drupal_id = None
    type_ = 'system' if is_system else ('official' if is_official else None)
    return user_name, user, user_drupal_id, type_, this_is_me

def user_link_info(user_name, organization=None):  # Overwrite h.linked_user
    '''Given a user, return the display name and link to their profile page.
    '''
    from ckan.lib.base import h

    # Work out who the user is that we want to view
    user_name, user, user_drupal_id, type_, this_is_me = user_properties(user_name)

    # Now decide how to display the user
    if (is_an_official() or this_is_me or type_ is None):
        # User can see the actual user name - i.e. if:
        # * viewer is an official
        # * viewing ones own user
        # * viewing a member of public
        if user:
            if type_ == 'system':
                name = 'System Process (%s)' % user_name
            else:
                name = user.fullname or user.name

            if not user_drupal_id:
                link_url = h.url_for(controller='user', action='read', id=user.name)
            else:
                link_url = '/user/%s' % user_drupal_id

            return (name, link_url)
        else:
            if type_ == 'system':
                user_name = 'System Process (%s)' % user_name
            return (user_name, None)
    else:
        # Can't see the user name - it gets anonymised.
        # Joe public just gets a link to the user's publisher(s)
        if user:
            groups = user.get_groups('organization')
            if type_ == 'official' and is_sysadmin(user):
                return ('System Administrator', None)
            elif groups:
                # We don't want to show all of the groups that the user belongs to.
                # We will try and match the organization name if provided and use that
                # instead.  If none is provided, or we can't match one then we will use
                # the highest level org.
                matched_group = None
                for group in groups:
                    if group.title == organization or group.name == organization:
                        matched_group = group
                        break
                if not matched_group:
                    matched_group = groups[0]

                return (matched_group.title,
                       '/publisher/%s' % matched_group.name)
            elif type_ == 'system':
                return ('System Process', None)
            else:
                return ('Staff', None)
        else:
            return ('System process' if type_ == 'system' else 'Staff', None)

def dgu_linked_user(user_name, maxlength=24, organization=None):  # Overwrite h.linked_user
    '''Given a user, return the HTML Anchor to their user profile page, making
    sure officials are kept anonymous to the public.
    '''
    from ckan.lib.base import h
    display_name, href = user_link_info(user_name, organization=organization)
    display_name = truncate(display_name, length=maxlength)
    if href:
        return h.link_to(display_name, urllib.quote(href))
    else:
        return display_name


def render_datestamp(datestamp_str, format='%d/%m/%Y'):
    '''
    Takes a FULL ISO datetime and returns a pretty-printed date
    e.g. '2012-06-12T17:33:02.884649' returns '12/6/2012'
    '''
    if not datestamp_str:
        return ''
    try:
        return datetime.datetime(*map(int, re.split('[^\d]', datestamp_str)[:-1])).strftime(format)
    except Exception:
        return ''


def render_partial_datestamp(datestamp_str):
    '''
    Takes a full or partial ISO datetime and returns a pretty-printed UK date
    e.g. '2012-06-12T17:33:02.884649' returns '12/6/2012'
         '2012-06' returns 'Jun 2012'
    '''
    if not datestamp_str:
        return ''
    try:
        bits = map(int, re.split('[^\d]', datestamp_str)[:3])
        num_bits = len(bits)
        format_ = {3: '%d/%m/%Y', 2: '%b %Y', 1: '%Y'}[num_bits]
        # pad it out to three bits (if its a partial date)
        bits += [1] * (3 - num_bits)
        return datetime.datetime(*bits).strftime(format_)
    except:
        try:
            request_path = t.request.path
        except:   # This may be TypeError or KeyError
            # not in a request (e.g. in a test)
            request_path = ''
        log.error('Could not render datestamp: %r %s', datestamp_str,
                  request_path)
        return ''


def get_cache(resource_dict):
    from ckanext.archiver.model import Archival
    archival = Archival.get_for_resource(resource_dict['id'])
    if not archival:
        return (None, None)
    url = (archival.cache_url or '').strip().replace('None', '')
    # strip off the domain, in case this is running in test
    # on a machine other than data.gov.uk
    url = url.replace('http://data.gov.uk/', '/')
    return url, archival.updated


# used in render_stars and read_common.html
def mini_stars_and_caption(num_stars):
    '''
    Returns HTML for a numbers of mini-stars with a caption describing the meaning.
    '''
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
    return t.literal('%s&nbsp; %s' % (mini_stars, captions[num_stars]))

# Used in read_common.html
def calculate_dataset_stars(dataset_id):
    from ckan.logic import get_action, NotFound
    from ckan import model
    if not is_plugin_enabled('qa'):
        return (0, '', '')
    try:
        context = {'model': model, 'session': model.Session}
        qa = get_action('qa_package_openness_show')(context, {'id': dataset_id})
    except NotFound:
        return (0, '', '')
    if not qa:
        return (0, '', '')
    return (qa['openness_score'],
            qa['openness_score_reason'],
            qa['updated'])

# Used in resource_read.html
def render_resource_stars(resource_id):
    from ckan.logic import get_action, NotFound
    from ckan import model
    if not is_plugin_enabled('qa'):
        return 'QA not installed'
    try:
        context = {'model': model, 'session': model.Session}
        qa = get_action('qa_resource_show')(context, {'id': resource_id})
    except NotFound:
        return 'To be determined'
    if not qa:
        return 'To be determined'
    return render_stars(qa['openness_score'], qa['openness_score_reason'],
                        qa['updated'])

# used by render_qa_info_for_resource
def does_detected_format_disagree(detected_format, resource_format):
    '''Returns boolean saying if there is an anomoly between the format of the
    resolved URL detected by ckanext-qa and resource.format (as input by the
    publisher).'''
    if not detected_format or not resource_format:
        return False
    is_disagreement = detected_format.strip().lower() != resource_format.strip().lower()
    return is_disagreement

# used by resource_read.html
def render_qa_info_for_resource(resource_dict):
    resource_id = resource_dict['id']
    from ckan.logic import get_action, NotFound
    from ckan import model
    if not is_plugin_enabled('qa'):
        return 'QA not installed'
    try:
        context = {'model': model, 'session': model.Session}
        qa = get_action('qa_resource_show')(context, {'id': resource_id})
    except NotFound:
        return 'To be determined'
    if not qa:
        return 'To be determined'
    reason_list = (qa['openness_score_reason'] or '').replace('Reason: Download error. ', '').replace('Error details: ', '').split('. ')
    resource = model.Resource.get(resource_id)
    ctx = {'qa': qa,
           'reason_list': reason_list,
           'resource_format': resource.format,
           'resource_format_disagrees': does_detected_format_disagree(qa['format'], resource_dict['format']),
           'is_data': resource_dict['resource_type'] in ('file', None),
           }
    return t.render_snippet('package/resource_qa.html', ctx)

def render_stars(stars, reason, last_updated):
    '''Returns HTML to show a number of stars out of five, with a reason and
    date, plus a tooltip describing the levels.'''
    if stars==0:
        stars_html = 5 * '<i class="icon-star-empty"></i>'
    else:
        stars_html = (stars or 0) * '<i class="icon-star"></i>'

    tooltip = t.literal('<div class="star-rating-reason"><b>Reason: </b>%s</div>' % escape(reason)) if reason else ''
    for i in range(5,0,-1):
        classname = 'fail' if (i > (stars or 0)) else ''
        tooltip += t.literal('<div class="star-rating-entry %s">%s</div>' % (classname, mini_stars_and_caption(i)))

    if last_updated:
        datestamp = render_datestamp(last_updated)
        tooltip += t.literal('<div class="star-rating-last-updated"><b>Score updated: </b>%s</div>' % datestamp)

    return t.literal('<span class="star-rating"><span class="tooltip">%s</span><a href="http://lab.linkeddata.deri.ie/2010/star-scheme-by-example/" target="_blank">%s</a></span>' % (tooltip, stars_html))

def scraper_icon(res, alt=None):
    if not alt and 'scraped' in res and 'scraper_source' in res:
        alt = "File link has been added automatically by scraping {url} on {date}. " \
              "Powered by scraperwiki.com.".format(url=res.get('scraper_source'), date=res.get('scraped').format("%d/%m/%Y"))
    return icon('scraperwiki_small', alt=alt)

def get_organization_from_resource(res_dict):
    from ckan import model
    res_id = res_dict.get('id')
    res = model.Resource.get(res_id)
    if not res:
        return None
    return res.resource_group.package.get_organization()

def ga_download_tracking(resource, publisher_name, action='download'):
    '''Google Analytics event tracking for downloading a resource. (Universal
    Analytics syntax)

    Values for action: download, download-cache

    e.g. ga('send', 'event', 'button', 'click', 'nav buttons', 4);

    The call here is wrapped in a timeout to give the push call time to complete as some browsers
    will complete the new http call without allowing ga() time to complete.  This *could* be resolved
    by setting a target of _blank but this forces the download (many of them remote urls) into a new
    tab/window.
    '''
    return "var that=this;ga('send','event','resource','%s','%s');"\
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

def dgu_drill_down_url(params_to_keep, added_params):
    '''Since you must not mix spatial search with other facets,
    we need to strip off "sort=spatial+desc" from the params if it
    is there.

    params_to_keep: All the params apart from 'page' or
                    'sort=spatial+desc' (it is more efficient to calculate
                    this once and pass it in than to calculate it here).
                    List of (key, value) pairs.
    added_params: Dict of params to add, for this facet option
    '''
    from ckan.controllers.package import search_url

    params = set(params_to_keep)
    params |= set(added_params.items())

    return search_url(params)

def render_json(json_str):
    '''Given a JSON string, list or dict, return it for display,
    being pragmatic.'''
    if not json_str:
        return ''
    try:
        obj = json.loads(json_str)
    except ValueError:
        return json_str.strip('"[]{}')
    if isinstance(obj, basestring):
        return obj
    elif isinstance(obj, list):
        return ', '.join(obj)
    elif isinstance(obj, dict):
        return ', ',join(['%s: %s' % (k, v) for k, v in obj.items()])
    # json can't be anything else

def json_list(json_str):
    '''Given a JSON list, return it for display,
    being pragmatic.'''
    if not json_str:
        return []
    try:
        obj = json.loads(json_str)
    except ValueError:
        return json_str.strip('"[]{}')
    if isinstance(obj, basestring):
        return [obj]
    elif isinstance(obj, list):
        return obj
    elif isinstance(obj, dict):
        return obj.items()
    # json can't be anything else

def list_flatten(data):
    '''
    If data is a list flatten it,
    otherwise return input data
    '''
    if isinstance(data, list):
        return ", ".join(data)
    else:
        return data

def dgu_format_icon(format_string):
    fmt = formats.Formats.match(format_string.strip().lower())
    icon_name = 'document'
    if fmt is not None and fmt['icon']!='':
        icon_name = fmt['icon']
    url = '/images/fugue/%s.png' % icon_name
    return icon_html(url)

def dgu_format_name(format_string):
    fmt = formats.Formats.match(format_string.strip().lower())
    if fmt is not None:
        return fmt['display_name']
    return format_string

def name_for_uklp_type(package):
    uklp_type = get_uklp_package_type(package)
    if uklp_type:
        item_type = '%s (UK Location)' % uklp_type.capitalize()
    else:
        item_type = 'Dataset'

def package_publisher_dict(package):
    if not package:
        return {'name':'', 'title': ''}

    dct = package.get('organization')
    if dct:
        return dct
    return {'name':'', 'title': ''}


def formats_for_package(package):
    formats = [res.get('format', '').strip().lower()
               for res in package.get('resources', [])
               if res.get('resource_type') != 'documentation']
    # Strip empty strings, deduplicate and sort
    formats = filter(bool, formats)
    formats = set(formats)
    formats = sorted(list(formats))
    return formats


def has_hidden_unpublished():
    return t.request.params.get('unpublished','true') == 'false'

def has_visible_unpublished():
    return t.request.params.get('unpublished','true') == 'true'

def search_params_contains(arg):
    return arg in t.request.params

def search_params_val(arg, default=None):
    return t.request.params.get(arg, default)

def facet_params_to_keep():
    return [(k, v) for k,v in t.request.params.items() if k != 'page' and not (k == 'sort' and v == 'spatial desc')]

def uklp_display_provider(package):
    uklps = [d for d in package.get('extras', {}) if d['key'] in ('UKLP', 'INSPIRE')]
    is_uklp = uklps[0]['value'] == '"True"' if len(uklps) else False
    if not is_uklp:
        return None

    providers = [d for d in package.get('extras', {}) if (d['key'] == 'provider')]
    return providers[0]['value'] if len(providers) else ''

def random_tags():
    from ckan.lib.base import h
    tags = h.unselected_facet_items('tags', limit=20)
    random.shuffle(tags)
    return tags

def get_resource_fields(resource, pkg_extras):
    from ckan.lib.base import h
    from ckanext.dgu.lib.resource_helpers import ResourceFieldNames, DisplayableFields

    field_names = ResourceFieldNames()
    field_names_display_only_if_value = ['content_type', 'content_length', 'mimetype',
                                         'mimetype-inner', 'name']
    res_dict = dict(resource)
    field_value_map = {
        # field_name : {display info}
        'url': {'label': 'URL', 'value': h.link_to(res_dict['url'], res_dict['url'])},
        'date-updated-computed': {'label': 'Date updated', 'label_title': 'Date updated on data.gov.uk', 'value': render_datestamp(res_dict.get('revision_timestamp'))},
        'content_type': {'label': 'Content Type', 'value': ''},
        'scraper_url': {'label': 'Scraper',
            'label_title':'URL of the scraper used to obtain the data',
            'value': t.literal(scraper_icon(c.resource)) + h.link_to(res_dict.get('scraper_url'), 'https://scraperwiki.com/scrapers/%s' %res_dict.get('scraper_url')) if res_dict.get('scraper_url') else None},
        'scraped': {'label': 'Scrape date',
            'label_title':'The date when this data was scraped',
            'value': h.render_datetime(res_dict.get('scraped'), "%d/%m/%Y")},
        'scraper_source': {'label': 'Scrape date',
            'label_title':'The date when this data was scraped',
            'value': res_dict.get('scraper_source')},
        '': {'label': '', 'value': ''},
        '': {'label': '', 'value': ''},
        '': {'label': '', 'value': ''},
        '': {'label': '', 'value': ''},
    }

    # add in fields that only display if they have a value
    for field_name in field_names_display_only_if_value:
        if pkg_extras.get(field_name):
            field_names.add([field_name])

    # calculate displayable field values
    return  DisplayableFields(field_names, field_value_map, pkg_extras)

def get_package_fields(package, package_dict, pkg_extras, dataset_was_harvested,
                       is_location_data, dataset_is_from_ns_pubhub, is_local_government_data):
    from ckan.lib.base import h
    from ckan.lib.field_types import DateType
    from ckanext.dgu.schema import GeoCoverageType
    from ckanext.dgu.lib.resource_helpers import DatasetFieldNames, DisplayableFields

    field_names = DatasetFieldNames(['date_added_to_dgu', 'mandate', 'temporal_coverage', 'geographic_coverage', 'schema', 'codelist', 'sla'])
    field_names_display_only_if_value = ['date_update_future', 'precision', 'update_frequency', 'temporal_granularity', 'taxonomy_url', 'data_issued', 'data_modified'] # (mostly deprecated) extra field names, but display values anyway if the metadata is there
    if is_an_official():
        field_names_display_only_if_value.append('external_reference')
        field_names_display_only_if_value.append('import_source')
    pkg_extras = dict(pkg_extras)
    harvest_date = harvest_guid = harvest_url = dataset_reference_date = None
    if dataset_was_harvested:
        field_names.add(['harvest-url', 'harvest-date', 'metadata-date', 'harvest-guid'])
        field_names.remove(['geographic_coverage', 'mandate'])
        from ckan.logic import get_action, NotFound
        from ckan import model
        try:
            context = {'model': model, 'session': model.Session}
            harvest_source = get_action('harvest_source_for_a_dataset')(context,{'id':package.id})
            harvest_url = harvest_source['url']
        except NotFound:
            harvest_url = 'Metadata not available'
        harvest_object_id = pkg_extras.get('harvest_object_id')
        if harvest_object_id:
            try:
                from ckanext.harvest.model import HarvestObject
            except ImportError:
                pass
            else:
                harvest_object = HarvestObject.get(harvest_object_id)
                if harvest_object:
                    harvest_date = harvest_object.gathered.strftime("%d/%m/%Y %H:%M")
                else:
                    harvest_date = 'Metadata not available'
        harvest_guid = pkg_extras.get('guid')
        harvest_source_reference = pkg_extras.get('harvest_source_reference')
        if harvest_source_reference and harvest_source_reference != harvest_guid:
            field_names.add(['harvest_source_reference'])
        if is_location_data:
            field_names.add(('bbox', 'spatial-reference-system', 'dataset-reference-date', 'frequency-of-update', 'responsible-party', 'access_constraints', 'resource-type', 'metadata-language'))
            if pkg_extras.get('resource-type') == 'service':
                field_names.add(['spatial-data-service-type'])
            dataset_reference_date = ', '.join(['%s (%s)' % (DateType.db_to_form(date_dict.get('value')), date_dict.get('type')) \
                        for date_dict in json_list(pkg_extras.get('dataset-reference-date'))])
    elif dataset_is_from_ns_pubhub:
        field_names.add(['national_statistic', 'categories'])
    if is_local_government_data:
        field_names.add(('la-function', 'la-service'))

    field_names.add_after('date_added_to_dgu', 'theme')
    if pkg_extras.get('theme-secondary'):
        field_names.add_after('theme', 'theme-secondary')

    temporal_coverage_from = pkg_extras.get('temporal_coverage-from','').strip('"[]')
    temporal_coverage_to = pkg_extras.get('temporal_coverage-to','').strip('"[]')
    if temporal_coverage_from and temporal_coverage_to:
        temporal_coverage = '%s - %s' % \
          (DateType.db_to_form(temporal_coverage_from),
           DateType.db_to_form(temporal_coverage_to))
    elif temporal_coverage_from or temporal_coverage_to:
        temporal_coverage = DateType.db_to_form(temporal_coverage_from or \
                                                temporal_coverage_to)
    else:
        temporal_coverage = ''

    taxonomy_url = pkg_extras.get('taxonomy_url') or ''
    if taxonomy_url and taxonomy_url.startswith('http'):
        taxonomy_url = h.link_to(truncate(taxonomy_url, 70), taxonomy_url)
    primary_theme = pkg_extras.get('theme-primary') or ''
    secondary_themes = pkg_extras.get('theme-secondary')
    if secondary_themes:
        try:
            secondary_themes = json.loads(secondary_themes) or ''

            if isinstance(secondary_themes, types.ListType):
                secondary_themes = ', '.join(secondary_themes)
        except ValueError:
            # string for single value
            secondary_themes = unicode(secondary_themes)

    mandates = render_mandates(pkg_extras)

    def linkify(schema):
        if schema['url']:
            return h.link_to(schema['title'], schema['url'])
        return escape(schema['title'])
    def list_of_links(schemas):
        try:
            schemas = [linkify(schema) for schema in schemas]
            return Markup('<br>'.join(schemas))
            #return Markup('<ul>\n<li>%s</li>\n</ul>' %
            #              '</li>\n<li>'.join(schemas))
        except ValueError, e:
            log.error('Could not display schemas: %r %s', schemas, e)
            pass
    schemas = package_dict.get('schema')
    if schemas:
        schemas = list_of_links(schemas)

    codelists = package_dict.get('codelist')
    if codelists:
        codelists = list_of_links(codelists)
    sla = package_dict.get('sla')
    if sla:
        if sla == 'true':
            sla = Markup('<span class="js-tooltip" title="%s" data-container="body" >SLA Agreed <i class="icon-info-sign"></i></span>' % escape(get_sla()))

    field_value_map = {
        # field_name : {display info}
        'date_added_to_dgu': {'label': 'Added to data.gov.uk', 'value': package.metadata_created.strftime('%d/%m/%Y')},
        'date_updated_on_dgu': {'label': 'Updated on data.gov.uk', 'value': package.metadata_modified.strftime('%d/%m/%Y')},
        'state': {'label': 'State', 'value': c.pkg.state},
        'harvest-url': {'label': 'Harvest URL', 'value': harvest_url},
        'harvest-date': {'label': 'Harvest date', 'value': harvest_date},
        'harvest-guid': {'label': 'Harvest GUID', 'value': harvest_guid},
        'bbox': {'label': 'Extent', 'value': t.literal('Latitude: %s&deg; to %s&deg; <br/> Longitude: %s&deg; to %s&deg;' % (escape(pkg_extras.get('bbox-north-lat')), escape(pkg_extras.get('bbox-south-lat')), escape(pkg_extras.get('bbox-west-long')), escape(pkg_extras.get('bbox-east-long')))) if has_extent(c.pkg) else ''},
        'categories': {'label': 'ONS category', 'value': pkg_extras.get('categories')},
        'data_issued': {'label': 'Data first issued', 'value': render_partial_datestamp(pkg_extras.get('data_issued', ''))},
        'data_modified': {'label': 'Data last modified', 'value': render_partial_datestamp(pkg_extras.get('data_modified', ''))},
        'date_updated': {'label': 'Date data last updated', 'value': DateType.db_to_form(pkg_extras.get('date_updated', ''))},
        'date_released': {'label': 'Date data last released', 'value': DateType.db_to_form(pkg_extras.get('date_released', ''))},
        'temporal_coverage': {'label': 'Temporal coverage', 'value': temporal_coverage},
        'geographic_coverage': {'label': 'Geographic coverage', 'value': GeoCoverageType.strip_off_binary(pkg_extras.get('geographic_coverage', ''))},
        'resource-type': {'label': 'ISO19139 resource type', 'value': pkg_extras.get('resource-type')},
        'spatial-data-service-type': {'label': 'Gemini2 service type', 'value': pkg_extras.get('spatial-data-service-type')},
        'access_constraints': {'label': 'Access constraints', 'value': render_json(pkg_extras.get('access_constraints'))},
        'taxonomy_url': {'label': 'Taxonomy URL', 'value': taxonomy_url},
        'theme': {'label': 'Theme', 'value': primary_theme},
        'theme-secondary': {'label': 'Themes (secondary)', 'value': secondary_themes},
        'mandate': {'label': 'Mandate', 'value': mandates},
        'schema': {'label': 'Schema/Vocabulary', 'value': schemas},
        'codelist': {'label': 'Code list', 'value': codelists},
        'sla': {'label': 'Service Level', 'value': sla},
        'metadata-language': {'label': 'Metadata language', 'value': pkg_extras.get('metadata-language', '').replace('eng', 'English')},
        'metadata-date': {'label': 'Metadata date', 'value': DateType.db_to_form(pkg_extras.get('metadata-date', ''))},
        'dataset-reference-date': {'label': 'Dataset reference date', 'value': dataset_reference_date},
        'la-function': {'label': 'Local Authority Function', 'value': pkg_extras.get('la_function')},
        'la-service': {'label': 'Local Authority Service', 'value': pkg_extras.get('la_service')},
        '': {'label': '', 'value': ''},
    }

    # add in fields that only display if they have a value
    for field_name in field_names_display_only_if_value:
        if pkg_extras.get(field_name):
            field_names.add([field_name])

    # calculate displayable field values
    return DisplayableFields(field_names, field_value_map, pkg_extras)


def render_mandates(pkg_extras):
    mandates = pkg_extras.get('mandate')
    if mandates:
        def linkify(string):
            # string is already escaped so we don't have to escape again
            if string.startswith('http://') or string.startswith('https://'):
                return '<a href="%s" target="_blank">%s</a>' % (string, string)
            else:
                return string

        try:
            mandates = json.loads(mandates)
            mandates = [Markup.escape(m) for m in mandates]
            mandates = [linkify(m) for m in mandates]
            mandates = Markup("<br>".join(mandates))
        except ValueError:
            pass  # Not JSON for some reason...
    return mandates


def results_sort_by():
    # Default to location if there is a bbox and no other parameters. Otherwise
    # relevancy if there is a keyword, otherwise popularity.
    # NB This ties in with the default sort set in ckanext/dgu/plugin.py
    bbox = t.request.params.get('ext_bbox')
    search_params_apart_from_bbox_or_sort = [key for key, value in t.request.params.items()
                                         if key not in ('ext_bbox', 'sort') and value != '']
    return c.sort_by_fields or ('spatial' if not sort_by_location_disabled() else ('rank' if c.q else 'popularity'))

def sort_by_location_disabled():
    # TODO: Duplicated code from above, needs tidying
    bbox = t.request.params.get('ext_bbox')
    search_params_apart_from_bbox_or_sort = [key for key, value in t.request.params.items()
                                         if key not in ('ext_bbox', 'sort') and value != '']
    return not(bool(bbox and not search_params_apart_from_bbox_or_sort))

def relevancy_disabled():
    return not(bool(t.request.params.get('q')))

def get_resource_formats():
    from ckanext.dgu.lib.formats import Formats
    return json.dumps(Formats.by_display_name().keys())


def get_wms_info_urls(pkg_dict):
    return get_wms_info(pkg_dict)[0]

def get_wms_info_extent(pkg_dict):
    return get_wms_info(pkg_dict)[1]

def user_display_name(user):
    user_str = ''
    if user.get('fullname'):
        user_str += user['fullname']
    user_str += ' [%s]' % user['name']
    return user_str

def pluralise_text(num):
    return 's' if num > 1 or num == 0 else ''

def group_category(group_extras):
    category = group_extras.get('category')
    if category:
        from ckanext.dgu.forms.validators import categories
        return dict(categories).get(category, category)
    return None

def spending_published_by(group_extras):
    from ckan import model
    spb = group_extras.get('spending_published_by')
    if spb:
        return model.Group.by_name(spb)
    return None

def advanced_search_url():
    from ckan.controllers.package import search_url
    params = dict(t.request.params)
    if not 'publisher' in params:
        params['parent_publishers'] = c.group.name
    return search_url(params.items())


def isopen(pkg):
    '''Replacement for ckan.model.package.isopen.
    Returns True or False'''
    # Normal datasets (created in the form) store the licence in the
    # pkg.license value as a License.id value.
    if pkg.license:
        # _isopen is the original one (before this method was monkey-patched in
        # its place)
        return pkg._isopen()
    elif pkg.license_id:
        # However if the user selects 'free text' in the form, that is stored
        # in the same pkg.license field.
        license_text = pkg.license_id
    else:
        # UKLP might have multiple licenses and don't adhere to the License
        # values, so are in the 'licence' extra.
        license_text_list = json_list(pkg.extras.get('licence') or '')
        # UKLP might also have a URL to go with its licence
        license_text_list.extend([pkg.extras.get('licence_url', '') or '',
                                  pkg.extras.get('licence_url_title') or ''])
        license_text = ';'.join(license_text_list)
    open_licenses = [
        'Open Government Licen',
        'http://www.nationalarchives.gov.uk/doc/open-government-licence/',
        'http://reference.data.gov.uk/id/open-government-licence',
        'OS OpenData Licence',
        'OS Open Data Licence',
        'Ordnance Survey OpenData Licence',
        'http://www.ordnancesurvey.co.uk/docs/licences/os-opendata-licence.pdf',
        'Open Data Commons Open Database License',
        'ODC Open Database License',
        '(ODbL)',
    ]
    for open_license in open_licenses:
        if open_license in license_text:
            return True
    return False

def get_licenses(pkg):
    # isopen is tri-state: True, False, None (for unknown)
    licenses = [] # [(title, url, isopen, isogl), ... ]

    # Normal datasets (created in the form) store the licence in the
    # pkg.license value as a License.id value.
    if pkg.license:
        licenses.append((pkg.license.title.split('::')[-1], pkg.license.url, pkg.license.isopen(), pkg.license.id == 'uk-ogl'))
    elif pkg.license_id:
        # However if the user selects 'free text' in the form, that is stored in
        # the same pkg.license field.
        licenses.append((pkg.license_id, None, None, pkg.license_id.startswith('Open Government Licen')))

    # UKLP might have multiple licenses and don't adhere to the License
    # values, so are in the 'licence' extra.
    license_extra_list = json_list(pkg.extras.get('licence') or '')
    for license_extra in license_extra_list:
        license_extra_url = None
        if license_extra.startswith('http'):
            license_extra_url = license_extra
        # british-waterways-inspire-compliant-service-metadata specifies OGL as
        # only one of many licenses. Set is_ogl bar a little higher - licence
        # text must start off saying it is OGL.
        is_ogl = license_extra.startswith('Open Government Licen')
        licenses.append((license_extra, license_extra_url, True if (is_ogl or 'OS OpenData Licence' in license_extra) else None, is_ogl))

    # UKLP might also have a URL to go with its licence
    license_url = pkg.extras.get('licence_url')
    if license_url:
        license_url_is_ogl = \
            '//www.nationalarchives.gov.uk/doc/open-government-licence' in license_url or\
            '//reference.data.gov.uk/id/open-government-licence' in license_url
        already_said_we_are_ogl = any([license[3] for license in licenses])
        if not (license_url_is_ogl and already_said_we_are_ogl):
            license_url_title = pkg.extras.get('licence_url_title') or license_url
            isopen = (license_url=='http://www.ordnancesurvey.co.uk/docs/licences/os-opendata-licence.pdf')
            licenses.append((license_url_title, license_url, True if isopen else None, False))
    return licenses

def get_dataset_openness(pkg):
    licenses = get_licenses(pkg) # [(title,url,isopen)...]
    openness = [ x[2] for x in licenses ]
    if True in openness:
        # Definitely open. OpenDefinition icon.
        return True
    if False in openness:
        # Definitely closed. Padlock icon.
        return False
    # Indeterminate
    return None

def get_contact_details(pkg, pkg_extras):
    publisher = c.pkg.get_organization()
    name = pkg_extras.get('contact-name')
    email = pkg_extras.get('contact-email')
    phone = pkg_extras.get('contact-phone')
    web_url = web_name = None

    # If package has no contact details then inherit from the publisher
    if not (name or email or phone) and publisher:
        extras = publisher.extras
        name = extras.get('contact-name')
        email = extras.get('contact-email')
        phone = extras.get('contact-phone')
        web_url = extras.get('website-url')
        web_name = extras.get('website-name')

    return (name, email, phone, web_url, web_name,)

def have_foi_contact_details(pkg, pkg_extras):
    return any(get_foi_contact_details(pkg, pkg_extras))

def get_contact_name(pkg, extras):
    name = extras.get('contact-name')
    if not name:
        publisher = pkg.get_organization()
        if publisher:
            name = publisher.extras.get('contact-name')
    return name

def get_foi_contact_name(pkg, extras):
    name = extras.get('foi-name')
    if not name:
        publisher = pkg.get_organization()
        if publisher:
            name = publisher.extras.get('foi-name')
    return name

def get_foi_contact_details(pkg, pkg_extras):
    publisher = c.pkg.get_organization()
    foi_name = pkg_extras.get('foi-name')
    foi_email = pkg_extras.get('foi-email')
    foi_phone = pkg_extras.get('foi-phone')
    foi_web = pkg_extras.get('foi-web')

    # If package has no FOI contact details then inherit from the publisher
    if not (foi_phone or foi_email or foi_phone or foi_web) and publisher:
        extras = publisher.extras
        foi_name = extras.get('foi-name')
        foi_email = extras.get('foi-email')
        foi_phone = extras.get('foi-phone')
        foi_web = extras.get('foi-web')

    return (foi_name, foi_email, foi_phone, foi_web, None,)

def coupled_pkg_tuples(pkg):
    try:
        from ckanext.spatial.lib.helpers import get_coupled_packages
        coupled_pkg_tuples = get_coupled_packages(pkg)
    except ImportError:
        coupled_pkg_tuples = []
    return  coupled_pkg_tuples

def is_package_deleted(pkg):
    from ckan.model import State
    return pkg.state == State.DELETED


def is_sysadmin(u=None):
    from ckan import new_authz, model
    user = u or c.userobj
    if not user:
        return False
    if isinstance(user, model.User):
        return user.sysadmin
    return new_authz.is_sysadmin(user)

def is_sysadmin_by_context(context):
    # For a context, returns whether this user is a syadmin or not
    from ckan import new_authz

    # auth_user_obj is set to None in check_access if it isn't already
    # present in the context.  This means that it will break for places where
    # check_access is called (and then this function) before the c.userobj is
    # set
    auth_user_obj = context.get('auth_user_obj')
    if auth_user_obj:
        return auth_user_obj.sysadmin

    return new_authz.is_sysadmin(context['user'])

def prep_user_detail():
    # Non-sysadmins cannot see personally identifiable information
    if not c.is_myself and not is_sysadmin():
        c.user_dict['about']        = ''
        c.about_formatted           = ''
        c.user_dict['display_name'] = c.user_dict['name']
        c.user_dict['fullname']     = None
        c.user_dict['email']        = None
        c.user_dict['openid']       = None
    return ""

def user_get_groups(uid):
    from ckan import model
    groups = []
    u = model.User.get(uid)
    if c.userobj and len( c.userobj.get_groups('organization') ) > 0 or is_sysadmin():
        groups = u.get_groups('organization' )
    return groups


def group_get_users(group, capacity):
    import ckan.model as model
    return group.members_of_type(model.User, capacity=capacity)


def prep_group_edit_data(data):
    # Note when you get a fresh form the extras are in data['extras']. But
    # on validation error, the submitted values appear in data[key] with the original
    # values in data['extras']. Therefore populate the form with the data[key] values
    # in preference, and fall back on the data['extra'] values.
    original_extra_fields = dict([(extra_dict['key'], extra_dict['value']) \
                                for extra_dict in data.get('extras', {})])
    for key, value in original_extra_fields.items():
        if key not in data:
            data[key] = value


def top_level_init():
    '''These 'globals' are initialised by Genshi's layout_base only - not done
    in Jinja, so for new templates use instead: is_an_official() or
    groups_for_current_user().
    '''
    c.groups = groups_for_current_user()
    c.is_an_official = bool(c.groups or is_sysadmin())


def is_an_official():
    if is_sysadmin():
        return True
    return bool(groups_for_current_user())


def groups_for_current_user():
    if c.groups == '':
        c.groups = c.userobj.get_groups(group_type='organization') \
            if c.userobj else []
    return c.groups


def additional_extra_fields(res):
    return [r for r in res.keys() if r not in
            ('id','resource_type','resource_group_id',
             'revision_id', 'url','description','format', 'scraper_url')]


def hidden_extra_fields(data):
    from ckanext.dgu.forms.dataset_form import DatasetForm
    schema_fields = set(DatasetForm.form_to_db_schema().keys())
    return [ e for e in data.get('extras', []) \
                        if e['key'] not in schema_fields ]

def timeseries_extra_fields(res):
    return [r for r in res.keys() if r not in
            ('id','resource_type','resource_group_id',
            'revision_id', 'url','description','format','date')]

def resource_extra_fields(res):
    return [r for r in res.keys() if r not in
            ('id','resource_type','resource_group_id',
            'revision_id', 'url','description','format')]

def cell_has_errors(errors, res_type, num, col):
    resource_errors = errors.get('individual_resources', [])
    return resource_errors and \
           num < len(resource_errors) and \
           bool(resource_errors[num].get(col, False))


def iterate_error_dict(d):
    for (k,v) in d.items():
        if isinstance(v, list) and len(v)==1:
            v = v[0]
        if isinstance(k, basestring):
            k = _translate_ckan_string(k)
        if isinstance(v, basestring):
            v = _translate_ckan_string(v)
        yield (k,v)

def _translate_ckan_string(o):
    """DGU uses different words for things compared to CKAN, so
    adjust the language of errors using mappings."""
    field_name_map = {
        'groups': 'Publisher',
        'organization': 'Publisher',
        'individual_resources': 'Data Files',
        'timeseries_resources': 'Data Files',
        'title': 'Name',
        'name': 'Unique identifier',
        'url': 'URL',
        'notes': 'Description',
        'theme-primary': 'Primary Theme',
        'license_id': 'Licence'
    }
    field_error_key_map = {
        'group': 'publisher',
        'organization': 'publisher',
        'description': 'title',
    }
    field_error_value_map = {
        'That group name or ID does not exist.': 'Missing value',
    }

    o = field_name_map.get(o,o)
    o = field_error_key_map.get(o,o)
    o = field_error_value_map.get(o,o)
    o = re.sub('[_-]', ' ', o)
    if o[0].lower() == o[0]:
        o = o.capitalize()
    return o

def get_license_extra(pkg):
    try:
        license_extra = pkg.extras.get('licence')
    except:
        license_extra = None
    return license_extra

ckan_licenses = None
def get_ckan_licenses():
    global ckan_licenses
    if ckan_licenses is None:
        from ckan import model
        ckan_license_dicts = model.Package.get_license_options()
        ckan_licenses = dict([(k, v) for v, k in ckan_license_dicts])
    return ckan_licenses

def license_choices(data):
    license_ids = ['uk-ogl', 'odc-odbl', 'odc-by', 'cc-zero', 'cc-by', 'cc-by-sa']
    selected_license = data.get('license_id')
    ckan_licenses = get_ckan_licenses()
    if selected_license not in license_ids and \
            selected_license in ckan_licenses:
        license_ids.append(selected_license)
    return [(id, ckan_licenses[id]) for id in license_ids]

def edit_publisher_group_name(data):
    if not data.get('organization'):
        group_name = None
        group_id = None
    else:
        group_id = data.get('organization').get('id', '')
        group_name = data.get('organization').get('name', '')

    if group_id:
      groups = [p['name'] for p in c.publishers.values() if p['id'] == group_id ]
      group_name = groups[0] if groups else ''

    return group_name
    #return c.publishers.get(group_name, {}) if group_id else data

def edit_publisher_group(data):
    if not data.get('organization'):
        group_name = None
        group_id = None
    else:
        group_id = data.get('organization').get('id', '')
        group_name = data.get('organization').get('name', '')

    if group_id:
      groups = [p['name'] for p in c.publishers.values() if p['id'] == group_id ]
      group_name = groups[0] if groups else ''

    return c.publishers.get(group_name, {}) if group_id else data

def secondary_themes(data):
    secondary_themes_raw = data.get('theme-secondary', '')
    if isinstance(secondary_themes_raw, basestring):
      secondary_themes = set(map(lambda s: s.strip(), re.sub('[["\]]', '', data.get('theme-secondary', '')).split(',')))
    else:
      secondary_themes = set(secondary_themes_raw)
    return secondary_themes

def free_tags(data):
    all_tags = [t['name'] for t in data.get('tags', [])]
    return set(all_tags) - set([data.get('theme-primary', '')]) - secondary_themes(data)

def is_package_edit_form(data):
    return bool(data.get('id', None)) and data.get('id') != 'None'

def use_wizard(data, errors):
    return not bool(errors) and not is_package_edit_form(data)

def are_timeseries_resources(data):
    are_timeseries_resources = False
    for res in data.get('timeseries_resources',[]):
        if res.get('format') or res.get('url') or res.get('description') or res.get('date'):
            are_timeseries_resources = True
            break
    return are_timeseries_resources

def are_legacy_extras(data):
    # These are not displayed on a package, but show on the edit form if they
    # have values, so that they are not lost.
    are_legacy_extras = False
    for key in set(('url', 'taxonomy_url', 'national_statistic', 'date_released', 'date_updated', 'date_update_future', 'precision', 'temporal_granularity', 'geographic_granularity')) & set(data.keys()):
        if data[key]:
            are_legacy_extras = True
            break
    return are_legacy_extras

def timeseries_resources():
    from ckan.lib.field_types import DateType
    unsorted = c.pkg_dict.get('timeseries_resources', [])
    get_iso_date = lambda resource: DateType.form_to_db(resource.get('date'),may_except=False)
    return sorted(unsorted, key=get_iso_date)

def additional_resources():
    return c.pkg_dict.get('additional_resources', [])

def gemini_resources():
    if not is_location_data(c.pkg_dict):
        return []
    harvest_object_id = get_pkg_dict_extra(c.pkg_dict, 'harvest_object_id')
    gemini_resources = [
        {'url': '/api/2/rest/harvestobject/%s/xml' % harvest_object_id,
         'title': 'Source GEMINI2 record',
         'type': 'XML',
         'action': 'View',
         'id': '',
         'gemini':True},
        {'url': '/api/2/rest/harvestobject/%s/html' % harvest_object_id,
         'title': 'Source GEMINI2 record (formatted)',
         'type': 'HTML',
         'action': 'View',
         'id': '',
         'gemini':True}]
    return gemini_resources

def individual_resources():
    r = c.pkg_dict.get('individual_resources', [])
    # In case the schema changes, the resources may or may not be split up into
    # three keys. So combine them if necessary
    if not r and not timeseries_resources() and not additional_resources():
        r = dict(c.pkg_dict).get('resources', [])
    return r

def has_group_ons_resources():
    resources = individual_resources()
    if not resources:
        return False

    return any(r.get('release_date', False) for r in resources)

def get_ons_releases():
    import collections
    resources = individual_resources()
    groupings = collections.defaultdict(list)
    for r in resources:
        groupings[r['release_date']].append(r)
    return sorted(groupings.keys(), reverse=True)

def ons_release_count():
    return len(get_ons_releases())

def get_limited_ons_releases():
    gps = get_ons_releases()
    return [gps[0]]

def get_resources_for_ons_release(release, count=None):
    import collections
    resources = individual_resources()
    groupings = collections.defaultdict(list)
    for r in resources:
        groupings[r['release_date']].append(r)
    if count:
        return groupings[release][:count]
    return groupings[release]

def get_resources_for_ons():
    import collections
    resources = individual_resources()
    groupings = collections.defaultdict(list)
    for r in resources:
        groupings[r['release_date']].append(r)
    return groupings


def init_resources_for_nav():
    # Core CKAN expects a resource dict to render in the navigation
    if c.pkg_dict:
        if not 'resources' in dict(c.pkg_dict):
            c.pkg_dict['resources'] = individual_resources() + timeseries_resources() + \
                additional_resources() + gemini_resources()

def was_dataset_harvested(pkg_extras):
    extras = dict(pkg_extras)
    # NB hopefully all harvested resources will soon use import_source=harvest
    # and we can simplify this.
    return extras.get('import_source') == 'harvest' or extras.get('UKLP') == 'True' or extras.get('INSPIRE') == 'True'

def get_harvest_object(pkg):
    from ckanext.harvest.model import HarvestObject
    harvest_object_id = pkg.extras.get('harvest_object_id')
    if harvest_object_id:
        return HarvestObject.get(harvest_object_id)

# 'Type'/'Source' of dataset determined by these functions
# (replaces dataset_type() as there were overlaps like local&location)

def is_location_data(pkg_dict):
    if get_pkg_dict_extra(pkg_dict, 'UKLP') == 'True' or \
       get_pkg_dict_extra(pkg_dict, 'INSPIRE') == 'True':
        return True

def dataset_is_from_ns_pubhub(pkg_dict):
    if get_pkg_dict_extra(pkg_dict, 'external_reference') == 'ONSHUB':
        return True

def is_local_government_data(pkg_dict):
    if pkg_dict['organization']:
        from ckan import model
        org = model.Group.get(pkg_dict['organization']['id'])
        if org:
            if org.extras.get('category') == 'local-council':
                return True

# end of 'Type'/'Source' of dataset functions


def has_bounding_box(extras):
    pkg_extras = dict(extras)
    return pkg_extras.get('bbox-north-lat') and pkg_extras.get('bbox-south-lat') and \
        pkg_extras.get('bbox-west-long') and pkg_extras.get('bbox-east-long')

def facet_keys(facet_tuples):
    keys = [ x[0] for x in facet_tuples ]
    keys = sorted( set(keys) )
    return keys

def facet_values(facet_tuples, facet_key):
    values = [ v for (k,v) in facet_tuples if k==facet_key ]
    values = sorted(values)
    return values

def has_extent(pkg):
    return bool(pkg.extras.get('spatial'))

def get_extent(pkg):
    extent_json_str = pkg.extras.get('spatial', False)
    # ensure it is JSON for security purposes, since the template will put it
    # in Javascipt unescaped using |safe
    try:
        return json.dumps(json.loads(extent_json_str))
    except ValueError:  # includes JSONDecodeError
        return ''

def get_tiles_url():
    GEOSERVER_HOST = config.get('ckanext-os.geoserver.host',
                'osinspiremappingprod.ordnancesurvey.co.uk') # Not '46.137.180.108'
    tiles_url_ckan = config.get('ckanext-os.tiles.url', 'http://%s/geoserver/gwc/service/wms' % GEOSERVER_HOST)
    api_key = config.get('ckanext-os.geoserver.apikey', '')
    if api_key:
        tiles_url_ckan+= '?key=%s' % urllib.quote(api_key)
    return tiles_url_ckan



def publisher_performance_data(publisher, include_sub_publishers):
    """
        Returns additional info for publishers, as traffic lights so that
        it can be viewed on the publisher read page.

        broken_links - green = 0%, amber <= 60% broken links, red > 60% broken
        openness - green if all > 4 *, amber for 50%> 3*, red otherwise
    """
    try:
        import ckanext.qa
    except ImportError:
        return None
    import time
    from ckanext.qa.reports import broken_resource_links_for_organisation
    from ckanext.dgu.lib import publisher as publib

    start_time = time.time()

    rcount = publib.resource_count(publisher, include_sub_publishers)
    log.debug("{p} has {r} resources".format(p=publisher.name, r=rcount))

    # Issues data
    issues = "green"

    if 'issues' in config['ckan.plugins']:
        # If issues are installed then we can use the info to determine
        # whether the issues are older than a month, between a fortnight
        # and a month, or less than a fortnight.
        from ckanext.issues.lib import util

        more_than_month = util.old_unresolved(publisher, days=30)
        more_than_fortnight = util.old_unresolved(publisher, days=14)

        if more_than_month:
            issues = 'red'
        elif more_than_fortnight:
            issues = 'amber'
        else:
            issues = 'green'

    spending = 'green'
    if publisher_has_spend_data(publisher):
        spending = 'red'

    # TODO: Add a count to result of broken_resource_links_for_organisation or write a version
    # that returns count().
    data = broken_resource_links_for_organisation(publisher.name, include_sub_publishers, use_cache=True)
    broken_count = len(data['data'])

    if broken_count == 0 or rcount == 0:
        pct = 0
    else:
        pct = int(100 * float(broken_count)/float(rcount))
    log.debug("{d}% of resources in {p} are broken".format(d=pct, p=publisher.name))

    broken_links = 'green'
    if 1 < pct <= 60:
        broken_links = 'amber'
    elif pct > 60:
        broken_links = 'red'

    openness = ''
    total, counters = publib.openness_scores(publisher, include_sub_publishers)
    number_x_or_above = lambda x: sum(counters.get(str(c),0) for c in xrange(x, 6))

    above_3 = number_x_or_above(3)
    pct_above_3 = int(100 * float(total)/float(above_3)) if above_3 else 0

    if number_x_or_above(4) == total:
        openness = 'green'
    elif pct_above_3 >= 50:
        openness = 'amber'
    else:
        openness = 'red'

    log.debug("publisher performance data took {d} seconds".format(d=time.time()-start_time))
    return {
        'broken_links': broken_links,
        'openness': openness,
        'issues': issues,
        'spending': spending
    }

def publisher_has_spend_data(publisher):
    return publisher.extras.get('category','') == 'ministerial-department'

def search_facets_unselected(facet_keys,sort_by='count'):
    unselected_raw = []
    for key in facet_keys:
        for value in unselected_facet_items(key):
            unselected_raw.append( (key,value) )
    unselected_raw = sorted(unselected_raw,reverse=True,key=lambda x:x[1][sort_by])
    unselected = []
    for key,value in unselected_raw:
        link = dgu_drill_down_url(facet_params_to_keep(), {key: value['name']})
        text = "%s (%d)" % (search_facet_text(key,value['name']),value['count'])
        tooltip = search_facet_tooltip(key,value['name'])
        unselected.append( (link,text,tooltip,value['name']) )
    # Special case behaviour for publishers
    if 'publisher' in facet_keys and request.params.get('publisher',''):
        params_to_keep = dict(facet_params_to_keep())
        del params_to_keep['publisher']
        link = dgu_drill_down_url(params_to_keep.items(), {'parent_publishers':request.params.get('publisher','')})
        unselected.append( (link,'Include sub-publishers',None,None) )
    return unselected

def search_facets_selected(facet_keys):
    selected = []
    for (key,value) in c.fields:
        if key not in facet_keys: continue
        link = c.remove_field(key,value)
        text = search_facet_text(key,value)
        tooltip = search_facet_tooltip(key,value)
        selected.append( (link,text,tooltip) )
    # Special case behaviour for publishers
    if 'parent_publishers' in facet_keys and request.params.get('parent_publishers',''):
        params_to_keep = dict(facet_params_to_keep())
        del params_to_keep['parent_publishers']
        link = dgu_drill_down_url(params_to_keep.items(), {'publisher':request.params.get('parent_publishers','')})
        selected.append( (link,'Include sub-publishers',None) )
    return selected

def search_facet_text(key,value):
    if key=='core_dataset':
        if value=='true':
            return 'Show NII datasets'
        return 'Hide NII datasets'
    if key=='api':
        if value=='true':
            return 'Show datasets with APIs'
        return 'Hide datasets with APIs'
    if key=='unpublished':
        if value=='true':
            return 'Unpublished datasets'
        return 'Published datasets'
    if key=='license_id-is-ogl':
        if value=='true':
            return 'Open Government Licence'
        elif value=='unpublished':
            return 'Unpublished dataset'
        return 'Non-Open Government Licence'
    if key=='openness_score':
        try:
            stars = int(value)
        except ValueError:
            return value
        if stars == -1:
            return 'TBC'
        return t.literal( (stars * '&#9733') + ('&#9734' * (5-stars)) )
    if key=='publisher' or key=='parent_publishers':
        return ckan.lib.helpers.group_name_to_title(value)
    if key=='UKLP':
        return 'UK Location Dataset'
    if key=='resource-type':
        # The values retrieved for resource-type are quoted
        # and shouldn't be.  If they are found to start with a "
        # then we will strip them.
        if value.startswith('"'):
            value = value[1:-1]
        mapping = {
                'dataset' : 'Dataset',
                'service' : 'Service',
                'series' : 'Series',
                'nonGeographicDataset' : 'Non-Geographic Dataset',
                'application' : 'Application',
            }
        return mapping.get(value,value)
    if key=='spatial-data-service-type':
        mapping = {
                'view' : 'View',
                'other' : 'Other',
                'OGC:WMS' : 'Web Map Service',
                'download' : 'Download',
                'discovery' : 'Discovery',
            }
        return mapping.get(value,value)
    return value

def search_facet_tooltip(key,value):
    if key=='openness_score':
        try:
            stars = int(value)
        except ValueError:
            return
        if stars == -1:
            return
        mini_stars = stars * '&#9733'
        mini_stars += '&#9734' * (5-stars)
        captions = [
            'Unavailable or not openly licensed',
            'Unstructured data (e.g. PDF)',
            'Structured data but proprietry format (e.g. Excel)',
            'Structured data in open format (e.g. CSV)',
            'Linkable data - served at URIs (e.g. RDF)',
            'Linked data - data URIs and linked to other data (e.g. RDF)'
            ]
        return captions[stars]
    return

def social_url_twitter(url,title):
    import urllib
    twitter_parameters = {
      'original_referer':url.encode('utf-8'),
      'text':title.encode('utf-8'),
      'tw_p':'tweetbutton',
      'url':url.encode('utf-8'),
    }
    twitter_url = 'https://twitter.com/intent/tweet?' + urllib.urlencode(twitter_parameters)
    return twitter_url

def social_url_facebook(url):
    facebook_url = 'https://www.facebook.com/sharer/sharer.php?u='+url
    return facebook_url

def social_url_google(url):
    google_url = 'https://plus.google.com/share?url='+url
    return google_url

def ckan_asset_timestamp():
    from ckanext.dgu.theme.timestamp import asset_build_timestamp
    return asset_build_timestamp

shared_assets_timestamp = None
def get_shared_assets_timestamp():
    global shared_assets_timestamp
    if shared_assets_timestamp is None:
        # Deployments should set this config
        timestamp_filepath = config.get('dgu.shared_assets_timestamp_path')
        if not timestamp_filepath:
            # Default place to find shared_dguk_assets repo is next to this
            # repo - perfect for developers
            import os
            this_file = os.path.dirname(os.path.realpath(__file__))
            timestamp_filepath = os.path.join(this_file, '..', '..', '..', '..', 'shared_dguk_assets', 'assets', 'timestamp')
        try:
            with open(timestamp_filepath) as f:
                shared_assets_timestamp = f.read()
        except Exception as e:
            log.error('failed to load shared assets timestamp: %s' % e)
            shared_assets_timestamp = '-1'
    return shared_assets_timestamp

def search_theme_mode_primary():
    # Return True if searching by Primary Theme.
    return 'theme-primary' in request.params.keys()

def search_theme_mode_secondary():
    # Return True if searching by Any Theme.
    return (not search_theme_mode_primary()) and 'all_themes' in request.params.keys()

def search_theme_mode_none():
    # True when no Theme facet is active.
    # The user can select whether their Theme facet is restricted to the _primary_ theme.
    return not (search_theme_mode_primary() or search_theme_mode_secondary())

def search_theme_mode_attrs():
    out = {}
    if not search_theme_mode_none():
        out['disabled'] = 'disabled'
    if not search_theme_mode_secondary():
        out['checked'] = 'checked'
    return out

def get_package_from_id(id):
    from ckan.model import Package
    return Package.get(id)

def will_be_published(package):
    from paste.deploy.converters import asbool
    has_restriction = asbool(get_from_flat_dict(package['extras'], 'publish-restricted', False))
    if not has_restriction:
        return True, unpublished_release_date(package)
    return False, None

def unpublished_release_date(package):
    return get_from_flat_dict(package['extras'], 'publish-date')


def is_unpublished_item(package):
    if not package:
        # e.g. when displaying package/new form
        return False
    from paste.deploy.converters import asbool
    return asbool(get_from_flat_dict(package['extras'], 'unpublished'))

def is_unpublished_unavailable(package):
    return get_from_flat_dict(package['extras'], 'publish-restricted', False)

def unpublished_release_notes(package):
    return get_from_flat_dict(package['extras'], 'release-notes')

def tidy_url(url):
    '''
    Given a URL it does various checks before returning a tidied version
    suitable for calling.
    '''
    import urlparse

    # Find out if it has unicode characters, and if it does, quote them
    # so we are left with an ascii string
    try:
        url = url.decode('ascii')
    except:
        parts = list(urlparse.urlparse(url))
        parts[2] = urllib.quote(parts[2].encode('utf-8'))
        url = urlparse.urlunparse(parts)
    url = str(url)

    # strip whitespace from url
    # (browsers appear to do this)
    url = url.strip()

    try:
        parsed_url = urlparse.urlparse(url)
    except Exception, e:
        raise Exception('URL parsing failure: %s' % e)

    # Check we aren't using any schemes we shouldn't be
    if not parsed_url.scheme in ('http', 'https', 'ftp'):
        raise Exception('Invalid url scheme "%s". Please use one of: http, https, ftp. Url: %s' % (parsed_url.scheme, url))

    if not parsed_url.netloc:
        raise Exception('URL parsing failure - did not find a host name: %s' % url)

    return url

def inventory_status(package_items):
    from ckan import model
    for p in package_items:
        pid = p['package']
        action = p['action']
        pkg = model.Package.get(pid)
        grp = pkg.get_organization()

        yield pkg,grp, pkg.extras.get('publish-date', ''), pkg.extras.get('release-notes', ''), action

def themes_count():
    from ckan import model
    theme_count = {}
    for theme, theme_dict in themes().items():
        count = model.Session.query(model.Package)\
            .join(model.PackageExtra)\
            .filter(model.PackageExtra.key=='theme-primary')\
            .filter(model.PackageExtra.value==theme_dict['title'])\
            .filter(model.Package.state=='active').count()
        theme_count[theme_dict['title']] = count
    return theme_count

def themes():
    from ckanext.dgu.lib.theme import Themes
    return Themes.instance().data

def span_read_more(text, word_limit, classes=""):
    trimmed = truncate(text, length=word_limit, whole_word=True)
    if trimmed==text:
        return t.literal('<span class="%s">%s</span>' %
                         (classes, escape(text)))
    return t.literal('<span class="read-more-parent">\
            <span style="display:none;" class="expanded %s">%s</span>\
            <span class="collapsed %s">%s</span>\
            <a href="#" class="collapsed link-read-more">Read more &raquo;</a>\
            <a href="#" class="expanded link-read-less" style="display:none;">&laquo; Hide</a>\
            </span>' % (classes, escape(text),
                        classes, trimmed))

def render_db_date(db_date_str):
    '''Takes a string as we generally store it in the database and returns it
    rendered nicely to show to the user.
    e.g. '2014/02/01' -> '1/2/2014'
         '2014/02' -> '2/2014'
         '2014' -> '2014'
    Non-parsing strings get '' returned.
    '''
    from ckan.lib.field_types import DateType, DateConvertError
    try:
        return DateType.db_to_form(db_date_str)
    except DateConvertError:
        return ''


def pagination_links(page,numpages,url_for_page):
    # Link to the first page, lastpage, and nearby pages
    pages_nearby = range( max(page-3,1), min(page+3,numpages) )
    pages_all = [1,numpages] + pages_nearby
    # Walk through the ordered, deduplicated list of pages
    out = sorted(list(set(pages_all)))
    for i in range(len(out)):
        if out[i]==page:
            yield out[i], None
        else:
            yield out[i], url_for_page(out[i])
        # Is there a jump? Emit a "..."
        if i+1<len(out):
            if out[i+1] > out[i]+1:
                yield "...",None

############################################
# Commitment report helpers
############################################
def commitments_count_and_met(publisher_name, commitments):
    count, met = 0, 0
    for c in commitments:
        if c.publisher == publisher_name:
            count = count + 1
            if c.dataset:
                met = met + 1
    return count, met

def commitments_count_and_met_totals(commitments):
    count, met = 0, 0
    for c in commitments:
        count = count + 1
        if c.dataset:
            met = met + 1
    return count, met

def commitments_by_source(all_commitments, source):
    commitments = []
    for co in all_commitments:
        if co.source == source:
            commitments.append(co)
    commitments.sort(key=lambda x: x.commitment_text)
    return commitments

def commitment_dataset(commitment):
    import ckan.model as model
    if commitment.dataset:
        dataset = model.Package.get(commitment.dataset)
        return dataset
    return None

def open_data_strategy_link(publisher):
    from ckanext.dgu.model.commitment import ODS_ORGS, ODS_LINKS
    for k, v in ODS_ORGS.iteritems():
        if v == publisher.name:
            return ODS_LINKS[k]
    return ""

def has_commitment(publisher):
    from ckanext.dgu.model.commitment import ODS_ORGS
    return publisher.name in ODS_ORGS.values()

def is_core_dataset(package):
    from paste.deploy.converters import asbool
    v = get_from_flat_dict(package['extras'], 'core-dataset')
    try:
        return asbool(v)
    except:
        pass

    return False

def report_generated_at(reportname, object_id='__all__', withsub=False):
    from ckan import model
    from ckanext.report.model import DataCache
    nm = reportname
    if withsub:
        nm = nm + '-withsub'
    cache_data = model.Session.query(DataCache.created)\
        .filter(DataCache.object_id == object_id)\
        .filter(DataCache.key == nm).first()
    log.debug("Generation date for {0} using {1} - found? {2}"\
        .format(nm, object_id, cache_data is not None))
    return cache_data[0] if cache_data else datetime.datetime.now()

def relative_url_for(**kwargs):
    '''Return the existing URL but amended for the given url_for-style
    parameters. Much easier than calling h.add_url_param etc. For switching to
    URLs inside the current controller action only.
    '''
    from ckan.lib.base import h
    # Restrict the request params to the same action & controller, to avoid
    # being an open redirect.
    disallowed_params = set(('controller', 'action', 'anchor', 'host',
                             'protocol', 'qualified'))
    user_specified_params = [(k, v) for k, v in request.params.items()
                             if k not in disallowed_params]
    args = dict(request.environ['pylons.routes_dict'].items()
                + user_specified_params
                + kwargs.items())
    # remove blanks
    for k, v in args.items():
        if not v:
            del args[k]
    return h.url_for(**args)

def get_related_apps(pid):
    from ckan import model
    pkg = model.Package.get(pid)
    for rel in pkg.related:
        if rel.type == 'App':
            yield rel

def has_related_apps(pid):
    return len(list(get_related_apps(pid))) > 0

def parse_date(date_string):
    from ckan.lib.field_types import DateType, DateConvertError

    try:
        return DateType.parse_timedate(date_string, 'form')
    except DateConvertError:
        class FakeDate(dict):
            pass
        return FakeDate(year='')

def user_page_url():
    from ckan.lib.base import h
    url = '/user' if 'dgu_drupal_auth' in config['ckan.plugins'] \
                  else h.url_for(controller='user', action='me')
    if not c.user:
        url += '?destination=%s' % request.path[1:]
    return url

def is_plugin_enabled(plugin_name):
    return plugin_name in config.get('ckan.plugins', '').split()

def config_get(key, default=None):
    return config.get(key, default)

def paginator_page_url(pageobj):
    # Return a function that can be queried to get the url for a specific
    # page.
    return lambda x: pageobj._url_generator(page=x)

def is_dict(d):
    return type(d) == dict and bool(d)

def is_list(d):
    return type(d) == list and bool(d)

def is_string(d):
    return (type(d) in [str, unicode]) and bool(d)

def list_enumerate(l):
    return enumerate(l)

def sorted_list(l):
    return sorted(l)

def as_dict(d):
    return dict(d)

def extract_year(resource_dict):
    return parse_date(resource_dict.get('date'))['year']

def report_match_organization_name(name, dct):
    return filter(lambda d: d['organization_name'] == name, dct)

def report_match_rows(rows, type_, quarter):
    return [row for row in rows if (row[3]==type_ and row[4]==quarter)]

def report_timestamps_split(timestamps):
    return [render_datetime(timestamp) for timestamp in timestamps.split(' ')]

def report_users_split(users, organization):
    return [dgu_linked_user(user, organization=organization) for user in users.split(' ')]

def closed_publisher_ids():
    """
    Returns the IDs of all of the closed publishers. For use in
    publisher_index.
    """
    import ckan.model as model
    extras = model.Session.query(model.GroupExtra.group_id)\
        .filter(model.GroupExtra.key == 'closed')\
        .filter(model.GroupExtra.value == 'true')\
        .filter(model.GroupExtra.state == 'active')
    return set(e[0] for e in extras.all())

def all_publishers(exclude=None):
    import ckan.model as model
    pubs = model.Session.query(model.Group.name, model.Group.title)\
        .filter(model.Group.state=='active')\
        .filter(model.Group.type=='organization')

    return pubs.order_by(model.Group.title)

def get_closed_publisher_message(pub):
    """ For publishers that are closed, this function will return a message to
        display on the publisher_read/publisher_edit pages """
    import ckan.model as model

    closed = pub.get('closed')
    replaced_by = pub.get('replaced_by')

    if not closed:
        return None

    extra_msg = None
    if replaced_by:
        if isinstance(replaced_by, basestring):
            replaced_by = [replaced_by]
        publisher_urls = []
        for p in replaced_by:
            g = model.Group.get(p)
            if not g:
                log.warning('Could not find %s which replaces publisher %s', p,
                            pub['name'])
                continue
            publisher_urls.append('<a href="/publisher/%s">%s</a>' % (g.name, g.title,))
        extra_msg = ' or '.join(publisher_urls)
        extra_msg = 'Please see %s instead.' % extra_msg

    return 'This publisher has closed. %s ' % (extra_msg or '')

def put_closed_publishers_last(pub_list, closed_publisher_ids):
    open_pubs = []
    closed_pubs = []
    for pub in pub_list:
        if pub['id'] in closed_publisher_ids:
            closed_pubs.append(pub)
        else:
            open_pubs.append(pub)
    return open_pubs + closed_pubs

def get_dgu_dataset_form_options(field_name):
    '''
    Returns a list of option tuples for the given field.
    Each tuple: (code_as_stored_in_db, displayed_value)

    :param field_name: e.g. "geographic_granularity"
    '''
    from ckanext.dgu.forms import dataset_form
    return getattr(dataset_form, field_name)

def orgs_for_admin_report():
    from ast import literal_eval
    from ckan.logic import get_action
    from ckan import model

    context = {'model': model, 'session': model.Session}

    admin_orgs = organizations_available(permission='admin')

    relationship_managers = literal_eval(config.get('dgu.relationship_managers', '{}'))

    allowed_orgs = relationship_managers.get(c.user, [])
    if allowed_orgs:
        data_dict = {
            'organizations': allowed_orgs,
            'all_fields': True,
        }
        rm_orgs = get_action('organization_list')(context, data_dict)
    else:
        rm_orgs = []

    all_orgs = {}
    for org in (admin_orgs + rm_orgs):
       all_orgs[org['name']] = org

    return sorted(all_orgs.values(), key=lambda x: x['title'])

def all_la_org_names():
    from ckan import model
    la_root = model.Group.get('local-authorities')
    return sorted([la.name for la in sorted(la_root.get_children_groups(type='organization'), key=lambda g: g.title)])

def all_la_org_names_and_titles():
    from ckan import model
    la_root = model.Group.get('local-authorities')
    return sorted([(la.name, la.title) for la in sorted(la_root.get_children_groups(type='organization'), key=lambda g: g.title)])

def get_schema_options():
    from ckan.logic import get_action
    from ckan import model

    context = {'model': model, 'session': model.Session}
    return get_action('schema_list')(context, {})

def get_la_schema_options():
    all_schemas = get_schema_options()
    incentive_schemas = []
    for schema in all_schemas:
        if 'LGTC' in schema['title']:
            incentive_schemas.append(schema)
    return incentive_schemas

def get_codelist_options():
    from ckan.logic import get_action
    from ckan import model

    context = {'model': model, 'session': model.Session}
    return get_action('codelist_list')(context, {})

def get_mandate_list(data):
    mandate = data.get('mandate') or []
    if isinstance(mandate, basestring):
        # This shouldn't happen, but maybe a harvester puts in a string
        return [mandate]
    if not isinstance(mandate, list):
        log.error('Mandate should be a list: %r', mandate)
        return mandate
    return mandate

def ensure_ids_are_in_a_list_of_dicts(l):
    if isinstance(l, basestring):
        # validation error when there is a single schema/codelist drop-down
        return [{'id': l}]
    elif isinstance(l, list) and l and isinstance(l[0], basestring):
        # validation error when there are multiple schema/codelist drop-downs
        return [{'id': id} for id in l]
    # initial load of the form
    return l

def get_sla():
    return 'The data publisher commits to the continuing publication of the data and to provide advance notice (on the data.gov.uk dataset page) of any changes to the structure of the data, the update schedule or cessation.'

def get_issue_count(pkg_id):
    if not is_plugin_enabled('issues'):
        return 0
    return 10

