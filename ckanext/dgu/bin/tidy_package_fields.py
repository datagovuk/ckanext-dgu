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

from pylons import config, translator
from paste.registry import Registry

from running_stats import StatsList

def load_config(path):
    import paste.deploy
    conf = paste.deploy.appconfig('config:' + path)
    import ckan

    ckan.config.environment.load_environment(conf.global_conf,
            conf.local_conf)

field_map = {
    # ('existing_field1', 'existing_field2', ...): 'destination_field_name'),
    ('author', 'maintainer'): 'contact-name',
    ('author_email', 'maintainer_email'): 'contact-email',
    ('geographical_granularity',): 'geographic_granularity',
    ('temporal_coverage_from',): 'temporal_coverage-from',
    ('temporal_coverage_to',): 'temporal_coverage-to',
}
delete_fields = ('agency', 'department', 'date_released ', 'temporal_coverage_from ', 'temporal_coverage_to ', 'update_frequency ', 'openness_score', 'openness_score_last_checked')

def command(dry_run=False):
    from ckan import model

    # Register a translator in this thread so that
    # the _() functions in logic layer can work
    from ckan.lib.cli import MockTranslator
    registry=Registry()
    registry.prepare()
    translator_obj=MockTranslator() 
    registry.register(translator, translator_obj) 

    global_log.info('Tidying package fields')

    stats = StatsList()

    if not dry_run:
        rev = model.repo.new_revision()
        rev.message = 'Package fields migration'

    for pkg in model.Session.query(model.Package)\
            .filter_by(state='active')\
            .order_by(model.Package.name):
        # field map
        for existing_fields, destination_field in field_map.items():
            value = pkg.extras.get(destination_field)
            if value:
                continue
            for existing_field in existing_fields:
                if hasattr(pkg, existing_field):
                    value = getattr(pkg, existing_field)
                else:
                    value = pkg.extras.get(existing_field)
                if value:
                    value = value.strip()
                    if value:
                        # take the first hit
                        continue
            if not dry_run:
                pkg.extras[destination_field] = value or ''
                # delete existing field values
                for existing_field in existing_fields:
                    if hasattr(pkg, existing_field):
                        setattr(pkg, existing_field, '')
                    elif existing_field in pkg.extras:
                        del pkg.extras[existing_field]
            if value:
                stats.add('Merged to field "%s"' % destination_field, pkg.name)
            else:
                stats.add('Not merged to field "%s"' % destination_field, pkg.name)

        # move url to additional resource
        if pkg.url:
            stats.add('Url moved to additional resource', value)
            if not dry_run:
                if not pkg.resource_groups:
                    res_group = model.ResourceGroup(label="default")
                    pkg.resource_groups.append(res_group)
                res_group = pkg.resource_groups[0]
                res = model.Resource(format='HTML', resource_type='documentation',
                                     url=pkg.url, description='Web page about the data')
                res_group.resources.append(res)
                model.Session.add(res)
                #pkg.url = ''
            stats.add('URL moved to additional resource', pkg.name)
        else:
            stats.add('No URL to move to additional resource', pkg.name)

        # delete fields
        for field in delete_fields:
            if field in pkg.extras:
                if not dry_run:
                    del pkg.extras[field]
                stats.add('Deleted field "%s"' % field, pkg.name)
            else:
                stats.add('No field to delete "%s"' % field, pkg.name)

    if not dry_run:
        model.repo.commit_and_remove()

    global_log.info(stats.report())

def canonise(format_):
    return tidy(format_).lower()

def tidy(format_):
    return format_.strip().lstrip('.')

warnings = []
global global_log
global_log = None
def warn(msg, *params):
    global warnings
    warnings.append(msg % params)
    global_log.warn(msg, *params)

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
        from ckan import model
        model.init_model(engine)

        logging.config.fileConfig(config_path)
        global_log = logging.getLogger(os.path.basename(__file__))

    command(dry_run=options.dry_run)
