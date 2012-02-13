###############################################################################
# Uses a CSV export from DGU Drupal to determine which datasets are owned by 
# which publishers.

# The SQL to generate the CSV looks like:
#
# SELECT R.title, 
#      (SELECT title FROM dgu_drupal.node_revisions AS rr WHERE rr.nid = P.nid) AS 'pub_title'
# FROM dgu_drupal.content_type_ckan_package as K
# INNER JOIN dgu_drupal.node_revisions AS R ON R.vid=K.vid
# INNER JOIN dgu_drupal.content_type_publisher AS P ON P.nid=K.field_publisher_nid;
#
###############################################################################

import os
import logging
import sys
import ckan
from ckan import model
from ckan.lib.search import rebuild
from ckan.lib.munge import munge_title_to_name
from sqlalchemy import engine_from_config


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

    print 'Fetching group cache'
    groups = {}
    for g in model.Session.query(model.Group).filter(model.Group.type=='publisher').all():
        groups[g.name] = g
    print ' .. done'    
    
    packages = {}
    
    with open(sys.argv[2], 'rU') as f:
        reader = csv.reader( f) 
        reader.next() # skip headers
        
        count, proc = 0, 0
        for row in reader:
            dataset_title, publisher_title = row
            publisher_slug = munge_title_to_name( publisher_title )
            
            proc = proc + 1
            if proc % 500 == 0:
                print '-> %d/%d' % (count,proc,)

            if not publisher_slug in groups:
                continue
                
            if dataset_title in packages:
                pkg = packages[dataset_title]     
            else:
                qp = model.Session.query(model.Package).\
                          filter(model.Package.title==dataset_title and model.Package.state == 'active')
                if qp.count() == 0:
                    continue
                pkg = qp.all()[0]
                packages[dataset_title] = pkg

            count = count + 1            

            pub = groups[publisher_slug]
            c = model.Session.query(model.Member).\
                          filter(model.Member.table_id==pkg.id and model.Member.group == pub and
                                 model.Member.table_name == 'package').count()
            if c > 0:
                continue

            model.Session.add( model.Member(group=pub, table_id=pkg.id, table_name='package')  )
            model.Session.commit()
            rebuild( package=pkg.id )
        
            print 'Processed', count, 'rows'
        
        
def usage():
    print """
Usage:
  Associates publishers with datasets from the provided CSV

    python publisher_datasets_assoc.py <path to ini file>  <path to csv file>
    """
    
if __name__ == '__main__':
    if len(sys.argv) != 3:
        usage()
        sys.exit(0)
    command()
