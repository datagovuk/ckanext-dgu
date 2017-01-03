'''
Dump Drupal data to csv files.
'''
import argparse
from pprint import pprint
import traceback
import json
import sys
import gzip

from ckanext.dgu.drupalclient import (
    DrupalClient,
    DrupalRequestError,
    log as drupal_client_log
    )
from running_stats import Stats
import common

args = None
stats = Stats()


def users():
    drupal = get_drupal_client()

    # TODO get a full list of users

    if args.user:
        user_id_list = [args.user]
    elif args.ckan_users:
        # Get just users CKAN knows about
        ckan_users = parse_jsonl(args.ckan_users)
        user_id_list = [
            u['name'].replace('user_d', '')
            for u in ckan_users
            if u['name'].startswith('user_d')
            ]
    else:
        # Try ids sequentially
        user_id_list = [str(i) for i in range(1, 100000)]

    for i, user_id in enumerate(user_id_list):
        if i > 0 and i%100 == 0:
            print stats
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
        print stats.add('User ok', int(user_id))
        if args.user:
            pprint(user)

    print '\nUsers:', stats

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
    subparser.add_argument('--ckan-users',
                           help='Filepath of ckan users.jsonl.gz')
    subparser.add_argument('-u', '--user',
                           help='Only do it for a single user name')

    args = parser.parse_args()

    # call the function
    args.func()
