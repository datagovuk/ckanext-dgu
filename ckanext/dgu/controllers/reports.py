import collections

import ckan.plugins.toolkit as t
import ckan.lib.helpers as h
import ckanext.dgu.lib.helpers as dguhelpers
from ckanext.dgu.lib import reports
from ckan.lib.base import BaseController, abort, request, response

c = t.c

class ReportsController(BaseController):

    def index(self):
        return t.render('reports/index.html')

    def activity(self, id, fmt=None):
        import ckan.model as model
        from ckanext.dgu.lib.reports import publisher_activity_report

        try:
            context = {'model':model,'user': c.user, 'owner_org': id}
            t.check_access('package_create',context)
        except t.NotAuthorized, e:
            h.redirect_to('/user?destination={0}'.format(request.path[1:]))

        c.publisher = model.Group.get(id)
        if not c.publisher:
            abort(404, "Publisher not found")
        data = publisher_activity_report(c.publisher, use_cache=True)
        c.created = data['created']
        c.modified = data['modified']
        return t.render('reports/activity.html')

    def nii(self, format=None):
        import ckan.model as model
        from ckanext.dgu.lib.reports import nii_report
        tmpdata = nii_report(use_cache=True)
        c.data = {}

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
            response.headers['Content-Type'] = "text/csv; charset=utf-8"
            response.headers['Content-Disposition'] = str('attachment; filename=nii-broken-resources.csv')

            writer = csv.writer(response)
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
            abort(400, 'include_sub_publishers parameter value must be boolean')
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
        c.include_subpublisher = t.asbool(request.params.get('show-subpub', 0))
        c.show_zero_feedback = t.asbool(request.params.get('show-zero-feedback', 0))
        c.include_published = t.asbool(request.params.get('show-published', 0))

        try:
            page = int(request.params.get('page', 1))
        except ValueError:
            abort(404, _('Not found'))

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
            return h.url_for(**params)

        c.page = h.Page(
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
            from pylons import response

            response.headers['Content-Type'] = "text/csv; charset=utf-8"
            response.headers['Content-Disposition'] = str('attachment; filename=feedback.csv')

            writer = csv.writer(response)
            header = ["Dataset", "Publish date", "Publisher", "Economic",
                      "Social", "Effective", "Linked", "Other", "Total comments",
                      "Link"]
            writer.writerow(header)

            for row in c.data:
                link = h.url_for(controller='package', action='read', id=row['package-name'], qualified=True)
                row = [row['package-title'].encode('utf-8'), row['publish-date'],
                       row['publisher-title'], row.get('economic',0),
                       row.get('social',0), row.get('effective',0),
                       row.get('linked',0), row.get('other',0),
                       row.get('total-comments',0), link]
                writer.writerow(row)
            return

        return t.render('reports/feedback.html')

