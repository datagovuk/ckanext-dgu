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

from dump_analysis import get_run_info, TxtAnalysisFile, CsvAnalysisFile, DumpAnalysisOptions, DumpAnalysis

def load_config(path):
    import paste.deploy
    conf = paste.deploy.appconfig('config:' + path)
    import ckan
    ckan.config.environment.load_environment(conf.global_conf,
            conf.local_conf)

start_time = datetime.datetime.today()
def report_time_taken():
    time_taken = (datetime.datetime.today() - start_time).seconds
    logging.info('Time taken: %i seconds' % time_taken)

def get_db_config(config): # copied from fabfile
    url = config['sqlalchemy.url']
    # e.g. 'postgres://tester:pass@localhost/ckantest3'
    db_details_match = re.match('^\s*(?P<db_type>\w*)://(?P<db_user>\w*):?(?P<db_pass>[^@]*)@(?P<db_host>[^/:]*):?(?P<db_port>[^/]*)/(?P<db_name>[\w.-]*)', url)

    db_details = db_details_match.groupdict()
    return db_details

def command():
    USAGE = '''Daily script for government
    Usage: python %s [config.ini]
    ''' % sys.argv[0]
    if len(sys.argv) < 2 or sys.argv[1] in ('--help', '-h'):
        err = 'Error: Please specify config file.'
        print USAGE, err
        logging.error('%s\n%s' % (USAGE, err))
        sys.exit(1)
    config_file = sys.argv[1]
    path = os.path.abspath(config_file)

    load_config(path)

    from pylons import config

    # settings
    ckan_instance_name = os.path.basename(config_file).replace('.ini', '')
    if ckan_instance_name != 'development':
        default_dump_dir = '/var/lib/ckan/%s/static/dump' % ckan_instance_name
        default_backup_dir = '/var/backups/ckan/%s' % ckan_instance_name
        default_log_dir = '/var/log/ckan/%s' % ckan_instance_name
    else:
        # test purposes
        default_dump_dir = '~/dump'
        default_backup_dir = '~/backups'
        default_log_dir = '~'
    dump_dir = os.path.expanduser(config.get('ckan.dump_dir',
                                             default_dump_dir))
    backup_dir = os.path.expanduser(config.get('ckan.backup_dir',
                                               default_backup_dir))
    log_dir = os.path.expanduser(config.get('ckan.log_dir',
                                            default_log_dir))
    dump_filebase = config.get('ckan.dump_filename_base',
                               'data.gov.uk-ckan-meta-data-%Y-%m-%d')
    dump_analysis_filebase = config.get('ckan.dump_analysis_base',
                               'data.gov.uk-analysis')
    backup_filebase = config.get('ckan.backup_filename_base',
                                 ckan_instance_name + '.%Y-%m-%d.pg_dump')
    log_filepath = os.path.join(log_dir, 'gov-daily.log')
    print 'Logging to: %s' % log_filepath
    tmp_filepath = config.get('ckan.temp_filepath', '/tmp/dump.tmp')

    logging.basicConfig(filename=log_filepath, level=logging.INFO)
    logging.info('----------------------------')
    logging.info('Starting daily script')
    start_time = datetime.datetime.today()
    logging.info(start_time.strftime('%H:%M %d-%m-%Y'))

    import ckan.model as model
    import ckan.lib.dumper as dumper

    # Check database looks right
    num_packages_before = model.Session.query(model.Package).count()
    logging.info('Number of existing packages: %i' % num_packages_before)
    if num_packages_before < 2:
        logging.error('Expected more packages.')
        sys.exit(1)
    elif num_packages_before < 2500:
        logging.warn('Expected more packages.')

    # Create dumps for users
    logging.info('Creating database dump')
    if not os.path.exists(dump_dir):
        logging.info('Creating dump dir: %s' % dump_dir)
        os.makedirs(dump_dir)
    query = model.Session.query(model.Package)
    dump_file_base = start_time.strftime(dump_filebase)
    logging.getLogger("MARKDOWN").setLevel(logging.WARN)
    for file_type, dumper_ in (('csv', dumper.SimpleDumper().dump_csv),
                              ('json', dumper.SimpleDumper().dump_json),
                             ):
        dump_filename = '%s.%s' % (dump_file_base, file_type)
        dump_filepath = os.path.join(dump_dir, dump_filename + '.zip')
        tmp_file = open(tmp_filepath, 'w')
        logging.info('Creating %s file: %s' % (file_type, dump_filepath))
        dumper_(tmp_file, query)
        tmp_file.close()
        dump_file = zipfile.ZipFile(dump_filepath, 'w', zipfile.ZIP_DEFLATED)
        dump_file.write(tmp_filepath, dump_filename)
        dump_file.close()
    report_time_taken()

    # Dump analysis
    logging.info('Creating dump analysis')
    json_dump_filepath = os.path.join(dump_dir, '%s.json.zip' % dump_file_base)
    txt_filepath = os.path.join(dump_dir, dump_analysis_filebase + '.txt')
    csv_filepath = os.path.join(dump_dir, dump_analysis_filebase + '.csv')
    run_info = get_run_info()
    options = DumpAnalysisOptions(analyse_by_source=True)
    analysis = DumpAnalysis(json_dump_filepath, options)
    logging.info('Saving dump analysis')
    output_types = (
        # (output_filepath, analysis_file_class)
        (txt_filepath, TxtAnalysisFile),
        (csv_filepath, CsvAnalysisFile),
        )
    analysis_files = {} # analysis_file_class, analysis_file
    for output_filepath, analysis_file_class in output_types:
        logging.info('Saving dump analysis to: %s' % output_filepath)
        analysis_file = analysis_file_class(output_filepath, run_info)
        analysis_file.add_analysis(analysis.date, analysis.analysis_dict)
        analysis_file.save()
    report_time_taken()

    # Create complete backup
    logging.info('Creating database backup')
    if not os.path.exists(backup_dir):
        logging.info('Creating backup dir: %s' % backup_dir)
        os.makedirs(backup_dir)

    db_details = get_db_config(config)
    pg_dump_filename = start_time.strftime(backup_filebase)
    pg_dump_filepath = os.path.join(backup_dir, pg_dump_filename)
    cmd = 'export PGPASSWORD=%(db_pass)s&&pg_dump -U %(db_user)s -h %(db_host)s -p %(db_port)s %(db_name)s' % db_details + ' > %s' % pg_dump_filepath
    logging.info('Backup command: %s' % cmd)
    ret = os.system(cmd)
    if ret == 0:
        logging.info('Backup successful: %s' % pg_dump_filepath)
    else:
        logging.error('Backup error: %s' % ret)
    logging.info('Zipping up backup')
    pg_dump_zipped_filepath = pg_dump_filepath + '.gz'
    cmd = 'gzip %s' % pg_dump_filepath
    logging.info('Zip command: %s' % cmd)
    ret = os.system(cmd)
    if ret == 0:
        logging.info('Backup gzip successful: %s' % pg_dump_zipped_filepath)
    else:
        logging.error('Backup gzip error: %s' % ret)

    # Log footer
    report_time_taken()
    logging.info('Finished daily script')
    logging.info('----------------------------')

if __name__ == '__main__':
    command()
