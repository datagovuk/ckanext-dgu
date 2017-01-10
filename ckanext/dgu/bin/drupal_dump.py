'''
Dump Drupal data to csv files.
'''
import argparse
from pprint import pprint
import traceback
import json
import sys
import gzip
import unicodecsv
from collections import defaultdict

from ckanext.dgu.drupalclient import (
    DrupalClient,
    DrupalRequestError,
    )
from running_stats import Stats
import common

args = None
stats = Stats()


def users():
    drupal = get_drupal_client()

    # Get a list of users to try (the api doesn't tell us)

    if args.user:
        user_id_list = [args.user]
    elif args.users_from_drupal_user_table_dump:
        with gzip.open(args.users_from_drupal_user_table_dump, 'rb') as f:
            csv_reader = unicodecsv.DictReader(f, encoding='utf8')
            user_id_list = [
                int(user_dict['uid'])
                for user_dict in csv_reader
                if user_dict['status'] != '0'  # i.e. not blocked
                ]
    elif args.users_from_ckan_dump:
        # Get users Drupal knows about
        ckan_users = parse_jsonl(args.users_from_ckan_dump)
        user_id_list = [
            int(u['name'].replace('user_d', ''))
            for u in ckan_users
            if u['name'].startswith('user_d')
            ]
    elif args.users_tried_sequentially:
        # Try ids sequentially
        user_id_list = [str(i) for i in range(1, 500000)]

    user_id_list.sort()
    print 'Users to try: %s (up to %s)' % (len(user_id_list), user_id_list[-1])

    i = 0
    with gzip.open(args.output_fpath, 'wb') as output_f:
        for user_id in common.add_progress_bar(
                user_id_list, maxval=len(user_id_list)):
            if i > 0 and i % 100 == 0:
                print stats
            i += 1

            if args.user and str(user_id) != str(args.user):
                continue
            try:
                user = drupal.get_user_properties(user_id)
            except DrupalRequestError, e:
                if 'There is no user with ID' in str(e):
                    print stats.add('User ID unknown', int(user_id))
                    continue
                elif 'Access denied for user anonymous' in str(e):
                    print stats.add('User blocked', int(user_id))
                    continue
                print stats.add('Error: %s' % e, int(user_id))
                continue
            if not args.user:
                output_f.write(json.dumps(user) + '\n')
            stats.add('User dumped ok', int(user_id))

            if args.user:
                pprint(user)

    print '\nUsers:', stats
    if not args.user:
        print '\nWritten to: %s' % args.output_fpath
    else:
        print '\nNot written due to filter'


def organograms():
    drupal = get_drupal_client()

    organogram_files = drupal.get_organogram_files()

    # e.g.
    # {u'fid': u'16449',
    #  u'name': u'cabinet-office',
    #  u'publish_date': u'1482088184',
    #  u'signoff_date': u'1482088160'}
    #  u'deadline_date': u'1475190000',

    print 'Organogram files to try: %s' % len(organogram_files)

    i = 0
    with gzip.open(args.output_fpath, 'wb') as output_f:
        for organogram_file in common.add_progress_bar(organogram_files):
            if i > 0 and i % 100 == 0:
                print stats
            i += 1

            fid = organogram_file['fid']
            if args.publisher and organogram_file['name'] != args.publisher:
                continue
            try:
                organogram = drupal.get_organogram_file_properties(fid)
            except DrupalRequestError, e:
                if 'There is no organogram file with fid' in str(e):
                    print stats.add('Organogram fid unknown',
                                    int(fid))
                    continue
                print stats.add('Error: %s' % e, int(fid))
                continue
            if not args.publisher:
                output_f.write(json.dumps(organogram) + '\n')
            stats.add('Organogram dumped ok', int(fid))

            if args.publisher:
                pprint(organogram)

    print '\nOrganograms:', stats
    if not args.publisher:
        print '\nWritten to: %s' % args.output_fpath
    else:
        print '\nNot written due to filter'


def apps():
    drupal = get_drupal_client()

    # dataset_referrers help us link up the apps and the ckan dataset id
    referrers = drupal.get_dataset_referrers()
    app_datasets = defaultdict(list)  # app nid: [ckan_dataset_id, ... ]
    for referrer in referrers:
        if referrer['type'] != 'App':
            continue
        app = referrer

        # {u'ckan_id': u'13dbf974-6646-4eef-878d-c1ba2039ead5',
        #  u'nid': u'4461',
        #  u'path': u'/apps/sound-buy',
        #  u'title': u'Sound Buy',
        #  u'type': u'App'}

        app_datasets[app['nid']].append(app['ckan_id'])

        #thumb = app.get('thumbnail', '').replace('://', '/')
        #if thumb:
        #    thumb_url = urljoin(root_url,
        #                        '/sites/default/files/styles/medium/')
        #    thumb_url = urljoin(thumb_url, thumb)
        #else:
        #    thumb_url = ''

    nodes = drupal.get_nodes()

    with gzip.open(args.output_fpath, 'wb') as output_f:
        for node in common.add_progress_bar(nodes):
            # ignore Forum topics and blog posts that refer
            # Eventually we might handle other types.
            if node['type'] != 'app':
                continue
            app = node
            if args.app and args.app not in (app['nid'], app['title']):
                continue

            # Get main details from the node
            try:
                app_node = drupal.get_node(node['nid'])
            except DrupalRequestError, e:
                if 'There is no app file with nid' in str(e):
                    print stats.add('Node id unknown',
                                    int(node['nid']))
                    continue
                print stats.add('Error: %s' % e, int(fid))
                continue
            # app_node is a superset of app
            app = app_node

            # NB contains personal data in:
            # field_submitter_email
            # field_submitter_name
            # name

            # screenshot:           "filename": "data.gov_.uk_.3_10.jpg"
            # is:           /sites/default/files/data.gov_.uk_.1_10.jpg
            # found: /var/www/files/drupal/dgud7/data.gov_.uk_.1_10.jpg

            # Get the linked datasets
            # u'field_uses_dataset': {u'und': [{u'target_id': u'13231'},
            try:
                dataset_nids = [
                    d['target_id']
                    for d in app.get('field_uses_dataset', {})['und']] \
                    if app.get('field_uses_dataset') else []
            except TypeError:
                import pdb; pdb.set_trace()
            try:
                dataset_ids = app_datasets[app['nid']]
            except KeyError:
                dataset_ids = []
                stats.add('App with no datasets',
                          '%s %s' % (dataset_nid, node['title']))
            if len(dataset_nids) != len(dataset_ids):
                # this occurs occasionally eg commutable-careers
                # where perhaps a dataset is deleted. it's fine.
                stats.add('Error - app with wrong number of datasets',
                          '%s %s %s' % (len(dataset_nids), len(dataset_ids),
                                        node['title']))
            app['field_uses_dataset_ckan_ids'] = dataset_ids

            if not args.app:
                output_f.write(json.dumps(app) + '\n')
            stats.add('%s dumped ok' % node['type'], node['title'])

            if args.app:
                pprint(app)

    print '\nApps:', stats
    if not args.app:
        print '\nWritten to: %s' % args.output_fpath
    else:
        print '\nNot written due to filter'

def parse_jsonl(filepath):
    with gzip.open(filepath, 'rb') as f:
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
                import pdb
                pdb.set_trace()


def get_drupal_client():
    try:
        password = common.get_config_value_without_loading_ckan_environment(
            args.ckan_ini, 'dgu.xmlrpc_password')
    except ValueError, e:
        print e
        sys.exit(1)

    return DrupalClient(dict(
        xmlrpc_scheme='https',
        xmlrpc_domain=args.domain,
        xmlrpc_username='CKAN_API',
        xmlrpc_password=password))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ckan_ini', help='Filepath of the ckan.ini')
    parser.add_argument('-d', '--domain', default='data.gov.uk',
                        help='Remote domain to query')

    subparsers = parser.add_subparsers()

    subparser = subparsers.add_parser('users')
    subparser.set_defaults(func=users)
    subparser.add_argument('--output_fpath',
                           default='drupal_users.jsonl.gz',
                           help='Location of the output '
                                'drupal_users.jsonl.gz file')
    subparser.add_argument('--users-from-ckan-dump',
                           help='Filepath of ckan users.jsonl.gz')
    subparser.add_argument('--users-from-drupal-user-table-dump',
                           help='Filepath of drupal_users_table.csv.gz')
    subparser.add_argument('--users-tried-sequentially',
                           action='store_true',
                           help='Rather than try a given list of user ids, '
                                'just try all ids in order from 1 to 500000.')
    subparser.add_argument('-u', '--user',
                           help='Only do it for a single user (eg 845)')

    subparser = subparsers.add_parser('organograms')
    subparser.set_defaults(func=organograms)
    subparser.add_argument('--output_fpath',
                           default='organograms.jsonl.gz',
                           help='Location of the output '
                                'organograms.jsonl.gz file')
    subparser.add_argument('-p', '--publisher',
                           help='Only do it for a single publisher '
                                '(eg cabinet-office)')

    subparser = subparsers.add_parser('apps')
    subparser.set_defaults(func=apps)
    subparser.add_argument('--output_fpath',
                           default='apps.jsonl.gz',
                           help='Location of the output '
                                'apps.jsonl.gz file')
    subparser.add_argument('--app',
                           help='Only do it for a single app '
                                '(eg Illustreets)')

    args = parser.parse_args()

    # call the function
    args.func()
