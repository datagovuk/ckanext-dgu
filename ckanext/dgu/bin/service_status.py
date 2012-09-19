# Reports on a DGU server\'s status

import subprocess
import os
import ConfigParser
import re
import sys

def check_archiver():
    print '\n** Archiver **'
    celery_command = check_supervisord('dgu')
    check_celery(celery_command, 'ckanext.archiver')

def check_qa():
    print '\n** QA **'
    celery_command = check_supervisord('dgu')
    check_celery(celery_command, 'ckanext.qa')

def check_supervisord(config):
    check_process('/usr/bin/supervisord')
    celery_config = ConfigParser.ConfigParser()
    if config == 'dgu':
      config_file = '/etc/supervisor/conf.d/celery-supervisor-dgu.conf'
      config_section = 'program:celery-dgu'
    else:
      assert 0, 'Unknown config: %s' % config
    celery_config.read(config_file)
    celery_command = celery_config.get(config_section, 'command')
    print 'Celery command: %s' % celery_command
    celery_logfile_name = celery_config.get(config_section, 'stderr_logfile')
    print 'Celery logfile: %s' % celery_logfile_name
    logfile_tail(celery_logfile_name)
    return celery_command

def check_celery(celery_command, celery_task):   
    config_filepath = extract_ckan_config_from_commandline(celery_command)
    ckan_log_filepath = extract_ckan_log_filepath(config_filepath)
    logfile_tail(ckan_log_filepath, celery_task)

def extract_ckan_log_filepath(config_filepath):
    ckan_config = ConfigParser.ConfigParser()
    ckan_config.read(config_filepath)
    args_line = ckan_config.get('handler_file', 'args')
    match = re.match('\(\"([^"]*)\",.*\)', args_line)
    if match:
        log_filepath = match.groups()[0]
        print 'CKAN logfile: %s' % log_filepath
        return log_filepath
    else:
        print 'Could not extract log filename from: %s' % args_line

def extract_ckan_config_from_commandline(commandline):
    match = re.search('--config=([^\s]+)', commandline)
    if match:
        config_filepath = match.groups()[0]
        print 'CKAN config: %s' % config_filepath
        return config_filepath
    print 'ERROR: Could not match a config file in the commandline: %s' % commandline

def logfile_tail(log_filepath, grep=None):
    max_lines = 10
    if not os.path.exists(log_filepath):
        print 'ERROR Log file doesn\'t exist: %s' % log_filepath
        return
    if not grep:
        p2 = subprocess.Popen(['tail', '-n', str(max_lines), log_filepath], stdout=subprocess.PIPE)
    else:
        p1 = subprocess.Popen(['grep', grep, log_filepath], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(['tail', '-n', str(max_lines)], stdin=p1.stdout, stdout=subprocess.PIPE)
        p1.stdout.close()
    lines = p2.communicate()[0].split('\n')
    for line in lines:
        print '> ' + line

    

def tail(f, window=20):
    BUFSIZ = 1024
    f.seek(0, 2)
    bytes = f.tell()
    size = window
    block = -1
    data = []
    while size > 0 and bytes > 0:
        if (bytes - BUFSIZ > 0):
            # Seek back one whole BUFSIZ
            f.seek(block*BUFSIZ, 2)
            # read BUFFER
            data.append(f.read(BUFSIZ))
        else:
            # file too small, start from begining
            f.seek(0,0)
            # only read what was not read
            data.append(f.read(bytes))
        linesFound = data[-1].count('\n')
        size -= linesFound
        bytes -= BUFSIZ
        block -= 1
    return ''.join(data).splitlines()[-window:]

processes = None
def check_process(process_text):
    global processes
    if not processes:
        processes = subprocess.Popen(['ps', 'aux'], stdout=subprocess.PIPE).communicate()[0]
    for process in processes.split('\n'):
        if process_text in process:
            print 'Process %s is running: %s' % (process_text, process)
            return
    print 'ERROR: Process %s is not running' % process_text

if __name__ == '__main__':
    usage = '''Service Status

Usage: python %s [archiver|qa]''' % sys.argv[0]
    if len(sys.argv) != 2:
        print usage
        sys.exit(1)
    service = sys.argv[1]
    if service == 'archiver':
        check_archiver()
    elif service == 'qa':
        check_qa()
    else:
        print 'Error: Service "%s" not found' % service
        print usage
        sys.exit(1)
