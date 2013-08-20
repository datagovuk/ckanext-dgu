'''
Generates statistics about themed datasets
'''

import os
import logging
import sys
import collections
from sqlalchemy import engine_from_config, or_
from pylons import config


#No theme            7448
#Health              530
#Spending Data       483
#Society             209
#Environment         203
#Administration      184
#Finance             75
#Transportation      34
#Defence             27
#Education           23
#Location            7
#Empty               2

publisher_themes = {
    'british-geological-survey': 'Environment',
    'met-office': 'Environment',
    'ministry-of-defence': 'Defence',
    'crown-prosecution-service': 'Society',
    'department-of-energy-and-climate-change': 'Environment',
    'ordnance-survey': 'Location',
    'centre-for-ecology-hydrology': 'Environment',
    'department-of-health': 'Health',
    'department-for-education': 'Education',
    'department-for-environment-food-and-rural-affairs': 'Environment',
}

def load_config(path):
    import paste.deploy
    conf = paste.deploy.appconfig('config:' + path)
    import ckan, pylons
    ckan.config.environment.load_environment(conf.global_conf,
            conf.local_conf)

    from ckan.lib.cli import MockTranslator    
    from paste.registry import Registry 
    registry=Registry() 
    registry.prepare()     
    translator_obj=MockTranslator() 
    registry.register(pylons.translator, translator_obj) 


def command(config_ini, commit):
    config_ini_filepath = os.path.abspath(config_ini)
    load_config(config_ini_filepath)
    engine = engine_from_config(config, 'sqlalchemy.')

    logging.config.fileConfig(config_ini_filepath)
    log = logging.getLogger(os.path.basename(__file__))
    global global_log
    global_log = log

    from ckan import model
    model.init_model(engine)    
    model.repo.new_revision()

    guess_theme(commit)

def guess_theme(commit):
    from ckan import model
    from ckanext.dgu.lib import publisher as publib

    log = global_log

    for k,v in publisher_themes.iteritems():
        updated = 0
        pubs = list(publib.go_down_tree(model.Group.get(k))) 
        print "Processing %d publishers from %s" % (len(pubs), k)

        for publisher in pubs:
            packages = publisher.members_of_type(model.Package).filter(model.Package.state=='active')
            print "\r", " " * 80,  # blank the line
            print "\rProcessing %s" % publisher.name,

            for package in packages:
                if 'spend' in package.name or 'financ' in package.name:
                    continue 

                if not 'theme-primary' in package.extras or package.extras['theme-primary'] == '':
                    package.extras['theme-primary'] = v
                    model.Session.add(package)
                    updated = updated + 1

        print "\nWe updated %d themes under %s" % (updated, k)

        if commit.lower() == 'y':
            print "Committing results"
            model.Session.commit()


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

    python theme-stats.py <CKAN config ini filepath> <commit: y/n>
    """
    
if __name__ == '__main__':
    if len(sys.argv) != 3:
        usage()
        sys.exit(0)
    cmd, config_ini, commit = sys.argv
    command(config_ini, commit)
