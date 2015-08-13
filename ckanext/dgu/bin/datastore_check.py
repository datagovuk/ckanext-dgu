'''
Checks that all of the resources that *should* be in the datastore, ARE
in the datastore.
'''

import collections
import common
import json
from optparse import OptionParser
from ckan import model
import ckan.plugins as p
import ckan.logic as logic
from running_stats import StatsList

from ckanext.datapusher.plugin import DEFAULT_FORMATS

stats = StatsList()


class DatastoreCheck(object):

    @classmethod
    def command(cls, config_ini):
        common.load_config(config_ini)
        common.register_translator()

        rev = model.repo.new_revision()

        nii_dataset_q = model.Session.query(model.Package)\
            .join(model.PackageExtra, model.PackageExtra.package_id == model.Package.id)\
            .filter(model.PackageExtra.key == 'core-dataset')\
            .filter(model.PackageExtra.value == 'true')\
            .filter(model.Package.state == 'active')

        info_func = p.toolkit.get_action('datastore_info')
        site_user = p.toolkit.get_action('get_site_user')({'model': model,'ignore_auth': True}, {})
        ctx = {'model': model, 'session': model.Session, 'ignore_auth': True, 'user': site_user['name']}


        result = collections.defaultdict(list)
        expected = collections.defaultdict(int)

        total_resources = 0
        for pkg in nii_dataset_q:
            if pkg.extras.get('unpublished', False):
                continue

            resources = pkg.resources
            if not resources:
                continue

            for resource in resources:
                # Check format to save time ...
                if not resource.format.lower() in DEFAULT_FORMATS:
                    continue

                expected[pkg] = expected[pkg] + 1
                total_resources += 1

                # Resource SHOULD be in the datastore
                try:
                    res = info_func(ctx, {'id': resource.id})
                    stats.add("Resource in datastore", resource.id)

                    result[pkg].append(res)
                except logic.NotFound:
                    stats.add("Resource not in datastore", resource.id)


        #stats.add('Deleting empty string', package.name)
        print "\tTotal viable resources: {}".format(total_resources)
        print ""
        print stats.report()
        print ""
        for pkg, v in result.iteritems():
            print pkg.name, len(v), "out of", expected[pkg]


usage = __doc__ + '''
Usage:
    python datastore_check.py <CKAN config ini filepath>'''

if __name__ == '__main__':
    parser = OptionParser(usage=usage)
    (_, args) = parser.parse_args()
    if len(args) != 1:
        parser.error('Wrong number of arguments')
    config_ini = args[0]
    DatastoreCheck.command(config_ini)
