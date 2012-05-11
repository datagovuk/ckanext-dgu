'''
Goes through a CKAN database and move old and incorrect fields into
the new ones for June 2012 relaunch.

Usage:
 $ python ../dgu/ckanext/dgu/bin/tidy_package_fields.py --config=ckan-demo.ini

'''

import os
import logging
import sys
from sqlalchemy import engine_from_config
from optparse import OptionParser

from pylons import config

import ckan
from ckan import model
from running_stats import StatsList

def load_config(path):
    import paste.deploy
    conf = paste.deploy.appconfig('config:' + path)
    ckan.config.environment.load_environment(conf.global_conf,
            conf.local_conf)

field_map = {
    # ('existing_field1', 'existing_field2', ...): 'destination_field_name'),
    (),
}

def command(dry_run=False):
    if not dry_run:
        model.repo.new_revision()

    # Add canonised formats to map
    for format_ in res_type_map.keys():
        res_type_map[canonise(format_)] = res_type_map[format_]

    stats = StatsList()

    for res in model.Session.query(model.Resource):
        canonised_fmt = canonise(res.format or '')
        if canonised_fmt in res_type_map:
            improved_fmt = res_type_map[canonised_fmt]
        else:
            improved_fmt = tidy(res.format)
        if (improved_fmt or '') != (res.format or ''):
            if not dry_run:
                res.format = improved_fmt
            stats.add(improved_fmt, res.format)
        else:
            stats.add('No change', res.format)

    if not dry_run:
        model.repo.commit_and_remove()

    print stats.report()

def canonise(format_):
    return tidy(format_).lower()

def tidy(format_):
    return format_.strip().lstrip('.')

if __name__ == '__main__':
    usage = '''usage: %prog [options]
    ''' # NB Options are automatically listed
    parser = OptionParser(usage=usage)
    parser.add_option('-c', '--config', dest='config', help='Config filepath', default='development.ini')
    parser.add_option('-d', '--dry-run', dest='dry_run', help='Dry run',
                      action='store_true', default=False)

    (options, args) = parser.parse_args()
    if len(args) > 0:
        parser.print_help()
        sys.exit(1)

    if options.config:
        config_path = os.path.abspath(options.config)
        if not os.path.exists(config_path):
            print 'Config file does not exist: %s' % config_path
            sys.exit(1)            
        load_config(config_path)
        engine = engine_from_config(config, 'sqlalchemy.')
        model.init_model(engine)
            
    command(dry_run=options.dry_run)
