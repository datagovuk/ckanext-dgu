'''
Returns a random sample of datasets and one of their resources
'''
import argparse
import random

import unicodecsv
import requests_cache
import ckanapi
import progressbar

from running_stats import Stats

args = None

one_day = 60 * 60 * 24
one_month = one_day * 30
requests_cache.install_cache('.email_extract_cache', expire_after=one_month)
ckan = ckanapi.RemoteCKAN('https://data.gov.uk', get_only=True)

def run():
    all_dataset_names = ckan.action.package_list()
    random.seed(args.seed)
    tried_dataset_names = set()
    selected_datasets = []
    bar = progressbar.ProgressBar(maxval=args.number).start()
    stats = Stats()
    while True:
        # pick dataset that's not been tried before
        if len(selected_datasets) >= args.number:
            break
        bar.update(len(selected_datasets))
        dataset_name = None
        attempts_to_find_new_dataset = 0
        while not dataset_name or dataset_name in tried_dataset_names:
            dataset_name = random.choice(all_dataset_names)
            attempts_to_find_new_dataset += 1
            if attempts_to_find_new_dataset > 1000:
                print '** GIVING UP finding datasets **'
                break

        # see if the dataset matches the filter
        tried_dataset_names.add(dataset_name)
        dataset = ckan.action.package_show(id=dataset_name)
        resources = dataset['resources']
        if len(resources) == 0:
            stats.add('No resources', dataset_name)
            continue
        if args.resource_type != 'all':
            if args.resource_type == 'data':
                resources = [
                    res for res in resources
                    if res.get('resource_type') in ('file', 'api', None)
                ]
            elif args.resource_type == 'additional':
                resources = [
                    res for res in resources
                    if res.get('resource_type') == 'documentation'
                ]
            else:
                raise NotImplementedError()
        if len(resources) == 0:
            stats.add('No resources of type %s' % args.resource_type,
                            dataset_name)
            continue
        resource = random.choice(resources)

        # success - dataset is picked
        selected_datasets.append((dataset, resource))
        stats.add('Selected dataset', dataset_name)
    bar.finish()

    print '\n\nFinding dataset resources\n', stats

    # save the results
    headers = ['dataset_name', 'dataset_url',
               'resource_id', 'resource_name',
               'resource_date', 'resource_url']
    out_rows = []
    for dataset, resource in sorted(selected_datasets,
                                    key=lambda d: d[0]['name']):
        res_date = resource.get('date') or ''
        if res_date:
            res_date = "'" + res_date
        out_rows.append(dict(
            dataset_name=dataset['name'],
            dataset_url='https://data.gov.uk/dataset/%s' % dataset['name'],
            resource_id=resource['id'],
            resource_name=' '.join(
                [r for r in resource.get('name'), resource.get('description'),
                 if r] or ''),
            resource_date=res_date,
            resource_url=resource['url'],
            ))
    out_filename = 'random_resources.csv'
    with open(out_filename, 'wb') as csv_write_file:
        csv_writer = unicodecsv.DictWriter(csv_write_file,
                                           fieldnames=headers,
                                           encoding='utf-8')
        csv_writer.writeheader()
        for row in out_rows:
            csv_writer.writerow(row)
    print 'Written %s' % out_filename

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed',
                        default=None,
                        help='Seed for the random number generator. Pick a number to make the choice repeatable. Default uses the system clock.')
    parser.add_argument('-n', '--number',
                        default=500,
                        type=int,
                        help='Size of the sample')
    parser.add_argument('--resource-type',
                        default='data',
                        choices=['data', 'additional', 'all'],
                        help='Size of the sample')
    args = parser.parse_args()
    run()
