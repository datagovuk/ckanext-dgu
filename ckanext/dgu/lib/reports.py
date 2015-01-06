import collections
import datetime
import logging

from ckan import model
from ckan.lib.helpers import OrderedDict
import ckan.plugins as p
from ckanext.report import lib

log = logging.getLogger(__name__)


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
                'dataset_notes': lib.dataset_notes(dataset_object),
                'organization_name': org.name,
                'unpublished': p.toolkit.asbool(dataset_object.extras.get('unpublished')),
                'num_broken_resources': len(broken_resources),
                'broken_resources': broken_resources,
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
    'description': 'Details of the datasets in the NII.',
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
    pkgs = model.Session.query(model.Package)\
                .filter_by(state='active')
    pkgs = lib.filter_by_organizations(pkgs, organization,
                                       include_sub_organizations).all()

    # Get their resources
    def create_row(pkg_, resource_dict):
        org_ = pkg_.get_organization()
        return OrderedDict((
                ('publisher_title', org_.title),
                ('publisher_name', org_.name),
                ('package_title', pkg_.title),
                ('package_name', pkg_.name),
                ('package_notes', lib.dataset_notes(pkg_)),
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
    for organization in lib.all_organizations():
        for include_sub_organizations in (False, True):
                yield {'organization': organization,
                       'include_sub_organizations': include_sub_organizations}

publisher_resources_info = {
    'name': 'publisher-resources',
    'description': 'A list of all the datasets and resources for a publisher.',
    'option_defaults': OrderedDict((('organization', 'cabinet-office'),
                                    ('include_sub_organizations', False))),
    'option_combinations': publisher_resources_combinations,
    'generate': publisher_resources,
    'template': 'report/publisher_resources.html',
    }


def feedback_report(organization=None, include_sub_organizations=False, include_published=False):
    """
    For the publisher provided (and optionally for sub-publishers) this
    function will generate a report on the feedback for that publisher.
    """
    import ckan.lib.helpers as helpers
    from ckanext.dgu.model.feedback import Feedback

    if organization:
        organization = model.Group.by_name(organization)
        if not organization:
            raise p.toolkit.ObjectNotFound()
    else:
        organization = None

    # Get packages for these organization(s)
    memberships = model.Session.query(model.Member)\
        .join(model.Package, model.Package.id==model.Member.table_id)\
        .filter(model.Member.state == 'active')
    memberships = lib.filter_by_organizations(memberships, organization,
                                              include_sub_organizations)\
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


def feedback_report_combinations():
    organization = None
    include_sub_organizations = True  # assumed for index anyway
    for include_published in (False, True):
        yield {'organization': organization,
               'include_sub_organizations': include_sub_organizations,
               'include_published': include_published}

    for organization in lib.all_organizations():
        for include_sub_organizations in (False, True):
            for include_published in (False, True):
                yield {'organization': organization,
                       'include_sub_organizations': include_sub_organizations,
                       'include_published': include_published}

feedback_report_info = {
    'name': 'feedback',
    'description': 'A summary of the feedback given on datasets, originally used to determine those to make part of the NII.',
    'option_defaults': OrderedDict((('organization', None),
                                    ('include_sub_organizations', True),
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
                      'current_revision_fixer2', 'fix_contact_details.py',
                      'Repoint 410 Gone to webarchive url',
                      'Fix duplicate resources',
                      'fix_secondary_theme.py',
                      )
    system_author_template = 'script-%'  # "%" is a wildcard

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
    else:
        pkgs = model.Session.query(model.Package)
        pkgs = lib.filter_by_organizations(pkgs, organization,
                                           include_sub_organizations).all()

    for pkg in pkgs:
        created_ = model.Session.query(model.PackageRevision)\
            .filter(model.PackageRevision.id == pkg.id) \
            .order_by("revision_timestamp asc").first()

        pr_q = model.Session.query(model.PackageRevision, model.Revision)\
            .filter(model.PackageRevision.id == pkg.id)\
            .filter_by(state='active')\
            .join(model.Revision)\
            .filter(~model.Revision.author.in_(system_authors)) \
            .filter(~model.Revision.author.like(system_author_template))
        rr_q = model.Session.query(model.Package, model.ResourceRevision, model.Revision)\
            .filter(model.Package.id == pkg.id)\
            .filter_by(state='active')\
            .join(model.ResourceGroup)\
            .join(model.ResourceRevision,
                  model.ResourceGroup.id == model.ResourceRevision.resource_group_id)\
            .join(model.Revision)\
            .filter(~model.Revision.author.in_(system_authors))\
            .filter(~model.Revision.author.like(system_author_template))
        pe_q = model.Session.query(model.Package, model.PackageExtraRevision, model.Revision)\
            .filter(model.Package.id == pkg.id)\
            .filter_by(state='active')\
            .join(model.PackageExtraRevision,
                  model.Package.id == model.PackageExtraRevision.package_id)\
            .join(model.Revision)\
            .filter(~model.Revision.author.in_(system_authors))\
            .filter(~model.Revision.author.like(system_author_template))

        for quarter_name in quarters:
            quarter = quarters[quarter_name]
            if quarter[0] < created_.revision_timestamp < quarter[1]:
                published = not asbool(pkg.extras.get('unpublished'))
                created[quarter_name].append(
                    (created_.name, created_.title, lib.dataset_notes(pkg),
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
                        (pkg.name, pkg.title, lib.dataset_notes(pkg),
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
    for org in lib.all_organizations(include_none=False):
        for include_sub_organizations in (False, True):
            yield {'organization': org,
                   'include_sub_organizations': include_sub_organizations}

publisher_activity_report_info = {
    'name': 'publisher-activity',
    'description': 'A quarterly list of datasets created and edited by a publisher.',
    'option_defaults': OrderedDict((('organization', 'cabinet-office'),
                                    ('include_sub_organizations', False),
                                    )),
    'option_combinations': publisher_activity_combinations,
    'generate': publisher_activity,
    'template': 'report/publisher_activity.html',
    }


def unpublished():
    pkgs = model.Session.query(model.Package)\
                .filter_by(state='active')\
                .join(model.PackageExtra)\
                .filter_by(key='unpublished')\
                .filter_by(value='true')\
                .filter_by(state='active')\
                .all()
    pkg_dicts = []
    for pkg in pkgs:
        org = pkg.get_organization()
        pkg_dict = {
                'name': pkg.name,
                'title': pkg.title,
                'organization title': org.title,
                'organization name': org.name,
                'notes': pkg.notes,
                'publish date': pkg.extras.get('publish-date'),
                'will not be released': pkg.extras.get('publish-restricted'),
                'release notes': pkg.extras.get('release-notes'),
                }
        pkg_dicts.append(pkg_dict)
    return {'table': pkg_dicts}

unpublished_report_info = {
    'name': 'unpublished',
    'title': 'Unpublished datasets',
    'description': 'Unpublished dataset properties provided by publishers.',
    'option_defaults': None,
    'option_combinations': None,
    'generate': unpublished,
    'template': 'report/unpublished.html',
    }

def last_resource_deleted(pkg):
    
    resource_revisions = model.Session.query(model.ResourceRevision) \
                              .join(model.ResourceGroup) \
                              .join(model.Package) \
                              .filter_by(id=pkg.id) \
                              .order_by(model.ResourceRevision.revision_timestamp) \
                              .all()
    previous_rr = None
    # go through the RRs in reverse chronological order and when an active
    # revision is found, return the rr in the previous loop.
    for rr in resource_revisions[::-1]:
        if rr.state == 'active':
            return previous_rr.revision_timestamp, previous_rr.url
        previous_rr = rr
    return None, ''

def datasets_without_resources():
    pkg_dicts = []
    pkgs = model.Session.query(model.Package)\
                .filter_by(state='active')\
                .order_by(model.Package.title)\
                .all()
    for pkg in pkgs:
        if len(pkg.resources) != 0 or \
          pkg.extras.get('unpublished', '').lower() == 'true':
            continue
        org = pkg.get_organization()
        deleted, url = last_resource_deleted(pkg)
        pkg_dict = OrderedDict((
                ('name', pkg.name),
                ('title', pkg.title),
                ('organization title', org.title),
                ('organization name', org.name),
                ('metadata created', pkg.metadata_created.isoformat()),
                ('metadata modified', pkg.metadata_modified.isoformat()),
                ('last resource deleted', deleted.isoformat() if deleted else None),
                ('last resource url', url),
                ('dataset_notes', lib.dataset_notes(pkg)),
                ))
        pkg_dicts.append(pkg_dict)
    return {'table': pkg_dicts}


datasets_without_resources_info = {
    'name': 'datasets-without-resources',
    'title': 'Datasets without resources',
    'description': 'Datasets that have no resources (data URLs). Excludes unpublished ones.',
    'option_defaults': None,
    'option_combinations': None,
    'generate': datasets_without_resources,
    'template': 'report/datasets_without_resources.html',
    }


def dataset_app_report():
    table = []

    datasets = collections.defaultdict(lambda: {'apps': []})
    for related in model.Session.query(model.RelatedDataset).filter(model.Related.type=='App').all():
        dataset_name = related.dataset.name

        app = {
          'title': related.related.title,
          'url': related.related.url
        }

        datasets[dataset_name]['title'] = related.dataset.title
        datasets[dataset_name]['theme'] = related.dataset.extras.get('theme-primary', '')
        datasets[dataset_name]['apps'].append(app)

    for dataset_name, dataset in datasets.items():
        sorted_apps = sorted(dataset['apps'], key=lambda x: x['title'])
        table.append({'dataset_title': dataset['title'],
                      'dataset_name': dataset_name,
                      'theme': dataset['theme'],
                      'app_titles': "\n".join(a['title'] for a in sorted_apps),
                      'app_urls': "\n".join(a['url'] for a in sorted_apps)})

    return {'table': table}

dataset_app_report_info = {
    'name': 'dataset-app-report',
    'title': 'Datasets used in apps',
    'description': 'Datasets that have been used by apps, grouped by theme.',
    'option_defaults': None,
    'option_combinations': None,
    'generate': dataset_app_report,
    'template': 'report/dataset_app_report.html',
    }
