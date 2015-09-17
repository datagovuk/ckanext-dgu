'''
Merge tool for datasets, usually in a time series.
Keeps resources from all datasets and helps you resolve the differences for the
other fields.
e.g. for spend_may_14, spend_june_14, spend_july_14

If things go wrong, it often puts you into a pdb shell so that you can sort
things out, see what happened and not lose work.
'''

import re
import sys
import common
from optparse import OptionParser
from collections import defaultdict
from pprint import pprint

import dateutil
import ckanapi
from ckan.logic import NotFound

from running_stats import Stats


class MergeDatasets(object):
    @classmethod
    def command(cls, config_ini, dataset_names, options):
        common.load_config(config_ini)
        common.register_translator()
        ckan = ckanapi.LocalCKAN()

        if options.publisher:
            org = ckan.action.organization_show(id=options.publisher,
                                                include_datasets=True)
            dataset_names.extend([d['name'] for d in org['packages']])

        datasets = []
        datasets_by_name = {}
        for dataset_name in dataset_names:
            print 'Dataset: %s' % dataset_name
            dataset = ckan.action.package_show(id=dataset_name)
            datasets.append(dataset)
            datasets_by_name[dataset['name']] = dataset
        datasets.sort(key=lambda x: x['metadata_modified'])

        # aggregate resources
        def resource_identity(res_dict, dataset_name):
            return (res_dict.get('date'), res_dict['url'],
                    res_dict.get('title') or res_dict['description'],
                    res_dict.get('format'),
                    dataset_name)
        combined_resources = {}  # identity
        res_stats = Stats()
        for dataset in datasets:
            for resource in dataset['resources']:
                identity = resource_identity(resource, dataset['name'])
                resource['dataset_name'] = dataset['name']
                if identity in combined_resources:
                    print res_stats.add('Discarding duplicate', '%s duplicate of %s' % (resource, combined_resources[identity]))
                else:
                    combined_resources[identity] = resource
        resources = combined_resources.values()

        # find dates for resources
        if options.frequency:
            url_munge_re = re.compile('(%20|-|_|\.)')

            def fields_to_hunt_for_date(res):
                date = res.get('date')
                if date:
                    yield 'date', date
                title = res.get('title')
                if title:
                    yield 'title', title
                yield 'description', res['description']
                yield 'url', url_munge_re.sub(' ', res['url'])
                dataset = datasets_by_name[res['dataset_name']]
                yield 'dataset-title', dataset['title']
                yield 'dataset-notes', dataset['notes']

            ensure_regexes_are_initialized()
            global regexes
            for resource in resources:
                for field_name, field_value in fields_to_hunt_for_date(resource):
                    if options.frequency == 'monthly':
                        month, year = hunt_for_month_and_year(field_value)
                        if year and month:
                            resource['date'] = '%02d/%s' % (month, year)
                            res_stats.add('Found date in %s' % field_name,
                                          '%s %r' %
                                          (resource['date'], resource))
                            break
                    elif options.frequency == 'annually':
                        year = regexes['year'].search(field_value)
                        if year:
                            resource['date'] = year.groups()[0]
                            res_stats.add('Found date in %s' % field_name,
                                          '%s %r' %
                                          (resource['date'], resource))
                            break
                else:
                    print res_stats.add('Could not find date', resource)
                    continue

            print 'Resources: \n', res_stats

            resources_without_date = [res for res in resources
                                      if not res.get('date')]
            for i, res in enumerate(resources_without_date):
                print 'Resources without dates %s/%s' % (i+1, len(resources_without_date))
                for field_name, field_value in fields_to_hunt_for_date(res):
                    print '  %s: %s' % (field_name, field_value)
                date_format = {'annually': 'YYYY',
                               'monthly': 'YYYY-MM'}
                res['date'] = raw_input('Date (%s): ' %
                                        date_format[options.frequency])

        # Ensure there is not a mixture of resources with and without a date
        have_dates = None
        for res in resources:
            if have_dates is None:
                have_dates = bool(res.get('date'))
            else:
                has_date = bool(res.get('date'))
                if has_date != have_dates:
                    print [res.get('date') for res in resources]
                    print 'Cannot mix resources with dates and others without!'
                    import pdb
                    pdb.set_trace()

        # Remove 'dataset_name' and others fields from resources
        ignore_res_fields = set(('dataset_name', 'created', 'position', 'revision_id', 'id', 'tracking_summary'))
        for res in resources:
            for field in ignore_res_fields & set(res.keys()):
                del res[field]

        # Merge dataset fields
        def get_all_fields_and_values(datasets):
            ignore_fields = set((
                'id', 'resources', 'last_major_modification', 'data_dict',
                'revision_timestamp', 'num_tags', 'metadata_created',
                'metadata_modified', 'odi_certificate',
                'extras',  # they are at top level already
                'timeseries_resources', 'individual_resources',
                'additional_resources',
                'revision_id', 'organization',
                'tracking_summary',
                'num_resources',
                'license_title',
                'author', 'temporal_granularity', 'geographic_granularity',
                'state', 'isopen', 'url', 'date_update_future', 'date_updated', 'date_released',
                'temporal_coverage-from', 'temporal_coverage-to',
                ))
            first_fields = ['title', 'name', 'notes', 'theme-primary', 'theme-secondary']
            all_field_values = defaultdict(list)
            for dataset in datasets:
                for field in dataset:
                    if field not in ignore_fields and dataset[field]:
                        all_field_values[field].append(dataset[field])
            for field in first_fields:
                yield field, all_field_values.get(field, [])
            for field in all_field_values:
                if field not in first_fields:
                    yield field, all_field_values[field]
        combined_dataset = {'resources': resources}
        all_fields_and_values = get_all_fields_and_values(datasets)
        for field, values in all_fields_and_values:
            if field == 'tags':
                # just merge them up-front and
                # dont offer user any choice
                tags_by_name = {}
                for dataset_tags in values:
                    for tag in dataset_tags:
                        if tag['name'] not in tags_by_name:
                            tags_by_name[tag['name']] = tag
                values = [tags_by_name.values()]
            print '\n%s:' % field
            pprint(list(enumerate(values)))
            #if field == 'primary_theme':
            #    import pdb; pdb.set_trace()
            # dont be case-sensitive for boolean fields
            if field == 'core-dataset':
                values = [v.lower() for v in values]
            try:
                values_identicle = len(set(values)) == 1
            except TypeError:
                if len(values):
                    val1 = values[0]
                    for val in values[1:]:
                        if val != val1:
                            values_identicle = False
                            break
                    else:
                        values_identicle = True
            if not len(values):
                pass
            elif values_identicle:
                value = values[0]
            elif field == 'name':
                while True:
                    from ckan.lib.munge import munge_title_to_name
                    munged_title = munge_title_to_name(combined_dataset['title'])
                    munged_publisher = munge_title_to_name(datasets[0]['organization']['title'])
                    value = raw_input('Type new value (%s-%s): ' % (munged_title, munged_publisher))
                    if not value:
                        value = munged_title
                    if len(value) < 3:
                        print 'Too short'
                        continue
                    if value in values:
                        print 'That name is taken'
                        continue
                    existing = ckan.action.package_autocomplete(q=value)
                    if value in existing:
                        print 'That name is taken on CKAN'
                        continue
                    break
            else:
                while True:
                    response = raw_input('%s: value (number) or type new one: ' % field)
                    try:
                        value_index = int(response)
                        value = values[value_index]
                        print value
                    except ValueError:
                        # fix pound signs if the user pasted from the repr'd version
                        response = re.sub(r'\\xa3', u'\xa3', response)
                        value = response
                    if not value and field in ('title', 'owner_org', 'notes', 'license_id'):
                        print 'You must have a value for this field!'
                        continue
                    break
            if value:
                combined_dataset[field] = value

        # Store
        print '\nMerged dataset:\n'
        pprint(combined_dataset)

        response = raw_input('Press enter to write or pdb to edit in pdb first: ')
        if response == 'pdb':
            import pdb
            pdb.set_trace()
        try:
            ckan.action.dataset_create(**combined_dataset)
        except Exception, e:
            print e
            import pdb
            pdb.set_trace()
        print 'Created: %s' % combined_dataset['name']

        # Delete old ones
        datasets_to_delete = datasets_by_name.keys()
        if combined_dataset['name'] in datasets_to_delete:
            datasets_to_delete.remove(combined_dataset['name'])
        print 'Old ones to delete: %r' % datasets_to_delete
        response = raw_input('Press enter to delete the old ones: ')
        for name in datasets_to_delete:
            ckan.action.dataset_delete(id=name)
        print 'Done'

        # Print summary to help when communicating the change
        def print_user(user, custom_info=''):
            print '  "%s" %s %s' % (user['fullname'], user['email'], custom_info)
        print 'Creators:'
        for dataset in datasets:
            creator_id = dataset['creator_user_id']
            try:
                user = ckan.action.user_show(id=creator_id)
                print_user(user)
            except NotFound:
                print '  Not found: %s' % creator_id
        print 'Publisher Editors & Admins:'
        org = ckan.action.organization_show(id=dataset['owner_org'], include_users=True)
        for user_summary in org['users']:
            user = ckan.action.user_show(id=user_summary['name'])
            print_user(user, user_summary['capacity'])
        print '\n--------------------------------------------------------\n'
        print 'Publisher: %s https://data.gov.uk/publisher/%s' % \
            (org['title'], org['name'])
        if org.get('closed'):
            print '*** Closed ***'
        print '%s datasets that were merged (now deleted):' % len(datasets)
        for dataset in datasets:
            print '  https://data.gov.uk/dataset/%s' % (dataset['name'])
        print 'Resulting dataset:'
        print '  https://data.gov.uk/dataset/%s' % (combined_dataset['name'])
        print '  with %s resources:' % len(combined_dataset['resources'])
        for res in combined_dataset['resources']:
            print '    %s %s' % (res.get('date'), res.get('title') or res['description'])
        print '\nFor more about merging dataset series, see: http://datagovuk.github.io/guidance/monthly_datasets_problem.html'

global regexes
regexes = None
def ensure_regexes_are_initialized():
    global regexes
    if not regexes:
        regexes = {
            'year': re.compile(r'\b(20\d{2})\b'),
            'year_at_start_of_date': re.compile(r'\b(20\d{2})[-/]'),
            'year_at_end_of_date': re.compile(r'[-/](20\d{2})\b'),
            'month': re.compile(r'\b(jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|sept|september|oct|october|nov|november|dec|december)\b', flags=re.IGNORECASE),
            'month_year': re.compile(r'\b(\d{1,2})[-/](20\d{2})\b'),
            'year_month': re.compile(r'\b(20\d{2})[-/](\d{1,2})\b'),
        }

def hunt_for_month_and_year(field_value):
    global regexes
    ensure_regexes_are_initialized()
    month_year_match = regexes['month_year'].search(field_value)
    if month_year_match:
        month, year = month_year_match.groups()
        if int(month) < 13 and int(month) > 0:
            return int(month), int(year)
    year_month_match = regexes['year_month'].search(field_value)
    if year_month_match:
        year, month = year_month_match.groups()
        if int(month) < 13 and int(month) > 0:
            return int(month), int(year)
    year_match = regexes['year'].search(field_value) or \
        regexes['year_at_start_of_date'].search(field_value) or \
        regexes['year_at_end_of_date'].search(field_value)
    month_match = regexes['month'].search(field_value)
    if year_match and month_match:
        # dateutil converts 'june 2014' to datetime(2014, 6, xyz)
        date = dateutil.parser.parse('%s %s' %
            (month_match.groups()[0], year_match.groups()[0]))
        return date.month, date.year
    return None, None


def test():
    from nose.tools import assert_equal
    assert_equal(hunt_for_month_and_year('11-2014'), (11, 2014))
    assert_equal(hunt_for_month_and_year('2014-11'), (11, 2014))
    assert_equal(hunt_for_month_and_year('nov 2014'), (11, 2014))
    assert_equal(hunt_for_month_and_year('April 2014'), (4, 2014))
    assert_equal(hunt_for_month_and_year('2014 nov'), (11, 2014))
    assert_equal(hunt_for_month_and_year('2014 Nov'), (11, 2014))
    assert_equal(hunt_for_month_and_year('2014 November'), (11, 2014))
    assert_equal(hunt_for_month_and_year('15-2014'), (None, None))
    print 'ok'

usage = '''
Merge datasets, usually in a time series

    python merge_datasets.py <CKAN config ini filepath> [-f monthly/annually] <dataset_name_1> <dataset_name_2> [...]
'''.strip()

if __name__ == '__main__':
    parser = OptionParser(usage=usage)
    parser.add_option('-p', '--publisher', dest='publisher', help='Take all datasets from a publisher')
    parser.add_option('-f', '--frequency', dest='frequency', metavar='FREQ')

    (options, args) = parser.parse_args()
    if args == ['test']:
        test()
        sys.exit(0)
    if len(args) < 1:
        parser.error('Need at least 1 arguments')
    config_ini = args[0]
    datasets = args[1:]
    FREQUENCIES = ['monthly', 'annually']
    if options.frequency and options.frequency not in FREQUENCIES:
        parser.error('Frequency must be one of: %r' % FREQUENCIES)

    MergeDatasets.command(config_ini, dataset_names=datasets, options=options)
