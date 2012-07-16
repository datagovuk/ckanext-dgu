'''
Goes through a CKAN database and normalises the value in the format
field for all resources. It makes them capitalised and not .xls etc.

Usage:
 $ python ../dgu/ckanext/dgu/bin/tidy_resource_types.py --config=ckan-demo.ini

'''

import os
import logging
import sys
from sqlalchemy import engine_from_config
from optparse import OptionParser

from pylons import config, translator
from paste.registry import Registry

def load_config(path):
    import paste.deploy
    conf = paste.deploy.appconfig('config:' + path)
    import ckan
    ckan.config.environment.load_environment(conf.global_conf,
                                             conf.local_conf)

res_type_map = {
    'application/x-msexcel': 'XLS',
    'Excel': 'XLS',
    'ecel': 'XLS',
    'Excel (xls)': 'XLS',
    'Excel (.xls)': 'XLS',
    'xlsx': 'XLS',
    'osd': 'ODS',
    'cvs': 'CSV',
    'Zipped CSV': 'CSV/Zip',
    'CSV Zip': 'CSV/Zip',
    'CSV Zipped': 'CSV/Zip',
    '.csv zipped': 'CSV/Zip',
    'csvzipped': 'CSV/Zip',
    'csv/pdf': 'PDF/CSV',
    'csv file': 'CSV',
    'web': 'HTML',
    'Web link': 'HTML',
    'Webpage': 'HTML',
    'hmtl': 'HTML',
    'Portable Document File': 'PDF',
    'Adobe PDF': 'PDF',
    'Shapefile': 'SHP',
    'RDFa': 'HTML+RDFa',
    'plain text': 'TXT',
    'doc': 'DOC',
    'Word': 'DOC',
    'Word doc': 'DOC',
    'Unverified': '',
    'iCalendar': 'iCal',
    'HTML/iCalendar': 'iCal',
    'HTML/iCal': 'iCal',
    'gztxt': 'TXT/Zip',
    'zip': 'Zip',
    'Other XML': 'XML',
    ' ': '',
    }

def command(dry_run=False):
    from ckan import model
    from ckanext.dgu.lib.resource_formats import match
    from running_stats import StatsList

    # Register a translator in this thread so that
    # the _() functions in logic layer can work
    from ckan.lib.cli import MockTranslator
    registry=Registry()
    registry.prepare()
    translator_obj=MockTranslator() 
    registry.register(translator, translator_obj) 

    if not dry_run:
        model.repo.new_revision()

    # Add canonised formats to map
    for format_ in res_type_map.keys():
        res_type_map[canonise(format_)] = res_type_map[format_]

    log.info('Tidying resource types')

    stats = StatsList()

    res_query = model.Session.query(model.Resource)
    log.info('Tidying formats. Resources=%i Canonised formats=%i',
             res_query.count(), len(set(res_type_map.values())))

    for res in res_query:
        canonised_fmt = canonise(res.format or '')
        if canonised_fmt in res_type_map:
            improved_fmt = res_type_map[canonised_fmt]
        else:
            improved_fmt = tidy(res.format)
        match_ = match(improved_fmt)
        if match_:
            improved_fmt = match_
        if (improved_fmt or '') != (res.format or ''):
            if not dry_run:
                res.format = improved_fmt
            stats.add(improved_fmt, res.format)
        else:
            stats.add('No change', res.format)

    if not dry_run:
        model.repo.commit_and_remove()

    log.info('Stats report: %r', stats.report())
    print stats.report()

    log.info('Warnings (%i): %r', len(warnings), warnings)

def canonise(format_):
    return tidy(format_).lower()

def tidy(format_):
    return format_.strip().lstrip('.')

warnings = []
log = None
def warn(msg, *params):
    global warnings
    warnings.append(msg % params)
    log.warn(msg, *params)

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
        global log
        log = logging.getLogger(os.path.basename(__file__))
        
    command(dry_run=options.dry_run)
