import sys
from optparse import OptionParser

import common
from running_stats import Stats


class Deleter(object):

    @classmethod
    def parse_file(cls, filepath):
        with open(filepath, 'r') as f:
            content = f.read()
        datasets = []
        for chunk in content.split():
            chunk = chunk.strip().strip(',')
            if chunk:
                datasets.append(chunk)
        print 'File contained %s dataset names' % len(datasets)
        return datasets

    @classmethod
    def run(cls, config_ini_or_ckan_url, dataset_names):
        ckan = common.get_ckanapi(config_ini_or_ckan_url)

        stats = Stats()
        for dataset_name in dataset_names:
            dataset_name = common.name_stripped_of_url(dataset_name)
            try:
                ckan.call_action('dataset_delete',
                                 {'id': dataset_name})
                print stats.add('Deleted (or was already deleted)', dataset_name)
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception, e:
                if 'CKANAPIError' in str(e):
                    print e
                    print 'Not calling API correctly - aborting'
                    sys.exit(1)
                print stats.add('Error %s' % type(e).__name__,
                                '%s %s' % (dataset_name, e))

        print '\nSummary:\n', stats

usage = '''
Bulk deletion of datasets, with a list of datasets specified on the command-line or in a text file.

    python delete_bulk.py {<CKAN config ini filepath>|data.gov.uk} [-f datasets.txt] [<dataset_name_1> <dataset_name_2> ...]
'''.strip()

if __name__ == '__main__':
    parser = OptionParser(usage=usage)
    parser.add_option('-f', '--file', dest='filepath', metavar='FILE',
                      help='File path containing datasets listed')

    (options, args) = parser.parse_args()
    if len(args) < 1:
        parser.error('Need at least 1 arguments')
    config_ini = args[0]
    datasets = args[1:]
    if options.filepath:
        datasets += Deleter.parse_file(options.filepath)
    if not datasets:
        parser.error('No datasets specified')
    Deleter.run(config_ini, dataset_names=datasets)
