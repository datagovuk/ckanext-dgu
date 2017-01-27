'''
Tool to dump info about publishers and users from ckan database.
'''
from __future__ import print_function
import argparse
from pprint import pprint

from running_stats import Stats
import common


args = None
stats = Stats()

def dump():
    from ckan import model
    events = Events()

    # date, user_id, create_account
    users = model.Session.query(model.User.name, model.User.created,
                                model.User.state) \
        .limit(args.limit) \
        .all()
    for name, created, state in users:
        events.add(created, name, 'create_account', None)

    for event in events.get_all()[:10]:
        pprint(event)



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
    parser.add_argument('--limit', help='Limit queries')
    args = parser.parse_args()

    common.load_config(args.ckan_ini)
    dump()