import collections
from ckan import model
from ckan.lib.helpers import OrderedDict
from ckanext.dgu.lib.publisher import go_down_tree

import ckan.plugins as p

import logging

log = logging.getLogger(__name__)

def get_source(package):
    '''Returns the source of package object if it is not entered by the form.
    Of particular interest are those from the NS Pub Hub (StatsHub) and
    UK Location.'''
    if p.toolkit.asbool(package.extras.get('INSPIRE')):
        return 'UK Location'
    if p.toolkit.asbool(package.extras.get('external_reference') == 'ONSHUB'):
        return 'StatsHub'
    return ''

def nii_report():
    '''A list of the NII datasets, grouped by publisher, with details of broken
    links and source.'''
    nii_dataset_q = model.Session.query(model.Package)\
        .join(model.PackageExtra, model.PackageExtra.package_id == model.Package.id)\
        .join(model.Group, model.Package.owner_org == model.Group.id)\
        .filter(model.PackageExtra.key == 'core-dataset')\
        .filter(model.PackageExtra.value == 'true')\
        .filter(model.Package.state == 'active')
    nii_dataset_objects = nii_dataset_q\
            .order_by(model.Group.title, model.Package.title).all()

    def broken_resources_for_package(package_id):
        from ckanext.archiver.model import Archival

        archivals = model.Session.query(Archival)\
                         .filter(Archival.is_broken == True)\
                         .join(model.Package, Archival.package_id == package_id)\
                         .filter(model.Package.state == 'active')\
                         .join(model.Resource, Archival.resource_id == model.Resource.id)\
                         .filter(model.Resource.state == 'active')

        broken_resources = [(archival.resource.description, archival.resource.id)
                            for archival in archivals.all()]
        return broken_resources

    nii_dataset_details = []
    total_broken_resources = 0
    total_broken_datasets = 0
    nii_organizations = set()
    for dataset_object in nii_dataset_objects:
        broken_resources = broken_resources_for_package(dataset_object.id)
        org = dataset_object.get_organization()
        dataset_details = {
                'name': dataset_object.name,
                'title': dataset_object.title,
                'organization_name': org.name,
                'unpublished': p.toolkit.asbool(dataset_object.extras.get('unpublished')),
                'num_broken_resources': len(broken_resources),
                'broken_resources': broken_resources,
                'source': get_source(dataset_object)
                }
        nii_dataset_details.append(dataset_details)
        total_broken_resources += len(broken_resources)
        if broken_resources:
            total_broken_datasets += 1
        nii_organizations.add(org)

    org_tuples = [(org.name, org.title) for org in
                  sorted(nii_organizations, key=lambda o: o.title)]

    return {'data': nii_dataset_details,
            'organizations': org_tuples,
            'total_broken_resources': total_broken_resources,
            'total_broken_datasets': total_broken_datasets,
            }

nii_report_info = {
    'name': 'nii',
    'title': 'National Information Infrastructure',
    'option_defaults': OrderedDict([]),
    'option_combinations': None,
    'generate': nii_report,
    'template': 'reports/nii.html',
}

def sql_to_filter_by_organisation(organisation,
                                  include_sub_organisations=False):
    '''
    Returns: (sql_org_filter, sql_params)
    In your sql you need:
          WHERE %(org_filter)s
    Run this function:
          sql_org_filter, sql_params = sql_to_filter_by_organisation( ... )
    And execute your sql with the tuple:
          rows = model.Session.execute(sql % sql_org_filter, sql_params)
    '''
    sql_org_filter = {}
    sql_params = {}
    if not include_sub_organisations:
        sql_org_filter['org_filter'] = '"group".name = :org_name'
        sql_params['org_name'] = organisation.name
    else:
        sub_org_filters = ['"group".name=\'%s\'' % org.name for org in go_down_tree(organisation)]
        sql_org_filter['org_filter'] = '(%s)' % ' or '.join(sub_org_filters)
    return sql_org_filter, sql_params


def british_date_formatter(datetime_):
    return datetime_.strftime('%d/%m/%Y')


def british_datetime_formatter(datetime_):
    return datetime_.strftime('%d/%m/%Y  %H:%M')


def organisation_resources(organisation_name,
                           include_sub_organisations=False,
                           date_formatter=None):
    '''
    Returns a dictionary detailing resources for each dataset in the
    organisation specified.

    headings: ['Publisher title', 'Publisher name', 'Dataset title', 'Dataset name', 'Resource index', 'Description', 'URL', 'Format', 'Date created']

    i.e.:
    {'organization_name': 'cabinet-office',
     'organization_title:': 'Cabinet Office',
     'schema': {'Publisher title': 'organization_id',
                'Publisher name': 'organization_name',
                ...},
     'rows': [ row_dict, row_dict, ... ]
    }
    '''
    sql = """
        select package.id as package_id,
               package.title as package_title,
               package.name as package_name,
               resource.id as resource_id,
               resource.url as resource_url,
               resource.format as resource_format,
               resource.description as resource_description,
               resource.position as resource_position,
               resource.created as resource_created,
               "group".id as publisher_id,
               "group".name as publisher_name,
               "group".title as publisher_title
        from resource
            left join resource_group on resource.resource_group_id = resource_group.id
            left join package on resource_group.package_id = package.id
            left join member on member.table_id = package.id
            left join "group" on member.group_id = "group".id
        where
            package.state='active'
            and resource.state='active'
            and resource_group.state='active'
            and "group".state='active'
            and %(org_filter)s
        order by "group".name, package.name, resource.position
        """
    org = model.Group.by_name(organisation_name)
    if not org:
        abort(404, 'Publisher not found')
    organisation_title = org.title

    sql_org_filter, sql_params = sql_to_filter_by_organisation(
        org,
        include_sub_organisations=include_sub_organisations)
    raw_rows = model.Session.execute(sql % sql_org_filter, sql_params)

    schema = OrderedDict((('Organization title', 'publisher_title'),
                          ('Organization name', 'publisher_name'),
                          ('Dataset title', 'package_title'),
                          ('Dataset name', 'package_name'),
                          ('Resource index', 'resource_position'),
                          ('Resource ID', 'resource_id'),
                          ('Description', 'resource_description'),
                          ('URL', 'resource_url'),
                          ('Format', 'resource_format'),
                          ('Date created', 'resource_created'),
                          ))
    rows = []
    for raw_row in raw_rows:
        #row = [getattr(raw_row, key) for key in schema.values()]
        row = OrderedDict([(key, getattr(raw_row, key)) for key in schema.values()])
        if date_formatter:
            for col in ('resource_created',):
                if row[col]:
                    row[col] = date_formatter(row[col])
        rows.append(row)
    return {'organization_name': org.name,
            'organization_title': org.title,
            'schema': schema,
            'rows': rows,
            }

def organisation_dataset_scores(organisation_name,
                                include_sub_organisations=False):
    '''
    Returns a dictionary detailing openness scores for the organisation
    for each dataset.

    i.e.:
    {'organization_name': 'cabinet-office',
     'organization_title:': 'Cabinet Office',
     'data': [
       {'package_name', 'package_title', 'resource_url', 'openness_score', 'reason', 'last_updated', 'is_broken', 'format'}
      ...]

    NB the list does not contain datasets that have 0 resources and therefore
       score 0

    '''
    values = {}
    sql = """
        select package.id as package_id,
               task_status.key as task_status_key,
               task_status.value as task_status_value,
               task_status.error as task_status_error,
               task_status.last_updated as task_status_last_updated,
               resource.id as resource_id,
               resource.url as resource_url,
               resource.position,
               package.title as package_title,
               package.name as package_name,
               "group".id as publisher_id,
               "group".name as publisher_name,
               "group".title as publisher_title
        from resource
            left join task_status on task_status.entity_id = resource.id
            left join resource_group on resource.resource_group_id = resource_group.id
            left join package on resource_group.package_id = package.id
            left join member on member.table_id = package.id
            left join "group" on member.group_id = "group".id
        where
            entity_id in (select entity_id from task_status where task_status.task_type='qa')
            and package.state = 'active'
            and resource.state='active'
            and resource_group.state='active'
            and "group".state='active'
            and task_status.task_type='qa'
            and task_status.key='status'
            %(org_filter)s
        order by package.title, package.name, resource.position
        """
    sql_options = {}
    org = model.Group.by_name(organisation_name)
    if not org:
        abort(404, 'Publisher not found')
    organisation_title = org.title

    if not include_sub_organisations:
        sql_options['org_filter'] = 'and "group".name = :org_name'
        values['org_name'] = organisation_name
    else:
        sub_org_filters = ['"group".name=\'%s\'' % org.name for org in go_down_tree(org)]
        sql_options['org_filter'] = 'and (%s)' % ' or '.join(sub_org_filters)

    rows = model.Session.execute(sql % sql_options, values)
    data = dict() # dataset_name: {properties}
    for row in rows:
        package_data = data.get(row.package_name)
        if not package_data:
            package_data = OrderedDict((
                ('dataset_title', row.package_title),
                ('dataset_name', row.package_name),
                ('organization_title', row.publisher_title),
                ('organization_name', row.publisher_name),
                # the rest are placeholders to hold the details
                # of the highest scoring resource
                ('resource_position', None),
                ('resource_id', None),
                ('resource_url', None),
                ('openness_score', None),
                ('openness_score_reason', None),
                ('last_updated', None),
                ))
        if row.task_status_value > package_data['openness_score']:
            package_data['resource_position'] = row.position
            package_data['resource_id'] = row.resource_id
            package_data['resource_url'] = row.resource_url

            try:
                package_data.update(json.loads(row.task_status_error))
            except ValueError, e:
                log.error('QA status "error" should have been in JSON format, but found: "%s" %s', task_status_error, e)
                package_data['reason'] = 'Could not display reason due to a system error'

            package_data['openness_score'] = row.task_status_value
            package_data['openness_score_reason'] = package_data['reason'] # deprecated
            package_data['last_updated'] = row.task_status_last_updated

        data[row.package_name] = package_data

    # Sort the results by openness_score asc so we can see the worst
    # results first
    data = OrderedDict(sorted(data.iteritems(),
        key=lambda x: x[1]['openness_score']))

    return {'organization_name': organisation_name,
            'organization_title': organisation_title,
            'data': data.values()}


def feedback_report(organization=None, include_sub_organizations=False, include_published=False):
    """
    For the publisher provided (and optionally for sub-publishers) this
    function will generate a report on the feedback for that publisher.
    """
    import collections
    import datetime
    import ckan.lib.helpers as helpers
    from ckanext.dgu.lib.publisher import go_down_tree
    from ckanext.dgu.model.feedback import Feedback
    from operator import itemgetter

    if organization:
        organization_name = organization
        organization = model.Group.by_name(organization_name)
        if not organization:
            raise p.toolkit.NotFound()
    else:
        organization_name = '__all__'
        organization = None

    # Get packages for these organization(s)
    if organization:
        group_ids = [organization.id]
        if include_sub_organizations:
            groups = sorted([x for x in go_down_tree(organization)], key=lambda x: x.title)
            group_ids = [x.id for x in groups]

        memberships = model.Session.query(model.Member)\
            .join(model.Package, model.Package.id==model.Member.table_id)\
            .filter(model.Member.state == 'active')\
            .filter(model.Member.group_id.in_(group_ids))\
            .filter(model.Member.table_name == 'package')\
            .filter(model.Package.state == 'active')

    else:
        memberships = model.Session.query(model.Member)\
            .join(model.Package, model.Package.id==model.Member.table_id)\
            .filter(model.Member.state == 'active')\
            .filter(model.Member.table_name == 'package')\
            .filter(model.Package.state == 'active')

    results = []
    for member in memberships.all():
        pkg = model.Package.get(member.table_id)

        # Skip unpublished datasets if that's asked for
        if not include_published and not pkg.extras.get('unpublished', False):
            continue

        data = collections.defaultdict(int)
        data['organization-name'] = member.group.name
        data['generated-at'] = helpers.render_datetime(datetime.datetime.now(), "%d/%m/%Y %H:%M")
        data['organization-title'] = member.group.title
        data['package-name'] = pkg.name
        data['package-title'] = pkg.title
        data['publish-date'] = pkg.extras.get('publish-date', '')

        for item in model.Session.query(Feedback).filter(Feedback.visible == True)\
                .filter(Feedback.package_id == member.table_id )\
                .filter(Feedback.active == True ):
            if item.economic: data['economic'] += 1
            if item.social: data['social'] += 1
            if item.linked: data['linked'] += 1
            if item.other: data['other'] += 1
            if item.effective: data['effective'] += 1

        data['total-comments'] = sum([data['economic'], data['social'],
                                     data['linked'], data['other'],
                                     data['effective']])
        results.append(data)

    return sorted(results, key=itemgetter('package-title'))


def all_organizations():
    orgs = model.Session.query(model.Group).\
        filter(model.Group.type=='organization').\
        filter(model.Group.state=='active').order_by('name')
    for org in orgs:
        yield org.name


def feedback_report_combinations():
    organization = None
    include_sub_organizations = True  # assumed for index anyway
    for include_published in (False, True):
        yield {'organization': organization,
               'include_sub_organizations': include_sub_organizations,
               'include_published': include_published}

    for organization in all_organizations():
        for include_sub_organizations in (False, True):
            for include_published in (False, True):
                yield {'organization': organization,
                       'include_sub_organizations': include_sub_organizations,
                       'include_published': include_published}

feedback_report_info = {
    'name': 'feedback',
    'option_defaults': OrderedDict((('organization', None),
                                    ('include_sub_organizations', False),
                                    ('include_published', False))),
    'option_combinations': feedback_report_combinations,
    'generate': feedback_report,
    'template': 'reports/feedback_report.html',
    }


def publisher_activity(organization, include_sub_organizations=False):
    """
    Contains information about the datasets a specific organization has released within
    the last 3 months.
    """
    import datetime
    import ckan.model as model
    from paste.deploy.converters import asbool

    created = []
    modified = []

    cutoff = datetime.datetime.now() - datetime.timedelta(3*365/12)

    publisher = model.Group.by_name(organization)
    if not publisher:
        raise p.toolkit.NotFound()

    for pkg in model.Session.query(model.Package)\
            .filter(model.Package.owner_org==publisher.id)\
            .filter(model.Package.state=='active').all():

        rc = model.Session.query(model.PackageRevision)\
            .filter(model.PackageRevision.id==pkg.id) \
            .order_by("revision_timestamp asc").first()
        rm = model.Session.query(model.PackageRevision)\
            .filter(model.PackageRevision.id==pkg.id) \
            .order_by("revision_timestamp desc").first()

        if rc.revision_timestamp > cutoff:
            rc.published = not asbool(pkg.extras.get('unpublished'))
            created.append((rc.name,rc.title,'created',rc.revision_timestamp.isoformat(),rc.revision.author,rc.published))

        if rm.revision_timestamp > cutoff:
            exists = [rc[0] for rc in created]
            if not rm.name in exists:
                rm.published = not asbool(pkg.extras.get('unpublished'))
                modified.append((rm.name,rm.title,'modified',rm.revision_timestamp.isoformat(),rm.revision.author,rm.published))

    datasets = sorted(created, key=lambda x: x[1])
    datasets += sorted(modified, key=lambda x: x[1])
    columns = ('Dataset name', 'Dataset title', 'Modified or created', 'Timestamp', 'Author', 'Published')

    return {'data': datasets, 'columns': columns}

def publisher_activity_combinations():
    for org in all_organizations():
        for include_sub_organizations in (False, True):
            yield {'organization': org,
                   'include_sub_organizations': include_sub_organizations}

publisher_activity_report_info = {
    'name': 'publisher-activity',
    'option_defaults': OrderedDict((('organization', 'cabinet-office'),
                                    ('include_sub_organizations', False),
                                    )),
    'option_combinations': publisher_activity_combinations,
    'generate': publisher_activity,
    'template': 'reports/publisher_activity.html',
    }
