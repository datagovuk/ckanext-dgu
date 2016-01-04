"""
For those resources that do not have valid formats (i.e. empty, or just whitespace), this
script will set the value from the QA object that was previously created.

This will trigger an archive/packagezip/qa cycle, so should not be used too frequently.
"""
from sqlalchemy.exc import IntegrityError
from pprint import pprint
import ckan.plugins.toolkit as t
from optparse import OptionParser

from ckan.logic import ValidationError
from ckanext.dgu.bin.common import get_ckanapi
from running_stats import Stats

stats = Stats()
ds_stats = Stats()

class SetResourceFormatsCommand(object):

    def __init__(self, config_or_url):
        self.ckan = get_ckanapi(config_or_url)

    def update_resource_dict(self, resource):
        """ Set the format on the resource to the format determined by QA """
        try:
            qa_info = self.ckan.action.qa_resource_show(id=resource['id'])
            if qa_info.get('format', ''):
                resource['format'] = qa_info['format']
                stats.add("Updating format to %s" % qa_info['format'], resource['id'])
        except t.ObjectNotFound:
            # No QA yet
            return False

        # Resource was changed
        return True

    def run(self, options):
        """ Iterate over datasets and process the resources """

        # Create a function to get a list of dataset names to work with
        get_datasets_fn = self.ckan.action.package_list
        if options.dataset:
            get_datasets_fn = lambda: [options.dataset]

        if not options.write:
            print "NOT writing package as -w was not specified"


        # For each dataset, get resources and process those with no format.
        for pkg_name in get_datasets_fn():
            updated = False

            pkg = self.ckan.action.package_show(id=pkg_name)
            resources = pkg['resources']
            if 'individual_resources':
                resources = pkg.get('individual_resources', []) + \
                    pkg.get('timeseries_resources', []) + \
                    pkg.get('additional_resources', [])
                del pkg['resources']

            for resource in resources:
                del resource['revision_id']
                if resource['format'].strip() == '':
                    if self.update_resource_dict(resource):
                        updated = True
                        resource['format']


            # Removing the codelist or schema here does remove it during package_update
            # Removing last_major_modification is calculated on write.
            for k in ['last_major_modification', 'schema', 'codelist']:
                if k in pkg:
                    del pkg[k]

            if 'tags' in pkg and pkg['tags']:
                newtags = []
                for t in pkg['tags']:
                    newtags.append({'name': t['name']})

                pkg['tags'] = newtags

            if updated:
                if options.write:
                    try:
                        self.ckan.action.package_update(**pkg)
                        ds_stats.add("Packages updated", pkg['id'])
                    except ValidationError, ve:
                        print "DATASET: %s had a validation error: %s" % (pkg['name'], str(ve), )
                    except IntegrityError, ie:
                        print "Integrity error in", pkg['name']
        print stats.report(show_time_taken=True)
        print ds_stats.report(show_time_taken=True)


usage = __doc__ + '''
Usage:
    python set_missing_resource_formats.py <CKAN config ini filepath> [-d DATASET_ID/NAME]  -w'''

if __name__ == '__main__':
    parser = OptionParser(usage=usage)
    parser.add_option('-d', '--dataset', dest='dataset')
    parser.add_option("-w", "--write",
                      action="store_true",
                      dest="write",
                      default=False,
                      help="write the changes to the datasets")
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error('Wrong number of arguments')
    config_ini = args[0]
    cmd = SetResourceFormatsCommand(config_ini)
    cmd.run(options)
