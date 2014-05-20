import collections
import datetime
import logging

from pylons import config

from ckan import model
from ckan.lib.helpers import OrderedDict
from ckanext.dgu.lib.publisher import go_down_tree
import ckan.plugins as p

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

        results = model.Session.query(Archival, model.Resource)\
                       .filter(Archival.package_id == package_id)\
                       .filter(Archival.is_broken == True)\
                       .join(model.Package, Archival.package_id == model.Package.id)\
                       .filter(model.Package.state == 'active')\
                       .join(model.Resource, Archival.resource_id == model.Resource.id)\
                       .filter(model.Resource.state == 'active')

        broken_resources = [(resource.description, resource.id)
                            for archival, resource in results.all()]
        return broken_resources

    nii_dataset_details = []
    num_resources = 0
    num_broken_resources = 0
    num_broken_datasets = 0
    broken_organization_names = set()
    nii_organizations = set()
    for dataset_object in nii_dataset_objects:
        broken_resources = broken_resources_for_package(dataset_object.id)
        org = dataset_object.get_organization()
        dataset_details = {
                'name': dataset_object.name,
                'title': dataset_object.title,
                'dataset_notes': dataset_notes(dataset_object),
                'organization_name': org.name,
                'unpublished': p.toolkit.asbool(dataset_object.extras.get('unpublished')),
                'num_broken_resources': len(broken_resources),
                'broken_resources': broken_resources,
                'source': get_source(dataset_object)
                }
        nii_dataset_details.append(dataset_details)
        if broken_resources:
            num_broken_resources += len(broken_resources)
            num_broken_datasets += 1
            broken_organization_names.add(org.name)
        nii_organizations.add(org)
        num_resources += len(dataset_object.resources)

    org_tuples = [(org.name, org.title) for org in
                  sorted(nii_organizations, key=lambda o: o.title)]

    return {'table': nii_dataset_details,
            'organizations': org_tuples,
            'num_resources': num_resources,
            'num_datasets': len(nii_dataset_objects),
            'num_organizations': len(nii_organizations),
            'num_broken_resources': num_broken_resources,
            'num_broken_datasets': num_broken_datasets,
            'num_broken_organizations': len(broken_organization_names),
            }

nii_report_info = {
    'name': 'nii',
    'title': 'National Information Infrastructure',
    'option_defaults': OrderedDict([]),
    'option_combinations': None,
    'generate': nii_report,
    'template': 'report/nii.html',
}


def publisher_resources(organization=None,
                        include_sub_organizations=False):
    '''
    Returns a dictionary detailing resources for each dataset in the
    organisation specified.
    '''
    org = model.Group.by_name(organization)
    if not org:
        raise p.toolkit.ObjectNotFound('Publisher not found')

    # Get packages
    if include_sub_organizations:
        orgs = sorted([x for x in go_down_tree(org)], key=lambda x: x.name)
        org_ids = [x.id for x in orgs]
        pkgs = model.Session.query(model.Package)\
                .filter_by(state='active')\
                .filter(model.Package.owner_org.in_(org_ids))\
                .all()
    else:
        pkgs = model.Session.query(model.Package)\
                .filter_by(state='active')\
                .filter(model.Package.owner_org == org.id)\
                .all()

    # Get their resources
    def create_row(pkg_, resource_dict):
        org_ = pkg_.get_organization()
        return OrderedDict((
                ('publisher_title', org_.title),
                ('publisher_name', org_.name),
                ('package_title', pkg_.title),
                ('package_name', pkg_.name),
                ('package_notes', dataset_notes(pkg_)),
                ('resource_position', resource_dict.get('position')),
                ('resource_id', resource_dict.get('id')),
                ('resource_description', resource_dict.get('description')),
                ('resource_url', resource_dict.get('url')),
                ('resource_format', resource_dict.get('format')),
                ('resource_created', resource_dict.get('created')),
               ))
    num_resources = 0
    rows = []
    for pkg in pkgs:
        resources = pkg.resources
        if resources:
            for res in resources:
                res_dict = {'id': res.id, 'position': res.position,
                            'description': res.description, 'url': res.url,
                            'format': res.format, 'created': res.created}
                rows.append(create_row(pkg, res_dict))
            num_resources += len(resources)
        else:
            # packages with no resources are still listed
            rows.append(create_row(pkg, {}))

    return {'organization_name': org.name,
            'organization_title': org.title,
            'num_datasets': len(pkgs),
            'num_resources': num_resources,
            'table': rows,
            }

def publisher_resources_combinations():
    for organization in all_organizations():
        for include_sub_organizations in (False, True):
                yield {'organization': organization,
                       'include_sub_organizations': include_sub_organizations}

publisher_resources_info = {
    'name': 'publisher-resources',
    'option_defaults': OrderedDict((('organization', 'cabinet-office'),
                                    ('include_sub_organizations', False))),
    'option_combinations': publisher_resources_combinations,
    'generate': publisher_resources,
    'template': 'report/publisher_resources.html',
    }


def organisation_dataset_scores(organisation_name,
                                include_sub_organisations=False):
    '''
    Returns a dictionary detailing openness scores for the organisation
    for each dataset.

    i.e.:
    {'organization_name': 'cabinet-office',
     'organization_title:': 'Cabinet Office',
     'table': [
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
        raise p.toolkit.ObjectNotFound('Publisher not found')
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
            'table': data.values()}


def feedback_report(organization=None, include_sub_organizations=False, include_published=False):
    """
    For the publisher provided (and optionally for sub-publishers) this
    function will generate a report on the feedback for that publisher.
    """
    import ckan.lib.helpers as helpers
    from ckanext.dgu.lib.publisher import go_down_tree
    from ckanext.dgu.model.feedback import Feedback

    if organization:
        organization = model.Group.by_name(organization)
        if not organization:
            raise p.toolkit.ObjectNotFound()
    else:
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

    # For each package, count the feedback comments
    results = []
    num_pkgs_with_feedback = 0
    for member in memberships.all():
        pkg = model.Package.get(member.table_id)

        # Skip unpublished datasets if that's asked for
        if not include_published and not pkg.extras.get('unpublished', False):
            continue

        pkg_data = collections.defaultdict(int)
        pkg_data['organization-name'] = member.group.name
        pkg_data['generated-at'] = helpers.render_datetime(datetime.datetime.now(), "%d/%m/%Y %H:%M")
        pkg_data['organization-title'] = member.group.title
        pkg_data['package-name'] = pkg.name
        pkg_data['package-title'] = pkg.title
        pkg_data['publish-date'] = pkg.extras.get('publish-date', '')

        for feedback in model.Session.query(Feedback).filter(Feedback.visible == True)\
                .filter(Feedback.package_id == member.table_id )\
                .filter(Feedback.active == True ):
            if feedback.economic: pkg_data['economic'] += 1
            if feedback.social: pkg_data['social'] += 1
            if feedback.linked: pkg_data['linked'] += 1
            if feedback.other: pkg_data['other'] += 1
            if feedback.effective: pkg_data['effective'] += 1

        pkg_data['total-comments'] = sum([pkg_data['economic'],
                                          pkg_data['social'],
                                          pkg_data['linked'],
                                          pkg_data['other'],
                                          pkg_data['effective']])
        results.append(pkg_data)
        if pkg_data['total-comments'] > 0:
            num_pkgs_with_feedback += 1

    return {'table': sorted(results, key=lambda x: -x.get('total-comments')),
            'dataset_count': len(results),
            'dataset_count_with_feedback': num_pkgs_with_feedback,
            }


def all_organizations(include_none=False):
    if include_none:
        yield None
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
    'template': 'report/feedback.html',
    }

def get_quarter_dates(datetime_now):
    '''Returns the dates for this (current) quarter and last quarter. Uses
    calendar year, so 1 Jan to 31 Mar etc.'''
    now = datetime_now
    month_this_q_started = (now.month - 1) // 3 * 3 + 1
    this_q_started = datetime.datetime(now.year, month_this_q_started, 1)
    this_q_ended = datetime.datetime(now.year, now.month, now.day)
    last_q_started = datetime.datetime(
                      this_q_started.year + (this_q_started.month-3)/12,
                      (this_q_started.month-4) % 12 + 1,
                      1)
    last_q_ended = this_q_started - datetime.timedelta(days=1)
    return {'this': (this_q_started, this_q_ended),
            'last': (last_q_started, last_q_ended)}


def publisher_activity(organization, include_sub_organizations=False):
    """
    Contains information about the datasets a specific organization has
    released in this and last quarter (calendar year). This is needed by
    departments for their quarterly transparency reports.
    """
    import datetime
    import ckan.model as model
    from paste.deploy.converters import asbool

    # These are the authors whose revisions we ignore, as they are trivial
    # changes. NB we do want to know about revisions by:
    # * harvest (harvested metadata)
    # * dgu (NS Stat Hub imports)
    # * Fix national indicators
    system_authors = ('autotheme', 'co-prod3.dh.bytemark.co.uk',
                      'Date format tidier', 'current_revision_fixer',
                      'current_revision_fixer2')

    created = {'this': [], 'last': []}
    modified = {'this': [], 'last': []}

    now = datetime.datetime.now()
    quarters = get_quarter_dates(now)

    if organization:
        organization = model.Group.by_name(organization)
        if not organization:
            raise p.toolkit.ObjectNotFound()

    if not organization:
        pkgs = model.Session.query(model.Package)\
                .all()
    elif include_sub_organizations:
        orgs = sorted([x for x in go_down_tree(organization)],
                      key=lambda x: x.title)
        org_ids = [x.id for x in orgs]
        pkgs = model.Session.query(model.Package)\
                    .filter(model.Package.owner_org.in_(org_ids))\
                    .all()
    else:
        pkgs = model.Session.query(model.Package)\
                    .filter(model.Package.owner_org == organization.id)\
                    .all()

    for pkg in pkgs:
        created_ = model.Session.query(model.PackageRevision)\
            .filter(model.PackageRevision.id == pkg.id) \
            .order_by("revision_timestamp asc").first()

        pr_q = model.Session.query(model.PackageRevision, model.Revision)\
            .filter(model.PackageRevision.id == pkg.id)\
            .filter_by(state='active')\
            .join(model.Revision)\
            .filter(~model.Revision.author.in_(system_authors))
        rr_q = model.Session.query(model.Package, model.ResourceRevision, model.Revision)\
            .filter(model.Package.id == pkg.id)\
            .filter_by(state='active')\
            .join(model.ResourceGroup)\
            .join(model.ResourceRevision,
                  model.ResourceGroup.id == model.ResourceRevision.resource_group_id)\
            .join(model.Revision)\
            .filter(~model.Revision.author.in_(system_authors))
        pe_q = model.Session.query(model.Package, model.PackageExtraRevision, model.Revision)\
            .filter(model.Package.id == pkg.id)\
            .filter_by(state='active')\
            .join(model.PackageExtraRevision,
                  model.Package.id == model.PackageExtraRevision.package_id)\
            .join(model.Revision)\
            .filter(~model.Revision.author.in_(system_authors))

        for quarter_name in quarters:
            quarter = quarters[quarter_name]
            if quarter[0] < created_.revision_timestamp < quarter[1]:
                published = not asbool(pkg.extras.get('unpublished'))
                created[quarter_name].append(
                    (created_.name, created_.title, dataset_notes(pkg),
                     'created', quarter_name,
                     created_.revision_timestamp.isoformat(),
                     created_.revision.author, published))
            else:
                prs = pr_q.filter(model.PackageRevision.revision_timestamp > quarter[0])\
                          .filter(model.PackageRevision.revision_timestamp < quarter[1])
                rrs = rr_q.filter(model.ResourceRevision.revision_timestamp > quarter[0])\
                          .filter(model.ResourceRevision.revision_timestamp < quarter[1])
                pes = pe_q.filter(model.PackageExtraRevision.revision_timestamp > quarter[0])\
                          .filter(model.PackageExtraRevision.revision_timestamp < quarter[1])
                authors = ' '.join(set([r[1].author for r in prs] +
                                      [r[2].author for r in rrs] +
                                      [r[2].author for r in pes]))
                dates = set([r[1].timestamp.date() for r in prs] +
                            [r[2].timestamp.date() for r in rrs] +
                            [r[2].timestamp.date() for r in pes])
                dates_formatted = ' '.join([date.isoformat()
                                            for date in sorted(dates)])
                if authors:
                    published = not asbool(pkg.extras.get('unpublished'))
                    modified[quarter_name].append(
                        (pkg.name, pkg.title, dataset_notes(pkg),
                         'modified', quarter_name,
                         dates_formatted, authors, published))

    datasets = []
    for quarter_name in quarters:
        datasets += sorted(created[quarter_name], key=lambda x: x[1])
        datasets += sorted(modified[quarter_name], key=lambda x: x[1])
    columns = ('Dataset name', 'Dataset title', 'Dataset notes', 'Modified or created', 'Quarter', 'Timestamp', 'Author', 'Published')

    return {'table': datasets, 'columns': columns,
            'quarters': quarters}

def publisher_activity_combinations():
    for org in all_organizations(include_none=False):
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
    'template': 'report/publisher_activity.html',
    }


def dataset_notes(pkg):
    '''Returns a string with notes about the given package. It is configurable.'''
    expression = config.get('ckanext-report.notes.dataset')
    return eval(expression, None, {'pkg': pkg, 'asbool': p.toolkit.asbool})
