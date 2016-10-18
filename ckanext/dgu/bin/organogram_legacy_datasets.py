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
from collections import defaultdict

from paste.deploy.converters import asbool

import common
import timeseries_convert
from running_stats import Stats
stats_datasets = Stats()
stats_merge = Stats()
stats_dates = Stats()
stats_res = Stats()


def main(source, source_type, destination,
         save_relevant_datasets_json,
         write,
         dataset_filter=None, res_url_filter=None):

    if source_type == 'json':
        all_datasets = get_datasets_from_json(source)
    elif source_type == 'jsonl':
        all_datasets = get_datasets_from_jsonl(source)
    else:
        all_datasets = get_datasets_from_ckan(source)

    datasets = []  # legacy ones
    revamped_datasets = []  # ones created on 3rd October 2016 launch
    revamped_datasets_by_org = {}
    revamped_resources = {}
    csv_out_rows = []
    csv_corrected_rows = []
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
                    and 'posts and pay' not in dataset_str \
                    and 'organisation chart' not in dataset_str \
                    and 'organization chart' not in dataset_str \
                    and 'org chart' not in dataset_str:
                stats_datasets.add('Ignored - not organograms',
                                   dataset['name'])
                continue
            if dataset['name'] in (
                    'eastbourne-borough-council-public-toilets',
                    'staff-organograms-and-pay-government-offices',
                    ) \
                    or dataset['id'] in (
                        '47f69ebb-9939-419f-880d-1b976676cb0e',
                    ):
                stats_datasets.add('Ignored - not organograms',
                                   dataset['name'])
                continue
            if asbool(dataset.get('unpublished')):
                stats_datasets.add('Ignored - unpublished',
                                   dataset['name'])
                continue
            extras = dict((extra['key'], extra['value'])
                          for extra in dataset['extras'])
            if extras.get('import_source') == 'harvest':
                stats_datasets.add('Ignored - harvested so can\'t edit it',
                                   dataset['name'])
                continue
            org_id = dataset['owner_org']

            if extras.get('import_source') == 'organograms_v2':
                revamped_datasets.append(dataset)
                assert org_id not in revamped_datasets_by_org, org_id
                revamped_datasets_by_org[org_id] = dataset
                for res in dataset['resources']:
                    date = date_to_year_month(res['date'])
                    revamped_resources[(org_id, date)] = res
                continue
            else:
                # legacy dataset
                datasets.append(dataset)

        if save_relevant_datasets_json:
            filename = 'datasets_organograms.json'
            if not (dataset_filter or res_url_filter):
                output = json.dumps(
                    datasets + revamped_datasets,
                    indent=4, separators=(',', ': '),  # pretty print)
                    )
                with open(filename, 'wb') as f:
                    f.write(output)
                print 'Written %s' % filename
            else:
                print 'Not written %s because you filtered by a ' \
                    'dataset/resource' % filename

        all_resource_ids_to_delete = defaultdict(list)  # dataset_name: res_id_list
        dataset_names_to_delete = set()
        for dataset in datasets:
            org_id = dataset['owner_org']

            # save csv as it has been
            save_csv_rows(csv_out_rows, dataset, None, None)

            original_dataset = copy.deepcopy(dataset)
            delete_dataset = False

            dataset_to_merge_to = \
                get_dataset_to_merge_to(dataset, revamped_datasets_by_org)

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
                resource_corrections(res, dataset, extras,
                                     revamped_resources,
                                     revamped_datasets_by_org,
                                     dataset_to_merge_to,
                                     org_id,
                                     resources_to_delete,
                                     stats_res)
            for res in resources_to_delete:
                dataset['resources'].remove(res)
            if not dataset['resources']:
                delete_dataset = True
            elif resources_to_delete and not dataset_to_merge_to:
                all_resource_ids_to_delete[dataset['name']].extend(
                    res['id'] for res in resources_to_delete)
            org_id = dataset['owner_org']  # it might have changed

            for res in dataset['resources']:
                if res_url_filter and res['url'] != res_url_filter:
                    continue
                if res.get('resource_type') != 'documentation' and not res.get('date'):
                    stats_dates.add('Missing date', dataset['name'])
                    break
            else:
                stats_dates.add('Ok dates', dataset['name'])

            # record changes
            if delete_dataset:
                stats_datasets.add('Delete dataset - no resources', dataset['name'])
                dataset_names_to_delete.add(dataset['name'])
                continue
            elif original_dataset != dataset:
                stats_datasets.add('Updated dataset', dataset['name'])
                has_changed = True
            else:
                stats_datasets.add('Unchanged dataset', dataset['name'])
                has_changed = False

            if dataset_to_merge_to:
                stats_merge.add('Merge', dataset_to_merge_to)
            else:
                stats_merge.add('No merge', dataset['name'])

            # save csv with corrections
            save_csv_rows(csv_corrected_rows, dataset, has_changed, dataset_to_merge_to)

    except:
        traceback.print_exc()
        import pdb; pdb.set_trace()

    stats_merge.report_value_limit = 500
    stats_res.report_value_limit = 500
    print '\nDatasets\n', stats_datasets
    print '\nDataset merges\n', stats_merge
    print '\nDates\n', stats_dates
    print '\nResources\n', stats_res

    # save csvs
    if dataset_filter or res_url_filter:
        for row in csv_corrected_rows:
            if res_url_filter and row['res_url'] != res_url_filter:
                continue
            pprint(row)
        print 'Not written csv because you specified a particular dataset'
    else:
        headers = [
            'name', 'org_title', 'org_id', 'notes',
            'res_id', 'res_name', 'res_url', 'res_format',
            'res_date', 'res_type',
            'has_changed',
            'merge_to_dataset',
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

    # group merges by the revamped_dataset
    resources_to_merge = defaultdict(list)  # revamped_dataset_name: resource_list
    resources_to_update = defaultdict(list)  # dataset_name: resource_list
    for row in csv_corrected_rows:
        if row['has_changed'] is False:
            continue
        res = dict(
            id=row['res_id'],
            name=row['res_name'],
            url=row['res_url'],
            format=row['res_format'],
            date=row['res_date'],
            type=row['res_type'])
        if row['merge_to_dataset']:
            res['id'] = None  # ignore the id
            resources_to_merge[row['merge_to_dataset']].append(res)
            # also delete the merged dataset
            if row['name'] not in dataset_names_to_delete:
                dataset_names_to_delete.add(row['name'])
        else:
            resources_to_update[row['name']].append(res)

    # write changes - merges etc
    if destination:
        write_caveat = ' (NOP without --write)'
        print 'Writing changes to datasets' + write_caveat
        stats_write_res = Stats()
        stats_write_dataset = Stats()
        ckan = common.get_ckanapi(destination)
        import ckanapi

        print 'Updating datasets'
        for dataset_name, res_list in resources_to_update.iteritems():
            dataset = ckan.action.package_show(id=dataset_name)
            resources_by_id = dict((r['id'], r) for r in dataset['resources'])
            dataset_changed = False
            for res in res_list:
                res_ref = '%s-%s' % (dataset_name, res_list.index(res))
                res_to_update = resources_by_id.get(res['id'])
                if res_to_update:
                    res_changed = False
                    for key in res.keys():
                        if res[key] != res_to_update.get(key):
                            res_to_update[key] = res[key]
                            dataset_changed = True
                            res_changed = True
                    if res_changed:
                        stats_write_res.add(
                            'update - ok' + write_caveat, res_ref)
                    else:
                        stats_write_res.add(
                            'update - not needed', res_ref)
                else:
                    stats_write_res.add(
                        'update - could not find resource id', dataset_name)
            if dataset_changed:
                if write:
                    ckan.action.package_update(dataset)
                stats_write_dataset.add(
                    'Update done' + write_caveat, dataset_name)
            else:
                stats_write_dataset.add(
                    'Update not needed', dataset_name)

        print 'Merging datasets'
        for revamped_dataset_name, res_list in \
                resources_to_merge.iteritems():
            try:
                dataset = ckan.action.package_show(id=revamped_dataset_name)
            except ckanapi.NotFound:
                stats_write_dataset.add(
                    'Merge - dataset not found', revamped_dataset_name)
                continue
            existing_res_urls = set(r['url'] for r in dataset['resources'])
            dataset_changed = False
            for res in res_list:
                res_ref = '%s-%s' % (revamped_dataset_name, res_list.index(res))
                if res['url'] in existing_res_urls:
                    stats_write_res.add(
                        'merge - no change - resource URL already there',
                        res_ref)
                else:
                    dataset_changed = True
                    dataset['resources'].append(res)
                    stats_write_res.add(
                        'merge - add' + write_caveat, res_ref)
            if dataset_changed:
                if write:
                    ckan.action.package_update(dataset)
                stats_write_dataset.add(
                    'Merge done' + write_caveat, revamped_dataset_name)
            else:
                stats_write_dataset.add('Merge not needed', revamped_dataset_name)

        print 'Deleting resources'
        for dataset_name, res_id_list in \
                all_resource_ids_to_delete.iteritems():
            if dataset_name in dataset_names_to_delete:
                stats_write_dataset.add(
                    'Delete resources not needed as deleting dataset later',
                    dataset_name)
                continue
            try:
                dataset = ckan.action.package_show(id=dataset_name)
            except ckanapi.NotFound:
                stats_write_dataset.add(
                    'Delete res - dataset not found', dataset_name)
                continue
            existing_resources = \
                dict((r['id'], r) for r in dataset['resources'])
            dataset_changed = False
            for res_id in res_id_list:
                res_ref = '%s-%s' % (dataset_name, res_id_list.index(res_id))
                existing_resource = existing_resources.get(res_id)
                if existing_resource:
                    dataset_changed = True
                    dataset['resources'].remove(existing_resource)
                    stats_write_res.add(
                        'delete res - done' + write_caveat, res_ref)
                else:
                    stats_write_res.add(
                        'delete res - could not find res id', res_ref)
            if dataset_changed:
                if write:
                    ckan.action.package_update(dataset)
                stats_write_dataset.add(
                    'Delete res done' + write_caveat, dataset_name)
            else:
                stats_write_dataset.add(
                    'Delete res not needed', dataset_name)

        print 'Deleting datasets'
        for dataset_name in dataset_names_to_delete:
            try:
                dataset = ckan.action.package_show(id=dataset_name)
            except ckanapi.NotFound:
                stats_write_dataset.add(
                    'Delete dataset - not found', dataset_name)
            else:
                if write:
                    ckan.action.package_delete(id=dataset_name)
                stats_write_dataset.add(
                    'Delete dataset - done' + write_caveat, dataset_name)

        print '\nResources\n', stats_write_res
        print '\nDatasets\n', stats_write_dataset
    else:
        print 'Not written changes to datasets'

def resource_corrections(res, dataset, extras,
                         revamped_resources, revamped_datasets_by_org,
                         dataset_to_merge_to,
                         org_id,
                         resources_to_delete, stats_res):
    # e.g. "http:// http://reference.data.gov.uk/gov-structure/organogram/?pubbod=science-museum-group"
    res['url'] = res['url'].strip()
    if res['url'].startswith('http:// '):
        res['url'] = res['url'].replace('http:// ', '')
    if res['url'] == 'http://fera.co.uk/aboutUs/documents/feraOrganogramAug13.pdf':
        res['date'] = '08/2013'
        res['resource_type'] = 'file'
    if res['id'] == '8924a06d-2983-4671-b689-389da3d5a8b6':
        # https://data.gov.uk/dataset/cambridgeshire-county-council-organisation-chart1/resource/
        res['resource_type'] = 'documentation'
        return
    if res['url'] == 'https://www.gov.uk/government/organisations/hm-revenue-customs/series/organisation':
        res['resource_type'] = 'documentation'

    # fix organization
    if dataset['name'] == 'staff-organograms-and-pay-treasury-solicitors-department':
        dataset['owner_id'] = '4bce2270-4307-4da2-b419-891139264b34'
        dataset['organization'] = {
            'id': '4bce2270-4307-4da2-b419-891139264b34',
            'title': 'Treasury Solicitor\'s Department',
            'name': 'treasury-solicitors-department',
        }
    elif dataset['name'] == 'organogram-and-staff-pay-data-for-the-disclosure-and-barring-service':
        dataset['owner_id'] = "2738f6bd-e1e4-4af8-883b-845072293160"
        dataset['organization'] = {
            'title': "The Disclosure and Barring Service",
            'name': "the-disclosure-and-barring-service",
            'id': "2738f6bd-e1e4-4af8-883b-845072293160",
        }
    elif dataset['name'] == 'organogram-and-staff-pay-data-for-the-gangmasters-licensing-authority':
        dataset['organization'] = {
            'title': "Gangmasters Licensing Authority",
            'name': "gangmasters-licensing-authority",
            'id': "0eb2cb9d-59dd-43f6-a99f-f7c21ad227d5",
        }
        dataset['owner_id'] = dataset['organization']['id']
    elif dataset['name'] == 'organogram-dsa':
        dataset['organization'] = {
            'title': "Driving Standards Agency",
            'name': "driving-standards-agency",
            'id': "b79e03cc-24a0-428e-ba6a-aa00a4eedab4",
        }
        dataset['owner_id'] = dataset['organization']['id']
    elif dataset['name'] == 'organogram-dvla':
        dataset['organization'] = {
            'title': "Driver and Vehicle Licensing Agency",
            'name': "driver-and-vehicle-licensing-agency",
            'id': "9d416cc3-786b-4955-94c6-d03b8b9aeae4",
        }
        dataset['owner_id'] = dataset['organization']['id']
    elif dataset['name'] == 'organogram-ha':
        dataset['organization'] = {
            'title': "Highways Agency",
            'name': "highways-agency",
            'id': "2e608e14-7635-48b2-ba2a-6777aeee4807",
        }
        dataset['owner_id'] = dataset['organization']['id']
    elif dataset['name'] == 'organogram-mca':
        dataset['organization'] = {
            'title': "Maritime and Coastguard Agency",
            'name': "maritime-and-coastguard-agency",
            'id': "5e3fe168-abca-417c-b88e-83580a017495",
        }
        dataset['owner_id'] = dataset['organization']['id']
    elif dataset['name'] == 'organogram-vca':
        dataset['organization'] = {
            'title': "Vehicle Certification Agency",
            'name': "vehicle-certification-agency",
            'id': "fe0223c4-01ac-4770-9af5-c761fee7fbaf",
        }
        dataset['owner_id'] = dataset['organization']['id']
    elif dataset['name'] == 'organogram-vosa':
        dataset['organization'] = {
            'title': "Vehicle and Operator Services Agency",
            'name': "vehicle-and-operator-services-agency",
            'id': "a1e904c0-c067-40fc-b8a2-621ae32918aa",
        }
        dataset['owner_id'] = dataset['organization']['id']
    elif dataset['name'] == 'sjsm_org_pay':
        dataset['organization'] = {
            'title': "Sir John Soane's Museum",
            'name': "sir-john-soanes-museum",
            'id': "df009a00-36ee-4eb9-8e4f-1bff097a8ffb",
        }
        dataset['owner_id'] = dataset['organization']['id']
    elif dataset['name'] == 'staff-organograms-and-pay-ahvla':
        dataset['organization'] = {
            'title': "Animal Health and Veterinary Laboratories Agency",
            'name': "animal-health-and-veterinary-laboratories-agency",
            'id': "56addc06-2534-45db-acb5-41f007310501",
        }
        dataset['owner_id'] = dataset['organization']['id']
    elif dataset['name'] == 'staff-organograms-and-pay-ccwater':
        dataset['organization'] = {
            'title': "Consumer Council for Water",
            'name': "consumer-council-for-water",
            'id': "7e912f56-1fe0-4d03-9273-732a7b6f4d51",
        }
        dataset['owner_id'] = dataset['organization']['id']
    elif dataset['name'] == 'staff-organograms-and-pay-cefas':
        dataset['organization'] = {
            'title': "Centre for Environment, Fisheries & Aquaculture Science",
            'name': "centre-for-environment-fisheries-aquaculture-science",
            'id': "2f1c6ccb-3f21-40c0-8b26-41566c53eb2f",
        }
        dataset['owner_id'] = dataset['organization']['id']
    elif dataset['name'] == 'staff-organograms-and-pay-ihol':
        dataset['organization'] = {
            'title': "Independent Housing Ombudsman",
            'name': "independent-housing-ombudsman",
            'id': "c9b97267-2606-4e27-87a4-a58a21548b5d",
        }
        dataset['owner_id'] = dataset['organization']['id']
    elif dataset['name'] == 'staff-organograms-and-pay-nihrc':
        dataset['organization'] = {
            'title': "Northern Ireland Human Rights Commission",
            'name': "northern-ireland-human-rights-commission",
            'id': "ce440659-22bf-4919-871a-d6a8685309b3",
        }
        dataset['owner_id'] = dataset['organization']['id']
    elif dataset['name'] == 'staff-organograms-and-pay-pcni':
        dataset['organization'] = {
            'title': "Parades Commission for Northern Ireland",
            'name': "parades-commission-for-northern-ireland",
            'id': "842d6905-acfe-4b49-a1b8-f29bd50915b0",
        }
        dataset['owner_id'] = dataset['organization']['id']

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
                import pdb; pdb.set_trace()
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
        # ones added 10 Jun 2011 and previous
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
    if dataset['name'] == 'norwich_organisation_chart':
        # assume because it was added 19/11/2014
        res['date'] = '30/06/2010'
    if dataset['name'] == 'organisation-chart1':
        # assume because it was added 25/03/2015
        res['date'] = '03/2015'
    if dataset['name'] == 'organisation-structure':
        # assume based on temporal coverage 1/1/2014 - 31/12/2014
        res['date'] = '2014'
    if dataset['name'] == 'organisation-and-salary-information-for-craven-district-council':
        if res['url'] == 'http://www.cravendc.gov.uk/CHttpHandler.ashx?id=8673&p=0':
            res['date'] = '09/02/2015'  # from the pdf itself
        else:
            res['resource_type'] = 'documentation'
            return
    if dataset['name'] == 'organisation-chart-architects-registration-board-uk':
        # added 29/10/2013
        res['date'] = '30/09/2013'
    if dataset['name'] == 'organisation-structure-local-government-transparency-code':
        # added 31/03/2015
        res['date'] = '31/03/2015'

    if res.get('date'):
        date = parse_date(res.get('date'))
        date_year_month = '%s-%s' % (date.year, date.month)
        revamped_res = revamped_resources.get((org_id, date_year_month))
        if revamped_res:
            if res.get('format'):
                if res['format'].upper() == 'CSV':
                    resources_to_delete.append(res)
                    stats_res.add('duplicate period to revamp csv deleted', res['url'])
                    return
                elif res['format'] == 'RDF':
                    stats_res.add('duplicate period to revamp rdf - leave',
                                  res['url'])
                    return
                else:
                    stats_res.add('duplicate period to revamp non-csv/rdf - leave',
                                  '%s %s' % (res['format'], res['url']))
                    return
            else:
                stats_res.add('??? duplicate period to revamp formatless since 2011', res['url'])
                return

    # gov.uk URLs will often be duplicates
    if re.match(r'https:\/\/www.gov.uk\/government\/(organisations|publications|uploads)\/.*', res['url']):
        if org_id not in revamped_datasets_by_org:
            stats_res.add('gov.uk but org not known in new scheme', '%s %s' % (org_id, res['url']))
            return
        # eg https://www.gov.uk/government/organisations/cabinet-office/series/cabinet-office-structure-charts
        # eg https://www.gov.uk/government/publications/bis-junior-staff-numbers-and-payscales-30-september-2012
        # eg https://www.gov.uk/government/uploads/system/uploads/attachment_data/file/11577/1920406.csv
        if res.get('date'):
            #print '\n%s from %s added to dataset already with:' % (date_year_month, dataset['name'])
            d = revamped_datasets_by_org[org_id]
            #for r in d['resources']:
            #    print '  %s: %s' % (d['name'], r.get('date'))
            #print '\n'

            if date > datetime.datetime(2012, 1, 1):
                # this data should be in the organogram tool
                if res.get('format'):
                    if res['format'].upper() == 'CSV':
                        resources_to_delete.append(res)
                        stats_res.add('delete - gov.uk csv since 2012 deleted', res['url'])
                        return
                    else:
                        # lots of alternative formats - ODS, PPTX, XLS, HTML
                        stats_res.add('keep - gov.uk non-csv since 2012',
                                      '%s' % (res['format']))
                else:
                    stats_res.add('??? gov.uk formatless since 2012', res['url'])
            elif date > datetime.datetime(2011, 1, 1):
                # this data should be in the organogram tool
                if res.get('format'):
                    if res['format'].upper() == 'CSV':
                        resources_to_delete.append(res)
                        stats_res.add('gov.uk csv since 2011 deleted', res['url'])
                        return
                    else:
                        # mostly RDF
                        stats_res.add('keep - gov.uk non-csv 2011',
                                      '%s' % (res['format']))
                else:
                    stats_res.add('??? gov.uk formatless since 2011', res['url'])
            elif date > datetime.datetime(2010, 1, 1):
                # this data should be in the organogram tool
                if res.get('format'):
                    if res['format'].upper() == 'CSV':
                        resources_to_delete.append(res)
                        stats_res.add('delete - gov.uk csv 2010 deleted', res['url'])
                        return
                    else:
                        # mostly PDF and PPT
                        stats_res.add('keep - gov.uk non-csv 2010',
                                      '%s' % (res['format']))
                else:
                    stats_res.add('??? gov.uk formatless 2010', res['url'])
            else:
                stats_res.add('gov.uk pre-2010 - keep', res['url'])
        elif extras.get('resource_type') != 'file':
            # ignore documentation
            pass
        else:
            stats_res.add('??? gov.uk but no date', dataset['name'])

    if dataset_to_merge_to and res['format'] == 'HTML' \
            and res.get('resource_type') != 'documentation':
        stats_res.add('Mark HTML as documentation', res['url'])
        res['resource_type'] = 'documentation'


def save_csv_rows(csv_rows, dataset, has_changed, dataset_to_merge_to):
    '''Saves the dataset to the csv_rows'''
    for res in dataset['resources']:
        csv_rows.append(dict(
            name=dataset['name'],
            org_title=dataset['organization']['title'],
            org_id=dataset['organization']['id'],
            notes='',   #dataset['notes'],
            res_id=res['id'],
            res_name=res['description'] or res.get('name', ''),
            res_url=res['url'],
            res_format=res['format'],
            res_date=res.get('date') or '',
            res_type=res.get('resource_type'),
            has_changed=has_changed,
            merge_to_dataset=dataset_to_merge_to,
            ))


def get_datasets_from_jsonl(filepath):
    with open(filepath, 'rb') as f:
        while True:
            line = f.readline()
            if line == '':
                break
            line = line.rstrip('\n')
            if not line:
                continue
            try:
                yield json.loads(line,
                                 encoding='utf8')
            except Exception:
                traceback.print_exc()
                import pdb; pdb.set_trace()


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

def get_dataset_to_merge_to(dataset, revamped_datasets_by_org):
    merge_dataset = revamped_datasets_by_org.get(dataset.get('owner_org'))
    if not merge_dataset:
        return
    return merge_dataset['name']


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
    parser.add_argument('-d', '--dataset',
                        help='Only do it for a single dataset name')
    parser.add_argument('--res-url',
                        help='Only do it for a single resource url')
    parser.add_argument('--destination',
                        help='Destination ckan (ini filename or URL), for when'
                        'changes will be written with --write')
    parser.add_argument('-w', '--write',
                        action='store_true',
                        help='Writes the changes to datasets (including '
                        'merges)')

    args = parser.parse_args()
    if args.source.endswith('.json'):
        source_type = 'json'
        if not os.path.exists(args.source):
            parser.error("Error: File not found: %s" % args.source)
    elif args.source.endswith('.jsonl'):
        source_type = 'jsonl'
        if not os.path.exists(args.source):
            parser.error("Error: File not found: %s" % args.source)
    else:
        source_type = 'domain'
    main(args.source, source_type, args.destination,
         args.save_relevant_datasets_json,
         args.write,
         dataset_filter=args.dataset, res_url_filter=args.res_url)
