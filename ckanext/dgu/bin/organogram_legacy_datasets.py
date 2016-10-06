'''
Tool for dealing with organogram datasets on data.gov.uk that have been put
there manually, over the years.
'''

import traceback
import argparse
import json
import os.path
import unicodecsv
import copy
import re
from pprint import pprint
import datetime

import timeseries_convert
from running_stats import Stats
stats_datasets = Stats()
stats_dates = Stats()
stats_res = Stats()


def main(source, source_type, save_relevant_datasets_json=False,
         dataset_filter=None, res_url_filter=None):

    if source_type == 'json':
        all_datasets = get_datasets_from_json(source)
    else:
        all_datasets = get_datasets_from_ckan(source)

    datasets = []  # legacy ones
    revamped_datasets = []  # ones created on 3rd October 2016 launch
    revamped_resources = {}
    csv_out_rows = []
    csv_corrected_rows = []
    datasets_to_delete = []
    try:
        for dataset in all_datasets:

            if dataset_filter and dataset['name'] != dataset_filter:
                continue
            if res_url_filter and \
                res_url_filter not in [r['url'] for r in dataset['resources']]:
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
            org_name = dataset['groups'][0] if dataset.get('groups') else ''

            if dataset['extras'].get('import_source', '') == 'organograms_v2':
                revamped_datasets.append(dataset)
                for res in dataset['resources']:
                    date = date_to_year_month(res['date'])
                    revamped_resources[(org_name, date)] = res
                continue
            else:
                # legacy dataset
                datasets.append(dataset)

        for dataset in datasets:
            # save csv as it has been
            save_csv_rows(csv_out_rows, dataset)

            original_dataset = copy.deepcopy(dataset)
            delete_dataset = False

            # detect dates
            for res in dataset['resources']:
                if res_url_filter and res['url'] != res_url_filter:
                    continue
                stats = timeseries_convert.add_date_to_resource(
                    res, dataset=dataset)

            # resource corrections
            resources_to_delete = []
            for res in dataset['resources']:
                if res_url_filter and res['url'] != res_url_filter:
                    continue
                resource_corrections(res, dataset, revamped_resources,
                                     org_name,
                                     resources_to_delete,
                                     stats_res)
            for res in resources_to_delete:
                dataset['resources'].remove(res)
            if not dataset['resources']:
                delete_dataset = True

            for res in dataset['resources']:
                if res_url_filter and res['url'] != res_url_filter:
                    continue
                if res['resource_type'] != 'documentation' and not res.get('date'):
                    stats_dates.add('Missing date', dataset['name'])
                    break
            else:
                stats_dates.add('Ok dates', dataset['name'])

            # update dataset TODO
            if delete_dataset:
                stats_datasets.add('Delete dataset - no resources', dataset['name'])
            elif original_dataset != dataset:
                stats_datasets.add('Updated dataset', dataset['name'])
            else:
                stats_datasets.add('Unchanged dataset', dataset['name'])

            # save csv with corrections
            save_csv_rows(csv_corrected_rows, dataset)

    except:
        traceback.print_exc()
        import pdb; pdb.set_trace()

    stats_dates.report_value_limit = 500
    print '\nDates\n', stats_dates
    print '\nDatasets\n', stats_datasets
    print '\nResources\n', stats_res

    if save_relevant_datasets_json:
        filename = 'datasets_organograms.json'
        output = json.dumps(
            datasets + revamped_datasets,
            indent=4, separators=(',', ': '),  # pretty print)
            )
        with open(filename, 'wb') as f:
            f.write(output)
        print 'Written %s' % filename

    # save csvs
    if dataset_filter or res_url_filter:
        for row in csv_corrected_rows:
            if res_url_filter and row['res_url'] != res_url_filter:
                continue
            pprint(row)
        print 'Not written csv because you specified a particular dataset'
    else:
        headers = [
            'name', 'org_name', 'notes',
            'res_name', 'res_url', 'res_date', 'res_type',
            ]
        for csv_rows, out_filename in (
                (csv_out_rows, 'organogram_legacy_datasets.csv'),
                (csv_corrected_rows, 'organogram_legacy_datasets_corrected.csv'),
                ):
            with open(out_filename, 'wb') as csv_write_file:
                csv_writer = unicodecsv.DictWriter(csv_write_file,
                                                   fieldnames=headers,
                                                   encoding='utf-8')
                csv_writer.writeheader()
                for row in sorted(csv_rows, key=lambda r: r['res_url']):
                    csv_writer.writerow(row)
            print 'Written', out_filename

def resource_corrections(res, dataset, revamped_resources, org_name,
                         resources_to_delete, stats_res):
    # e.g. "http:// http://reference.data.gov.uk/gov-structure/organogram/?pubbod=science-museum-group"
    res['url'] = res['url'].strip()
    if res['url'].startswith('http:// '):
        res['url'] = res['url'].replace('http:// ', '')
    if res['url'] == 'http://fera.co.uk/aboutUs/documents/feraOrganogramAug13.pdf':
        res['date'] = '08/2013'
        res['resource_type'] = 'file'

    # date fixes
    if dataset['name'] in ('organogram-staff-pay-passenger-focus',
                           'organogram-staff-pay-renewable-fuels-agency'):
        # clue is in a res name
        res['date'] = '20/06/2010'

    # reference.data.gov.uk deletions
    if res['url'].startswith('http://reference.data.gov.uk/gov-structure/organogram/') or re.match(r'https?:\/\/(www\.)?data.gov.uk\/organogram\/.*', res['url']):
        # e.g. http://reference.data.gov.uk/gov-structure/organogram/?pubbod=student-loans-company
        # e.g. http://www.data.gov.uk/organogram/home-office
        # duplicates existing links to organograms, so delete resource
        resources_to_delete.append(res)
        stats_res.add('Link to old viz deleted', res['url'])
        return

    # dataset deletions
    if dataset['name'] in (
            'public-roles-and-salaries',  # general CO links
            'staff-organograms-and-pay-foreign-and-commonwealth-office-30-09-2011', # no resources of interest
            ):
        resources_to_delete.append(res)
    if 'co-prod2.dh.bytemark' in res['url']:
        # test data
        resources_to_delete.append(res)
        stats_res.add('Test resource deleted', res['url'])
        return

    # date from filename
    # http://organogram.data.gov.uk/data/english-heritage/2011-09-30/300911---EH---organogram---ver1.rdf
    if not res.get('date'):
        date = re.search('\/(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})\/', res['url']) or \
            re.search('\/(?P<day>3[01])(?P<month>0[39])(?P<year>\d{2,4})-', res['url']) or \
            re.search('\/(?P<year>\d{2,4})(?P<month>0[39])(?P<day>3[01])-', res['url']) or \
            re.search('\/(?P<year>201\d)(?P<month>\d{2})(?P<day>\d{2})-', res['url'])
        if date:
            year = int(date.groupdict()['year'])
            month = int(date.groupdict()['month'])
            day = int(date.groupdict()['day'])
            if year < 16:
                year += 2000
            if year < 2009 or year > 2017:
                print stats_res.add('Invalid year', '%s %s' % (year, dataset['name']))
                import pdb; pdb.set_Trace()
            elif day in (30, 31) and month in (3, 9):
                res['date'] = '%s/%s' % (month, year)
            else:
                res['date'] = '%s/%s/%s' % (day, month, year)

    # manual fix date
    if res['url'] in (
        'https://www.gov.uk/government/uploads/system/uploads/attachment_data/file/51044/SO_20Junior_20Staff_20posts.csv',
        'https://www.gov.uk/government/uploads/system/uploads/attachment_data/file/51042/SO_20Senior_20Staff_20Salaries.csv',
        'https://www.gov.uk/government/uploads/system/uploads/attachment_data/file/51043/SO_20Senior_20Staff_20posts.csv'):
        # from temporal coverage
        res['date'] = '31/3/2011'
    if dataset['name'] == 'organogram-and-staff-pay-data-for-nerc-natural-environment-research-council':
        # assume because dataset created 17/05/2013
        res['date'] = '31/3/2013'
    if dataset['name'] == 'organogram-directly-operated-railways':
        # date is in related resources, added on same day
        res['date'] = '30/6/2010'
    if dataset['name'] == 'organogram-for-arts-council-england':
        # assume because dataset created 16/08/2013
        res['date'] = '31/3/2013'
    if dataset['name'] == 'organogram-staff-data-dstl':
        # assume because dataset created 13/06/2011
        res['date'] = '31/3/2011'
    if dataset['name'] == 'organogram-staff-pay-hs2':
        # assume because dataset created 29/11/2010
        res['date'] = '30/9/2010'
    if dataset['name'] == 'sjsm_org_pay':
        # assume because dataset created 30/11/2011
        res['date'] = '30/09/2011'
    if dataset['name'] == 'staff-organograms-and-pay-chre' and '2011' not in res['description']:
        # 2011 ones added 10 Jun 2011 and previous
        res['date'] = '30/06/2010'
    if dataset['name'] == 'staff-organograms-and-pay-chre' and '2011' in res['description']:
        # 2011 ones added 10 Jun 2011
        res['date'] = '2011'
    if dataset['name'] == 'staff-organograms-and-pay-national-employment-savings-trust':
        # assume because dataset created 22/10/2010
        res['date'] = '30/09/2010'
    if res['url'] == 'http://www.institute.nhs.uk/images//documents/About_US/Salaries/NHSI%20Organogram2.ppt':
        # added at the same time as the other res, which has a date
        res['date'] = '29/10/2010'
    if res['url'] == 'http://www.ofsted.gov.uk/sites/default/files/documents/about-ofsted/o/Ofsted%20organogram.zip':
        # res moved to additional resource manually and url changed
        resources_to_delete.append(res)
        return
    if '31 March 20111' in res['description']:
        # staff-organograms-and-pay-olympic-delivery-authority
        res['date'] = '31/03/2011'
    if dataset['name'] == 'staff-organograms-and-pay-sport-england' and res['url'] in (
            'http://www.sportengland.org/about_us/how_we_are_structured/our_executive_team/idoc.ashx?docid=aa62fe19-1527-4163-bb5d-afea1f37f86f&version=-1',
            'http://www.sportengland.org/about_us/how_we_are_structured/our_executive_team/idoc.ashx?docid=a7702ae9-e632-4578-a38e-afe6ef44867e&version=-1',
            'http://www.sportengland.org/about_us/how_we_are_structured/our_executive_team/idoc.ashx?docid=bc55a7ed-0874-4765-970d-39bbc6d6ffe7&version=-1'):
        # assume because dataset created 20/10/2010 and one of the first 4 had date 30/06/2010
        res['date'] = '30/06/2010'

    if res.get('date'):
        date = parse_date(res.get('date'))
        date_year_month = '%s-%s' % (date.year, date.month)
        revamped_res = revamped_resources.get((org_name, date_year_month))
        if revamped_res:
            if res.get('format'):
                if res['format'] == 'CSV':
                    resources_to_delete.append(res)
                    stats_res.add('duplicate period to revamp csv deleted', res['url'])
                    return
                elif res['format'] == 'RDF':
                    stats_res.add('duplicate period to revamp rdf - leave',
                                  res['url'])
                    return
                else:
                    stats_res.add('??? duplicate period to revamp non-csv/rdf',
                                  '%s %s' % (res['format'], res['url']))
                    return
            else:
                stats_res.add('??? duplicate period to revamp formatless since 2011', res['url'])
                return

    # gov.uk URLs will often be duplicates
    if re.match(r'https:\/\/www.gov.uk\/government\/(organisations|publications|uploads)\/.*', res['url']):
        # eg https://www.gov.uk/government/organisations/cabinet-office/series/cabinet-office-structure-charts
        # eg https://www.gov.uk/government/publications/bis-junior-staff-numbers-and-payscales-30-september-2012
        # eg https://www.gov.uk/government/uploads/system/uploads/attachment_data/file/11577/1920406.csv
        if res.get('date'):
            if date > datetime.datetime(2011, 1, 1):
                # this data should be in the organogram tool - TODO CHECK
                if res.get('format'):
                    if res['format'] == 'CSV':
                        resources_to_delete.append(res)
                        stats_res.add('gov.uk csv since 2011 deleted', res['url'])
                        return
                    else:
                        stats_res.add('??? gov.uk non-csv since 2011',
                                      '%s %s' % (res['format'], res['url']))
                else:
                    stats_res.add('??? gov.uk formatless since 2011', res['url'])
            elif date > datetime.datetime(2010, 1, 1):
                # this data should be in the organogram tool - TODO CHECK
                if res.get('format'):
                    if res['format'] == 'CSV':
                        resources_to_delete.append(res)
                        stats_res.add('gov.uk csv 2010 deleted', res['url'])
                        return
                    else:
                        stats_res.add('??? gov.uk non-csv 2010',
                                      '%s %s' % (res['format'], res['url']))
                else:
                    stats_res.add('??? gov.uk formatless 2010', res['url'])
            else:
                stats_res.add('gov.uk pre-2010 - keep', res['url'])
        else:
            stats_res.add('??? gov.uk but no date', res['url'])

def save_csv_rows(csv_rows, dataset):
    '''Saves the dataset to the csv_rows'''
    for res in dataset['resources']:
        csv_rows.append(dict(
            name=dataset['name'],
            org_name=dataset['groups'][0] if dataset.get('groups') else '',
            notes='',   #dataset['notes'],
            res_name=res['description'] or res['name'],
            res_url=res['url'],
            res_date=date_to_year_first(res.get('date') or ''),
            res_type=res['resource_type'],
            ))


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

def date_to_year_first(date_day_first):
    return '-'.join(date_day_first.split('/')[::-1])


def date_to_year_month(date_day_first):
    bits = date_day_first.replace('-', '/').split('/')[::-1]
    bits = [int(bit) for bit in bits]
    bits += [1] * (3 - len(bits))
    return '%s-%s' % (bits[-1], bits[-2])


def parse_date(date_day_first):
    bits = date_day_first.split('/')[::-1]
    bits = [int(bit) for bit in bits]
    bits += [1] * (3 - len(bits))
    return datetime.datetime(*bits)


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
    parser.add_argument('--res-url',
                        help='Only do it for a single resource url')

    args = parser.parse_args()
    if args.source.endswith('.json'):
        source_type = 'json'
        if not os.path.exists(args.source):
            parser.error("Error: File not found: %s" % args.source)
    else:
        source_type = 'domain'
    main(args.source, source_type, args.save_relevant_datasets_json,
         dataset_filter=args.dataset, res_url_filter=args.res_url)
