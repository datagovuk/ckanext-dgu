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

            if isinstance(organogram, bool):
                print stats.add('Error: returned bool %s' % organogram,
                                int(fid))
                continue

            # NB private information:
            #  uid - user id of uploader
            #  not-yet-published organograms (publish_date=0)

            organogram.update(organogram_file)
            # timestamp here is an upload date, uid is an id of a user who uploaded it (user object can be retrieved from /services/rest/user/{uid})
            organogram['upload_date'] = organogram['timestamp']
            del organogram['timestamp']

            # Published and sign off dates are returned in original call as 'publish_date' and 'signoff_date', they can be timestamps or have value of 0 if not published or not signed off yet.

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

    nodes = drupal.get_nodes(type_filter='app')

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


def forum():
    drupal = get_drupal_client()

    topics = drupal.get_nodes(type_filter='forum')

    # e.g.
    # {u'changed': u'1457965356',
    #  u'comment': u'0',
    #  u'created': u'1457965350',
    #  u'language': u'und',
    #  u'nid': u'4490',
    #  u'promote': u'0',
    #  u'status': u'1',      - all have the same value
    #  u'sticky': u'0',      - ie stays at the top of the screen
    #  u'title': u'How to remove a dataset?',
    #  u'tnid': u'0',        - translation source
    #  u'translate': u'0',
    #  u'type': u'forum',
    #  u'uid': u'411731',    - user who created it (public)
    #  u'uri': u'https://test.data.gov.uk/services/rest/node/4490',
    #  u'vid': u'10900'}     - version

    print 'Topics to try: %s' % len(topics)

    i = 0
    with gzip.open(args.output_fpath, 'wb') as output_f:
        for topic in common.add_progress_bar(topics):
            if i > 0 and i % 100 == 0:
                print stats
            i += 1

            if args.topic and args.topic not in (topic['nid'], topic['title']):
                continue

            # Get main details from the node
            try:
                topic_node = drupal.get_node(topic['nid'])
            except DrupalRequestError, e:
                if 'There is no node with nid' in str(e):
                    print stats.add('Node id unknown',
                                    int(node['nid']))
                    continue
                print stats.add('Error: %s' % e, int(fid))
                continue

            # topic_node is a superset of topic
            topic = topic_node

            # interesting added fields:
            # {u'body': {u'und': [{
            #         u'format': u'filtered_html',
            #         u'safe_summary': u'',
            #         u'safe_value': u'<p>Once a dataset has been added to data.gov.uk it seems that I cannot remove it? The contact page is also ineffective as I have been waiting for a response for a very long time now.</p>\n<p>Does anyone know how to remove a dataset?\xa0</p>\n',
            #         u'summary': u'',
            #         u'value': u'<p>Once a dataset has been added to data.gov.uk it seems that I cannot remove it? The contact page is also ineffective as I have been waiting for a response for a very long time now.</p>\r\n\r\n<p>Does anyone know how to remove a dataset?&nbsp;</p>\r\n'}]},
            #  "path": "https://test.data.gov.uk/forum/general-discussion/how-remove-dataset",

            if topic_node['status'] != '1':
                print stats.add('Unknown status: %s' % topic_node['status'],
                                topic_node['nid'])

            # TODO add in comments

            if not args.topic:
                output_f.write(json.dumps(topic) + '\n')
            stats.add('Topic dumped ok', int(topic['nid']))

            if args.topic:
                pprint(organogram)

    print '\nForum:', stats
    if not args.topic:
        print '\nWritten to: %s' % args.output_fpath
    else:
        print '\nNot written due to filter'


def library():
    drupal = get_drupal_client()

    items = drupal.get_nodes(type_filter='resource')

    # e.g.
    # {
    # "nid": "3341",
    # "vid": "6194",
    # "type": "resource",
    # "language": "und",
    # "title": "UK Location Metadata Editor 2 - User Guide",
    # "uid": "845",              - user that added it
    # "status": "1",
    # "created": "1406568348",
    # "changed": "1447195725",
    # "comment": "0",
    # "promote": "1",
    # "sticky": "0",
    # "tnid": "0",
    # "translate": "0",
    # "uri": "https://test.data.gov.uk/services/rest/node/3341"
    # },

    print 'Library items to try: %s' % len(items)

    i = 0
    with gzip.open(args.output_fpath, 'wb') as output_f:
        for item in common.add_progress_bar(items):
            if i > 0 and i % 100 == 0:
                print stats
            i += 1

            if args.item and args.item not in (item['nid'], item['title']):
                continue

            # Get main details from the node
            try:
                item_node = drupal.get_node(item['nid'])
            except DrupalRequestError, e:
                if 'There is no node with nid' in str(e):
                    print stats.add('Node id unknown',
                                    int(item['nid']))
                    continue
                print stats.add('Error: %s' % e, int(item['nid']))
                continue

            # item_node is a superset of item apart from 'uri'
            item.update(item_node)

            # interesting added fields:
            # u'field_resource_file': {u'und': [
            #   {u'alt': u'',
            #    u'description': u'',
            #    u'display': u'1',
            #    u'fid': u'5294',
            #    u'filemime': u'application/vnd.oasis.opendocument.text',
            #    u'filename': u'20150415 ODUG Minutes.odt',
            #    u'filesize': u'37128',
            #    u'metadata': [],
            #    u'rdf_mapping': [],
            #    u'status': u'1',
            #    u'timestamp': u'1432825729',
            #    u'title': u'',
            #    u'type': u'document',
            #    u'uid': u'395502',
            #    u'uri': u'public://library/20150415 ODUG Minutes.odt'}]},
            # which relates to:
            # https://data.gov.uk/sites/default/files/20150415 ODUG Minutes.odt
            # "field_document_type": {
            # "und": [
            #   {
            #     "tid": "85"
            #   }
            # ]
            # "field_category": {
            #  "und": [
            #   {
            #     "tid": "83"
            #   },
            #   {
            #     "tid": "84"
            #   }
            #  ]
            # },

            # NB Some private fields:
            # 'name' (of uploader)
            # 'revision_uid'
            # 'uid' (including in 'field_resource_file')

            # document types found by inspecting the facets urls at:
            # https://data.gov.uk/library
            # Also from the drupal db:
            # select * from taxonomy_term_data where vid=2;
            document_type_map = {
                85: 'Case study',
                90: 'ODUG Minutes',
                87: 'Guidance',
                86: 'Data strategy',
                88: 'Transparency policy',
                89: 'Minutes Transparency Board',
                91: 'ODUG Papers',
                }
            try:
                type_ids = [
                    item_['tid']
                    for item_ in item.get('field_document_type', {})['und']] \
                    if item.get('field_document_type') else []
            except TypeError:
                import pdb; pdb.set_trace()
            try:
                item['document_type'] = document_type_map[int(type_ids[0])] \
                    if type_ids else ''
            except KeyError:
                print stats.add('Unknown document_type id %s' % type_ids[0],
                                item['nid'])
            if len(type_ids) > 1:
                print stats.add('Multiple tids: %s' % len(type_ids),
                                item['nid'])

            # categories found by inspecting the facets urls at:
            # https://data.gov.uk/library
            # or drupal db:
            # select tid, name from taxonomy_term_data where vid=1 order by tid;
            category_map = {
                83: 'Government',
                84: 'Policy',
                79: 'Location',
                76: 'Society',
                81: 'Administration',
                80: 'Linked data',
                78: 'Transportation',
                74: 'Education',
                73: 'Environment',
                }
            try:
                category_ids = [
                    item_['tid']
                    for item_ in item.get('field_category', {})['und']] \
                    if item.get('field_category') else []
            except TypeError:
                import pdb; pdb.set_trace()
            try:
                item['categories'] = [
                    category_map[int(tid)] for tid in category_ids]
            except KeyError:
                print stats.add('Unknown category id %s' % type_ids[0],
                                item['nid'])

            if item['status'] != '1':
                print stats.add('Unknown status: %s' % item['status'],
                                item['nid'])

            # TODO add in comments

            if not args.item:
                output_f.write(json.dumps(item) + '\n')
            stats.add('Library item dumped ok', int(item['nid']))

            if args.item:
                pprint(item)

    print '\nLibrary:', stats
    if not args.item:
        print '\nWritten to: %s' % args.output_fpath
    else:
        print '\nNot written due to filter'


def dataset_requests():
    drupal = get_drupal_client()

    requests = drupal.get_nodes(type_filter='dataset_request')

    # e.g.
    # {u'changed': u'1470914906',
    #  u'comment': u'0',
    #  u'created': u'1470905244',
    #  u'language': u'und',
    #  u'nid': u'4994',
    #  u'promote': u'0',
    #  u'status': u'1',
    #  u'sticky': u'0',
    #  u'title': u'Daily Average temperature UK 2014 to 2016 ',
    #  u'tnid': u'0',
    #  u'translate': u'0',
    #  u'type': u'dataset_request',
    #  u'uid': u'425562',
    #  u'uri': u'https://data.gov.uk/services/rest/node/4994',
    #  u'vid': u'11564'}

    print 'Dataset requests to try: %s' % len(requests)

    i = 0
    with gzip.open(args.output_fpath, 'wb') as output_f:
        for request in common.add_progress_bar(requests):
            if i > 0 and i % 100 == 0:
                print stats
            i += 1

            if args.request and args.request not in (request['nid'],
                                                     request['title']):
                continue

            # Get main details from the node
            try:
                request_node = drupal.get_node(request['nid'])
            except DrupalRequestError, e:
                if 'There is no node with nid' in str(e):
                    print stats.add('Node id unknown',
                                    int(request['nid']))
                    continue
                print stats.add('Error: %s' % e, int(request['nid']))
                continue

            # request_node is a superset of request apart from 'uri'
            request.update(request_node)

            # interesting added fields:
            #  u'field_data_set_description': {u'und': [
            #     {u'format': None,
            #      u'safe_value': u'Hi there, I am doing a masters dissertation and require a data set that shows the average daily temperature for the UK from 1 March 2014 to 31 July 2016. For example with the following columns: Date, Average Temperature. E.g. 01032014, 12. The data doesn&#039;t need to broken down any further than that. The basic date and average temperature as a number will do. ',
            #      u'value': u"Hi there, I am doing a masters dissertation and require a data set that shows the average daily temperature for the UK from 1 March 2014 to 31 July 2016. For example with the following columns: Date, Average Temperature. E.g. 01032014, 12. The data doesn't need to broken down any further than that. The basic date and average temperature as a number will do. "}]},
            #   u'field_data_use_detail': {u'und': [
            #      {u'format': None,
            #       u'safe_value': u'This would help me complete my dissertation as I am trying to show the correlation between temperature and revenue. ',
            #       u'value': u'This would help me complete my dissertation as I am trying to show the correlation between temperature and revenue. '}]},
            #  u'field_benefits_overview': {u'und': [
            #      {u'format': None,
            #       u'safe_value': u'The benefits of the data would mean I could show there is a correlation between temperature and revenue. Basically that when its warmer, revenue increases. ',
            #       u'value': u'The benefits of the data would mean I could show there is a correlation between temperature and revenue. Basically that when its warmer, revenue increases. '}]},
            #  u'field_data_themes': {u'und': [{u'tid': u'73'}, {u'tid': u'74'}]},
            #  u'field_data_use': {u'und': [{u'value': u'2'}, {u'value': u'4'}]},
            #  u'name': u'Tal',  (public)
            #   "field_review_outcome": {
            #    "und": [
            #      {
            #        "value": "4"
            #      }
            #    ]
            #  },
            # 'requested on behalf of organization':
            #   "field_organisation_name": {
            #   "und": [
            #     {
            #       "format": "",
            #       "value": "Metcentral Ltd",
            #       "safe_value": "Metcentral Ltd"
            #     }
            #   ]
            # },

            # # private fields:
            #  u'field_data_holder': {u'und': [{u'format': None,
            #                       u'safe_value': u'Met office? ',
            #                       u'value': u'Met office? '}]},
            #  u'field_review_notes': [],
            #  u'field_review_outcome': [],
            #  u'field_review_status': {u'und': [{u'value': u'0'}]},
            #  u'field_submitter_type': {u'und': [{u'value': u'1'}]},
            #  "log"

            # Categories
            # ids found by inspecting the facets urls at:
            # https://data.gov.uk/search/everything/?f[0]=bundle%3Adataset_request
            organization_type_map = {
                7: 'Academic or Research',
                3: 'Small to Medium Business',
                2: 'Start up',
                4: 'Large Company (Over 250 employees)',
                6: 'Public Sector Organisation',
                5: 'Voluntary sector or not-for-profit organisation',
                }
            status_map = {
                0: 'New',
                1: 'Escalated to data holder',
                2: 'Queried by data holder',
                3: 'ODUG developing business case',
                4: 'Scheduled for release',
                5: 'Postponed',
                6: 'Closed',
                }
            outcome_map = {
                3: 'Not a data request or a data issue',
                2: 'Data already available',
                4: 'Technical issue resolved',
                1: 'Data cannot be released',
                0: 'New dataset released',
                }
            reason_map = {
                9: 'Other',
                6: 'The data is published but not in a format I can download and use (e.g. only displayed onscreen or only downloadable as a PDF rather than CVS)',
                7: 'The data is not up-to-date',
                1: 'The data is supposed to be published but the download links don\'t work',
                8: 'A version of the data is published but I need it in a different version',
                3: 'There are financial charges for the data',
                2: 'The data is available but the licensing terms are too restrictive',
                5: 'The data is subject to restrictions because of personal confidentiality',
                4: 'The data is subject to restrictions because of commercial confidentiality',
                }
            #
            # select tid, name from taxonomy_term_data where vid=1 order by tid;
            data_themes_map = {
                72: 'Health',
                73: 'Environment',
                74: 'Education',
                75: 'Finance',
                76: 'Society',
                77: 'Defence',
                78: 'Transportation',
                79: 'Location',
                80: 'Linked data',
                81: 'Administration',
                82: 'Spending data',
                83: 'Government',
                84: 'Policy',
            }

            def explain_id_meaning(id_type, id_map,
                                   field_name, field_dict_key,
                                   should_be_one_value=True):
                try:
                    ids = [
                        request_[field_dict_key]
                        for request_ in request.get(field_name, {})['und']] \
                        if request.get(field_name) else []
                except TypeError:
                    import pdb; pdb.set_trace()
                ids_mapped = [id_map[int(id)] for id in ids]
                if should_be_one_value:
                    if len(ids) == 0:
                        value = None
                    elif len(ids) > 1:
                        print stats.add(
                            'Warning - multiple values for %s' % field_name,
                            request['nid'])
                        value = ids_mapped[0]
                    else:
                        value = ids_mapped[0]
                else:
                    value = ids_mapped
                try:
                    request[id_type] = value
                except KeyError:
                    print stats.add('Unknown %s id %s' %
                                    (id_type, type_ids[0]),
                                    request['nid'])
            explain_id_meaning('organization_type', organization_type_map,
                               'field_organisation_type', 'value')
            explain_id_meaning('review_status', status_map,
                               'field_review_status', 'value')
            explain_id_meaning('review_outcome', outcome_map,
                               'field_review_outcome', 'value')
            explain_id_meaning('barriers_reason', reason_map,
                               'field_barriers_reason', 'value')
            explain_id_meaning('data_theme', data_themes_map,
                               'field_data_themes', 'tid',
                               should_be_one_value=False)

            if request['status'] != '1':
                print stats.add('Unknown status: %s' % request['status'],
                                request['nid'])

            # TODO add in comments
            # NB confidential requests are excluded (would need Drupal changes as I get "Access denied for user anonymous" eg for /services/rest/node/3137)

            if not args.request:
                output_f.write(json.dumps(request) + '\n')
            stats.add('Data Request dumped ok', int(request['nid']))

            if args.request:
                pprint(request)

    print '\nData requests:', stats
    if not args.request:
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

    subparser = subparsers.add_parser('forum')
    subparser.set_defaults(func=forum)
    subparser.add_argument('--output_fpath',
                           default='forum.jsonl.gz',
                           help='Location of the output '
                                'forum.jsonl.gz file')
    subparser.add_argument('--topic',
                           help='Only do it for a single forum topic'
                                '(eg "How to remove a dataset?")')

    subparser = subparsers.add_parser('library')
    subparser.set_defaults(func=library)
    subparser.add_argument('--output_fpath',
                           default='library.jsonl.gz',
                           help='Location of the output '
                                'library.jsonl.gz file')
    subparser.add_argument('--item',
                           help='Only do it for a single library item'
                                '(eg "Blossom Bristol")')

    subparser = subparsers.add_parser('dataset_requests')
    subparser.set_defaults(func=dataset_requests)
    subparser.add_argument('--output_fpath',
                           default='dataset_requests.jsonl.gz',
                           help='Location of the output '
                                'dataset_requests.jsonl.gz file')
    subparser.add_argument('--request',
                           help='Only do it for a single dataset request'
                                '(eg "Daily Average temperature UK 2014 to 2016 ")')
    args = parser.parse_args()

    # call the function
    args.func()
