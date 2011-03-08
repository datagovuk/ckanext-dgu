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

def load_config(path):
    import paste.deploy
    conf = paste.deploy.appconfig('config:' + path)
    import ckan
    ckan.config.environment.load_environment(conf.global_conf,
            conf.local_conf)

load_config(path)

import ckan.model as model
import ckan.lib.dumper as dumper
from pylons import config

# settings

log_filepath = os.path.join(os.path.expanduser(config.get('ckan.log_dir', '~')),
               'gov-daily.log')
dump_dir = os.path.expanduser(config.get('ckan.dump_dir', '~/dump'))
ckan_instance_name = re.sub(r'[^\w.-]|https?', '', 
                            config.get('ckan.site_url', 'dgu'))
dump_filebase = ckan_instance_name + '-%Y-%m-%d'
tmp_filepath = config.get('ckan.temp_filepath', '/tmp/dump.tmp')
backup_dir = os.path.expanduser(config.get('ckan.backup_dir', '~/backup'))
backup_filebase = ckan_instance_name + '.%Y-%m-%d.pg_dump'

logging.basicConfig(filename=log_filepath, level=logging.INFO)
logging.info('----------------------------')
logging.info('Starting daily script')
start_time = datetime.datetime.today()
logging.info(start_time.strftime('%H:%M %d-%m-%Y'))

def report_time_taken():
    time_taken = (datetime.datetime.today() - start_time).seconds
    logging.info('Time taken: %i seconds' % time_taken)


# Check database looks right
num_packages_before = model.Session.query(model.Package).count()
logging.info('Number of existing packages: %i' % num_packages_before)
if num_packages_before < 2500:
    logging.error('Expected more packages.')
    sys.exit(1)

# Import recent ONS data - REMOVED

# Create dumps for users
logging.info('Creating database dump')
if not os.path.exists(dump_dir):
    logging.info('Creating dump dir: %s' % dump_dir)
    os.makedirs(dump_dir)
query = model.Session.query(model.Package)
for file_type, dumper in (('csv', dumper.SimpleDumper().dump_csv),
                          ('json', dumper.SimpleDumper().dump_json),
                         ):
    dump_file_base = start_time.strftime(dump_filebase)
    dump_filename = '%s.%s' % (dump_file_base, file_type)
    dump_filepath = os.path.join(dump_dir, dump_filename + '.zip')
    tmp_file = open(tmp_filepath, 'w')
    logging.info('Creating %s file: %s' % (file_type, dump_filepath))
    dumper(tmp_file, query)
    tmp_file.close()
    dump_file = zipfile.ZipFile(dump_filepath, 'w', zipfile.ZIP_DEFLATED)
    dump_file.write(tmp_filepath, dump_filename)
    dump_file.close()
report_time_taken()

# Create complete backup
logging.info('Creating database backup')
if not os.path.exists(backup_dir):
    logging.info('Creating backup dir: %s' % backup_dir)
    os.makedirs(backup_dir)

def get_db_config(): # copied from fabfile
    url = config['sqlalchemy.url']
    # e.g. 'postgres://tester:pass@localhost/ckantest3'
    db_details_match = re.match('^\s*(?P<db_type>\w*)://(?P<db_user>\w*):?(?P<db_pass>[^@]*)@(?P<db_host>[^/:]*):?(?P<db_port>[^/]*)/(?P<db_name>[\w.-]*)', url)

    db_details = db_details_match.groupdict()
    return db_details
db_details = get_db_config()
pg_dump_filename = start_time.strftime(backup_filebase)
pg_dump_filepath = os.path.join(backup_dir, pg_dump_filename)
cmd = 'export PGPASSWORD=%s&&pg_dump -U %s -h %s %s > %s' % (db_details['db_pass'], db_details['db_user'], db_details['db_host'], db_details['db_name'], pg_dump_filepath)
logging.info('Backup command: %s' % cmd)
ret = os.system(cmd)
if ret == 0:
    logging.info('Backup successful: %s' % pg_dump_filepath)
else:
    logging.error('Backup error: %s' % ret)

# Log footer
report_time_taken()
logging.info('Finished daily script')
logging.info('----------------------------')
