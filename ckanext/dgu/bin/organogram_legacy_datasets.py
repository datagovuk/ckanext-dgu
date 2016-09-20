'''
Tool for dealing with organogram datasets on data.gov.uk that are put have been put there manually, over the years.
'''

import traceback
import argparse
import json
import os.path

import timeseries_convert
from running_stats import Stats
stats_datasets = Stats()
stats_dates = Stats()


def main(source, source_type, save_relevant_datasets_json=False,
         dataset_filter=None):

    if source_type == 'json':
        all_datasets = get_datasets_from_json(source)
    else:
        all_datasets = get_datasets_from_ckan(source)

    datasets = []
    try:
        for dataset in all_datasets:

            if dataset_filter and dataset['name'] != dataset_filter:
                continue

            # check it an organogram dataset
            dataset_str = repr(dataset).lower()
            if 'rganog' not in dataset_str \
                    and 'roles and salaries' not in dataset_str \
                    and 'pay and post' not in dataset_str \
                    and 'posts and pay' not in dataset_str:
                stats_datasets.add('Ignored dataset', dataset['name'])
                continue
            #print dataset['title']
            datasets.append(dataset)
            stats_datasets.add('Organogram dataset', dataset['name'])

            stats = timeseries_convert.add_date_to_resources(
                dataset['resources'], dataset=dataset)
            if stats.get('Could not find date'):
                print dataset['name']
                print stats['Could not find date']
                print
                stats_dates.add('Missing dates', dataset['name'])
            else:
                stats_dates.add('Dates found', dataset['name'])

    except:
        traceback.print_exc()
        import pdb; pdb.set_trace()

    print stats_datasets
    print stats_dates

    if save_relevant_datasets_json:
        filename = 'datasets_organograms.json'
        output = json.dumps(
            datasets,
            indent=4, separators=(',', ': '),  # pretty print)
            )
        with open(filename, 'wb') as f:
            f.write(output)
        print 'Written %s' % filename


def get_datasets_from_json(filepath):
    dataset_str = ''
    with open(filepath, 'rb') as f:
        while True:
            line = f.readline()
            if line == '[\n':
                continue
            if line in (']\n', ''):
                break
            dataset_str += line
            if line == '    },\n' or line == '    }\n':
                try:
                    yield json.loads(dataset_str.rstrip(',\n'),
                                     encoding='utf8')
                except Exception:
                    traceback.print_exc()
                    import pdb; pdb.set_trace()
                dataset_str = ''


def get_datasets_from_ckan(domain):
    common.load_config(config_ini)
    common.register_translator()

    from pylons import config
    apikey = config['dgu.merge_datasets.apikey']
    ckan = ckanapi.RemoteCKAN('https://%s' % domain, apikey=apikey)
    datasets = ckan.action.package_search(q='organogram', rows=400)
    return datasets


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',
                        help='Either the filepath of the JSON dump of '
                        'data.gov.uk or the domain of the ckan site to work '
                        'with')
    parser.add_argument('--save-relevant-datasets-json',
                        action='store_true',
                        help='Saves a JSON file of just the organogram '
                        'datasets')
    parser.add_argument('--dataset',
                        help='Only do it for a single dataset name')
    args = parser.parse_args()
    if args.source.endswith('.json'):
        source_type = 'json'
        if not os.path.exists(args.source):
            parser.error("Error: File not found: %s" % args.source)
    else:
        source_type = 'domain'
    main(args.source, source_type, args.save_relevant_datasets_json,
         dataset_filter=args.dataset)
