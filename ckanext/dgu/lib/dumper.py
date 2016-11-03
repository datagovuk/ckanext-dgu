"""
This file contain code analogous to ckan.lib.dumper except that instead
of dumping all of the packages and resources in the same table, it dumps
them to individual files (datasets.csv and resources.csv) before zipping
them.
"""
import unicodecsv as csv
import json
import tempfile
import urlparse

from paste.deploy.converters import asbool

from pylons import config
import ckan.logic as logic
import ckan.model as model

IGNORE_KEYS = [
    u'ratings_count',
    u'ratings_average',
    u'revision_id',
    u'creator_user_id',
    u'groups',
    u'ckan_url',
    u'owner_org',
    u'id',
    u'name',
    u'private',
    u'relationships',
    u'notes_rendered',
    u'state',
    u'title',
    u'type',
    u'ckan_url',
    u'url',
    u'author_email',
    u'maintainer_email',
    # emails, license, unpublished
]

INTERESTING_EXTRAS = [
    u'geographic_coverage',
    u'temporal_coverage-from',
    u'temporal_coverage-to',
    u'theme-primary',
    u'theme-secondary',
    u'update_frequency',
    u'mandate',
    u'odi-certificate',
]

def make_nice_name(name):

    # Special cases
    if name == 'odi-certificate-url': return 'ODI Certificate URL'
    if name == 'theme-primary': return 'Primary Theme'
    if name == 'theme-secondary': return 'Secondary Themes'

    return name.replace('_', ' ').replace('-', ' ').title()


class CSVDumper(object):


    def __init__(self, *args, **kwargs):
        self.dataset_file = tempfile.NamedTemporaryFile(delete=False)
        self.resource_file = tempfile.NamedTemporaryFile(delete=False)

        self.dataset_csv = csv.writer(self.dataset_file)
        self.resource_csv = csv.writer(self.resource_file)

        self.dataset_filename = self.dataset_file.name
        self.resource_filename = self.resource_file.name

        self.organization_cache = {}

        self.keys = []

    def dump(self, limit=None):
        packages = model.Session.query(model.Package)\
            .filter(model.Package.state == 'active')\
            .filter(model.Package.private == False)\
            .order_by('name')
        if limit:
            packages = packages.limit(limit)

        first = True
        for pkg in packages.yield_per(200):
            self.write_object(pkg, first)
            first = False

    def _encode(self, s):
        ''' csv.write doesn't do encoding - call this on all row cells
        first.
        '''
        if s is None:
            return ''
        if isinstance(s, unicode):
            return s.encode('utf-8')
        elif isinstance(s, bool):
            return str(s)
        elif isinstance(s, (int, float)):
            return s  # so that it can't get quoted by csv.QUOTE_NONNUMERIC
        elif not isinstance(s, str):
            s = str(s)
        return s

    def write_object(self, pkg, first=False):
        pkg_dict, resources = self._flatten(pkg)

        if first:
            # TODO Get a better list of fields to dump than just what we see in
            # the first dataset...
            self.dataset_keys = sorted(pkg_dict.keys())
            self.dataset_keys.remove('license')  # duplicate
            self.write_header(self.dataset_keys)

        url = config.get('ckan.site_url')
        full_url = urlparse.urljoin(url, '/dataset/%s' % pkg.name)

        if pkg.owner_org in self.organization_cache:
            organization, top_level_publisher = self.organization_cache.get(pkg.owner_org)
        else:
            org = model.Group.get(pkg.owner_org)
            organization = org.title

            parent_group_hierarchy = org.get_parent_group_hierarchy('organization')
            if parent_group_hierarchy:
                top_level_publisher = parent_group_hierarchy[0].title
            else:
                top_level_publisher = organization

            self.organization_cache[pkg.owner_org] = (organization, top_level_publisher)

        license = pkg.license or ''
        if license:
            license = pkg.license.title

        # This really should have been published, rather than unpublished.
        published = not asbool(pkg.extras.get('unpublished') or False)
        nii = asbool(pkg.extras.get('core-dataset') or False)
        location = asbool(pkg.extras.get('UKLP') or False)
        import_source = pkg.extras.get('import_source') or \
            'harvest' if pkg.extras.get('harvest_object_id') else ''

        vals = [self._encode(val) for val in [pkg.name, pkg.title, full_url, organization, top_level_publisher, license, published, nii, location, import_source]]
        vals += [self._encode(pkg_dict.get(k)) for k in self.dataset_keys]

        self.dataset_csv.writerow(vals)

        # Flatten the list
        resources = sum(resources, [])

        for resource in resources:
            # Important to include the date column for timeseries.
            date = resource.get('date', '')

            row = [pkg.name, resource['url'], resource['format'], resource.get('description', ''),
                resource['id'], resource['position'], date, organization, top_level_publisher]
            self.resource_csv.writerow(row)

    def write_header(self, dataset_keys):
        """
        Generate the header row for datasets.csv (with some preset fields) and then
        the fixed headers for resources.
        """
        dataset_header_row = [
            'Name', 'Title', 'URL', 'Organization', 'Top level organisation', 'License', 'Published', 'NII', 'Location', 'Import source'
        ]

        resource_header_row = [
            'Dataset Name', 'URL', 'Format', 'Description', 'Resource ID', 'Position', 'Date', 'Organization', 'Top level organization'
        ]

        for k in dataset_keys:
            dataset_header_row.append(self._encode(make_nice_name(k)))

        self.dataset_csv.writerow(dataset_header_row)
        self.resource_csv.writerow(resource_header_row)

    def _flatten(self, pkg):
        """
        Pull and flatten the package dict, making sure to promote any interesting
        extras we find.
        """
        pkg_dict = pkg.as_dict()
        resources = []

        new_dict = {}

        for name, value in pkg_dict.items()[:]:
            if name == 'extras' or name in IGNORE_KEYS:
                continue

            if name == 'resources':
                resources.append(value)
                continue

            if isinstance(value, (list, tuple)):
                new_dict[name] = ','.join(value)
                continue

            if isinstance(value, dict):
                for name_, value_ in value.items():
                    if name_ not in IGNORE_KEYS:
                        new_dict[name_] = value_
                continue

            new_dict[name] = value

        # Make sure all the extras we are interested in have keys
        for k in INTERESTING_EXTRAS:
            new_dict[k] = ''

        # Auto add cert fields
        new_dict['odi-certificate-url'] = ''

        # If we have values for those extras, then we should add
        # them.
        for k, v in pkg_dict['extras'].iteritems():
            # Temporary workaround for themes-secondary
            if k == 'theme-secondary' and isinstance(v, (str, unicode)):
                try:
                    d = json.loads(v)
                    if isinstance(d, list):
                        new_dict['theme-secondary'] = ', '.join(d)
                    else:
                        new_dict['theme-secondary'] = v
                    continue
                except:
                    pass

            if k == 'odi-certificate':
                self._add_cert_info(new_dict, v)
                del new_dict['odi-certificate']
            elif k in INTERESTING_EXTRAS:
                new_dict[k] = v

        return new_dict, resources

    def _add_cert_info(self, d, v):
        """
        Add the ODI Certificate URL if we have one
        """
        try:
            obj = json.loads(v)
            d['odi-certificate-url'] = obj['certificate_url']
        except:
            # Sometimes the value has no json in it. We'll
            # just pass on those.
            pass

    def close(self):
        self.dataset_file.close()
        self.resource_file.close()

        return self.dataset_filename, self.resource_filename
