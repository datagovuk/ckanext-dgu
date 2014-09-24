'''
Daily script for gov server
'''
import os
import logging
import sys
import zipfile
import datetime
import re
import urllib2
import json

from common import load_config, register_translator

start_time = datetime.datetime.today()
def report_time_taken(log):
    time_taken = (datetime.datetime.today() - start_time).seconds
    log.info('Time taken: %i seconds' % time_taken)

def get_db_config(config): # copied from fabfile
    url = config['sqlalchemy.url']
    # e.g. 'postgres://tester:pass@localhost/ckantest3'
    db_details_match = re.match('^\s*(?P<db_type>\w*)://(?P<db_user>\w*):?(?P<db_pass>[^@]*)@(?P<db_host>[^/:]*):?(?P<db_port>[^/]*)/(?P<db_name>[\w.-]*)', url)

    db_details = db_details_match.groupdict()
    return db_details


def run_task(taskname):
    return TASKS_TO_RUN and taskname in TASKS_TO_RUN

def command(config_file):
    # Import ckan as it changes the dependent packages imported
    from dump_analysis import (get_run_info, TxtAnalysisFile,
                               CsvAnalysisFile, DumpAnalysisOptions,
                               DumpAnalysis)

    from pylons import config

    # settings
    ckan_instance_name = os.path.basename(config_file).replace('.ini', '')
    if ckan_instance_name not in ['development', 'dgutest']:
        default_dump_dir = '/var/lib/ckan/%s/static/dump' % ckan_instance_name
        default_analysis_dir = '/var/lib/ckan/%s/static/dump_analysis' % ckan_instance_name
        default_backup_dir = '/var/backups/ckan/%s' % ckan_instance_name
        default_openspending_reports_dir = '/var/lib/ckan/%s/openspending_reports' % ckan_instance_name
    else:
        # test purposes
        default_dump_dir = '~/dump'
        default_analysis_dir = '~/dump_analysis'
        default_backup_dir = '~/backups'
        default_openspending_reports_dir = '~/openspending_reports'
    dump_dir = os.path.expanduser(config.get('ckan.dump_dir',
                                             default_dump_dir))
    analysis_dir = os.path.expanduser(config.get('ckan.dump_analysis_dir',
                                             default_analysis_dir))
    backup_dir = os.path.expanduser(config.get('ckan.backup_dir',
                                               default_backup_dir))
    openspending_reports_dir = os.path.expanduser(config.get('dgu.openspending_reports_dir',
                                                             default_openspending_reports_dir))
    ga_token_filepath = os.path.expanduser(config.get('googleanalytics.token.filepath', ''))
    dump_filebase = config.get('ckan.dump_filename_base',
                               'data.gov.uk-ckan-meta-data-%Y-%m-%d')
    dump_analysis_filebase = config.get('ckan.dump_analysis_base',
                               'data.gov.uk-analysis')
    backup_filebase = config.get('ckan.backup_filename_base',
                                 ckan_instance_name + '.%Y-%m-%d.pg_dump')
    tmp_filepath = config.get('ckan.temp_filepath', '/tmp/dump.tmp')
    openspending_reports_url = config.get('ckan.openspending_reports_url',
                                          'http://data.etl.openspending.org/uk25k/report/')


    log = logging.getLogger('ckanext.dgu.bin.gov_daily')
    log.info('----------------------------')
    log.info('Starting daily script')
    start_time = datetime.datetime.today()

    import ckan.model as model
    import ckan.lib.dumper as dumper
    from ckanext.dgu.lib.inventory import inventory_dumper

    # Check database looks right
    num_packages_before = model.Session.query(model.Package).filter_by(state='active').count()
    log.info('Number of existing active packages: %i' % num_packages_before)
    if num_packages_before < 2:
        log.error('Expected more packages.')
        sys.exit(1)
    elif num_packages_before < 2500:
        log.warn('Expected more packages.')

    # Analytics
    try:
        if ga_token_filepath:
            if run_task('analytics'):
                log.info('Getting analytics for this month')
                from ckanext.ga_report.download_analytics import DownloadAnalytics
                from ckanext.ga_report.ga_auth import (init_service, get_profile_id)
                try:
                    token, svc = init_service(ga_token_filepath, None)
                except TypeError:
                    log.error('Could not complete authorization for Google Analytics.'
                              'Have you correctly run the getauthtoken task and '
                              'specified the correct token file?')
                    sys.exit(0)
                downloader = DownloadAnalytics(svc, token=token, profile_id=get_profile_id(svc),
                                               delete_first=False,
                                               skip_url_stats=False)
                downloader.latest()
        else:
            log.info('No token specified, so not downloading Google Analytics data')
    except Exception, exc_analytics:
        log.error("Failed to process Google Analytics data")
        log.exception(exc_analytics)

    # Copy openspending reports
    if run_task('openspending'):
        log.info('OpenSpending reports')
        if not os.path.exists(openspending_reports_dir):
            log.info('Creating dump dir: %s' % openspending_reports_dir)
            os.makedirs(openspending_reports_dir)
        try:
            publisher_response = urllib2.urlopen('http://data.gov.uk/api/action/organization_list').read()
        except urllib2.HTTPError, e:
            log.error('Could not get list of publishers for OpenSpending reports: %s',
                      e)
        else:
            try:
                publishers = json.loads(publisher_response)['result']
                assert isinstance(publishers, list), publishers
                assert len(publishers) > 500, len(publishers)
                log.info('Got list of %i publishers starting: %r',
                         len(publishers), publishers[:3])
            except Exception, e:
                log.error('Could not decode list of publishers for OpenSpending reports: %s',
                          e)
            else:
                urls = [openspending_reports_url]
                log.info('Getting reports, starting with: %s', urls[0])
                for publisher in publishers:
                    urls.append('%spublisher-%s.html' % (openspending_reports_url, publisher))

                for url in urls:
                    try:
                        report_response = urllib2.urlopen(url).read()
                    except urllib2.HTTPError, e:
                        if e.code == 404:
                            log.info('Got 404 for openspending report %s' % url)
                        else:
                            log.error('Could not download openspending report %r: %s',
                                      url, e)
                    else:
                        report_html = report_response
                        # remove header
                        report_html = "".join(report_html.split('---')[2:])
                        # add import timestamp
                        report_html += '<p class="import-date">\n<a href="%s">Page</a> imported from <a href="http://openspending.org/">OpenSpending</a> on %s. Read more about <a href="http://openspending.org/resources/gb-spending/index.html">OpenSpending on data.gov.uk</a>\n</p>' % \
                                       (url.encode('utf8'),
                                        datetime.datetime.now().strftime('%d-%m-%Y'))
                        # add <html>
                        report_html = '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:i18n="http://genshi.edgewall.org/i18n" '\
                                      'xmlns:py="http://genshi.edgewall.org/" xmlns:xi="http://www.w3.org/2001/XInclude" '\
                                      'py:strip="">' + report_html + '</html>'
                        # Sort out non-encoded symbols
                        report_html = re.sub(u' & ', ' &amp; ', report_html)
                        report_html = re.sub('\xc2\xa3', '&pound;', report_html)
                        report_html = re.sub(u'\u2714', '&#x2714;', report_html)
                        report_html = re.sub(u'\u2718', '&#x2718;', report_html)
                        report_html = re.sub(u'\u0141', '&#x0141;', report_html)
                        # save it
                        filename = url[url.rfind('/')+1:] or 'index.html'
                        filepath = os.path.join(openspending_reports_dir, filename)
                        f = open(filepath, 'wb')
                        try:
                            f.write(report_html)
                        finally:
                            f.close()
                        log.info('Wrote openspending report %s', filepath)

    # Create dump for users
    if run_task('dump'):
        log.info('Creating database dump')
        if not os.path.exists(dump_dir):
            log.info('Creating dump dir: %s' % dump_dir)
            os.makedirs(dump_dir)
        query = model.Session.query(model.Package).filter(model.Package.state=='active')
        dump_file_base = start_time.strftime(dump_filebase)
        logging.getLogger("MARKDOWN").setLevel(logging.WARN)
        for file_type, dumper_ in (('csv', dumper.SimpleDumper().dump_csv),
                                  ('json', dumper.SimpleDumper().dump_json),
                                  ('unpublished.csv', inventory_dumper),
                                 ):
            dump_filename = '%s.%s' % (dump_file_base, file_type)
            dump_filepath = os.path.join(dump_dir, dump_filename + '.zip')
            tmp_file = open(tmp_filepath, 'w+b')
            log.info('Creating %s file: %s' % (file_type, dump_filepath))
            dumper_(tmp_file, query)
            tmp_file.close()
            log.info('Dumped data file is %dMb in size' % (os.path.getsize(tmp_filepath) / (1024*1024)))
            dump_file = zipfile.ZipFile(dump_filepath, 'w', zipfile.ZIP_DEFLATED)
            dump_file.write(tmp_filepath, dump_filename)
            dump_file.close()

            # Setup a symbolic link to dump_filepath from data.gov.uk-ckan-meta-data-latest.{0}.zip
            # so that it is up-to-date with the latest version for both JSON and CSV.
            link_filepath = os.path.join(dump_dir,
                "data.gov.uk-ckan-meta-data-latest.{0}.zip".format(file_type))

            if os.path.exists(link_filepath):
                os.unlink(link_filepath)
            os.symlink(dump_filepath, link_filepath)

            os.remove(tmp_filepath)

        report_time_taken(log)

    # Dump analysis
    if run_task('dump_analysis'):
        log.info('Doing dump analysis')
        dump_file_base = start_time.strftime(dump_filebase)
        json_dump_filepath = os.path.join(dump_dir, '%s.json.zip' % dump_file_base)
        txt_filepath = os.path.join(analysis_dir, dump_analysis_filebase + '.txt')
        csv_filepath = os.path.join(analysis_dir, dump_analysis_filebase + '.csv')
        log.info('Input: %s', json_dump_filepath)
        log.info('Output: %s & %s', txt_filepath, csv_filepath)
        if not os.path.exists(analysis_dir):
            log.info('Creating dump analysis dir: %s' % analysis_dir)
            os.makedirs(analysis_dir)
        run_info = get_run_info()
        options = DumpAnalysisOptions(analyse_by_source=True)
        analysis = DumpAnalysis(json_dump_filepath, options)
        output_types = (
            # (output_filepath, analysis_file_class)
            (txt_filepath, TxtAnalysisFile),
            (csv_filepath, CsvAnalysisFile),
            )
        for output_filepath, analysis_file_class in output_types:
            log.info('Saving dump analysis to: %s' % output_filepath)
            analysis_file = analysis_file_class(output_filepath, run_info)
            analysis_file.add_analysis(analysis.date, analysis.analysis_dict)
            analysis_file.save()
        report_time_taken(log)

    if run_task('backup'):
        # Create complete backup
        log.info('Creating database backup')
        if not os.path.exists(backup_dir):
            log.info('Creating backup dir: %s' % backup_dir)
            os.makedirs(backup_dir)

        db_details = get_db_config(config)
        pg_dump_filename = start_time.strftime(backup_filebase)
        pg_dump_filepath = os.path.join(backup_dir, pg_dump_filename)
        cmd = 'export PGPASSWORD=%(db_pass)s&&pg_dump ' % db_details
        for pg_dump_option, db_details_key in (('U', 'db_user'),
                                               ('h', 'db_host'),
                                               ('p', 'db_port')):
            if db_details.get(db_details_key):
                cmd += '-%s %s ' % (pg_dump_option, db_details[db_details_key])
        cmd += ' -E utf8 %(db_name)s' % db_details + ' > %s' % pg_dump_filepath
        log.info('Backup command: %s' % cmd)
        ret = os.system(cmd)
        if ret == 0:
            log.info('Backup successful: %s' % pg_dump_filepath)
            log.info('Zipping up backup')
            pg_dump_zipped_filepath = pg_dump_filepath + '.gz'
            # -f to overwrite any existing file, instead of prompt Yes/No
            cmd = 'gzip -f %s' % pg_dump_filepath
            log.info('Zip command: %s' % cmd)
            ret = os.system(cmd)
            if ret == 0:
                log.info('Backup gzip successful: %s' % pg_dump_zipped_filepath)
            else:
                log.error('Backup gzip error: %s' % ret)
        else:
            log.error('Backup error: %s' % ret)

    # Log footer
    report_time_taken(log)
    log.info('Finished daily script')
    log.info('----------------------------')

TASKS_TO_RUN = ['analytics','openspending','dump','dump_analysis','backup']

if __name__ == '__main__':
    USAGE = '''Daily script for government
    Usage: python %s [config.ini]

    You may provide an optional argument at the end which is the tasks to run,
    and you can choose from %s or run multiple by
    separating by a comma.
    ''' % (sys.argv[0], ','.join(TASKS_TO_RUN))

    if len(sys.argv) < 2 or sys.argv[1] in ('--help', '-h'):
        err = 'Error: Please specify config file.'
        print USAGE, err
        logging.error('%s\n%s' % (USAGE, err))
        sys.exit(1)
    config_file = sys.argv[1]
    config_ini_filepath = os.path.abspath(config_file)

    if len(sys.argv) == 3:
        TASKS_TO_RUN = sys.argv[2].split(',')

    load_config(config_ini_filepath)
    register_translator()
    logging.config.fileConfig(config_ini_filepath)

    command(config_file)
