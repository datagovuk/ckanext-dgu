import json
import logging
import os
import pylons
import re
import sqlalchemy
import urlparse

from ckanext.dgu.schema import THEMES
import ckan.authz
from ckan.lib.base import BaseController, model, abort, h, g
from ckanext.dgu.plugins_toolkit import request, c, render, _, NotAuthorized, get_action

log = logging.getLogger(__name__)

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
                'q':'',
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
            #data_dict = {'order_by': 'packages', 'all_fields': 1}
            #c.groups = get_action('group_list')(context, data_dict)
        except SearchError, se:
            log.error('Search error: %s', se)
            c.package_count = 0
            c.groups = []

        #c.recently_changed_packages_activity_stream = \
        #    get_action('recently_changed_packages_activity_list_html')(
        #            context, {})

        return render('data/index.html')

    def api(self):
        return render('data/api.html')

    def system_dashboard(self):
        is_sysadmin = ckan.authz.Authorizer().is_sysadmin(c.userobj) if c.userobj else False
        if not is_sysadmin:
            abort(401, 'User must be a sysadmin to view this page.')
        return render('data/system_dashboard.html')

    def openspending_browse(self):
        return render('data/openspending_browse.html')

    def _set_openspending_reports_dir(self):
	c.openspending_report_dir = os.path.expanduser(pylons.config.get(
            'dgu.openspending_reports_dir',
            '/var/lib/ckan/dgu/openspending_reports'))

    def openspending_report(self):
        self._set_openspending_reports_dir()
        return render('data/openspending_report.html')

    def openspending_publisher_report(self, id):
        id = id.replace('.html', '')
        if id.startswith('publisher-'):
            publisher_name = id.replace('publisher-', '')
            # Check the publisher actually exists, for security
            publisher = model.Group.by_name(publisher_name)
            if publisher:
                c.report_name = id
            else:
                abort(404, 'Publisher not found')
            self._set_openspending_reports_dir()
            return render('data/openspending_publisher_report.html')
        else:
            abort(404)

    def carparks(self):
        return render('data/carparks.html')


    def resource_cache(self, root, resource_id, filename):
        """
        Called when a request is made for an item in the resource cache and
        is responsible for rendering the data.  When the data to be rendered
        is HTML it will add a header to show that the content is cached, and
        set a <base> header if not present to make sure all relative links are
        resolved correctly.
        """
        from pylons import response
        from paste.fileapp import FileApp
        from ckanext.dgu.lib.helpers import tidy_url

        archive_root = pylons.config.get('ckanext-archiver.archive_dir')
        if not archive_root:
            # Bad configuration likely to cause this.
            abort(404, "Could not find archive folder")

        resource = model.Resource.get(resource_id)
        is_html = False
        content_type = "application/octet-stream"

        fmt = ""
        if resource:
            task_status = model.Session.query(model.TaskStatus).\
                          filter(model.TaskStatus.task_type=='qa').\
                          filter(model.TaskStatus.key=='status').\
                          filter(model.TaskStatus.entity_id==resource.id).first()
            if task_status:
                status = json.loads(task_status.error)
                fmt = status['format']

        # Make an attempt at getting the correct content type but fail with
        # application/octet-stream in cases where we don't know.
        formats = {
            "CSV": "application/csv",
            "XLS": "application/vnd.ms-excel",
            "HTML": 'text/html; charset=utf-8' }
        content_type = formats.get(fmt, "application/octet-stream")

        is_html = fmt == "HTML"

        filepath = os.path.join(archive_root, root, resource_id, filename).encode('utf-8')
        if not os.path.exists(filepath):
            abort(404, "Resource is not cached")

        file_size = os.path.getsize(filepath)
        if not is_html:
            headers = [('Content-Type', content_type),
                       ('Content-Length', str(file_size))]
            fapp = FileApp(filepath, headers=headers)
            return fapp(request.environ, self.start_response)

        origin = tidy_url(resource.url)
        parts = urlparse.urlparse(origin)
        url = "{0}://{1}".format(parts.scheme, parts.netloc)
        base_string = "<head><base href='{0}'>".format(url)

        response.headers['Content-Type'] = content_type
        try:
            f = open(filepath, "r")
        except IOError:
            log.error('Error reading resource cache file: %s', filepath)
            abort(403, "The system was unable to read this resource from the cache. Admins have been notified")

        content = f.read()
        f.close()

        if not re.search("<base ", content, re.IGNORECASE):
            compiled_head = re.compile(re.escape("<head>"), re.IGNORECASE)
            content = compiled_head.sub( base_string, content, re.IGNORECASE)

        if not '__archiver__cache__header__' in content:
            # We should insert our HTML block at the bottom of the page with
            # the appropriate CSS to render it at the top.  Easier to insert
            # before </body>.
            c.url = resource.url
            replacement = render("data/cache_header.html")
            try:
                compiled_body = re.compile(re.escape("</body>"), re.IGNORECASE)
                content = compiled_body.sub( "{0}</body>".format(replacement), content, re.IGNORECASE)
            except Exception, e:
                log.error("Failed to do the replacement in resource<{0}> and file: {1}".format(resource.id, filepath))
                return

        response.write(content)



