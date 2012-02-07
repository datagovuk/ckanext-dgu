'''
Daily script for gov server
'''
import os
import logging
import sys
import zipfile
import traceback
import datetime
import re
from sqlalchemy import engine_from_config
# Import ckan as it changes the dependent packages imported
import ckan
from ckan import model
from ckan.lib.munge import munge_title_to_name

def load_config(path):
    import paste.deploy
    conf = paste.deploy.appconfig('config:' + path)
    ckan.config.environment.load_environment(conf.global_conf,
            conf.local_conf)

def command():
    import csv
    from pylons import config

    load_config( os.path.abspath( sys.argv[1] ) )
    engine = engine_from_config(config,'sqlalchemy.')

    model.init_model(engine)    
    model.repo.new_revision()

   #'title', 'nid', 'parent_title', 'field_pub_parent_nid', 'field_acronym_value', 'field_pub_email_display_email', 'field_pub_web_url', 'field_pub_web_title'
    with open(sys.argv[2], 'rU') as f:
        reader = csv.reader( f) 
        reader.next() # skip headers
        for row in reader:
            slug = munge_title_to_name( row[0] )
            g = model.Group.get( slug ) 
            if not g:
                g = model.Group(name=slug, title=row[0], type='publisher')
                model.Session.add( g )
                model.Session.flush()

            if row[2]:
                parent_slug = munge_title_to_name( row[2] )
                parent = model.Group.get( parent_slug )
                if parent:
                    if model.Session.query(model.Member).\
                       filter(model.Member.group==parent and model.Member.table_id==g.id).count() == 0:
                        m = model.Member(group=parent, table_id=g.id, table_name='group')                 
                        model.Session.add( m )
        model.Session.commit()        
        f.seek(0)
 
    all_groups = model.Session.query(model.Group).\
                       filter(model.Group.type == 'publisher').order_by('title').all()
    print len(all_groups)

    

def usage():
    print """
Usage:
  Imports publishers from the specified CSV file.

    python import_publishers.py <path to ini file>  <path to csv file>
    """
    
if __name__ == '__main__':
    if len(sys.argv) != 3:
        usage()
        sys.exit(0)
    command()
