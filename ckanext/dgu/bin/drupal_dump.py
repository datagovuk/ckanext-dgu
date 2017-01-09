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

    args = parser.parse_args()

    # call the function
    args.func()
