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
        self.dataset_file  = tempfile.NamedTemporaryFile(delete = False)
        self.resource_file = tempfile.NamedTemporaryFile(delete = False)

        self.dataset_csv  = csv.writer(self.dataset_file)
        self.resource_csv = csv.writer(self.resource_file)

        self.dataset_filename  = self.dataset_file.name
        self.resource_filename = self.resource_file.name

        self.organization_cache = {}

        self.keys = []

    def dump(self, limit=None):
        packages = model.Session.query(model.Package)\
            .filter(model.Package.state == 'active')\
            .filter(model.Package.private == False )
        if limit:
            packages = packages.limit(limit)

        first = True
        for pkg in packages.yield_per(200):
            self.write_object(pkg, first)
            first = False

    def write_object(self, pkg, first=False):
        pkg_dict, resources = self._flatten(pkg)
        keys = sorted(pkg_dict.keys())

        if first:
            self.write_header(keys)

        url = config.get('ckan.site_url')
        full_url = urlparse.urljoin(url, '/dataset/%s' % pkg.name)

        organization = self.organization_cache.get(pkg.owner_org)
        if not organization:
            org = model.Group.get(pkg.owner_org)
            organization = org.title
            self.organization_cache[pkg.owner_org] = organization

        def encode(s):
            if not s:
                return u''
            if isinstance( s, (str, unicode)):
                return s.encode('utf-8')
            return unicode(s)

        vals = [pkg.name, pkg.title, full_url, organization] + \
            [encode(pkg_dict[k]) for k in keys]

        self.dataset_csv.writerow(vals)

        # Flatten the list
        resources = sum(resources, [])

        for resource in resources:
            row = [pkg.name, resource['url'], resource['format'], resource.get('description', '') ]
            self.resource_csv.writerow(row)

    def write_header(self, keys):
        """
        Generate the header row for datasets.csv (with some preset fields) and then
        the fixed headers for resources.
        """
        header_row = [
            'ID', 'Title', 'URL', 'Organization'
        ]

        for k in keys:
            header_row.append(make_nice_name(k))

        self.dataset_csv.writerow(header_row)
        self.resource_csv.writerow(['Dataset ID', 'URL', 'Format', 'Description'])

    def _flatten(self, pkg):
        """
        Pull and flatten the package dict, making sure to promote any interesting
        extras we find.
        """
        pkg_dict = pkg.as_dict()
        resources = []

        new_dict = {}

        for name, value in pkg_dict.items()[:]:
            if name == 'extras' or  name in IGNORE_KEYS:
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

    def _add_cert_info(self, d ,v):
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



