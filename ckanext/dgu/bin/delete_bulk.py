import sys
from argparse import ArgumentParser
import traceback
import re

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

def prompt_for_datasets():
    datasets = []
    while True:
        msg = '\nEnter dataset names/urls. Commands: view, delete. %s datasets so far\n> ' % len(datasets)
        response = raw_input(msg)
        if response.lower() == 'view':
            for dataset in datasets:
                print '   ', dataset
            continue
        elif response.lower() == 'delete':
            return datasets
        else:
            try:
                response_datasets = \
                    re.findall(r'\b(?:https://data.gov.uk/dataset/)?([^\s]+)',
                               response)
            except Exception, e:
                traceback.print_exc()
                import pdb; pdb.set_trace()
            duplicates = set(response_datasets) & set(datasets)
            if duplicates:
                print 'Discarding %s duplicates eg %s' % (
                    len(duplicates), list(duplicates)[0])
            count = 0
            for response_dataset in response_datasets:
                if response_dataset not in duplicates:
                    datasets.append(response_dataset)
                    count += 1
            print 'Added %s dataset(s)' % count

    return datasets

usage = '''
Bulk deletion of datasets, with a list of datasets specified on the command-line, a text file or failing that it prompts for them.

    python delete_bulk.py {<CKAN config ini filepath>|https://data.gov.uk} [-f datasets.txt] [<dataset_name_1> <dataset_name_2> ...]
'''.strip()

if __name__ == '__main__':
    parser = ArgumentParser(usage=usage)
    parser.add_argument('config_ini_or_ckan_url')
    parser.add_argument('-f', '--file', dest='filepath', metavar='FILE',
                        help='File path containing datasets listed')
    parser.add_argument('datasets', nargs='*', help='Dataset names')

    args = parser.parse_args()
    datasets = args.datasets
    if args.filepath:
        datasets += Deleter.parse_file(args.filepath)

    if not datasets:
        datasets = prompt_for_datasets()
    Deleter.run(args.config_ini_or_ckan_url, dataset_names=datasets)
