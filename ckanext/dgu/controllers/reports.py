import datetime
import json

import ckan.plugins.toolkit as t
from ckan.lib.helpers import Page
import ckanext.dgu.lib.helpers as dguhelpers
from ckanext.dgu.lib import reports
from ckan.lib.report_cache import ReportCacheRegistry
from ckan.lib.render import TemplateNotFound
from ckan.lib.json import DateTimeJsonEncoder
from ckan.common import OrderedDict

c = t.c


class ReportsController(t.BaseController):

    def index(self):
        registry = ReportCacheRegistry.instance()
        c.reports = registry.get_names()
        return t.render('reports/index.html')

    def view(self, report_name, organization=None, refresh=False):
        c.report_name = report_name
        report = ReportCacheRegistry.instance().get_report(report_name)

        # ensure correct url is being used
        if 'organization' in t.request.environ['pylons.routes_dict'] and \
            'organization' not in report.option_defaults:
                t.redirect_to(dguhelpers.relative_url_for(organization=None))
        elif 'organization' not in t.request.environ['pylons.routes_dict'] and \
            'organization' in report.option_defaults and \
            report.option_defaults['organization']:
                org = report.option_defaults['organization']
                t.redirect_to(dguhelpers.relative_url_for(organization=org))
        if 'organization' in t.request.params:
            # organization should only be in the url - let the param overwrite
            # the url.
            t.redirect_to(dguhelpers.relative_url_for())

        # options
        c.options = report.add_defaults_to_options(t.request.params)
        if 'format' in c.options:
            format = c.options.pop('format')
        else:
            format = None
        if 'organization' in report.option_defaults:
            c.options['organization'] = organization
            c.offer_organization_index = \
                    report.option_defaults['organization'] == None
        c.options_html = {}
        for option in c.options:
            try:
                c.options_html[option] = \
                    t.render_snippet('reports/option_%s.html' % option)
            except TemplateNotFound:
                continue
        c.report_title = report.title

        # Refresh the cache if requested
        if t.request.method == 'POST' and not format:
            if not (c.userobj and c.userobj.sysadmin):
                t.abort(401)
            report.refresh_cache(c.options)

        # Alternative way to refresh the cache - not in the UI, but is
        # handy for testing
        if t.asbool(t.request.params.get('refresh')):
            if not (c.userobj and c.userobj.sysadmin):
                t.abort(401)
            c.options.pop('refresh')
            report.refresh_cache(c.options)
            # Don't want the refresh=1 in the url once it is done
            t.redirect_to(dguhelpers.relative_url_for(refresh=None))

        c.data, c.report_date = report.get_fresh_report(**c.options)

        if format and format != 'html':
            ensure_data_is_dicts(c.data)
            anonymise_user_names(c.data, organization=c.options.get('organization'))
            if format == 'csv':
                filename = 'report_%s.csv' % report.generate_key(c.options).replace('?', '_')
                t.response.headers['Content-Type'] = 'application/csv'
                t.response.headers['Content-Disposition'] = str('attachment; filename=%s' % (filename))
                return make_csv_from_dicts(c.data['data'])
            elif format == 'json':
                t.response.headers['Content-Type'] = 'application/json'
                c.data['generated_at'] = c.report_date
                return json.dumps(c.data, cls=DateTimeJsonEncoder)
            else:
                t.abort(400, 'Format not known - try html, json or csv')

        c.are_some_results = bool(c.data['data'] if 'data' in c.data
                                  else c.data)
        if c.are_some_results:
            # you can't pass args into genshi template, so it will just look
            # for c.data
            c.report_snippet = t.render_snippet(report.get_template())
        return t.render('reports/view.html')




# OLD

    def activity(self, id, fmt=None):
        import ckan.model as model
        from ckanext.dgu.lib.reports import publisher_activity_report

        try:
            context = {'model':model,'user': c.user, 'owner_org': id}
            t.check_access('package_create',context)
        except t.NotAuthorized, e:
            t.redirect_to('/user?destination={0}'.format(request.path[1:]))

        c.publisher = model.Group.get(id)
        if not c.publisher:
            t.abort(404, "Publisher not found")
        data = publisher_activity_report(c.publisher, use_cache=True)
        c.created = data['created']
        c.modified = data['modified']
        return t.render('reports/activity.html')

    def nii(self, format=None):
        import ckan.model as model
        from ckanext.dgu.lib.reports import nii_report

        if 'regenerate' in request.GET and dguhelpers.is_sysadmin():
            from ckan.lib.helpers import flash_notice
            from ckanext.dgu.lib.reports import cached_reports
            cached_reports(['nii_report'])
            flash_notice("Report regenerated")
            t.redirect_to('/data/reports/nii')

        tmpdata = nii_report(use_cache=True)
        c.data = {}

        # Get the date time the report was generated, or now if it doesn't
        # appear in the cache
        cache_data = model.Session.query(model.DataCache.created)\
            .filter(model.DataCache.object_id=='__all__')\
            .filter(model.DataCache.key == 'nii-report').first()
        c.generated_date = cache_data[0] if cache_data else datetime.datetime.now()

        c.total_broken_packages = 0
        c.total_broken_resources = 0
        # Convert the lists of IDs into something usable in the template,
        # this could be faster if we did a bulk-fetch of groupname->obj for
        # instance.
        for k,list_of_dicts in tmpdata.iteritems():
            g = model.Group.get(k)
            c.data[g] = []
            for dct in list_of_dicts:
                for pkgname,results in dct.iteritems():
                    c.total_broken_resources += len(results)
                    if len(results):
                        c.total_broken_packages += 1
                    c.data[g].append({model.Package.get(pkgname): results})

        def _stringify(s, encoding, errors):
            if s is None:
                return ''
            if isinstance(s, unicode):
                return s.encode(encoding, errors)
            elif isinstance(s, (int , float)):
                pass #let csv.QUOTE_NONNUMERIC do its thing.
            elif not isinstance(s, str):
                s=str(s)
            return s

        if format == 'csv':
            import csv

            # Set the content-disposition so that it downloads the file
            t.response.headers['Content-Type'] = "text/csv; charset=utf-8"
            t.response.headers['Content-Disposition'] = str('attachment; filename=nii-broken-resources.csv')

            writer = csv.writer(t.response)
            writer.writerow(['Publisher', 'Parent publisher', 'Dataset name', 'Resource title', 'Resource link', 'Data link'])
            for publisher in c.data.keys():
                parent_groups = publisher.get_parent_groups(type='organization')
                parent_publisher = parent_groups[0].title if len(parent_groups) > 0 else ''

                for items in c.data[publisher]:
                    for dataset, resources in items.iteritems():
                        if len(resources) == 0:
                            continue
                        for resid,resdesc in resources:
                            resource = model.Resource.get(resid)
                            row = [
                                publisher.title,
                                parent_publisher,
                                _stringify(dataset.title, 'utf-8', 'ignore'),
                                _stringify(resource.description, 'utf-8', 'ignore') or 'No name',
                                'http://data.gov.uk/dataset/%s/resource/%s' % (dataset.name,resource.id,),
                                _stringify(resource.url, 'utf-8', 'ignore'),
                                'Yes' if dataset.extras.get('external_reference','') == 'ONSHUB' else 'No'
                            ]
                            writer.writerow(row)

            return ''

        return t.render('reports/nii.html')

    def resources(self, id=None):
        try:
            c.include_sub_publishers = t.asbool(t.request.params.get('include_sub_publishers') or False)
        except ValueError:
            t.abort(400, 'include_sub_publishers parameter value must be boolean')
        c.publisher_name = id or 'department-for-culture-media-and-sport'
        c.query = reports.organisation_resources
        c.data = c.query(organisation_name=c.publisher_name,
                         include_sub_organisations=c.include_sub_publishers)
        return t.render('reports/resources.html')

    def feedback(self, id=None, format=None):
        """
        Generates a report of all of the feedback related to datasets
        """
        import ckan.model as model
        from ckanext.dgu.lib.reports import feedback_report
        from ckanext.dgu.model.feedback import Feedback

        LIMIT = 50

        c.has_publisher = id
        try:
            c.include_subpublisher = t.asbool(request.params.get('show-subpub', 0))
            c.show_zero_feedback = t.asbool(request.params.get('show-zero-feedback', 0))
            c.include_published = t.asbool(request.params.get('show-published', 0))
        except:
            # If t.asbool throws an exception because of bad content being passed we
            # will reset to the default.  It shouldn't happen through the UI but any
            # manually concocted params can cause a fail here
            c.include_subpublisher = False
            c.show_zero_feedback = False
            c.include_published = False

        try:
            page = int(request.params.get('page', 1))
        except ValueError:
            t.abort(404, _('Not found'))

        # Fetch the (hopefully) cached data
        if id:
            c.publisher = model.Group.get(id)
            c.data = feedback_report(c.publisher,
                                     include_sub_publishers=c.include_subpublisher,
                                     include_published=c.include_published,
                                     use_cache=True)
        else:
            c.data = feedback_report(None,
                                     include_published=c.include_published,
                                     use_cache=True)

        # Get the total number of entries
        c.dataset_count = len(c.data)

        # Calculate the number of datasets that have comments, and refine the
        # data based on whether we want to show those with 0 feedback or not.
        if not c.show_zero_feedback:
            c.data = [d for d in c.data if d.get('total-comments',0) > 0]
            c.dataset_count_with_feedback = len(c.data)
        else:
            c.dataset_count_with_feedback = sum([1 for d in c.data if d.get('total-comments',0) > 0])

        if c.data:
            c.generated_at = c.data[0].get('generated-at')

        def pager_url(q=None, page=None):
            ctlr = 'ckanext.dgu.controllers.reports:ReportsController'
            params = {'controller': ctlr, 'action': 'feedback', 'page': page}
            if id:
                params['id'] = id
            if c.include_subpublisher:
                params['show-subpub'] = 1
            if c.show_zero_feedback:
                params['show-zero-feedback'] = 1
            return t.url_for(**params)

        c.page = Page(
            collection=c.data,
            page=page,
            item_count=len(c.data),
            items_per_page=LIMIT,
            url=pager_url,
        )

        if format == 'csv':
            # Write out the report in CSV format, we don't need paging for this so
            # we do it early.
            import csv

            t.response.headers['Content-Type'] = "text/csv; charset=utf-8"
            t.response.headers['Content-Disposition'] = str('attachment; filename=feedback.csv')

            writer = csv.writer(t.response)
            header = ["Dataset", "Publish date", "Publisher", "Economic",
                      "Social", "Effective", "Linked", "Other", "Total comments",
                      "Link"]
            writer.writerow(header)

            for row in c.data:
                link = t.url_for(controller='package', action='read', id=row['package-name'], qualified=True)
                row = [row['package-title'].encode('utf-8'), row['publish-date'],
                       row['publisher-title'], row.get('economic',0),
                       row.get('social',0), row.get('effective',0),
                       row.get('linked',0), row.get('other',0),
                       row.get('total-comments',0), link]
                writer.writerow(row)
            return

        return t.render('reports/feedback.html')


def make_csv_from_dicts(rows):
    import csv
    import cStringIO as StringIO

    csvout = StringIO.StringIO()
    csvwriter = csv.writer(
        csvout,
        dialect='excel',
        quoting=csv.QUOTE_NONNUMERIC
    )
    # extract the headers by looking at all the rows and
    # get a full list of the keys, retaining their ordering
    headers_ordered = []
    headers_set = set()
    for row in rows:
        new_headers = set(row.keys()) - headers_set
        headers_set |= new_headers
        for header in row.keys():
            if header in new_headers:
                headers_ordered.append(header)
    csvwriter.writerow(headers_ordered)
    for row in rows:
        items = []
        for header in headers_ordered:
            item = row.get(header, 'no record')
            if isinstance(item, datetime.datetime):
                item = item.strftime('%Y-%m-%d %H:%M')
            elif isinstance(item, (int, long, float, list, tuple)):
                item = unicode(item)
            elif item is None:
                item = ''
            else:
                item = item.encode('utf8')
            items.append(item)
        try:
            csvwriter.writerow(items)
        except Exception, e:
            raise Exception("%s: %s, %s"%(e, row, items))
    csvout.seek(0)
    return csvout.read()

def ensure_data_is_dicts(data):
    '''Ensure that the data is a list of dicts, rather than a list of tuples
    with column names, as sometimes is the case. Changes it in place'''
    if data['data'] and isinstance(data['data'][0], (list, tuple)):
        new_data = []
        columns = data['columns']
        for row in data['data']:
            new_data.append(OrderedDict(zip(columns, row)))
        data['data'] = new_data
        del data['columns']

def anonymise_user_names(data, organization=None):
    '''Ensure any columns with names in are anonymised, unless the current user
    has privileges.'''
    column_names = data['data'][0].keys() if data['data'] else []
    for col in column_names:
        if col.lower() in ('user', 'username', 'user name', 'author'):
            for row in data['data']:
                row[col] = dguhelpers.user_link_info(row[col],
                              organisation=organization)[0]

