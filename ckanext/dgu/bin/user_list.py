'''
Saves a CSV list of users from Drupal\'s XMLRPC interface.
'''

import os
import logging
import sys
from sqlalchemy import engine_from_config
import csv
from pylons import config
from nose.tools import assert_equal


class SaveUsers(object):
    drupal_client = None

    @classmethod
    def load_config(cls, path):
        import paste.deploy
        conf = paste.deploy.appconfig('config:' + path)
        import ckan
        ckan.config.environment.load_environment(conf.global_conf,
                conf.local_conf)

    @classmethod
    def command(cls, config_ini):
        config_ini_filepath = os.path.abspath(config_ini)
        cls.load_config(config_ini_filepath)
        engine = engine_from_config(config, 'sqlalchemy.')

        from ckan import model
        from ckanext.dgu.drupalclient import DrupalClient, DrupalRequestError
        import ckanext.dgu.drupalclient
        
        logging.config.fileConfig(config_ini_filepath)
        log = logging.getLogger(os.path.basename(__file__))
        global global_log
        global_log = log

        model.init_model(engine)    
        model.repo.new_revision()

        # disable xmlrpc logs
        ckanext.dgu.drupalclient.log.disabled = True

        cls.drupal_client = DrupalClient({'xmlrpc_domain': 'data.gov.uk',
                                          'xmlrpc_username': 'CKAN_API',
                                          'xmlrpc_password': config.get('dgu.xmlrpc_password')})

        f = open('users.csv', 'wb')
        users = csv.writer(f, quoting=csv.QUOTE_ALL)
        rows = []

        for nid in range(28, 35000):
            try:
                user = cls.drupal_client.get_user_properties(nid)
            except DrupalRequestError, e:
                if '404' in str(e):
                    # node not a user
                    continue
                else:
                    raise
            publishers = user['publishers']
            if len(publishers) > 1:
                log.info('Multiple publishers for user %s [%s]!: %r',
                     user['name'], user['uid'], repr(publishers)[:100])
            if len(publishers) > 100:
                warn('Ignoring user %s [%s] with %i publishers!',
                     user['name'], user['uid'], len(publishers))
                continue
            for publisher in publishers:
                row = [user['uid'], user['name'], user['mail'], publisher]
                rows.append(row)
                log.info('User: %r', row)
                users.writerow(row)
            f.flush()
        f.close()

        log.info('Total number of users: %i', len(rows))
        log.info('Warnings: %r', warnings)


warnings = []
global_log = None
def warn(msg, *params):
    global warnings
    warnings.append(msg % params)
    global_log.warn(msg, *params)
    

def usage():
    print """
Saves a CSV list of users from Drupal\'s XMLRPC interface.
Usage:

    python user_list.py <CKAN config ini filepath>
    """
    
if __name__ == '__main__':
    if len(sys.argv) != 2:
        usage()
        sys.exit(0)
    cmd, config_ini= sys.argv
    SaveUsers.command(config_ini)
