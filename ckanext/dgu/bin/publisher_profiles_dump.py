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
import sys
from collections import OrderedDict
import unicodecsv

# see install instructions above
from pymongo import MongoClient
from pymongo.errors import OperationFailure
from sqlalchemy import distinct
from sqlalchemy import func

from running_stats import Stats
import common

args = None
stats = Stats()

EVENT_TYPES = [
    'create-account',
    'login',
    'publish-form-new-submit-success',
    'dataset-created',
    'publish-form-edit-submit-success',
    'dataset-updated',
    ]

QUARTER_PROJECTION = {
    '$concat': [
        {'$substr': [{'$year': '$date'}, 0, 4]},  # substr casts int to str
        '-',
        {'$cond': [{'$lte': [{'$month': '$date'}, 3]},
                   'Q1',
                   {'$cond': [{'$lte': [{'$month': '$date'}, 6]},
                              'Q2',
                              {'$cond': [{'$lte': [{'$month': '$date'}, 9]},
                                         'Q3',
                                         'Q4']}]}]
         },
        ]
    }
USER_OR_HARVESTED_PROJECTION = {
    '$cond': ['$harvested',
              'harvested',
              '$user_name'
              ]
}

def mine_ckan_db():
    ds = DataStore.instance()

    # ckan db
    print('Opening CKAN db...')
    common.load_config(args.ckan_ini)
    print('...done')
    from ckan import model

    # create-account
    if not args.event or args.event == 'create-account':
        print('Getting user creations...')
        users = model.Session.query(model.User.name, model.User.created,
                                    model.User.state) \
            .filter_by(state='active') \
            .limit(args.limit) \
            .all()
        print('...done')
        for name, created, state in add_progress_bar(users):
            ds.add_event(created, name, 'create-account', None)

    # dataset-created
    if not args.event or args.event in ('dataset-created', 'dataset-updated'):

        def is_harvested(pr_creator_user_id):
            return pr_creator_user_id in (
                '60e687bf-a6d8-43e2-a50e-efab84b27952', # harvest
                '431b5956-7b87-41ba-8fc5-a4a8b681b797'  # co-prod3.dh.bytemark.co.uk for gemini
                )

        #print('Getting package names used by more than one id...')
        # e.g. building_price_and_cost_indices has two ids
        #select name, count(distinct id) from package_revision group by name order by count(distinct id) desc;
        # name_prs = model.Session.query(
        #     model.PackageRevision.name,
        #     func.count(distinct(model.PackageRevision.id)))\
        #     .group_by(model.PackageRevision.name)\
        #     .order_by(func.count(distinct(model.PackageRevision.id)).desc())\
        #     .all()
        # indistinct_names = set()
        # for name, num_ids in name_prs:
        #     if num_ids < 2:
        #         break
        #     indistinct_names.add(name)
        # print('...done')

        if args.event == 'dataset-created':
            print('Getting package creations...')
            #select distinct on (pr.id) pr.id, pr.name, pr.revision_timestamp from package_revision pr order by pr.id, pr.revision_timestamp;
            create_prs = model.Session.query(
                model.PackageRevision.id,
                model.PackageRevision.name,
                model.PackageRevision.revision_timestamp,
                model.PackageRevision.owner_org,
                model.PackageRevision.creator_user_id,
                model.Revision.author)\
                .distinct(model.PackageRevision.id)\
                .join(model.Revision)\
                .order_by(model.PackageRevision.id,
                          model.PackageRevision.revision_timestamp)
            create_prs = create_prs.all()
            print('...done')
            if args.dataset:
                create_prs = [pr for pr in create_prs
                              if pr.name == args.dataset]
            if args.since:
                create_prs = [pr for pr in create_prs
                              if pr.revision_timestamp > args.since]
            for id_, name, date, owner_org, creator_user_id, author in common.add_progress_bar(create_prs):
                if owner_org:
                    org_name = \
                        Organizations.instance().get_name_by_id(owner_org)
                else:
                    org_name = 'tbd'
                harvested = is_harvested(creator_user_id)
                user_name = author
                ds.add_event(
                    date, user_name, 'dataset-created',
                    dict(dataset_name=name,
                         dataset_id=id_,
                         organization_name=org_name,
                         harvested=harvested,
                         ),
                    print_it=False
                    )

        if args.event == 'dataset-updated':
            print('Getting package revisions...')
            # first package-revision of a dataset is the creation
            prs = model.Session.query(model.PackageRevision)\
                .order_by("revision_timestamp asc")
            # ignore the revision the package was created
            #select distinct on (pr.id) pr.revision_id from package_revision pr order by pr.id, pr.revision_timestamp;
            # package_creation_revision_ids = \
            #     model.Session.query(model.PackageRevision.revision_id)\
            #     .distinct(model.PackageRevision.id)\
            #     .order_by(model.PackageRevision.id,
            #               model.PackageRevision.revision_timestamp)\
            #     .subquery()
            package_creation_revision_ids = \
                model.Session.query(model.PackageRevision.revision_id)\
                .distinct(model.PackageRevision.id)\
                .order_by(model.PackageRevision.id,
                          model.PackageRevision.revision_timestamp)\
                .all()
            # couldnt get this to work with subquery
            # prs = prs.filter(model.PackageRevision.revision_id.notin_(
            #     package_creation_revision_ids))
            skip_revision_ids = set(
                t[0] for t in package_creation_revision_ids)
            if args.organization_name:
                print('Warning: organization filter only works for recent changes')
                org_id = Organizations.instance().get_id_by_name(
                    args.organization_name)
                prs = prs.filter(model.PackageRevision.owner_org==org_id)
            if args.dataset:
                prs = prs.filter(model.PackageRevision.name==args.dataset)
            if args.since:
                prs = prs.filter(model.PackageRevision.revision_timestamp > args.since)
            prs = prs\
                .limit(args.limit)\
                .all()
            print('...done {}'.format(len(prs)))
            for pr in common.add_progress_bar(prs):
                if pr.revision_id in skip_revision_ids:
                    continue
                skip_revision_ids.add(pr.revision_id)
                user_name = pr.revision.author
                date = pr.revision_timestamp
                org = pr.owner_org or pr.author
                org_name = \
                    Organizations.instance().get_name_by_id(org) \
                    or Organizations.instance().get_name_by_title(org) \
                    or org or ''
                harvested = is_harvested(pr.creator_user_id)
                if not date:
                    import pdb; pdb.set_trace()
                ds.add_event(
                    date, user_name, 'dataset-updated',
                    dict(dataset_name=pr.name,
                         dataset_id=pr.id,
                         organization_name=org_name,
                         harvested=harvested,
                         ),
                    print_it=False
                    )

            print('Getting extra revisions...')
            ers = model.Session.query(model.PackageExtraRevision)\
                .distinct(model.PackageExtraRevision.revision_timestamp, model.PackageExtraRevision.revision_id)\
                .order_by(model.PackageExtraRevision.revision_timestamp.desc(),model.PackageExtraRevision.revision_id)\
                .join(model.Package)
            if args.dataset:
                ers = ers.filter(model.Package.name==args.dataset)
            if args.since:
                ers = ers.filter(
                    model.PackageExtraRevision.revision_timestamp > args.since)
            ers = ers\
                .limit(args.limit)
            count = ers.count()
            print('...done {}'.format(count))
            for er in common.add_progress_bar(ers.yield_per(1000),
                                              maxval=count):
                if er.revision_id in skip_revision_ids:
                    continue
                skip_revision_ids.add(er.revision_id)
                user_name = er.revision.author
                date = er.revision_timestamp
                pkg = er.package
                org = pkg.owner_org or pkg.author
                org_name = \
                    Organizations.instance().get_name_by_id(org) \
                    or Organizations.instance().get_name_by_title(org) \
                    or org or ''
                harvested = is_harvested(pkg.creator_user_id)
                ds.add_event(
                    date, user_name, 'dataset-updated',
                    dict(dataset_name=pkg.name,
                         dataset_id=pkg.id,
                         organization_name=org_name,
                         harvested=harvested,
                         ),
                    print_it=False
                    )

            print('Getting resource revisions...')
            rrs = model.Session.query(model.ResourceRevision)\
                .distinct(model.ResourceRevision.revision_timestamp, model.ResourceRevision.revision_id)\
                .order_by(model.ResourceRevision.revision_timestamp.desc(), model.ResourceRevision.revision_id)\
                .join(model.ResourceGroup)\
                .join(model.Package)
            if args.since:
                rrs = rrs.filter(
                    model.ResourceRevision.revision_timestamp > args.since)
            if args.dataset:
                rrs = rrs.filter(model.Package.name==args.dataset)
            rrs = rrs\
                .limit(args.limit)
            count = rrs.count()
            print('...done {}'.format(count))
            for rr in common.add_progress_bar(rrs.yield_per(1000),
                                              maxval=count):
                if rr.revision_id in skip_revision_ids:
                    continue
                skip_revision_ids.add(rr.revision_id)
                user_name = rr.revision.author
                date = rr.revision_timestamp
                pkg = rr.resource_group.package
                org = pkg.owner_org or pkg.author
                org_name = \
                    Organizations.instance().get_name_by_id(org) \
                    or Organizations.instance().get_name_by_title(org) \
                    or org or ''
                harvested = is_harvested(pkg.creator_user_id)
                ds.add_event(
                    date, user_name, 'dataset-updated',
                    dict(dataset_name=pkg.name,
                         dataset_id=pkg.id,
                         organization_name=org_name,
                         harvested=harvested,
                         ),
                    print_it=False
                    )

    print(stats)
    # pr_q = model.Session.query(model.PackageRevision, model.Revision)\
    #     .filter(model.PackageRevision.id == pkg.id)\
    #     .filter_by(state='active')\
    #     .join(model.Revision)\
    #     .filter(~model.Revision.author.in_(system_authors)) \
    #     .filter(~model.Revision.author.like(system_author_template))
    # rr_q = model.Session.query(model.Package, model.ResourceRevision, model.Revision)\
    #     .filter(model.Package.id == pkg.id)\
    #     .filter_by(state='active')\
    #     .join(model.ResourceGroup)\
    #     .join(model.ResourceRevision,
    #           model.ResourceGroup.id == model.ResourceRevision.resource_group_id)\
    #     .join(model.Revision)\
    #     .filter(~model.Revision.author.in_(system_authors))\
    #     .filter(~model.Revision.author.like(system_author_template))
    # pe_q = model.Session.query(model.Package, model.PackageExtraRevision, model.Revision)\
    #     .filter(model.Package.id == pkg.id)\
    #     .filter_by(state='active')\
    #     .join(model.PackageExtraRevision,
    #           model.Package.id == model.PackageExtraRevision.package_id)\
    #     .join(model.Revision)\
    #     .filter(~model.Revision.author.in_(system_authors))\
    #     .filter(~model.Revision.author.like(system_author_template))


def mine_ckan_log():
    # The problem is that we only have logs back a couple of months
    ds = DataStore.instance()

    # logs
    if not args.event or args.event.startswith('publish-form'):
        count = 0
        for date, level, function, message in read_log(args.logfile):
            count += 1

            # new form (every render):
            # [ckan.lib.base] rendering /src/ckanext-dgu/ckanext/dgu/theme/templates/package/new.html [jinja2]
            # [ckan.lib.base] rendering /src/ckanext-dgu/ckanext/dgu/theme/templates/package/edit_form.html [jinja2]
            #if message.endswith('new.html [jinja2]'):
            #    ds.add_event(date, user['name'], 'login', None)

            # new form submit validate-error:
            # DEBUG [ckan.logic.action.create] package_create validate_errs={'name'

            # new form submit ok
            # DEBUG [ckan.logic.action.create] package_create validate_errs={} user=
            # INFO  [ckanext.dgu.plugin] Indexing: abc
            # DEBUG [ckan.logic.action.create] Created object abc
            if message.startswith('package_create validate_errs={}'):
                user, data = parse_validate_log_message(message)
                params = {'dataset_name': data['name']}
                ds.add_event(date, user, 'publish-form-new-submit-success',
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
            # Feb  7 08:59:16 co-prod3 2017-02-07 08:59:16,904 DEBUG [ckan.logic.action.update] package_update validate_errs={}
            if message.startswith('package_update validate_errs={}'):
                user, data = parse_validate_log_message(message)
                params = {'dataset_name': data['name']}
                ds.add_event(date, user, 'publish-form-edit-submit-success',
                           params)
        print('%s lines' % count)

def mine_drupal_users():
    ds = DataStore.instance()

    # users jsonl
    if not args.event or args.event in ('login',):
        for user in read_jsonl(args.drupal_users_jsonl):
            # login
            # date, user_name, login
            if not args.event or args.event == 'login':
                login_date = datetime.datetime.fromtimestamp(
                    float(user['login']))
                ds.add_event(login_date, user['name'], 'login', None)

def update_ckan_users():
    '''
    e.g.
    {
      "sysadmin": true,
      "state": "active",
      "password_hash": null,
      "email": "david@blah.com",
      "display_name": "davidread",
      "datasets": [ ... ],
      "about": "User account imported from Drupal system.",
      "email_hash": "d6fa5b63ffe634c3263bf73d76fb39de",
      "fullname": "davidread",
      "id": "c895ed6d-xyz",
      "name": "user_d845",
      "num_followers": 0,
      "number_administered_packages": 5,
      "number_of_edits": 5094,
      "openid": null
    }
    '''
    ckan_users = common.parse_jsonl(args.ckan_users)
    ckan_users_collection = DataStore.instance().db.ckan_users
    for ckan_user in ckan_users:
        # upsert
        filter_ = {"id": ckan_user['id']}
        ckan_users_collection.replace_one(filter_, ckan_user, upsert=True)

def update_drupal_user_table():
    '''
    e.g.
    {u'access': u'1485792509',
     u'created': u'1262863209',
     u'data': u'a:4:{s:7:\\contact\\";i:1;s:14:\\"picture_delete\\";s:0:\\"\\";s:14:\\"picture_upload\\";s:0:\\"\\";s:15:\\"ckan_publishers\\";a:2:{i:29;s:6:\\"editor\\";i:361;s:6:\\"editor\\";}}"',
     u'init': u'd.t.read@blah.com',
     u'language': u'',
     u'login': u'1485770410',
     u'mail': u'david.read@blah.com',
     u'name': u'davidread',
     u'pass': u'$S$Dy80Vp0blah',
     u'picture': u'0',
     u'signature': u'',
     u'signature_format': u'plain_text',
     u'status': u'1',
     u'theme': u'',
     u'timezone': u'Europe/London',
     u'uid': u'845'}
    '''
    drupal_users_collection = DataStore.instance().db.drupal_users
    with gzip.open(args.drupal_users_table, 'rb') as f:
        csv_reader = unicodecsv.DictReader(f, encoding='utf8')
        for user in csv_reader:
            # upsert
            if user['uid'] == '845':
                pprint(user)
            filter_ = {"uid": user['uid']}
            drupal_users_collection.replace_one(filter_, user, upsert=True)

def update_organizations():
    collection = DataStore.instance().db.organizations
    with gzip.open(args.drupal_users_table, 'rb') as f:
        csv_reader = unicodecsv.DictReader(f, encoding='utf8')
        for org in csv_reader:
            # upsert
            filter_ = {"id": org['id']}
            collection.replace_one(filter_, org, upsert=True)

def reset_db():
    DataStore.instance().wipe_events()
    print('Events wiped')

def print_summary():
    ds = DataStore.instance()
    print('Events')
    filter_ = get_filter()
    print('Count: {} of {}'.format(ds.db.events.find(filter_).count(),
                                   ds.db.events.count()))

    def run_query(grouping, project=None, print_it=True):
        aggregate_pipeline = [
            {'$match': filter_},
            ]
        if project:
            aggregate_pipeline.append(
            {'$project': project or {}}
            )
        aggregate_pipeline.extend([
            {'$group': {'_id': grouping,
                        'count': {'$sum': 1},
                        }
                        },
            {'$sort': {'_id': -1}},
            ])
        try:
            results = ds.db.events.aggregate(aggregate_pipeline)
        except OperationFailure, e:
            print('Fail {}'.format(e))
            import pdb; pdb.set_trace()
            for ev in ds.db.events.find(filter_):
                if not ev.get('date'):
                    print('No date: {}'.format(ev))
                    import pdb; pdb.set_trace()
        if print_it:
            for result in results:
                print(result)

    print('\noverall:')
    run_query({})

    print('\nover time:')
    project = None
    if args.time_divisions == 'years':
        grouping = OrderedDict({'year': {'$year': '$date'}})
    elif args.time_divisions == 'months':
        grouping = OrderedDict({'month': {'$month': '$date'},
                                'year': {'$year': '$date'}})
    elif args.time_divisions == 'quarters':
        project = {
            'harvested': 1,
            'organization_name': 1,
            'date': 1,
            'quarter': QUARTER_PROJECTION,
        }
        grouping = OrderedDict((('year', {'$year': '$date'}),
                                ('quarter', '$quarter')))
    run_query(grouping, project)

    print('\nharvest-breakdown:')
    grouping['harvested'] = {'harvested': '$harvested'}
    run_query(grouping, project)

    # print('\norganization:')
    # grouping['org'] = {'org': '$organization_name'}
    # run_query(grouping, project, print_it=False)


def print_by_org():
    ds = DataStore.instance()
    print('Events')
    filter_ = get_filter()
    aggregate_pipeline = [
        {'$match': filter_},
        {'$project': {
            'harvested': 1,
            'organization_name': 1,
            'user_or_harvested': USER_OR_HARVESTED_PROJECTION,
            'quarter': QUARTER_PROJECTION,
            }},
        {'$group': {'_id': OrderedDict((
            ('organization_name', '$organization_name'),
            ('user_or_harvested', '$user_or_harvested'),
            ('quarter', '$quarter'),
            )),
                    'count': {'$sum': 1}}},
        {'$sort': {'_id': 1}},
        ]
    out_rows = []
    for e in ds.db.events.aggregate(aggregate_pipeline):
        print(e)
        out_row = e[u'_id']
        out_row['count'] = e[u'count']
        out_rows.append(out_row)
    headers = ['organization_name', 'user_or_harvested', 'quarter', 'count']
    out_filename = args.output_csv
    with open(out_filename, 'wb') as f:
        csv_writer = unicodecsv.DictWriter(f,
                                           fieldnames=headers,
                                           encoding='utf-8')
        csv_writer.writeheader()
        for row in out_rows:
            csv_writer.writerow(row)
    print('Written', out_filename)


def print_events():
    ds = DataStore.instance()
    print('Events')
    filter_ = get_filter()
    assert set(filter_.keys()) & set(('organization_name', 'dataset_name')), \
        'You need to supply a filter - cannot print all events'
    for e in ds.db.events.find(filter_).sort('date'):
        date = e.pop('date')
        action = e.pop('action')
        # remove a few fields
        e.pop('dataset_id')
        e.pop('_id')
        if args.dataset:
            e.pop('dataset_name')
        print(date.strftime('%Y-%m-%d %H:%M'), action, e)


def dataset_notes(dataset):
    notes = []

    def get_extra(key, default=None):
        for extra in dataset['extras']:
            if extra.key == key:
                return extra['value']
        return default

    # Based on ckanext-report.notes.dataset
    # ' '.join(('Unpublished' if asbool(pkg.extras.get('unpublished')) else '', 'UKLP' if asbool(pkg.extras.get('UKLP')) else '', 'National Statistics Pub Hub' if pkg.extras.get('external_reference')=='ONSHUB' else ''))
    if asbool(dataset['extras'].get_extra('unpublished')):
        notes.append('Unpublished')
    if asbool(dataset['extras'].get_extra('UKLP')):
        notes.append('UKLP')
    if dataset['extras'].get_extra('external_reference') == 'ONSHUB':
        notes.append('National Statistics Pub Hub')
    return notes

def dataset_notes_from_dict(dataset_dict):
    notes = []

    def get_extra(key, default=None):
        for extra in dataset['extras']:
            if extra.key == key:
                return extra['value']
        return default

    # Based on ckanext-report.notes.dataset
    # ' '.join(('Unpublished' if asbool(pkg.extras.get('unpublished')) else '', 'UKLP' if asbool(pkg.extras.get('UKLP')) else '', 'National Statistics Pub Hub' if pkg.extras.get('external_reference')=='ONSHUB' else ''))
    if asbool(dataset['extras'].get_extra('unpublished')):
        notes.append('Unpublished')
    if asbool(dataset['extras'].get_extra('UKLP')):
        notes.append('UKLP')
    if dataset['extras'].get_extra('external_reference') == 'ONSHUB':
        notes.append('National Statistics Pub Hub')
    return notes

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

def get_filter():
    filter_ = {}
    if args.event:
        filter_['action'] = args.event
    if args.organization_name:
        filter_['organization_name'] = args.organization_name
    if args.dataset:
        filter_['dataset_name'] = args.dataset
    return filter_


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
    # Feb  7 08:59:16 co-prod3 2017-02-07 08:59:16,904 DEBUG [ckan.logic.action.update] package_update validate_errs={}
    try:
        date, level, function, message = re.search(
            r'(?P<date>\d{4}-\d{2}-\d{2} '
            '\d{2}:\d{2}:\d{2}),\d+ '
            '(?P<level>\w+)\s+'
            '\[(?P<function>[\w\.]+)\] (?P<message>.+)',
            line).groups()
    except AttributeError:
        assert 0, 'Error parsing:\n%s' % line
    date_format = '%Y-%m-%d %H:%M:%S'
    date = datetime.datetime.strptime(date, date_format)
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

class Organizations(object):
    _instance = None
    cache_upfront = False

    @classmethod
    def instance(cls):
        if not cls._instance:
            cls._instance = Organizations()
        return cls._instance

    def __init__(self):
        if Organizations.cache_upfront:
            from ckan import model
            print('Getting organization names_by_id')
            Organizations.names_by_id = dict(
                model.Session.query(model.Group.id, model.Group.name).all()
                )
            print('Getting organization names_by_title')
            Organizations.names_by_title = dict(
                model.Session.query(model.Group.title, model.Group.name).all()
                )
            print('Getting organization ids_by_name')
            Organizations.ids_by_name = dict(
                model.Session.query(model.Group.name, model.Group.id).all()
                )
            print('...done')

    def get_name_by_id(self, id_, default=None):
        if Organizations.cache_upfront:
            return Organizations.names_by_id.get(id_, default)
        from ckan import model
        org_name = model.Session.query(model.Group.name) \
            .filter_by(id=id_) \
            .first()
        if org_name is None:
            return default
        return org_name[0]

    def get_name_by_title(self, title, default=None):
        if Organizations.cache_upfront:
            return Organizations.names_by_title.get(title, default)
        from ckan import model
        org_name = model.Session.query(model.Group.name) \
            .filter_by(title=title) \
            .first()
        if org_name is None:
            return default
        return org_name[0]

    def get_id_by_name(self, name, default=None):
        if Organizations.cache_upfront:
            return Organizations.ids_by_name.get(name, default)
        from ckan import model
        org_id = model.Session.query(model.Group.id) \
            .filter_by(name=name) \
            .first()
        if org_id is None:
            return default
        return org_id[0]


class DataStore(object):
    _instance = None
    db = None

    @classmethod
    def instance(cls):
        if not cls._instance:
            cls._instance = DataStore()
        return cls._instance

    def __init__(self):
        client = MongoClient()
        self.db = client.publisher_profiles

    def add_event(self, date, user_name, action, params, print_it=False):
        identity = dict(
            date=date, user_name=user_name, action=action)
        event = identity.copy()
        event.update(params or {})
        if self.db.events.find_one(identity):
            if self.db.events.find_one(event):
                stats.add('Event already stored', repr(identity))
            else:
                event = self.db.events.replace_one(identity, event)
                stats.add('Event updated', repr(identity))
        else:
            event = self.db.events.insert_one(event)
            stats.add('Event added', repr(identity))
        if print_it:
            pprint((date, user_name, action, params))

    def get_events(self, limit=None):
        return sorted(self.values(), key=lambda x: x[0])[:limit]

    def wipe_events(self):
        self.db.drop_collection('events')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(help='Command')
    parser.add_argument('--limit', type=int, help='Limit queries')
    parser.add_argument('--since',
                        type=lambda d: datetime.datetime.strptime(d, '%Y-%m-%d'),
                        metavar='YYYY-MM-DD',
                        help='Limit queries to events since the given date')
    parser.add_argument('--event', choices=EVENT_TYPES,
                        help='Only one event type')
    parser.add_argument('--org', '--organization-name',
                        dest='organization_name',
                        help='Only one event org')
    parser.add_argument('--dataset',
                        help='Only one dataset')

    parser.add_argument('--reset', action='store_true',
                        help='Wipes the database and quits')

    subparser = subparsers.add_parser('ckan-db', help='Mines a CKAN database')
    subparser.add_argument('ckan_ini', help='Filepath of the ckan.ini')
    subparser.set_defaults(func=mine_ckan_db)

    subparser = subparsers.add_parser('ckan-log', help='Mines a CKAN log file')
    subparser.add_argument('logfile', help='ckan log file for analysis')
    subparser.set_defaults(func=mine_ckan_log)

    subparser = subparsers.add_parser('mine-drupal-users',
                                      help='Mines drupal users')
    subparser.add_argument('--drupal-users-jsonl',
                           default='drupal_users.jsonl.gz',
                           help='Location of the input '
                                'apps_public.jsonl.gz file')
    subparser.set_defaults(func=mine_drupal_users)

    subparser = subparsers.add_parser('update-ckan-users',
                                      help='Updates the users info in mongo')
    subparser.add_argument('ckan_users',
                           help='Filepath of ckan users.jsonl.gz')
    subparser.set_defaults(func=update_ckan_users)

    subparser = subparsers.add_parser('update-drupal-users-table',
                                      help='Updates the users info in mongo')
    subparser.add_argument('drupal_users_table',
                           help='Filepath of drupal_users_table.csv.gz')
    subparser.set_defaults(func=update_drupal_user_table)

    subparser = subparsers.add_parser('update-organizations',
                                      help='Updates the organization info in mongo (including editors/admins)')
    subparser.add_argument('organizations',
                           help='Filepath of data.gov.uk-ckan-meta-data-latest.organizations.jsonl.gz')
    subparser.set_defaults(func=update_organizations)

    subparser = subparsers.add_parser('reset-db')
    subparser.set_defaults(func=reset_db)

    subparser = subparsers.add_parser('print-summary')
    subparser.add_argument('--time-divisions',
                           choices=['years', 'months', 'quarters'],
                           default='months')
    subparser.set_defaults(func=print_summary)

    subparser = subparsers.add_parser('print-by-org')
    subparser.add_argument('--output-csv',
                           default='publisher_profiles.csv',
                           help='Output csv filename')
    subparser.set_defaults(func=print_by_org)

    subparser = subparsers.add_parser('print-events')
    subparser.set_defaults(func=print_events)

    args = parser.parse_args()

    args.func()