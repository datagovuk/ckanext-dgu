'''
Checks the URLs of broken resource links to see if NationalArchives has
a copy we can use instead.
'''

import csv
import os
import json
import logging
import sys

from paste.registry import Registry

from sqlalchemy import engine_from_config, or_
from pylons import config, translator
import time

from running_stats import StatsCount

global_log = logging.getLogger(__name__)

stats = StatsCount()

def load_config(path):
    import paste.deploy
    conf = paste.deploy.appconfig('config:' + path)
    import ckan
    ckan.config.environment.load_environment(conf.global_conf,
            conf.local_conf)

def command(input_csv, config_ini, commit=False):

    config_ini_filepath = os.path.abspath(config_ini)
    load_config(config_ini_filepath)
    engine = engine_from_config(config, 'sqlalchemy.')

    logging.config.fileConfig(config_ini_filepath)
    log = logging.getLogger(os.path.basename(__file__))

    from ckan import model
    from ckan.logic import get_action
    from ckan.lib.cli import MockTranslator

    model.init_model(engine)

    registry=Registry()
    registry.prepare()
    translator_obj=MockTranslator()
    registry.register(translator, translator_obj)

    ctx = {
        'model': model, 'session': model.Session,
        'user': get_action('get_site_user')({'model': model,'ignore_auth': True}, {})['name']
    }

    if commit:
        rev = model.repo.new_revision()

    packages_to_check = set()

    reader = csv.reader(open(input_csv, 'r'))
    for row in reader:
        # For each URL in the csv, get the list of resources referencing
        # that URL
        resources = model.Session.query(model.Resource)\
            .filter(model.Resource.state=='active')\
            .filter(model.Resource.url==row[0]).all()

        for resource in resources:
            # For each resource, add the package to the list
            packages_to_check.add(resource.get_package_id())

            # Delete the resource
            resource.state = 'deleted'
            model.Session.add(resource)
            if commit:
                model.Session.commit()

            print "Deleted resource: {0}".format(resource.id)

            stats.increment("Deleted resource")

    for pid in packages_to_check:
        # for each package we need to check, see if it has any
        # resources left, it not, delete it.
        pkg = model.Package.get(pid)
        if len(pkg.resources) == 0:
            pkg.state = 'deleted'
            model.Session.add(pkg)
            if commit:
                model.Session.commit()
            stats.increment('Deleted packages')

            print "Deleted package: {0}".format(pkg.name)

    if commit:
        model.repo.commit_and_remove()
    else:
        print ""
        print '*' * 60
        print "DON'T PANIC, this was a dry run, nothing was committed"
        print '*' * 60

    print ''
    print '*' * 60, 'Deletion Report'
    print stats.report(order_by_title=True)


def usage():
    print """
        Removes dead resources by deleting them (and the package if then empty)

        python ckanext/dgu/bin/delete_dead_resources.py <CSV_FILE> <CONFIG_FILE>
    """

if __name__ == '__main__':
    if len(sys.argv) < 3:
        usage()
        sys.exit(0)

    command(sys.argv[1], sys.argv[2], commit=len(sys.argv)==4 and sys.argv[3] == 'commit')
