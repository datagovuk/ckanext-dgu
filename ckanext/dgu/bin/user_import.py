##############################################################################
# Uses the publisher node lookup csv and a new user csv to create users and
# associate them with the appropriate publishers.
#
# SELECT U.uid, U.name, U.mail, R.name AS 'role_name',
#        A.nid AS 'old_publisher_id'
# FROM users U
# INNER JOIN users_roles AS UR ON UR.uid = U.uid
# INNER JOIN role AS R ON R.rid = UR.rid
# LEFT OUTER JOIN acl_user AS AU ON AU.uid= U.uid
# LEFT OUTER JOIN acl_node AS A ON AU.acl_id = A.acl_id
# WHERE R.name in ('publishing user', 'publisher admin')
# AND A.nid IS NOT NULL LIMIT 100000;
#
##############################################################################

import os
import logging
import sys
import csv
import re
import ckan
import uuid
from ckan import model
from ckan.lib.search import rebuild
from ckan.lib.munge import munge_title_to_name
from sqlalchemy import engine_from_config
from ckan.logic.schema import user_new_form_schema
from ckan.logic import get_action, tuplize_dict, clean_dict, parse_params
from pylons import config

publishers = {}

def load_config(path):
    import paste.deploy
    conf = paste.deploy.appconfig('config:' + path)
    ckan.config.environment.load_environment(conf.global_conf,
            conf.local_conf)

def _add_new_user(username, email, role):
    from ckan.logic.validators import name_validator

    try:
        name_validator(username, {})
    except:
        username =munge_title_to_name( username)

    ctx = {
            'session': model.Session,
            'user'   : u'127.0.0.1',
            'model'  : model,
            'save'   : True,
            'message': u'',
            'schema' : user_new_form_schema()
    }
    data = {
        'password1': u'123123',
        'password2': u'123123',
        'name': username,
        'fullname' : u'',
        'save': u'',
        'email': email
    }
    try:
        user = get_action('user_create')(ctx, data)
    except Exception as e:
        return username, None

    return username, user



def command():
    load_config( os.path.abspath( sys.argv[1] ) )
    engine = engine_from_config(config,'sqlalchemy.')

    model.init_model(engine)
    model.repo.new_revision()

    with open(sys.argv[2], 'rU') as f:
        reader = csv.reader( f)
        reader.next() # skip headers
        for row in reader:
            publishers[ int(row[0]) ] = munge_title_to_name(row[1])

    with open(sys.argv[3], 'rU') as f:
        reader = csv.reader( f)
        reader.next() # skip headers
        for row in reader:
            oldid, name,email, role, oldpubid = row

            # create a new user
            uname, u = _add_new_user( name, email, role )
            if not u:
                try:
                    u = model.Session.query(model.User).\
                             filter(model.User.name == uname).all()[0]
                    u = u.as_dict()
                except:
                    print 'Failed to find user ', name
                    continue

            # Find the publisher and add them as admin/editor
            if oldpubid and role:
                ids = model.Session.query("id")\
                            .from_statement("select id from public.group where name='%s'" %
                                             publishers[ int(oldpubid) ]).all()
                publisher_id = ids[0][0]

                capacity = None
                if role == 'publisher admin':
                    capacity = 'admin'
                elif role == 'publishing user':
                    capacity = 'editor'

                if capacity:
                    # Check for Member where table_name is u['id']
                    res = model.Session.query(model.Member).\
                            from_statement(MEMBER_LOOKUP).\
                            params(userid=u['id'], groupid=publisher_id).all()
                    if len(res) == 0:
                        m = model.Member(group_id=publisher_id, table_id=u['id'],
                                         table_name='user', capacity=capacity)
                        model.Session.add( m )

            # Update harvest_source user_id field to new user id.
            userid = u['id']
            model.Session.execute(HARVEST_QUERY,params={'uid':userid, 'oldid': str(oldid)})
            model.Session.commit()


HARVEST_QUERY = "UPDATE harvest_source set user_id=:uid WHERE user_id=:oldid"
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
        sys.exit(0)
    command()
