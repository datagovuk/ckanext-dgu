'''
Import ALL the resources to the datastore, or at least try
'''

import common
import json
from optparse import OptionParser
from ckan import model
import ckan.plugins as p
import ckan.logic as logic
from running_stats import StatsList

from ckanext.datapusher.plugin import DEFAULT_FORMATS

stats = StatsList()


class DatastoreImport(object):

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

        submit_func = p.toolkit.get_action('datapusher_submit')
        site_user = p.toolkit.get_action('get_site_user')({'model': model,'ignore_auth': True}, {})
        ctx = {'model': model, 'session': model.Session, 'ignore_auth': True, 'user': site_user['name']}

        for pkg in nii_dataset_q:
            if pkg.extras.get('unpublished', False):
                continue

            resources = pkg.resources
            if not resources:
                stats.add("Skipping NII package with no resources", pkg.name)
                continue

            for resource in resources:
                # Check format to save time ...
                if not resource.format.lower() in DEFAULT_FORMATS:
                    stats.add("Invalid format", resource.id)
                    continue

                try:
                    submit_func(ctx, {"resource_id": resource.id})
                except logic.ValidationError:
                    stats.add("Submission failed with validation error", resource.id)
                else:
                    stats.add("Processed resource successfully", resource.id)

        #stats.add('Deleting empty string', package.name)
        print stats.report()
        print '*' * 30
        print '\n'.join(stats['Processed resource successfully'])


usage = __doc__ + '''
Usage:
    python datastore_import.py <CKAN config ini filepath>'''

if __name__ == '__main__':
    parser = OptionParser(usage=usage)
    (_, args) = parser.parse_args()
    if len(args) != 1:
        parser.error('Wrong number of arguments')
    config_ini = args[0]
    DatastoreImport.command(config_ini)
