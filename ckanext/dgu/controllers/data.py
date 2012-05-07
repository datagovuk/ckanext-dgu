import sqlalchemy

import ckan.authz
from ckan.lib.base import BaseController, model, abort, h, g
from ckanext.dgu.plugins_toolkit import request, c, render, _, NotAuthorized, get_action

class DataController(BaseController):
    def __before__(self, action, **env):
        try:
            BaseController.__before__(self, action, **env)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))
        except (sqlalchemy.exc.ProgrammingError,
                sqlalchemy.exc.OperationalError), e:
            # postgres and sqlite errors for missing tables
            msg = str(e)
            if ('relation' in msg and 'does not exist' in msg) or \
                   ('no such table' in msg) :
                # table missing, major database problem
                abort(503, _('This site is currently off-line. Database is not initialised.'))
                # TODO: send an email to the admin person (#1285)
            else:
                raise

    def index(self):
        from ckan.lib.search import SearchError
        try:
            # package search
            context = {'model': model, 'session': model.Session,
                       'user': c.user or c.author}
            fq = 'capacity:"public"'
            data_dict = {
                'q':'*:*',
                'fq':fq,
                'facet.field':g.facets,
                'rows':0,
                'start':0,
            }
            query = get_action('package_search')(context,data_dict)
            c.package_count = query['count']
            c.facets = query['facets']
            c.search_facets = query['search_facets']

            # group search
            data_dict = {'order_by': 'packages', 'all_fields': 1}
            c.groups = get_action('group_list')(context, data_dict)
        except SearchError, se:
            c.package_count = 0
            c.groups = []

        c.recently_changed_packages_activity_stream = \
            get_action('recently_changed_packages_activity_list_html')(
                    context, {})

        return render('data/index.html')

    def api(self):
        return render('data/api.html')

    def system_dashboard(self):
        c.is_sysadmin = ckan.authz.Authorizer().is_sysadmin(c.userobj) if c.userobj else False
        if not c.is_sysadmin:
            abort(401, 'User must be a sysadmin to view this page.')
        return render('data/system_dashboard.html')
