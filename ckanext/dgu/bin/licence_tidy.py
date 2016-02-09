"""
Dataset licenses improved
* Merge anchor into a single free text 'licence' extra
* 'licence' extra is str rather than JSON-like
* If 'licence' extra mentions OGL then set license_id to OGL in addition
* Free text in license_id moved to 'licence' extra

https://github.com/datagovuk/ckanext-dgu/issues/348
"""
import ast
from optparse import OptionParser
import copy

from sqlalchemy.exc import IntegrityError

from ckan.logic import ValidationError
from ckanext.dgu.bin import common
from ckanext.dgu.lib import helpers as dgu_helpers
from running_stats import Stats

stats = Stats()
ckan_license_ids = None


class LicenceTidy(object):

    def __init__(self, config_or_url):
        self.ckan = common.get_ckanapi(config_or_url)

    def run(self, options):
        """ Iterate over datasets and tidy """

        if not options.write:
            print "NOT writing package as -w was not specified"

        datasets = common.get_datasets_via_api(self.ckan, options=options)

        for dataset in datasets:
            dataset, is_dataset_updated = self.get_tidied_dataset(dataset)

            if is_dataset_updated:
                # Prepare pkg to be written
                del dataset['resources']
                for resource in (dataset.get('individual_resources', []) +
                                 dataset.get('timeseries_resources', []) +
                                 dataset.get('additional_resources', [])):
                    del resource['revision_id']
                    # some resources got in (dcat harvester) with a name
                    # instead of a description. This fails validation, so swap
                    # it
                    if not resource['description'] and resource['name']:
                        resource['description'] = resource['name']
                        resource['name'] = ''

                # Removing the codelist or schema here does NOT remove it
                # during package_update as they are in the extras Removing
                # last_major_modification - legacy field
                for k in ['last_major_modification', 'schema', 'codelist']:
                    if k in dataset:
                        del dataset[k]

                if 'tags' in dataset and dataset['tags']:
                    newtags = []
                    for t in dataset['tags']:
                        newtags.append({'name': t['name']})

                    dataset['tags'] = newtags
                if options.write:
                    try:
                        self.ckan.action.package_update(**dataset)
                        print stats.add('Dataset updated', dataset['name'])
                    except ValidationError, ve:
                        print stats.add('Validation error on update',
                                        dataset['name'])
                        print ve
                    except IntegrityError:
                        print stats.add('Integrity error on update',
                                        dataset['name'])
                else:
                    stats.add('Dataset would be updated', dataset['name'])
            else:
                stats.add('No change', dataset['name'])
        print '\nDatasets:\n', stats.report(show_time_taken=True)

    def get_tidied_dataset(self, dataset):
        is_dataset_updated = False
        license_id = dataset['license_id'] or ''
        extras = dict((extra['key'], extra['value'])
                      for extra in dataset['extras'])
        licence = extras.get('licence') or ''

        if licence:
            # INSPIRE datasets are a python list repr'd
            # ast.literal_eval() is safer than eval()
            try:
                licence_bits = ast.literal_eval(licence) or []
                is_dataset_updated = True
            except (ValueError, SyntaxError):
                licence_bits = [licence]
        else:
            licence_bits = []

        # merge in anchor
        anchor_href = extras.get('licence_url')
        anchor_title = extras.get('licence_url_title')
        if anchor_href and anchor_title:
            licence_bits.append('%s - %s' % (anchor_title, anchor_href))
        elif anchor_href:
            licence_bits.append('%s' % anchor_href)
        elif anchor_title:
            licence_bits.append('%s' % anchor_title)

        # free text in license_id moved to licence
        global ckan_license_ids
        if not ckan_license_ids:
            ckan_licenses = self.ckan.action.license_list()
            ckan_license_ids = [l['id'] for l in ckan_licenses]
        if license_id and license_id not in ckan_license_ids:
            licence_bits.append(license_id)
            license_id = ''

        # licence is str not JSON-like list
        licence = '; '.join(licence_bits) or None

        # detect if OGL is in there
        if licence:
            license_id, licence = \
                dgu_helpers.get_licence_fields_from_free_text(licence)

        # update the dataset fields
        updated_dataset = copy.deepcopy(dataset)
        if license_id != updated_dataset['license_id']:
            # don't mark it as an update if only changing the license from ''
            # to None as this will not be saved on package_update if it is the
            # only thing
            if (updated_dataset['license_id'] and
                    updated_dataset['license_id'] != 'None' and
                    license_id):
                is_dataset_updated = True
            updated_dataset['license_id'] = license_id
        if extras.get('licence') != licence:
            if licence:
                set_extra(updated_dataset, 'licence', licence)
            else:
                del_extra(updated_dataset, 'licence')
            is_dataset_updated = True
        extras_to_delete = \
            set(('licence_url', 'licence_url_title')) & set(extras.keys())
        for key in extras_to_delete:
            del_extra(updated_dataset, key)
            is_dataset_updated = True

        return updated_dataset, is_dataset_updated


def set_extra(dataset, key, value):
    for extra in dataset['extras']:
        if extra['key'] == key:
            extra['value'] = value
            return
    dataset['extras'].append({'key': key, 'value': value})


def del_extra(dataset, key):
    for extra in dataset['extras']:
        if extra['key'] == key:
            dataset['extras'].remove(extra)
            return


usage = __doc__ + '''
Usage:
    python licence_tidy.py <CKAN config.ini or URL> [options]'''

if __name__ == '__main__':
    parser = OptionParser(usage=usage)
    parser.add_option('-d', '--dataset', dest='dataset')
    parser.add_option('-o', '--organization', dest='organization')
    parser.add_option('-w', '--write', dest='write',
                      action='store_true',
                      help='write the changes to the datasets')
    parser.add_option('--use-case-datasets', dest='use_case_datasets',
                      action='store_true',
                      help='Tidy only the particular datasets in the use '
                      'cases')
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error('Wrong number of arguments')
    if options.use_case_datasets:
        options.dataset = [
            'mot-active-vts',
            'ukcp09-gridded-monthly-values-mean-wind-speed',
            'basic-company-data',
            'admissions-timeline',
            'uk-postcodes',
            'lidar-composite-dsm-1m1',
            'national-address-gazetteer',
            'historic-flood-map1',
            'conservation-areas',
            'local-nature-partnerships',
            'soil-properties-and-soil-greenhouse-gas-emissions-in-biochar-amended-bioenergy-soils-undergoing1',
            ]
    config_ini = args[0]
    cmd = LicenceTidy(config_ini)
    cmd.run(options)
