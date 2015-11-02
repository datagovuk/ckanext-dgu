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
import warnings

from requests.packages.urllib3 import exceptions
import dateutil
import ckanapi
from ckan.logic import NotFound

from running_stats import Stats


class MergeDatasets(object):
    @classmethod
    def command(cls, config_ini, dataset_names, options):
        common.load_config(config_ini)
        common.register_translator()

        from pylons import config
        apikey = config['dgu.merge_datasets.apikey']
        ckan = ckanapi.RemoteCKAN('https://data.gov.uk', apikey=apikey)
        #ckan = ckanapi.LocalCKAN()

        if options.publisher:
            org_name = common.name_stripped_of_url(options.publisher)
            if options.search:
                results = ckan.action.package_search(q=options.search, fq='publisher:%s' % org_name, rows=100, escape_q=False)
                dataset_names.extend([dataset['name']
                                      for dataset in results['results']])
            else:
                org = ckan.action.organization_show(id=org_name,
                                                    include_datasets=True)
                dataset_names.extend([d['name'] for d in org['packages']])


        datasets = []
        datasets_by_name = {}

        def get_extra(dataset, key):
            for extra in dataset['extras']:
                if extra['key'] == key:
                    return extra['value']
        for dataset_name in dataset_names:
            print 'Dataset: %s' % dataset_name
        for dataset_name in dataset_names:
            # strip off the url part of the dataset name, if there is one
            dataset_name = common.name_stripped_of_url(dataset_name)
            dataset = ckan.action.package_show(id=dataset_name)
            harvest_source_ref = get_extra(dataset, 'harvest_source_reference')
            if harvest_source_ref:
                print '** Discarding dataset %s due to harvest source: %s **' \
                    % (dataset_name, harvest_source_ref)
                continue
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
                    print res_stats.add('Discarding duplicate', '\n%s duplicate of \n%s' % (resource, combined_resources[identity]))
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
                if not options.update:
                    dataset = datasets_by_name[res['dataset_name']]
                    yield 'dataset-title', dataset['title']
                    yield 'dataset-notes', dataset['notes']

            ensure_regexes_are_initialized()
            global regexes
            for resource in resources:
                for field_name, field_value in fields_to_hunt_for_date(resource):
                    if options.frequency in ('monthly', 'quarterly', 'twice annually'):
                        month, year = hunt_for_month_and_year(field_value)
                        if year and month:
                            resource['date'] = '%02d/%s' % (month, year)
                            res_stats.add('Found date in %s' % field_name,
                                          '%s %r' %
                                          (resource['date'], resource))
                            if resource.get('resource_type') == 'documentation':
                                resource['resource_type'] = 'file'
                                res_stats.add('Converted additional resource', resource)
                            break
                    elif options.frequency == 'annually':
                        year = regexes['year'].search(field_value)
                        if year:
                            resource['date'] = year.groups()[0]
                            res_stats.add('Found date in %s' % field_name,
                                          '%s %r' %
                                          (resource['date'], resource))
                            if resource.get('resource_type') == 'documentation':
                                resource['resource_type'] = 'file'
                                res_stats.add('Converted additional resource', resource)
                            break
                else:
                    if resource.get('resource_type') == 'documentation':
                        print res_stats.add('Could not find date but it\'s Additional Resource', resource)
                        continue
                    print res_stats.add('Could not find date', resource)
                    continue

            print 'Resources: \n', res_stats

            resources_without_date = [res for res in resources
                                      if not res.get('date') and
                                      res.get('resource_type') != 'documentation']
            for i, res in enumerate(resources_without_date):
                print 'Resources without dates %s/%s' % (i+1, len(resources_without_date))
                for field_name, field_value in fields_to_hunt_for_date(res):
                    print '  %s: %s' % (field_name, field_value.encode('latin-1', 'ignore'))
                print 'https://data.gov.uk/dataset/%s/resource/%s' % (res['dataset_name'], res['id'])
                date_format = {'annually': 'YYYY',
                               'monthly': 'MM/YYYY',
                               'twice annually': 'MM/YYYY',
                               'quarterly': 'MM/YYYY'}
                input_ = raw_input('Date (%s) or DOCS to make it an Additional Resource: ' %
                                   date_format[options.frequency])
                if input_.strip().lower() == 'docs':
                    res['date'] = ''
                    res['resource_type'] = 'documentation'
                else:
                    res['date'] = input_

            resources.sort(key=lambda x: x.get('date', '').split('/')[::-1])

        # Ensure there is not a mixture of resources with and without a date
        have_dates = None
        for res in resources:
            if res.get('resource_type') == 'documentation':
                continue
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
                'author', 'author_email',
                'maintainer', 'maintainer_email',
                'temporal_granularity', 'geographic_granularity',
                'state', 'isopen', 'url', 'date_update_future', 'date_updated',
                'date_released', 'precision',
                'taxonomy_url',
                'temporal_coverage-from', 'temporal_coverage-to',
                'published_via', 'creator_user_id',
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
        spend_data_defaults = {
            'geographic_coverage': None,
            'theme-primary': 'Government Spending',
            'theme-secondary': None,
            'update_frequency': 'monthly',
            }
        combined_dataset = {'resources': resources}
        all_fields_and_values = get_all_fields_and_values(datasets)
        for field, values in all_fields_and_values:
            if field == 'notes':
                values = [value.strip() for value in values]
            if field == 'tags':
                # just merge them up-front and
                # dont offer user any choice
                tags_by_name = {}
                for dataset_tags in values:
                    for tag in dataset_tags:
                        if tag['name'] not in tags_by_name:
                            tags_by_name[tag['name']] = tag
                values = [tags_by_name.values()]
            if field in ('codelist', 'schema'):
                # just merge them up-front
                # And convert the dict into just an id string
                ids = set()
                for dataset_values in values:
                    for value_dict in dataset_values:
                        ids.add(value_dict['id'])
                values = [list(ids)]
            print '\n%s:' % field
            pprint(list(enumerate(values)))
            if options.spend and field in spend_data_defaults:
                value = spend_data_defaults[field]
                print 'Spend data defaults to: %s' % value
                values = [value] if value is not None else None
            # dont be case-sensitive for boolean fields
            if field == 'core-dataset':
                values = [v.lower() for v in values]
            try:
                values_identicle = len(set(values)) == 1
            except TypeError:
                if values and len(values):
                    val1 = values[0]
                    for val in values[1:]:
                        if val != val1:
                            values_identicle = False
                            break
                    else:
                        values_identicle = True
            if (not values) or (not len(values)):
                pass
            elif values_identicle:
                value = values[0]
            elif field == 'name':
                while True:
                    from ckan.lib.munge import munge_title_to_name
                    munged_title = munge_title_to_name(combined_dataset['title'])
                    print munge_title_to_name(datasets[0]['organization']['title'])
                    value = raw_input('Type new value (%s): ' % (munged_title))
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
            if options.update:
                ckan.action.dataset_update(**combined_dataset)
            else:
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
        #response = raw_input('Press enter to delete the old ones: ')
        for name in datasets_to_delete:
            ckan.action.dataset_delete(id=name)
        print 'Done'

        # Print summary to help when communicating the change
        def print_user(user, custom_info=''):
            print '  "%s" %s %s' % (user['fullname'], user['email'], custom_info)
        print 'Creators:'
        user_cache = {}
        def get_user(id_):
            if id_ not in user_cache:
                try:
                    user = ckan.action.user_show(id=id_)
                except NotFound:
                    user = None
                user_cache[id_] = user
            return user_cache[id_]

        for dataset in datasets:
            creator_id = dataset['creator_user_id']
            user = get_user(creator_id)
            if user:
                print_user(user)
            else:
                print '  Not found: %s' % creator_id
        print 'Publisher Editors & Admins:'
        org = ckan.action.organization_show(id=dataset['owner_org'], include_users=True)
        for user_summary in org['users']:
            user = get_user(user_summary['name'])
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
            print '    %s %r' % (res.get('date'), res.get('title') or res['description'])
        print '\n--------------------------------------------------------\n'

        if org.get('closed'):
            print 'CLOSED - no need to notify'
            sys.exit(0)
        if options.update:
            print 'UPDATE - no need to notify'
            sys.exit(0)

        editors = [u for u in user_cache.values() if u is not None]
        params = {}
        params['editor_emails'] = ', '.join(['<%s>' % ed['email']
                                             for ed in editors if ed])
        params['publisher_title'] = org['title']
        params['dataset_name'] = combined_dataset['name']
        print '''
To: {editor_emails}
Subject: data.gov.uk spend data arrangements

Dear data.gov.uk editors at {publisher_title},

Please be aware that we've slightly changed the arrangements for the monthly spend data records that are published on data.gov.uk.

Until now you've been creating a new 'dataset' record on data.gov.uk each month. But this week these have been merged into a single dataset which contains a list of all the months' data links inside it. From now on, each month we ask you to 'Edit' the dataset, then click on the 'Data Files' tab and add your month's CSV link to the blank row at the bottom of the table.

View the merged dataset:

https://data.gov.uk/dataset/{dataset_name}

Edit the merged dataset:

https://data.gov.uk/dataset/edit/{dataset_name}

(it will ask you to log-in first if you have not done so already)

For more information about this process, please see:
http://datagovuk.github.io/guidance/monthly_datasets_problem.html

Regards,
David Read
data.gov.uk
        '''.format(**params)

global regexes
regexes = None
def ensure_regexes_are_initialized():
    global regexes
    if not regexes:
        months = 'jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|sept|september|oct|october|nov|november|dec|december'
        regexes = {
            'year': re.compile(r'\b(20\d{2})\b'),
            'year_at_start_of_date': re.compile(r'\b(20\d{2})[-/]'),
            'year_at_end_of_date': re.compile(r'[-/](20\d{2})\b'),
            'month': re.compile(r'\b(%s)\b' % months, flags=re.IGNORECASE),
            'month_2_digit_year': re.compile(r'\b(%s)[-/ ]?(\d{2})\b' % months, flags=re.IGNORECASE),
            'month_year': re.compile(r'\b(\d{1,2})[-/](20\d{2})\b'),
            'year_month': re.compile(r'\b(20\d{2})[-/](\d{1,2})\b'),
        }

def parse_month_as_word(month_word, year):
    month = month_word.lower().replace('sept', 'sep')
    month = month.replace('sepember', 'sep')
    month = month.replace('febuary', 'february')
    month = month.replace('february', 'february')
    month = month.replace('feburary', 'february')
    date_str = '1 %s %s' % (month, year)
    try:
        # dateutil converts '1 june 2014' to datetime(2014, 6, 1)
        # (we need the day or it won't parse 'february 2015' weirdly)
        date = dateutil.parser.parse(date_str)
    except ValueError:
        print 'ERROR parsing date: %s' % date_str
        import pdb; pdb.set_trace()
    return date.month, date.year

def hunt_for_month_and_year(field_value):
    global regexes
    ensure_regexes_are_initialized()
    month_year_match = regexes['month_year'].search(field_value)
    if month_year_match:
        month, year = month_year_match.groups()
        if int(month) < 13 and int(month) > 0:
            return int(month), int(year)
    month_2_digit_year_match = regexes['month_2_digit_year'].search(field_value)
    if month_2_digit_year_match:
        month, year = month_2_digit_year_match.groups()
        year = int(year)
        if year > 9 and year < 20:
            return parse_month_as_word(month, year + 2000)
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
        return parse_month_as_word(month_match.groups()[0], year_match.groups()[0])
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
    assert_equal(hunt_for_month_and_year('nov-14'), (11, 2014))
    assert_equal(hunt_for_month_and_year('nov14'), (11, 2014))
    assert_equal(hunt_for_month_and_year('15-2014'), (None, None))
    print 'ok'

usage = '''
Merge datasets, usually in a time series

    python merge_datasets.py <CKAN config ini filepath> [-f monthly/annually/quarterly] <dataset_name_1> <dataset_name_2> [...]
'''.strip()

if __name__ == '__main__':
    parser = OptionParser(usage=usage)
    parser.add_option('-p', '--publisher', dest='publisher', help='Take all datasets from a publisher')
    parser.add_option('-s', '--search', dest='search', help='Filter datasets by a search phrase (use with -p)')
    parser.add_option('-f', '--frequency', dest='frequency', metavar='FREQ')
    parser.add_option('--spend', dest='spend', action='store_true', default=False)
    parser.add_option('--update-dataset', dest='update', action='store_true', default=False, help='Updates a single dataset')

    (options, args) = parser.parse_args()
    if args == ['test']:
        test()
        sys.exit(0)
    if len(args) < 1:
        parser.error('Need at least 1 arguments')
    config_ini = args[0]
    datasets = args[1:]
    if options.search and not options.publisher:
        parser.error('If using --search you must also specify --publisher')
    if options.update and len(datasets) != 1:
        parser.error('Must be 1 dataset when specifying --update-dataset')
    FREQUENCIES = ['monthly', 'quarterly', 'twice annually', 'annually']
    if options.frequency and options.frequency not in FREQUENCIES:
        parser.error('Frequency must be one of: %r' % FREQUENCIES)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", exceptions.InsecurePlatformWarning)
        MergeDatasets.command(config_ini, dataset_names=datasets, options=options)
