import sqlalchemy
from pylons.i18n import _

import ckan.logic
from ckan.lib.base import request, c, BaseController, model, abort, h, g, render
#from ckan.controllers.package import PackageController

class DataController(BaseController):
    def __before__(self, action, **env):
        try:
            BaseController.__before__(self, action, **env)
        except ckan.logic.NotAuthorized:
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
            data_dict = {
                'q':'*:*',
                'facet.field':g.facets,
                'rows':0,
                'start':0,
            }
            query = ckan.logic.get_action('package_search')(context,data_dict)
            c.package_count = query['count']
            c.facets = query['facets']

            # group search
            data_dict = {'order_by': 'packages', 'all_fields': 1}
            c.groups = ckan.logic.get_action('group_list')(context, data_dict)
        except SearchError, se:
            c.package_count = 0
            c.groups = []

        c.recently_changed_packages_activity_stream = \
            ckan.logic.action.get.recently_changed_packages_activity_list_html(
                    context, {})

        return render('data/index.html')

    def api(self):
        return render('data/api.html')
