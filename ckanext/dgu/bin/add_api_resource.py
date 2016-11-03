''' Tool that reads a CSV file containing the resource
details to be created and for which dataset.

The columns are dataset_name, description, url and name
of the resource will always be "Data API".

'''
import collections
import csv

from ckanext.dgu.bin import common
from optparse import OptionParser

def add_api_resources(csv_input):
    from ckan import model
    from ckan.logic import get_action

    ctx = { 'model': model, 'session': model.Session, 'ignore_auth': True }

    site_user = get_action("get_site_user")(ctx, {})
    ctx['user'] = site_user['name']

    reader = csv.DictReader(open(csv_input, "r"))
    for row in reader:
        pkgname = row['dataset']

        print "Processing", pkgname
        package = get_action('package_show')(ctx, {'id': pkgname})

        resources = package['resources'][:]
        print "  - %d resources" % len(resources)

        for resource in resources:
            if resource['url'] == row['url'] \
                    and resource['format'].lower() == 'api':
                print "  API Resource already exists"
                break

        resource = {
            u'description': row['description'],
            'url': row['url'],
            'format': 'API',
            'position': 0
        }
        resources.append(resource)

        package['resources'] = resources
        package['codelist'] = [c['id'] for c in package.get('codelist', [])]
        package['schema'] = [s['id'] for s in package.get('schema', [])]
        res = get_action('package_update')(ctx, package)
        assert res['name'] == pkgname

if __name__ == '__main__':
    usage = __doc__ + """
usage:

%prog <api.csv> <ckan.ini>
"""
    parser = OptionParser(usage=usage)
    (options, args) = parser.parse_args()
    if len(args) != 2:
        parser.error('Wrong number of arguments (%i)' % len(args))
    csv_filepath, config_filepath = args
    print 'Loading CKAN config...'
    common.load_config(config_filepath)
    common.register_translator()
    add_api_resources(csv_filepath)
