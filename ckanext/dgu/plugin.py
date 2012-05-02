import os
import re

from logging import getLogger

from ckan.lib.helpers import flash_notice
from ckan.logic import NotFound
from ckan.plugins import implements, SingletonPlugin
from ckan.plugins import IRoutes
from ckan.plugins import IConfigurer
from ckan.plugins import IGenshiStreamFilter
from ckan.plugins import IMiddleware
from ckan.plugins import IAuthFunctions
from ckan.plugins import IPackageController
from ckan.plugins import ISession
from ckanext.dgu.drupal_auth import DrupalAuthMiddleware
from ckanext.dgu.auth import dgu_group_update, dgu_group_create, \
                             dgu_package_update, dgu_extra_fields_editable, \
                             dgu_dataset_delete
from ckan.lib.helpers import url_for
import ckanext.dgu
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

class ThemePlugin(SingletonPlugin):
    '''
    DGU Visual Theme for a CKAN install embedded in dgu/Drupal.
    '''
    implements(IConfigurer)
    implements(IRoutes)

    def update_config(self, config):
        configure_template_directory(config, 'theme/templates')
        configure_public_directory(config, 'theme/public')

        config['package_form'] = 'package_gov3'

    def before_map(self, map):
        """
        Make "/data" the homepage.
        """
        map.redirect('/', '/data')
        map.connect('/data', controller='ckanext.dgu.controllers.data:DataController', action='index')
        map.connect('/data/tag', controller='tag', action='index')
        map.connect('/data/tag/{id}', controller='tag', action='read')
        map.connect('/data/search', controller='package', action='search')
        map.connect('/data/api', controller='ckanext.dgu.controllers.data:DataController', action='api')

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

    implements(IAuthFunctions, inherit=True)
#    implements(IMiddleware,    inherit=True)

#    def make_middleware(self, app, config):
#        return DrupalAuthMiddleware(app, config)

    def get_auth_functions(self):
        return {
            'group_update' : dgu_group_update,
            'group_create' : dgu_group_create,
            'package_update' : dgu_package_update,
            'package_extra_fields_editable' : dgu_extra_fields_editable,
            'package_delete': dgu_dataset_delete,
        }


class DguForm(SingletonPlugin):

    implements(IRoutes)
    implements(IConfigurer)

    def before_map(self, map):
        dgu_package_controller = 'ckanext.dgu.controllers.package:PackageController'
        map.connect('/dataset/{id}.{format}', controller=dgu_package_controller, action='read')
        map.connect('/dataset/{id}', controller=dgu_package_controller, action='read')
        map.connect('/dataset/{id}/resource/{resource_id}', controller=dgu_package_controller, action='resource_read')
        map.connect('dataset_new','/dataset/new', controller=dgu_package_controller, action='new')
        map.connect('dataset_edit','/dataset/edit/{id}', controller=dgu_package_controller, action='edit')
        map.connect('/dataset/delete/{id}', controller=dgu_package_controller, action='delete')
        map.connect('dataset_history','/dataset/history/{id}', controller=dgu_package_controller, action='history')
        return map

    def after_map(self, map):
        return map

    def update_config(self, config):
        pass


class PublisherPlugin(SingletonPlugin):

    implements(IRoutes)
    implements(IConfigurer)
    implements(ISession, inherit=True)


    def before_commit(self, session):
        """
        Before we commit a session we will check to see if any of the new
        items are users so we
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
                    controller='group', action='edit' )
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
        map.connect('publisher_report',
                    '/publisher/report',
                    controller=pub_ctlr, action='report' )
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
    Since this is calcuable from the license_id, but is not a facet over the
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

        Set the 'qf' (queryfield) parameter to a fixed list of boosted solr fields
        tuned for DGU.

        If a dismax query is run, then these will be the fields that are searched
        within.
        """
        search_params['qf'] = 'title^4 name^3 notes^2 text tags^0.3 group_titles^0.3 extras_harvest_document_content^0.2'
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
        from ckan.model.group import Group

        # Dynamically create the license_id-is-ogl field.
        if not pkg_dict.has_key('license_id-is-ogl'):
            is_ogl = self._is_ogl(pkg_dict)
            pkg_dict['license_id-is-ogl'] = is_ogl
            pkg_dict['extras_license_id-is-ogl'] = is_ogl

        # Clean the resource formats prior to indexing
        pkg_dict['res_format'] = [ self._clean_format(f) for f in pkg_dict.get('res_format', []) ]

        # Populate group related fields
        groups = [Group.get(g) for g in pkg_dict['groups']]
        publishers = [g for g in groups if g.type == 'publisher']

        # Group titles 
        if not pkg_dict.has_key('group_titles'):
            pkg_dict['group_titles'] = [g.title for g in groups]
        else:
            log.warning('Unable to add "group_titles" to index, as the datadict '
                        'already contains a key of that name')

        # Each dataset should have exactly one group of type "publisher".
        # However, this is not enforced in the data model.
        if len(publishers) > 1:
            log.warning('Dataset %s seems to have more than one publisher!  '
                        'Only indexing the first one: %s', \
                        pkg_dict['name'], repr(publishers))
            publishers = publishers[:1]
        elif len(publishers) == 0:
            log.warning('Dataset %s doesn\'t seem to have a publisher!  '
                        'Unabled to add publisher to index.',
                        pkg_dict['name'])
            return pkg_dict

        # Publisher names
        if not pkg_dict.has_key('publisher'):
            pkg_dict['publisher'] = [p.name for p in publishers]
        else:
            log.warning('Unable to add "publisher" to index, as the datadict '
                        'already contains a key of that name')

        # Ancestry of publishers
        ancestors = []
        publisher = publishers[0]
        while(publisher is not None):
            ancestors.append(publisher)
            parent_publishers = publisher.get_groups('publisher')
            if len(parent_publishers) == 0:
                publisher = None
            else:
                if len(parent_publishers) > 1:
                    log.warning('Publisher %s has more than one parent publisher. '
                                'Ignoring all but the first. %s',
                                publisher, repr(parent_publishers))
                publisher = parent_publishers[0]
        

        if not pkg_dict.has_key('parent_publishers'):
            pkg_dict['parent_publishers'] = [ p.name for p in ancestors ]
        else:
            log.warning('Unable to add "parent_publishers" to index, as the datadict '
                        'already contains a key of that name. '
                        'Package: %s Parent_publishers: %r', \
                        pkg_dict['name'], pkg_dict['parent_publishers'])

        # Index a harvested dataset's XML content
        # (Given a low priority when searching)
        if pkg_dict.get('UKLP', '') == 'True':
            import ckan
            from ckan.logic import get_action

            context = {'model': ckan.model,
                       'session': ckan.model.Session,
                       'ignore_auth': True}

            data_dict = {'id': pkg_dict.get('harvest_object_id', '')}

            try:
                harvest_object = get_action('harvest_object_show')(context, data_dict)
                pkg_dict['extras_harvest_document_content'] = harvest_object.get('content', '')
            except NotFound:
                log.warning('Unable to find harvest object "%s" '
                            'referenced by dataset "%s"',
                            data_dict['id'], pkg_dict['id'])

        return pkg_dict

    _disallowed_characters = re.compile(r'[^a-z]')
    def _clean_format(self, format_string):
        if isinstance(format_string, basestring):
            return re.sub(self._disallowed_characters, '', format_string.lower())
        else:
            return format_string

    def _is_ogl(self, pkg_dict):
        """
        Returns true iff the represented dataset has an OGL license

        A dataset has an OGL license if the license_id == "uk-ogl"
        or if it's a UKLP dataset with "Open Government License" in the
        access_contraints extra field.
        """
        regex = re.compile(r'open government licen[sc]e', re.IGNORECASE)
        return pkg_dict['license_id'] == 'uk-ogl' or \
               bool(regex.search(pkg_dict.get('extras_access_constraints', '')))

