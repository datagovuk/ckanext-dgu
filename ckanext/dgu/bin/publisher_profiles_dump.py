'''
Tool to dump info about publishers and users from ckan database.
'''
from __future__ import print_function
import argparse
from pprint import pprint
import datetime
import gzip
import json

from running_stats import Stats
import common


args = None
stats = Stats()

EVENT_TYPES = [
    'create_account',
    'login',
    ]

def dump():
    events = Events()

    # create_account
    if not args.event or args.event == 'create_account':
        from ckan import model
        users = model.Session.query(model.User.name, model.User.created,
                                    model.User.state) \
            .filter_by(state='active') \
            .limit(args.limit) \
            .all()
        for name, created, state in users:
            events.add(created, name, 'create_account', None)

    if not args.event or args.event in ('login',):
        for user in read_jsonl(args.drupal_users_jsonl):
            # login
            # date, user_id, login
            if not args.event or args.event == 'login':
                login_date = datetime.datetime.fromtimestamp(
                    float(user['login']))
                events.add(login_date, user['name'], 'login', None)

    for event in events.get_all()[:10]:
        pprint(event)

def read_jsonl(filepath):
    count = 0
    with gzip.open(filepath, 'rb') as f:
        while True:
            if args.limit and count > args.limit:
                break
            line = f.readline().rstrip('\n')
            if not line:
                continue
            yield json.loads(line, encoding='utf8')
            count += 1


class Events(dict):
    def add(self, date, name, action, params):
        identity = self.event_identity(date, name, action)
        self[identity] = (date, name, action, params)

    @classmethod
    def event_identity(cls, date, user_id, action):
        return (date, user_id, action)

    def get_all(self):
        return sorted(self.values(), key=lambda x: x[0])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ckan_ini', help='Filepath of the ckan.ini')
    parser.add_argument('--drupal_users_jsonl',
                       default='drupal_users.jsonl.gz',
                       help='Location of the public output '
                            'apps_public.jsonl.gz file')
    parser.add_argument('--limit', type=int, help='Limit queries')
    parser.add_argument('--event', choices=EVENT_TYPES,
                        help='Only one event type')
    args = parser.parse_args()

    common.load_config(args.ckan_ini)
    dump()