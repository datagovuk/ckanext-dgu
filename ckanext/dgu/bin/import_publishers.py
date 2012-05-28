'''
Imports the DGU Publisher hierarchy from Drupal\'s hierarchy of publishers. This is obtained in CSV format using query:
    SELECT r.title, 
       p.nid,
       (SELECT title FROM dgu_drupal.node_revisions AS rr WHERE rr.nid = p.field_pub_parent_nid ) AS 'parent_title',
       p.field_pub_parent_nid, 
       p.field_acronym_value, 
       p.field_pub_email_display_email, 
       p.field_pub_web_url, 
       p.field_pub_web_title
    FROM dgu_drupal.content_type_publisher AS p
    INNER JOIN dgu_drupal.node_revisions AS r ON r.vid = p.vid;
'''

import os
import logging
import sys
from sqlalchemy import engine_from_config
import csv
from pylons import config
from nose.tools import assert_equal

# These publishers must be created by mistake
ignore_publishers = (28266, #'Hazel Lee'
                     28267, #'George Wilson'
                     11606, # ONS repeat, sub-pub of the other
                     20054, # Met Office repeat, falsely under MoD
                     33036, # "Royal Borough of Windsor and Maidenhead" repeat
                     32619, # "Monmouthshire County Council" under Welsh Government
                     )

def load_config(path):
    import paste.deploy
    conf = paste.deploy.appconfig('config:' + path)
    import ckan
    ckan.config.environment.load_environment(conf.global_conf,
            conf.local_conf)

def command(config_ini, drupal_csv):
    load_config(os.path.abspath(config_ini))
    engine = engine_from_config(config, 'sqlalchemy.')

    from ckan import model
    from ckan.lib.munge import munge_title_to_name

    FORMAT = '%(asctime)-7s %(levelname)s %(message)s'
    logging.basicConfig(format=FORMAT, level=logging.INFO)
    log = logging.getLogger(__name__)
    global global_log
    global_log = log

    model.init_model(engine)    
    model.repo.new_revision()

    with open(drupal_csv, 'rU') as drupal_csv_f:
        reader = csv.reader(drupal_csv_f)
        headers = reader.next()
        assert_equal(headers, ['title', 'nid', 'parent_title', 'field_pub_parent_nid', 'field_acronym_value', 'field_pub_email_display_email', 'field_pub_web_url', 'field_pub_web_title'])
        for row in reader:
            title, nid, parent_title, field_pub_parent_nid, field_acronym_value, field_pub_email_display_email, field_pub_web_url, field_pub_web_title = row
            title = title.strip()

            if title == 'title':
                # header row
                continue
            if nid in ignore_publishers:
                log.info('Publisher ignored: %s (%s)', title, nid)
                continue
            
            slug = munge_title_to_name( title )
            g = model.Group.get( slug ) 
            if g:
                log.info('Publisher already exists in db: %s', slug)
                continue
                
            g = model.Group(name=slug, title=title, type='publisher')
            g.extras['contact-name'] = '%s contact' % field_pub_web_title if field_pub_web_title else ''
            g.extras['contact-email'] = field_pub_email_display_email
            g.extras['contact-phone'] = ''
            g.extras['foi-name'] = ''
            g.extras['foi-email'] = ''
            g.extras['foi-phone'] = ''
            g.extras['abbreviation'] = field_acronym_value or ''
            g.extras[''] = field_acronym_value or ''
            model.Session.add(g)
            model.Session.commit()
            title_and_abbreviation = '%s (%s)' % (title, field_acronym_value) if field_acronym_value else title
            log.info('Added publisher: %s', title_and_abbreviation)

        # Run through drupal_csv again to use parent info - make publishers members of
        # their parents
        drupal_csv_f.seek(0)
        for row in reader:
            title, nid, parent_title, field_pub_parent_nid, field_acronym_value, field_pub_email_display_email, field_pub_web_url, field_pub_web_title = row
            title = title.strip()

            if title == 'title':
                # header row
                continue
            if nid in ignore_publishers:
                log.info('Publisher ignored: %s (%s)', title, nid)
                continue

            if not parent_title:
                log.info('Publisher has no parent: %s', title)
                continue

            slug = munge_title_to_name( title )
            g = model.Group.get( slug )
            if not g:
                warn('Could not find group for "%s": %r', slug, row)
                continue

            parent_slug = munge_title_to_name( parent_title )
            parent = model.Group.get( parent_slug )

            if not parent:
                warn('Could not find parent "%s" for "%s"', parent, g.name)
                continue

            if model.Session.query(model.Member).\
                filter(model.Member.group==parent and model.Member.table_id==g.id).count() == 0:
                m = model.Member(group=parent, table_id=g.id, table_name='group')                 
                model.Session.add(m)
                log.info('%s is parent of %s', parent_slug, g.name)
            else:
                log.info('%s is already a parent of %s', parent_slug, g.name)
                    
        model.Session.commit()        
        drupal_csv_f.seek(0)
 
    all_groups = model.Session.query(model.Group).\
                       filter(model.Group.type == 'publisher').order_by('title').all()
    log.info('Total number of groups: %i', len(all_groups))
    log.info('Warnings: %r', warnings)

warnings = []
global_log = None
def warn(msg, *params):
    global warnings
    warnings.append(msg % params)
    global_log.warn(msg, *params)
    

def usage():
    print """
Imports publishers from the specified CSV file.
Usage:

    python import_publishers.py <CKAN config ini filepath> <Drupal CSV filepath>
    """
    
if __name__ == '__main__':
    if len(sys.argv) != 3:
        usage()
        sys.exit(0)
    cmd, config_ini, drupal_csv = sys.argv
    command(config_ini, drupal_csv)
