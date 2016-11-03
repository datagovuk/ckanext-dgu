"""
Set the resource.format from the QA value for these resources:
* where the resource.format is empty (or just whitespace)
* where resource.format is not a poor one and QA is most likely more accurate

This will trigger an archive/packagezip/qa cycle, so should not be used too
frequently.
"""
from sqlalchemy.exc import IntegrityError
from optparse import OptionParser

from ckan.logic import ValidationError
from ckanext.dgu.bin import common
from running_stats import Stats

res_stats = Stats()
ds_stats = Stats()

UPDATE_FORMATS = {
    'CSV / ZIP': 'CSV',  # legacy - we now drop mention of the zip
    'XML': set((
        'WFS',  # previously we set UKLP WFS resources as XML but we can detect WFS now
        'Atom Feed',
        'SHP',
        'WCS',
        'WMTS',
        )),
    'DBASE': 'SHP',
    'ZIP': 'SHP',
    }


class SetResourceFormatsCommand(object):

    def __init__(self, config_or_url):
        self.ckan = common.get_ckanapi(config_or_url)

    def update_resource_dict(self, resource, qa_info,
                             res_nice_name):
        """
        Set the format on the resource to the format determined by QA.
        Returns whether it was changed or not.
        """
        existing_format = resource['format'] or '(blank)'
        resource['format'] = qa_info['format']
        print res_stats.add(
            'Updating format %s to %s' %
            (existing_format, qa_info['format']),
            res_nice_name)
        # Resource was changed
        return True

    def run(self, options):
        """ Iterate over datasets and process the resources """

        if not options.write:
            print "NOT writing package as -w was not specified"

        datasets = common.get_datasets_via_api(self.ckan, options=options)

        for pkg in datasets:
            pkg_updated = False

            resources = pkg['resources']
            # pkg has resources duplicated between 'resources' key and the trio
            # of keys but when you do package_update you should only have it in
            # the trio.
            if 'individual_resources':
                resources = pkg.get('individual_resources', []) + \
                    pkg.get('timeseries_resources', []) + \
                    pkg.get('additional_resources', [])
                del pkg['resources']

            for resource in resources:
                res_updated = False
                del resource['revision_id']
                res_nice_name = '%s:%s' % (pkg['name'], resource['id'][:4])

                qa_info = resource.get('qa')
                if not qa_info:
                    res_stats.add('QA not run yet on this resource',
                                  res_nice_name)
                    continue
                try:
                    qa_info = eval(qa_info)
                except ValueError:
                    print res_stats.add('QA not a dict', res_nice_name)
                    print repr(qa_info)
                    continue
                if not qa_info.get('format', ''):
                    res_stats.add("QA format empty", res_nice_name)
                    continue

                format_ = resource['format'].strip()
                if format_ == '':
                    res_updated = self.update_resource_dict(
                        resource, qa_info, res_nice_name)
                elif format_.upper() in UPDATE_FORMATS and \
                        (qa_info['format'] == UPDATE_FORMATS[format_.upper()]
                         or
                         qa_info['format'] in UPDATE_FORMATS[format_.upper()]):
                    res_updated = self.update_resource_dict(
                        resource, qa_info, res_nice_name)
                else:
                    res_stats.add('Format already ok', res_nice_name)
                pkg_updated |= res_updated

            if pkg_updated:
                # Prepare pkg to be written
                # Removing the codelist or schema here does NOT remove it
                # during package_update as they are in the extras Removing
                # last_major_modification - legacy field
                for k in ['last_major_modification', 'schema', 'codelist']:
                    if k in pkg:
                        del pkg[k]

                if 'tags' in pkg and pkg['tags']:
                    newtags = []
                    for t in pkg['tags']:
                        newtags.append({'name': t['name']})

                    pkg['tags'] = newtags
                if options.write:
                    try:
                        self.ckan.action.package_update(**pkg)
                        ds_stats.add('Dataset updated', pkg['name'])
                    except ValidationError, ve:
                        print ds_stats.add('Validation error on update',
                                           pkg['name'])
                        print ve
                    except IntegrityError:
                        print ds_stats.add('Integrity error on update',
                                           pkg['name'])
                else:
                    ds_stats.add('Dataset would be updated', pkg['name'])
            else:
                ds_stats.add('No change', pkg['name'])
        print '\nResources:\n', res_stats.report(show_time_taken=True)
        print '\nDatasets:\n', ds_stats.report(show_time_taken=True)


usage = __doc__ + '''
Usage:
    python set_missing_resource_formats.py <CKAN config.ini or URL> [-d DATASET_NAME] [-o ORGANISATION_NAME] -w'''

if __name__ == '__main__':
    parser = OptionParser(usage=usage)
    parser.add_option('-d', '--dataset', dest='dataset')
    parser.add_option('-o', '--organization', dest='organization')
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
