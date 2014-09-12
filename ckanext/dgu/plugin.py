from logging import getLogger

from pylons import config
import sqlalchemy.orm

from ckan.lib.helpers import flash_notice
import ckan.plugins as p
import ckan.plugins.toolkit as toolkit
from ckanext.dgu.authentication.drupal_auth import DrupalAuthMiddleware
from ckanext.dgu.authorize import (
                             dgu_package_update,
                             dgu_extra_fields_editable,
                             dgu_dataset_delete, dgu_user_list, dgu_user_show,
                             dgu_feedback_update, dgu_feedback_create,
                             dgu_feedback_delete, dgu_organization_delete,
                             dgu_group_change_state,
                             )
from ckanext.report.interfaces import IReport
from ckan.lib.helpers import url_for
from ckanext.dgu.lib.helpers import dgu_linked_user
from ckanext.dgu.lib.search import solr_escape
from ckanext.dgu.search_indexing import SearchIndexing
from ckan.config.routing import SubMapper
from ckan.exceptions import CkanUrlException

log = getLogger(__name__)


def after(instance, action, **params):
    from pylons import response
    instance._set_cors()
    response.headers['Vary'] = 'Cookie'

def not_found(self, url):
    from ckan.lib.base import abort
    abort(404)

def _guess_package_type(self, expecting_name=False):
    return 'dataset'

class DguReportPlugin(p.SingletonPlugin):
    p.implements(p.IRoutes, inherit=True)

    def after_map(self, map):
        # Put reports at /data/reports instead of /reports
        # Delete routes to /report otherwise url_for links end up pointed there.
        matches_to_delete = []
        for match in map.matchlist:
            if match.routepath.startswith('/report'):
                matches_to_delete.append(match)
        for match in matches_to_delete:
            map.matchlist.remove(match)
        for route_name in ('reports', 'report', 'report-org'):
            del map._routenames[route_name]

        # Add new routes to /data/reports
        report_ctlr = 'ckanext.report.controllers:ReportController'
        map.connect('reports', '/data/report', controller=report_ctlr, action='index')
        map.redirect('/data/reports', '/data/report')
        map.connect('report', '/data/report/:report_name', controller=report_ctlr, action='view')
        map.connect('report-org', '/data/report/:report_name/:organization', controller=report_ctlr, action='view')

        # Commitment reports
        c_ctlr = 'ckanext.dgu.controllers.commitment:CommitmentController'
        map.connect('commitments', '/data/reports/commitments',
                    controller=c_ctlr, action='index')
        map.connect('commitments_publisher', '/data/reports/commitments/:id',
                    controller=c_ctlr, action='commitments')
        map.connect('commitments_edit', '/data/reports/commitments/:id/edit',
                    controller=c_ctlr, action='edit')

        # Redirects for changed report locations May 2014
        map.redirect('/data/reports/qa/organisation/broken_resource_links',
                     '/data/report/broken-links')
        map.redirect('/data/reports/qa/organisation/broken_resource_links/:organization',
                     '/data/report/broken-links/:organization')
        map.redirect('/data/reports/feedback',
                     '/data/report/feedback')
        map.redirect('/data/reports/feedback/:organization',
                     '/data/report/feedback/:organization')
        map.redirect('/data/reports/resources/:organization',
                     '/data/report/publisher-resources/:organization')
        # openness done
        map.redirect('/data/reports/qa',
                     '/data/report')
        map.redirect('/data/reports/qa/organisation/:organization',
                     '/data/report/openness/:organization')
        map.redirect('/api/2/util/qa/{a:.*}',
                     '/data/report')
        map.redirect('/data/reports/qa/organisation/scores',
                     '/data/report/openness')
        map.redirect('/data/reports/qa/organisation/scores/:organization',
                     '/data/report/openness/:organization')
        # commitments - keep in existing controller
        #   /data/reports/commitments
        #   /data/reports/commitments/cabinet-office
        # site usage - keep as it is
        # Other misc:
        #   /publisher/report_publishers_and_users
        #   /publisher/report_groups_without_admins
        #   /publisher/report_users_not_assigned_to_groups

        # Older redirect
        map.redirect('/data/feedback/report/{id}.{format}', '/data/report/feedback/{id}?format={format}')
        map.redirect('/data/feedback/report/{id}', '/data/report/feedback/{id}')
        map.redirect('/data/feedback/report.{format}', '/data/report/feedback?format={format}')
        map.redirect('/data/feedback/report', '/data/report/feedback')

        return map


class ThemePlugin(p.SingletonPlugin):
    '''
    DGU Visual Theme for a CKAN install embedded in dgu/Drupal.
    '''
    p.implements(p.IConfigurer)
    p.implements(p.IRoutes, inherit=True)
    p.implements(p.ITemplateHelpers, inherit=True)

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
    # [Monkey patch] Stop autodetecting package-type by the URL since it seems
    # to think /data/search should search for 'search' packages!
    from ckan.controllers.package import PackageController
    PackageController._guess_package_type = _guess_package_type
    # [Monkey patch] We have complicated UKLP license info, so need a custom
    # isopen method
    from ckan import model
    from lib import helpers as dgu_helpers
    model.Package._isopen = model.Package.isopen
    model.Package.isopen = dgu_helpers.isopen

    def update_config(self, config):
        toolkit.add_template_directory(config, 'theme/templates')
        toolkit.add_public_directory(config, 'theme/public')

        # Shared assets may be configured to be elsewhere on disk,
        # so in that case let the user configure apache/nginx to serve
        # them manually. But for developers, the shared assets will
        # simply next door to this repo, dgu.shared_assets_timestamp_path
        # won't be set, so as a convenience we get paster to serve them.
        if not config.get('dgu.shared_assets_timestamp_path'):
            toolkit.add_public_directory(config, '../../../shared_dguk_assets')

    def get_helpers(self):
        """
        A dictionary of extra helpers that will be available to provide
        dgu specific helpers to the templates.  We may be able to override
        h.linked_user so that we don't need to monkey patch above.
        """
        from ckanext.dgu.lib import helpers
        from inspect import getmembers, isfunction

        helper_dict = {}

        functions_list = [o for o in getmembers(helpers, isfunction)]
        for name, fn in functions_list:
            if name[0] != '_':
                helper_dict[name] = fn

        return helper_dict

    def before_map(self, map):
        """
        Make "/data" the homepage.
        """
        data_controller = 'ckanext.dgu.controllers.data:DataController'
        tag_controller = 'ckanext.dgu.controllers.tag:TagController'
        user_controller = 'ckanext.dgu.controllers.user:UserController'
        map.redirect('/', '/data')
        map.redirect('/data', '/data/search')
        #map.connect('/data', controller=data_controller, action='index')

        map.connect('/linked-data-admin', controller=data_controller, action='linked_data_admin')
        map.connect('/data/tag', controller=tag_controller, action='index')
        map.connect('/data/tag/{id}', controller=tag_controller, action='read')
        map.connect('/data/search', controller='package', action='search')
        map.connect('/data/api', controller=data_controller, action='api')
        map.connect('/data/system_dashboard', controller=data_controller, action='system_dashboard')
        map.connect('/data/openspending-report/index', controller=data_controller, action='openspending_report')
        map.connect('/data/openspending-report/{id}', controller=data_controller, action='openspending_publisher_report')
        map.connect('/data/openspending-report/{id}', controller=data_controller, action='openspending_publisher_report')
        map.connect('/data/carparks', controller=data_controller, action='carparks')
        map.connect('/data/resource_cache/{root}/{resource_id}/{filename}', controller=data_controller, action='resource_cache')
        map.connect('/data/viz/social-investment-and-foundations', controller=data_controller, action='viz_social_investment_and_foundations')
        map.connect('/data/viz/investment-readiness-programme', controller=data_controller, action='viz_investment_readiness_programme')
        map.connect('/data/viz/new-front-page', controller=data_controller, action='viz_front_page')

        theme_controller = 'ckanext.dgu.controllers.theme:ThemeController'
        map.connect('/data/themes', controller=theme_controller, action='index')
        map.connect('/data/themes/{name}', controller=theme_controller, action='named_theme')

        # For test usage when Drupal is not running
        map.connect('/comment/get/{id}',
                    controller='ckanext.dgu.controllers.package:CommentProxy',
                    action='get_comments')

        # Remap the /user/me to the DGU version of the User controller
        with SubMapper(map, controller=user_controller) as m:
            m.connect('/data/user/me', action='me')

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
            #NB not /data/user/me
            m.connect('/data/user/set_lang/{lang}', action='set_lang')
            m.connect('/data/user/{id:.*}', action='read')
            m.connect('/data/user', action='index')

        map.redirect('/dashboard', '/data/user/me')

        return map

    def after_map(self, map):
        # Delete routes to /tag since we use /data/tag and /tag is confusing to
        # have kicking around still when it uses the same template with
        # different inputs.
        matches_to_delete = []
        for match in map.matchlist:
            if match.routepath.startswith('/tag'):
                matches_to_delete.append(match)
        for match in matches_to_delete:
            map.matchlist.remove(match)
        return map


class DrupalAuthPlugin(p.SingletonPlugin):
    '''Reads Drupal login cookies to log user in.'''
    p.implements(p.IMiddleware, inherit=True)

    def make_middleware(self, app, config):
        return DrupalAuthMiddleware(app, config)


class AuthApiPlugin(p.SingletonPlugin):
    '''Adds functions that work out if the user is allowed to do
    certain edits.'''

    p.implements(p.IAuthFunctions, inherit=True)

    def get_auth_functions(self):
        return {
                'package_update': dgu_package_update,
                'package_extra_fields_editable': dgu_extra_fields_editable,
                'package_delete': dgu_dataset_delete,
                'user_list': dgu_user_list,
                'user_show': dgu_user_show,
                'organization_delete': dgu_organization_delete,
                'group_change_state': dgu_group_change_state,
               }


class DguForm(p.SingletonPlugin):
    # NB the actual form (IDatasetForm) is in forms/dataset_form.py

    p.implements(p.IRoutes, inherit=True)

    # IRoutes

    def before_map(self, map):
        dgu_package_controller = 'ckanext.dgu.controllers.package:PackageController'
        map.connect('dataset_new', '/dataset/new', controller=dgu_package_controller, action='new')
        map.connect('dataset_edit', '/dataset/edit/{id}', controller=dgu_package_controller, action='edit')
        map.connect('/dataset/delete/{id}', controller=dgu_package_controller, action='delete')
        map.connect('dataset_history', '/dataset/history/{id}', controller=dgu_package_controller, action='history')
        map.connect('/dataset/{id}.{format}', controller=dgu_package_controller, action='read')
        map.connect('/dataset/{id}', controller=dgu_package_controller, action='read')
        map.connect('/dataset/{id}/resource/{resource_id}', controller=dgu_package_controller, action='resource_read')

        return map


class PublisherPlugin(p.SingletonPlugin):

    p.implements(p.IRoutes, inherit=True)
    p.implements(p.ISession, inherit=True)
    p.implements(IReport)

    def before_commit(self, session):
        """
        Before we commit a session we will check to see if any of the new
        items are users so we can notify them to apply for publisher access.
        """
        from pylons.i18n import _
        from ckan.model import User

        session.flush()
        if not hasattr(session, '_object_cache'):
            return

        pubctlr = 'ckanext.dgu.controllers.publisher:PublisherController'
        for obj in set(session._object_cache['new']):
            if isinstance(obj, (User)):
                try:
                    url = url_for(controller=pubctlr, action='apply')
                except CkanUrlException:
                    # This occurs when Routes has not yet been initialized
                    # yet, which would be before a WSGI request has been
                    # made. In this case, there will be no flash message
                    # required anyway.
                    return
                msg = "You can now <a href='%s'>apply for publisher access</a>" % url
                try:
                    flash_notice(_(msg), allow_html=True)
                except TypeError:
                    # Raised when there is no session registered, and this is
                    # the case when using the paster commands.
                    #log.debug('Did not add a flash message due to a missing session: %s' % msg)
                    pass

    def before_map(self, map):
        pub_ctlr = 'ckanext.dgu.controllers.publisher:PublisherController'

        map.redirect('/organization/{url:.*}', '/publisher/{url}')

        map.connect('publisher_index',
                    '/publisher',
                    controller=pub_ctlr, action='index')
        map.connect('publisher_edit',
                    '/publisher/edit/:id',
                    controller=pub_ctlr, action='edit')
        map.connect('publisher_apply',
                    '/publisher/apply/:id',
                    controller=pub_ctlr, action='apply')
        map.connect('publisher_apply_empty',
                    '/publisher/apply',
                    controller=pub_ctlr, action='apply')
        map.connect('publisher_users',
                    '/publisher/users/:id',
                    controller=pub_ctlr, action='users')
        map.connect('publisher_new',
                    '/publisher/new',
                    controller=pub_ctlr, action='new')
        map.connect('/publisher/report_groups_without_admins',
                    controller=pub_ctlr, action='report_groups_without_admins')
        map.connect('/publisher/report_publishers_and_users',
                    controller=pub_ctlr, action='report_publishers_and_users')
        map.connect('/publisher/report_users',
                    controller=pub_ctlr, action='report_users')
        map.connect('/publisher/report_users_not_assigned_to_groups',
                    controller=pub_ctlr, action='report_users_not_assigned_to_groups')
        map.connect('publisher_read',
                    '/publisher/:id',
                    controller=pub_ctlr, action='read')

        return map

    def after_map(self, map):
        return map

    def update_config(self, config):
        # set the auth profile to use the publisher based auth
        config['ckan.auth.profile'] = 'publisher'

        # same for the harvesting auth profile
        config['ckan.harvest.auth.profile'] = 'publisher'

    # IReport

    def register_reports(self):
        """Register details of an extension's reports"""
        from ckanext.dgu.lib import reports
        return [reports.nii_report_info,
                reports.feedback_report_info,
                reports.publisher_activity_report_info,
                reports.publisher_resources_info,
                reports.unpublished_report_info,
                reports.datasets_without_resources_info,
                ]


class InventoryPlugin(p.SingletonPlugin):

    p.implements(p.IRoutes, inherit=True)
    p.implements(p.IConfigurer)
    p.implements(p.ISession, inherit=True)
    p.implements(p.IAuthFunctions, inherit=True)

    def get_auth_functions(self):
        return {
            'feedback_update': dgu_feedback_update,
            'feedback_create': dgu_feedback_create,
            'feedback_delete': dgu_feedback_delete,
        }

    def before_commit(self, session):
        pass

    def before_map(self, map):
        fb_ctlr = 'ckanext.dgu.controllers.feedback:FeedbackController'

        # Feedback specific URLs
        map.connect('/data/feedback/moderate/:id',
                    controller=fb_ctlr, action='moderate')
        map.connect('/data/feedback/abuse/:id',
                    controller=fb_ctlr, action='report_abuse')
        map.connect('/data/feedback/moderation',
                    controller=fb_ctlr, action='moderation')

        # Adding and viewing feedback per dataset
        map.connect('/dataset/:id/feedback/view',
                    controller=fb_ctlr, action='view')
        map.connect('/dataset/:id/feedback/add',
                    controller=fb_ctlr, action='add')

        inv_ctlr = 'ckanext.dgu.controllers.inventory:InventoryController'
        map.connect('/unpublished/edit-item/:id',
                    controller=inv_ctlr, action='edit_item')
        map.connect('/unpublished/:id/edit',
                    controller=inv_ctlr, action='edit')
        map.connect('/unpublished/:id/edit/download',
                    controller=inv_ctlr, action='download')
        map.connect('/unpublished/:id/edit/template',
                    controller=inv_ctlr, action='template')
        map.connect('/unpublished/:id/edit/upload',
                    controller=inv_ctlr, action='upload')
        map.connect('/unpublished/:id/edit/upload_complete',
                    controller=inv_ctlr, action='upload_complete')
        map.connect('/unpublished/:id/edit/upload/:upload_id',
                    controller=inv_ctlr, action='upload_status')

        return map

    def after_map(self, map):
        return map

    def update_config(self, config):
        pass


class SearchPlugin(p.SingletonPlugin):
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

    p.implements(p.IPackageController, inherit=True)

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

        # ignore dataset_type:dataset which CKAN2 adds in - we dont use
        # dataset_type and it mucks up spatial search
        if search_params.get('fq'):
            search_params['fq'] = search_params['fq'].replace('+dataset_type:dataset', '')

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
        if is_plugin_enabled('harvest'):
            SearchIndexing.add_field__harvest_document(pkg_dict)
        SearchIndexing.add_field__openness(pkg_dict)
        SearchIndexing.add_popularity(pkg_dict)
        SearchIndexing.add_field__group_abbreviation(pkg_dict)
        SearchIndexing.add_inventory(pkg_dict)

        # Extract multiple theme values (concatted with ' ') into one multi-value schema field
        all_themes = set()
        for value in (pkg_dict.get('theme-primary', ''), pkg_dict.get('theme-secondary', '')):
            for theme in value.split(' '):
                if theme:
                    all_themes.add(theme)
        pkg_dict['all_themes'] = list(all_themes)
        return pkg_dict

class ApiPlugin(p.SingletonPlugin):
    '''DGU-specific API'''
    p.implements(p.IRoutes, inherit=True)
    p.implements(p.IActions)

    def before_map(self, map):
        api_controller = 'ckanext.dgu.controllers.api:DguApiController'
        map.connect('/api/util/latest-datasets', controller=api_controller, action='latest_datasets')
        map.connect('/api/util/dataset-count', controller=api_controller, action='dataset_count')
        map.connect('/api/util/revisions', controller=api_controller, action='revisions')
        map.connect('/api/util/latest-unpublished', controller=api_controller, action='latest_unpublished')
        map.connect('/api/util/popular-unpublished', controller=api_controller, action='popular_unpublished')

        return map

    def get_actions(self):
        from ckanext.dgu.logic.action.get import publisher_show
        return {
            'publisher_show': publisher_show,
            }


def is_plugin_enabled(plugin_name):
    return plugin_name in config.get('ckan.plugins', '').split()
