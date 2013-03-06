import os

from logging import getLogger
from urllib import quote

from pylons import config

from ckan.lib.helpers import flash_notice
from ckanext.dgu.plugins_toolkit import ObjectNotFound
from ckan.plugins import implements, SingletonPlugin
from ckan.plugins import IRoutes
from ckan.plugins import IConfigurer
from ckan.plugins import IGenshiStreamFilter
from ckan.plugins import IMiddleware
from ckan.plugins import IAuthFunctions
from ckan.plugins import IPackageController
from ckan.plugins import ISession
from ckanext.dgu.authentication.drupal_auth import DrupalAuthMiddleware
from ckanext.dgu.authorize import (dgu_group_update, dgu_group_create,
                             dgu_package_create, dgu_package_update,
                             dgu_package_create_rest, dgu_package_update_rest,
                             dgu_extra_fields_editable,
                             dgu_dataset_delete, dgu_user_list, dgu_user_show)
from ckan.lib.helpers import url_for
from ckanext.dgu.lib.helpers import dgu_linked_user
from ckanext.dgu.lib.search import solr_escape
import ckanext.dgu
from ckanext.dgu.search_indexing import SearchIndexing
from ckan.config.routing import SubMapper

log = getLogger(__name__)

def configure_template_directory(config, relative_path):
    configure_served_directory(config, relative_path, 'extra_template_paths')

def configure_public_directory(config, relative_path):
    configure_served_directory(config, relative_path, 'extra_public_paths')

def configure_served_directory(config, relative_path, config_var):
    'Configure serving of public/template directories.'
    assert config_var in ('extra_template_paths', 'extra_public_paths')
    this_dir = os.path.dirname(ckanext.dgu.__file__)
    absolute_path = os.path.join(this_dir, relative_path)
    if absolute_path not in config.get(config_var, ''):
        if config.get(config_var):
            config[config_var] = absolute_path + ',' + config[config_var]
        else:
            config[config_var] = absolute_path

def after(instance, action, **params):
    from pylons import response
    instance._set_cors()
    response.headers['Vary'] = 'Cookie'

def not_found(self, url):
    from ckan.lib.base import abort
    abort(404)

class ThemePlugin(SingletonPlugin):
    '''
    DGU Visual Theme for a CKAN install embedded in dgu/Drupal.
    '''
    implements(IConfigurer)
    implements(IRoutes, inherit=True)

    from ckan.lib.base import h, BaseController
    # [Monkey patch] Replace h.linked_user with a version to hide usernames
    h.linked_user = dgu_linked_user
    # [Monkey patch] Replace BaseController.__after__ to allow us to add more
    # headers for caching
    BaseController.__after__ = after
    # [Monkey patch] Replace TemplateController.view since it isn't used
    # in normal use. Hack attempts sometimes get through to it though
    # and there is no need to attempt to barf on their unicode characters
    from ckan.controllers.template import TemplateController
    TemplateController.view = not_found

    def update_config(self, config):
        configure_template_directory(config, 'theme/templates')
        configure_public_directory(config, 'theme/public')

    def before_map(self, map):
        """
        Make "/data" the homepage.
        """
        data_controller = 'ckanext.dgu.controllers.data:DataController'
        tag_controller = 'ckanext.dgu.controllers.tag:TagController'
        map.redirect('/', '/data')
        map.connect('/data', controller=data_controller, action='index')
        map.connect('/data/tag', controller=tag_controller, action='index')
        map.connect('/data/tag/{id}', controller=tag_controller, action='read')
        map.connect('/data/search', controller='package', action='search')
        map.connect('/data/api', controller=data_controller, action='api')
        map.connect('/data/system_dashboard', controller=data_controller, action='system_dashboard')
        map.connect('/data/openspending-browse', controller=data_controller, action='openspending_browse')
        map.connect('/data/openspending-report/index', controller=data_controller, action='openspending_report')
        map.connect('/data/openspending-report/{id}', controller=data_controller, action='openspending_publisher_report')
        map.connect('/data/openspending-report/{id}', controller=data_controller, action='openspending_publisher_report')
        map.connect('/data/carparks', controller=data_controller, action='carparks')

        # For test usage when Drupal is not running
        map.connect('/comment/get/{id}',
                    controller='ckanext.dgu.controllers.package:CommentProxy',
                    action='get_comments')

        # Map /user* to /data/user/ because Drupal uses /user
        with SubMapper(map, controller='user') as m:
            m.connect('/data/user/edit', action='edit')
            m.connect('/data/user/edit/{id:.*}', action='edit')
            m.connect('/data/user/reset/{id:.*}', action='perform_reset')
            m.connect('/data/user/register', action='register')
            m.connect('/data/user/login', action='login')
            m.connect('/data/user/_logout', action='logout')
            m.connect('/data/user/logged_in', action='logged_in')
            m.connect('/data/user/logged_out', action='logged_out')
            m.connect('/data/user/logged_out_redirect', action='logged_out_page')
            m.connect('/data/user/reset', action='request_reset')
            m.connect('/data/user/me', action='me')
            m.connect('/data/user/set_lang/{lang}', action='set_lang')
            m.connect('/data/user/{id:.*}', action='read')
            m.connect('/data/user', action='index')


        return map

    def after_map(self, map):
        return map

class DrupalAuthPlugin(SingletonPlugin):
    '''Reads Drupal login cookies to log user in.'''
    implements(IMiddleware, inherit=True)

    def make_middleware(self, app, config):
        return DrupalAuthMiddleware(app, config)

class AuthApiPlugin(SingletonPlugin):
    '''Adds functions that work out if the user is allowed to do
    certain edits.'''
    implements(IAuthFunctions, inherit=True)

    def get_auth_functions(self):
        return {
            'group_update' : dgu_group_update,
            'group_create' : dgu_group_create,
            'package_create' : dgu_package_create,
            'package_update' : dgu_package_update,
            'package_create_rest' : dgu_package_create_rest,
            'package_update_rest' : dgu_package_update_rest,
            'package_extra_fields_editable' : dgu_extra_fields_editable,
            'package_delete': dgu_dataset_delete,
            'user_list': dgu_user_list,
            'user_show': dgu_user_show,
        }


class DguForm(SingletonPlugin):

    implements(IRoutes, inherit=True)
    implements(IConfigurer)

    def before_map(self, map):
        dgu_package_controller = 'ckanext.dgu.controllers.package:PackageController'
        map.connect('dataset_new','/dataset/new', controller=dgu_package_controller, action='new')
        map.connect('dataset_edit','/dataset/edit/{id}', controller=dgu_package_controller, action='edit')
        map.connect('/dataset/delete/{id}', controller=dgu_package_controller, action='delete')
        map.connect('dataset_history','/dataset/history/{id}', controller=dgu_package_controller, action='history')
        map.connect('/dataset/{id}.{format}', controller=dgu_package_controller, action='read')
        map.connect('/dataset/{id}', controller=dgu_package_controller, action='read')
        map.connect('/dataset/{id}/resource/{resource_id}', controller=dgu_package_controller, action='resource_read')
        return map

    def after_map(self, map):
        return map

    def update_config(self, config):
        pass


class PublisherPlugin(SingletonPlugin):

    implements(IRoutes, inherit=True)
    implements(IConfigurer)
    implements(ISession, inherit=True)


    def before_commit(self, session):
        """
        Before we commit a session we will check to see if any of the new
        items are users so we can notify them to apply for publisher access.
        """
        from pylons.i18n import _
        from ckan.model.group import User

        session.flush()
        if not hasattr(session, '_object_cache'):
            return

        pubctlr = 'ckanext.dgu.controllers.publisher:PublisherController'
        for obj in set( session._object_cache['new'] ):
            if isinstance(obj, (User)):
                url = url_for(controller=pubctlr, action='apply')
                msg = "You can now <a href='%s'>apply for publisher access</a>" % url
                try:
                    flash_notice(_(msg), allow_html=True)
                except TypeError:
                    # Raised when there is no session registered, and this is
                    # the case when using the paster commands.
                    log.warning('Failed to add a flash message due to a missing session: %s' % msg)


    def before_map(self, map):
        pub_ctlr = 'ckanext.dgu.controllers.publisher:PublisherController'
        map.connect('publisher_index',
                    '/publisher',
                    controller=pub_ctlr, action='index')
        map.connect('publisher_edit',
                    '/publisher/edit/:id',
                    controller=pub_ctlr, action='edit' )
        map.connect('publisher_apply',
                    '/publisher/apply/:id',
                    controller=pub_ctlr, action='apply' )
        map.connect('publisher_apply_empty',
                    '/publisher/apply',
                    controller=pub_ctlr, action='apply' )
        map.connect('publisher_users',
                    '/publisher/users/:id',
                    controller=pub_ctlr, action='users' )
        map.connect('publisher_new',
                    '/publisher/new',
                    controller=pub_ctlr, action='new'  )
        map.connect('/publisher/report_groups_without_admins',
                    controller=pub_ctlr, action='report_groups_without_admins' )
        map.connect('/publisher/report_publishers_and_users',
                    controller=pub_ctlr, action='report_publishers_and_users' )
        map.connect('/publisher/report_users',
                    controller=pub_ctlr, action='report_users' )
        map.connect('/publisher/report_users_not_assigned_to_groups',
                    controller=pub_ctlr, action='report_users_not_assigned_to_groups' )
        map.connect('publisher_read',
                    '/publisher/:id',
                    controller=pub_ctlr, action='read' )
        return map

    def after_map(self, map):
        return map

    def update_config(self, config):
        # set the auth profile to use the publisher based auth
        config['ckan.auth.profile'] = 'publisher'

        # same for the harvesting auth profile
        config['ckan.harvest.auth.profile'] = 'publisher'

class SearchPlugin(SingletonPlugin):
    """
    DGU-specific searching.

    One thing DGU specific about the search is that DGU facets on
    whether a dataset's license_id is OGL (Open Government License) or not.
    Since this is calculable from the license_id, but is not a facet over the
    whole set of possible license_id values (ie. 'ukcrown', 'other' etc. should
    all be grouped together under the 'non-ogl' facet), we index on a field
    that doesn't exist on the dataset itself.  See `SearchPlugin.before_index`.

    Another thing that DGU does differently is that it cleans up the resource
    formats prior to indexing.

    A further thing that DGU does differently is to index the group title, as
    well as the group name.
    """

    implements(IPackageController)

    def read(self, entity):
        pass

    def create(self, entity):
        pass

    def edit(self, entity):
        pass

    def authz_add_role(self, object_role):
        pass

    def authz_remove_role(self, object_role):
        pass

    def delete(self, entity):
        pass

    def before_search(self, search_params):
        """
        Modify the search query.
        """
        # Set the 'qf' (queryfield) parameter to a fixed list of boosted solr fields
        # tuned for DGU. If a dismax query is run, then these will be the fields that are searched
        # within.
        search_params['qf'] = 'title^4 name^3 notes^2 text tags^0.3 group_titles^0.3 extras_harvest_document_content^0.2'

        # Escape q so that you can include dashes in the search and it doesn't mean 'NOT'
        # e.g. "Spend over 25,000 - NHS Leeds" -> "Spend over 25,000 \- NHS Leeds"
        # You can avoid this escaping on the API by setting escape_q=False.
        if 'q' in search_params and search_params.get('escape_q', True):
            search_params['q'] = solr_escape(search_params['q'])
        if 'escape_q' in search_params:
            search_params.pop('escape_q')

        # If the user does not specify a "sort by" method manually,
        # then it defaults here (and the UI has to have the same logic)
        # NB The UI has to be kept in step with this logic:
        #    ckanext/dgu/theme/templates/package/search.html
        order_by = search_params.get('sort')
        bbox = search_params.get('extras', {}).get('ext_bbox')
        search_params_apart_from_bbox = search_params.get('q', '') + search_params.get('fq', '')
        sort_by_location_enabled = bool(bbox and not search_params_apart_from_bbox)

        if order_by in (None, 'spatial desc') and sort_by_location_enabled:
            search_params['sort'] = 'spatial desc'
            # This sort parameter is picked up by ckanext-spatial
        elif order_by in (None, 'rank'):
            # Score = SOLR rank = relevancy = how well q keyword matches the
            # SOLR record's text content.
            # Add popularity into default ranking - this kicks when there is
            # no keyword, so no rank. Leave name there, in case no popularity
            # scores have been loaded.
            search_params['sort'] = 'score desc, popularity desc, name asc'

        return search_params

    def after_search(self, search_results, search_params):
        return search_results

    def before_view(self, pkg_dict):
        return pkg_dict

    def before_index(self, pkg_dict):
        """
        Dynamically creates a license_id-is-ogl field to index on, and clean
        up resource formats prior to indexing.
        """
        SearchIndexing.clean_title_string(pkg_dict)
        SearchIndexing.add_field__is_ogl(pkg_dict)
        SearchIndexing.resource_format_cleanup(pkg_dict)
        SearchIndexing.add_field__group_titles(pkg_dict)
        SearchIndexing.add_field__publisher(pkg_dict)
        SearchIndexing.add_field__harvest_document(pkg_dict)
        SearchIndexing.add_field__openness(pkg_dict)
        SearchIndexing.add_popularity(pkg_dict)
        return pkg_dict

class ApiPlugin(SingletonPlugin):
    '''DGU-specific API'''
    implements(IRoutes, inherit=True)

    def before_map(self, map):
        api_controller = 'ckanext.dgu.controllers.api:DguApiController'
        map.connect('/api/util/latest-datasets', controller=api_controller, action='latest_datasets')
        map.connect('/api/util/dataset-count', controller=api_controller, action='dataset_count')
        return map

class DguDatasetExtentMap(SingletonPlugin):

    implements(IGenshiStreamFilter)

    def filter(self, stream):
        from pylons import request, tmpl_context as c

        route_dict = request.environ.get('pylons.routes_dict')
        route = '%s/%s' % (route_dict.get('controller'), route_dict.get('action'))
        routes_to_filter = config.get('ckan.spatial.dataset_extent_map.routes', 'package/read').split(' ')
        if route in routes_to_filter and hasattr(c.pkg, 'id') and c.pkg.id:
            extent = c.pkg.extras.get('spatial',None)
            if extent:
                GEOSERVER_HOST = config.get('ckanext-os.geoserver.host',
                            'osinspiremappingprod.ordnancesurvey.co.uk') # Not '46.137.180.108'
                c.tiles_url_ckan = config.get('ckanext-os.tiles.url', 'http://%s/geoserver/gwc/service/wms' % GEOSERVER_HOST)
                api_key = config.get('ckanext-os.geoserver.apikey', '')
                if api_key:
                    c.tiles_url_ckan+= '?key=%s' % quote(api_key)
                c.dataset_extent = extent
        return stream

