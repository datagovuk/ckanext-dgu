'''
Server Log Tool

This is for getting stats out of our server logs.

Inspiration:
 *  https://speakerdeck.com/pyconslides/server-log-analysis-with-pandas-by-taavi-burns
 *  https://www.youtube.com/watch?v=ZOpR3P-jAno

You need Pandas to run this::

  pip install pandas

To play about with it, get setup with IPython notebook as well::

  sudo apt-get install libzmq-dev libpng-dev libfreetype6-dev g++ libhdf5-serial-dev
  pip install numpy numexpr ipython pyzmq tornado matplotlib pandas cython
  pip install tables
  ipython notebook --pylab inline --ip=0.0.0.0 --notebook-dir=/vagrant/src/ckanext-dgu/ckanext/dgu/notebooks

Browse the notebook on the host machine at: http://localhost:2888/

Get hold of a log like this:

  rsync -z --progress co@co-prod3.dh.bytemark.co.uk:/var/log/nginx/access.log /vagrant/

Parse and save as HDF5:

  python /vagrant/src/ckanext-dgu/ckanext/dgu/bin/server_log_tool.py /vagrant/access.log --save /vagrant/access.log.h5

Have a shell to play about with data:

  python /vagrant/src/ckanext-dgu/ckanext/dgu/bin/server_log_tool.py /vagrant/access.log.h5 --shell

Work on it in python like this:

  import pandas as pd
  store = pd.HDFStore('/vagrant/access_today.log.h5')
  df = store['log']
'''
from optparse import OptionParser
import re
import datetime

import pandas as pd

class Logs(object):
    df = None

    def load_log(self, filepath):
        rows = []
        index = []
        with open(filepath, 'rb') as f:
            for line in f:
                values = parse_line(line)
                timestamp_index = columns.index('timestamp')
                timestamp = values.pop(timestamp_index)
                rows.append(values)
                index.append(timestamp)
        columns_without_timestamp = [h for h in columns if h != 'timestamp']
        self.df = pd.DataFrame(rows, index=index, columns=columns_without_timestamp)
        print 'Loaded log %s' % filepath

    def load_h5(self, filepath):
        store = pd.HDFStore(filepath)
        self.df = store['log']
        print 'Loaded H5 %s' % filepath

    def save(self, filepath):
        store = pd.HDFStore(filepath, complib='blosc')
        store['log'] = self.df
        print 'Saved %s' % filepath

nginx_re = re.compile(r'(?P<ip>.+) - (?P<remote_user>.+) \[(?P<timestamp>.+)\] "(?P<url>[^"]*)" (?P<status>.+) (?P<size>.+) "(?P<referer>[^"]*)" "(?P<agent>[^"]*)"')
nginx_re_timed = re.compile(r'(?P<ip>.+) - (?P<remote_user>.+) \[(?P<timestamp>.+)\]  "(?P<url>[^"]*)" (?P<status>.+) (?P<size>.+) "(?P<referer>[^"]*)" "(?P<agent>[^"]*)" (?P<serve_time>.+) (?P<serve_time_upstream>.+)')
columns = ('ip', 'remote_user', 'timestamp', 'url', 'status', 'size', 'referer', 'agent', 'serve_time', 'serve_time_upstream')
def parse_line(line):
    match = re.match(nginx_re_timed, line)
    if not match:
        match = re.match(nginx_re, line)
        if not match:
            print 'Could not match line: ', line
    row = list(match.groups())
    if len(row) == len(columns) - 2:
        row += [0, 0]
    for key in ('serve_time', 'serve_time_upstream'):
        i = columns.index(key)
        try:
            row[i] = float(row[i])
        except ValueError:
            row[i] = None
    for key in ('size', 'status'):
        i = columns.index(key)
        try:
            row[i] = int(row[i])
        except ValueError:
            row[i] = None
    i = columns.index('timestamp')

    row[i] = datetime.datetime.strptime(row[i][:-6], "%d/%b/%Y:%H:%M:%S")
    return row

if __name__ == '__main__':
    # NB I am not sure, what this tool is for, so the command-line
    # syntax is a bit weird right now.
    usage = "usage: %prog [options] <filepath.log/.h5>"
    parser = OptionParser(usage=usage)
    parser.add_option("-s", "--save", dest="save",
                            help="Save data as HDF5")
    parser.add_option("--shell", dest="shell",
            action="store_true", default=False)
    (options, args) = parser.parse_args()
    filepath = args[0]

    logs = Logs()
    if filepath.endswith('.log'):
        logs.load_log(filepath)
    elif filepath.endswith('.h5'):
        logs.load_h5(filepath)
    else:
        raise NotImplemented

    if options.save:
        logs.save(options.save)
    if options.shell:
        import pdb; pdb.set_trace()

