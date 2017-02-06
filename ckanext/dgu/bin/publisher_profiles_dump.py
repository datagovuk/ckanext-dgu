'''
Tool to dump info about publishers and users from ckan database.

Install:

pip install pymongo==3.4.0
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 0C49F3730359A14518585931BC711F9BA15703C6
echo "deb [ arch=amd64 ] http://repo.mongodb.org/apt/ubuntu precise/mongodb-org/3.4 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-3.4.list
sudo apt-get update
sudo apt-get install -y mongodb-org
sudo service mongod start


'''
from __future__ import print_function
import argparse
from pprint import pprint
import datetime
import gzip
import re
import traceback
# see install instructions above
from pymongo import MongoClient

from running_stats import Stats
import common


args = None
stats = Stats()

EVENT_TYPES = [
    'create_account',
    'login',
    'publish-form-new-submit-success',
    ]

def dump():
    events = Events()

    # create_account
    if not args.event or args.event == 'create_account':
        common.load_config(args.ckan_ini)
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

    #logs
    if args.logfile and (
            not args.event or args.event.startswith('publish-form')):
        count = 0
        for date, level, function, message in read_log(args.logfile):
            count += 1

            # new form (every render):
            # [ckan.lib.base] rendering /src/ckanext-dgu/ckanext/dgu/theme/templates/package/new.html [jinja2]
            # [ckan.lib.base] rendering /src/ckanext-dgu/ckanext/dgu/theme/templates/package/edit_form.html [jinja2]
            #if message.endswith('new.html [jinja2]'):
            #    events.add(date, user['name'], 'login', None)

            # new form submit validate-error:
            # DEBUG [ckan.logic.action.create] package_create validate_errs={'name'

            # new form submit ok
            # DEBUG [ckan.logic.action.create] package_create validate_errs={} user=
            # INFO  [ckanext.dgu.plugin] Indexing: abc
            # DEBUG [ckan.logic.action.create] Created object abc
            if message.startswith('package_create validate_errs={}'):
                user, data = parse_validate_log_message(message)
                params = {'name': data['name']}
                events.add(date, user, 'publish-form-new-submit-success',
                           params)

            # edit form (every render):
            # DEBUG [ckan.lib.base] rendering /src/ckanext-dgu/ckanext/dgu/theme/templates/package/edit.html [jinja2]
            # DEBUG [ckan.lib.base] rendering /src/ckanext-dgu/ckanext/dgu/theme/templates/package/edit_form.html [jinja2]

            # edit form submit validate-error:
            # DEBUG [ckan.controllers.package] Package save request name: abc POST: UnicodeMultiDict([
            # DEBUG [ckan.logic.action.update] package_update validate_errs={'tit

            # edit form submit ok
            # DEBUG [ckan.controllers.package] Package save request name: abc POST:
            # DEBUG [ckan.logic.action.update] package_update validate_errs={} user=a
            if message.startswith('package_update validate_errs={}'):
                user, data = parse_validate_log_message(message)
                params = {'name': data['name']}
                events.add(date, user, 'publish-form-edit-submit-success',
                           params)
        print('%s lines' % count)

    # for event in events.get_all()[:10]:
    #     pprint(event)

def parse_validate_log_message(message):
    # package_create validate_errs={} user=
    try:
        user = re.search(r'user=([^ ]+)', message).groups()[0]
        data = eval(re.search(r'data=(\{.*\})$', message).groups()[0])
    except Exception, e:
        traceback.print_exc()
        import pdb; pdb.set_trace()
    return user, data

def read_log(filepath):
    '''Open a log file and return parsed messages'''
    count = 0
    for line in log_messages(filepath):
        if args.limit and count > args.limit:
            break
        yield parse_log_line(line)
        count += 1

def log_messages(filepath):
    '''Open a log file and return each log message, even if it is multiline'''
    cumulative_lines = ''
    with open(filepath, 'r') as f:
        while True:
            line = f.readline()
            if line.startswith('20') or line == '':
                # i.e. start of a new log message (or end of file)
                # so yield the queued log message
                cumulative_lines = cumulative_lines.rstrip('\n')
                if cumulative_lines:
                    yield cumulative_lines
                cumulative_lines = ''
                if line == '':
                    # end of file
                    break
            cumulative_lines += line

def parse_log_line(line):
    # 2017-02-02 08:59:33,136 DEBUG [ckan.logic] check access OK - dataset_update user=admin
    try:
        date, level, function, message = re.search(
            r'^(?P<date>\d{4}-\d{2}-\d{2} '
            '\d{2}:\d{2}:\d{2}),\d+ '
            '(?P<level>\w+)\s+'
            '\[(?P<function>[\w\.]+)\] (?P<message>.+)',
            line).groups()
    except AttributeError:
        assert 0, 'Error parsing:\n%s' % line
    return (date, level, function, message)

def read_jsonl(filepath):
    import json
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


class DataStore(dict):
    db = None

    @classmethod
    def get_mongo_db(cls):
        if cls.db = None:
            client = MongoClient()
            cls.db = client.publisher_profiles

    def add(self, date, name, action, params):
        event = dict(
            date=date, name=name, action=action, **params)
        DataStore.db.events.insert_one(event)
        pprint((date, name, action, params))

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
    parser.add_argument('--logfile', help='ckan log file for analysis')
    parser.add_argument('--limit', type=int, help='Limit queries')
    parser.add_argument('--event', choices=EVENT_TYPES,
                        help='Only one event type')
    args = parser.parse_args()

    dump()