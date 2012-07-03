'''
Uses the publisher node lookup csv and a new user csv to create users and
associate them with the appropriate publishers.

To create the users.csv:

python ../dgu/ckanext/dgu/bin/user_list.py dgutest.ini
(was done using an SQL query, but that missed off some people)

To create nodepublishermap.csv see publisher_datasets_assoc.py

'''

import os
import logging
import sys
import csv
import re
import uuid
import warnings as warnings_
from sqlalchemy import engine_from_config
from pylons import config, translator
import paste.deploy
from paste.registry import Registry

publishers = {}

def load_config(path):
    conf = paste.deploy.appconfig('config:' + path)

    import ckan
    ckan.config.environment.load_environment(conf.global_conf,
            conf.local_conf)

def get_ckan_username_from_drupal_id(node_id):
    return 'user_d%i' % node_id

def _add_new_user(node_id, username, email):
    '''Tries to create a user based on the parameters.
    Returns (username, ckan_user_id)
    '''
    from ckan.logic.validators import name_validator
    from ckan.lib.navl.dictization_functions import Invalid
    from ckan import model
    from ckan.logic.schema import user_new_form_schema
    from ckan.logic import get_action

    name = get_ckan_username_from_drupal_id(node_id)

    try:
        name_validator(name, {})
    except Invalid, e:
        log.error('Name does not validate %r - not created user.', username)
        return name, None

    existing_user = model.User.by_name(name)
    if existing_user:
        log.info('User %r already exists', name)
        return name, existing_user.id

    ctx = {
            'session': model.Session,
            'user'   : u'127.0.0.1',
            'model'  : model,
            'save'   : True,
            'message': u'',
            'schema' : user_new_form_schema()
    }
    data = {
        'password1': u'123123', # we use drupal for auth
        'password2': u'123123',
        'name': name,
        'fullname' : unicode(username),
        'save': u'',
        'email': email
    }
    try:
        user = get_action('user_create')(ctx, data)
    except Exception as e:
        warn('Could not create user: %r %s', e, e)
        return username, None

    return username, user['id']



def command(config_ini, nodepublisher_csv, users_csv):
    config_ini_filepath = os.path.abspath(config_ini)
    load_config(config_ini_filepath)
    engine = engine_from_config(config, 'sqlalchemy.')

    from ckan import model
    from ckan.lib.munge import munge_title_to_name
    import ckanext.dgu.plugin
    
    logging.config.fileConfig(config_ini_filepath)
    global log
    log = logging.getLogger(os.path.basename(__file__))

    model.init_model(engine)

    # Register a translator in this thread so that
    # the _() functions in logic layer can work
    from ckan.lib.cli import MockTranslator
    registry=Registry()
    registry.prepare()
    translator_obj=MockTranslator() 
    registry.register(translator, translator_obj) 

    with open(nodepublisher_csv, 'rU') as f:
        reader = csv.reader( f)
        for row in reader:
            publishers[ int(row[0]) ] = munge_title_to_name(row[1])
    log.info('Opened list of %i publishers', reader.line_num)

    # get rid of flash message warnings
    warnings_.filterwarnings('ignore', '.*flash message.*')
    ckanext.dgu.plugin.log.disabled = True

    with open(users_csv, 'rU') as f:
        reader = csv.reader(f)
        for row in reader:
            model.repo.new_revision()
            node_id, name, email, publisher_id = row

            # create a new user
            uname, user_id = _add_new_user(int(node_id), name, email)
            if not user_id:
                # validation error. warning already printed
                continue

            # Find the publisher and add them as editor
            if node_id:
                publisher_name = publishers[int(publisher_id)]
                publisher = model.Group.by_name(publisher_name)
		if not publisher:
                    warn('Could not find publisher %r so skipping making %r editor for it.', 
                         publisher_name, name)
                    continue

                capacity = 'editor'

                # Check for Member where table_name is u['id']
                res = model.Session.query(model.Member).\
                      from_statement(MEMBER_LOOKUP).\
                      params(userid=user_id, groupid=publisher.id).all()
                if len(res) == 0:
                    m = model.Member(group_id=publisher.id, table_id=user_id,
                                     table_name='user', capacity=capacity)
                    model.Session.add(m)
                    log.info('Made %r editor for %r', name, publisher_name)
                else:
                    log.info('%r already editor for %r', name, publisher_name)

            # Update harvest_source user_id field to new user id.
            model.Session.execute(HARVEST_QUERY,params={'uid':user_id, 'node_id': str(node_id)})
            model.Session.commit()
    log.info('Processed list of %i users', reader.line_num)

    log.info('Warnings (%i): %r', len(warnings), warnings)

warnings = []
log = None
def warn(msg, *params):
    global warnings
    warnings.append(msg % params)
    log.warn(msg, *params)

HARVEST_QUERY = "UPDATE harvest_source set user_id=:uid WHERE user_id=:node_id"
MEMBER_LOOKUP = "select * from public.member where table_id=:userid and group_id=:groupid"

def usage():
    print """
Usage:
    Loads users from the DGU database export and maps them to publishers along with their roles.

    python user_import.py <path to ini file>  <path to nodepublisher csv file> <path to user csv file>
    """

if __name__ == '__main__':
    if len(sys.argv) != 4:
        usage()
        sys.exit(1)
    cmd, config_ini, nodepublisher_csv, users_csv = sys.argv
    command(config_ini, nodepublisher_csv, users_csv)
