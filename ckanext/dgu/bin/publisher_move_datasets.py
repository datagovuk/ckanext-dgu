'''
Script for moving datasets from one organization to another.
'''

import common
from optparse import OptionParser
from running_stats import Stats


# This creates a user for the script, so that you can do an edit using the API. The idea was to get the publisher quarterly report to ignore edits by this user. But changing owner_org requires sysadmin user, and I wasn't sure about doing that.
def get_script_user(script_name):
    import string
    import random
    from ckan.plugins import toolkit
    user_name = 'script-%s' % script_name
    try:
        user = toolkit.get_action('user_show')(
            context={'ignore_auth': True},
            data_dict={'id': user_name})
    except toolkit.ObjectNotFound:
        password = ''.join(random.SystemRandom().choice(
            string.ascii_uppercase + string.ascii_lowercase + string.digits)
            for _ in range(20))
        user = toolkit.get_action('user_create')(
            context={'ignore_auth': True, 'user': None},
            data_dict={'name': user_name,
                       'email': 'dummy@example.com',
                       'password': password})
    return user


class MoveDatasets(object):
    @classmethod
    def command(cls, config_ini, org_names):
        common.load_config(config_ini)
        common.register_translator()
        from ckan.plugins import toolkit
        from ckan import model
        orgs = [toolkit.get_action('organization_show')(
                data_dict={'id': org_name})
                for org_name in org_names]
        source_org, dest_org = orgs
        assert source_org
        assert dest_org
        search_results = toolkit.get_action('package_search')(
            data_dict=dict(fq='publisher:%s' % source_org['name'], rows=1000))
        print 'Datasets: %s' % search_results['count']
        stats = Stats()
        if len(search_results['results']) != search_results['count']:
            assert 0, 'need to implement paging'

        #context = {
        #    'user': get_script_user(__name__)['name'],
        #    'ignore_auth': True,
        #    'model': model}
        rev = model.repo.new_revision()
        rev.author = 'script-%s.py' % __file__
        for dataset in search_results['results']:
            model.Package.get(dataset['id']).owner_org = dest_org['id']
            #dataset_ = toolkit.get_action('package_patch')(
            #    context=context,
            #    data_dict=dict(id=dataset['id'], owner_org=dest_org['id']))
            print stats.add('Changed owner_org', dataset['name'])
        print stats.report()
        print 'Writing'
        model.Session.commit()

usage = __doc__ + '''
Usage:
    python publisher_move_datasets.py <ckan.ini> <source_publisher> <destination_publisher>'''

if __name__ == '__main__':
    parser = OptionParser(usage=usage)
    (options, args) = parser.parse_args()
    if len(args) != 3:
        parser.error('Wrong number of arguments: %s', len(args))
    config_ini = args[0]
    org_names = args[1:3]
    MoveDatasets.command(config_ini, org_names)
