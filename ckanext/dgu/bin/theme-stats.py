'''
Generates statistics about themed datasets
'''

import os
import logging
import sys
import collections
from sqlalchemy import engine_from_config, or_
from pylons import config

def load_config(path):
    import paste.deploy
    conf = paste.deploy.appconfig('config:' + path)
    import ckan
    ckan.config.environment.load_environment(conf.global_conf,
            conf.local_conf)

def command(config_ini):
    config_ini_filepath = os.path.abspath(config_ini)
    load_config(config_ini_filepath)
    engine = engine_from_config(config, 'sqlalchemy.')

    logging.config.fileConfig(config_ini_filepath)
    log = logging.getLogger(os.path.basename(__file__))
    global global_log
    global_log = log

    from ckan import model
    model.init_model(engine)

    generate_stats()

def generate_stats():
    from ckan import model
    from ckan.lib.munge import munge_title_to_name

    log = global_log

    counter = collections.defaultdict(int)
    empties = collections.defaultdict(int)

    package_query = model.Session.query(model.Package)\
        .filter(model.Package.state=='active')

    for package in package_query.all():
        if 'theme-primary' in package.extras:
            counter[package.extras['theme-primary'] or 'Empty'] = counter[package.extras['theme-primary'] or 'Empty'] + 1
        else:
            counter['No theme'] = counter['No theme'] + 1
            org = package.get_organization()
            if not org
                print package.name, "has no organization"
            else:
                empties[org.name] = empties[org.name] + 1

    import operator
    print "Themed datasets"
    print "=" * 25
    srtd = sorted(counter.iteritems(),key=operator.itemgetter(1), reverse=True)
    for k,v in srtd:
        print "%s%s%s" % (k, ' ' * (20-len(k)), counter[k])


    import operator
    print "\nPublisher w/most missing"
    print "=" * 64
    srtd = sorted(empties.iteritems(),key=operator.itemgetter(1), reverse=True)
    for k,v in srtd:
        if empties[k]:
            print "%s%s%s" % (k, ' ' * (20-len(k)), empties[k])


warnings = []
global_log = None
def warn(msg, *params):
    global warnings
    warnings.append(msg % params)
    global_log.warn(msg, *params)


def usage():
    print """
Generates stats about themes used in data.gov.uk
Usage:

    python theme-stats.py <CKAN config ini filepath>
    """

if __name__ == '__main__':
    if len(sys.argv) != 2:
        usage()
        sys.exit(0)
    cmd, config_ini = sys.argv
    command(config_ini)
