from optparse import OptionParser
import zipfile
import gzip
import json
from collections import defaultdict
import datetime
import os
import logging
import re
import glob

from datautil.tabular import TabularData, CsvReader, CsvWriter
from sqlalchemy.util import OrderedDict

log = logging.getLogger(__file__)

import_source_prefixes = {
    'ONS': 'ONS feed',
    'COSPREAD': 'Spreadsheet upload',
    'Manual': 'Spreadsheet upload',
    'DATA4NR': 'Data for Neighbourhoods and Regeneration import',
    }
date_converters = (
    (re.compile('(\d{4})(\d{2})(\d{2})'), '%Y%m%d'),
    (re.compile('(\d{4})-(\d{2})-(\d{2})'), '%Y-%m-%d'),
    )

def parse_date(date_str, search=False):
    assert isinstance(date_str, basestring)
    for date_regex, date_format in date_converters:
        matcher = date_regex.search if search else date_regex.match
        match = matcher(date_str)
        if match:
            date = datetime.datetime.strptime(match.group(), date_format)
            return date.date()
    raise ValueError('Cannot parse date: %r' % date_str)

def get_run_info():
    run_info  = 'This analysis is produced by an OKF script\n'
    run_info += 'Date last updated: %r\n' % datetime.date.today().strftime('%Y-%m-%d')
    run_info += 'Script filename: %r\n' % os.path.basename(__file__)
    run_info += 'Script repository: http://bitbucket.org/okfn/ckanext-dgu\n'
    run_info += 'Dump files for analysis: http://data.gov.uk/data/dumps\n'
    return run_info

class AnalysisFile(object):
    def __init__(self, analysis_filepath, run_info=None):
        self.analysis_filepath = analysis_filepath
        self.data_by_date = None # {date: analysis_dict}
        self.run_info = run_info
        self.load()

    def load(self):
        '''Load analysis file and store in self.data_by_date'''
        raise NotImplementedError

    def init(self):
        '''Initialise self.data for the first time (instead of loading
        from an existing file).'''
        self.data_by_date = {}

    def save(self):
        '''Save self.data_by_date to analysis file'''
        raise NotImplementedError

    def format_date(self, date):
        assert isinstance(date, datetime.date)
        return date.strftime('%Y-%m-%d')

    def add_analysis(self, date, analysis_dict):
        '''Takes an analysis and updates self.data_by_date.'''
        assert isinstance(date, datetime.date)
        assert isinstance(analysis_dict, dict)
        self.data_by_date[date] = analysis_dict

class TabularAnalysisFile(AnalysisFile):
    def load(self):
        '''Load analysis file and store in self.data_by_date'''
        assert self.data_by_date == None, 'Data already present'
        self.data_by_date = {}
        table = self.load_table()
        if len(table.data) > 0:
            try:
                date_column = table.header.index('date')
            except ValueError:
                raise ValueError('Data does not have a date: %r' % table.header)            
            for row in table.data:
                row_data = dict(zip(table.header, row))
                date = parse_date(row_data['date'])
                del row_data['date']
                self.data_by_date[date] = row_data

    def load_table(self):
        '''Load analysis file and return as TabularData'''
        raise NotImplementedError

    def save(self):
        '''Save self.data_by_date to analysis file'''
        if self.data_by_date:
            header = ['date']
            for date in self.data_by_date:
                for column in self.data_by_date[date].keys():
                    if column not in header:
                        header.append(column)
        else:
            header = []
        data_rows = []
        for date, analysis in sorted(self.data_by_date.items(), key=lambda (date, analysis): date):
            data_row = [self.format_date(date)]
            for title in header[1:]:
                data_row.append(analysis.get(title))
            data_rows.append(data_row)
        data_table = TabularData(data_rows, header)
        self.save_table(data_table)

    def save_table(self, data_table):
        '''Save data_table to analysis file'''
        raise NotImplementedError

class CsvAnalysisFile(TabularAnalysisFile):
    def load_table(self):
        if not os.path.exists(self.analysis_filepath):
            log.info('Creating new analysis file: %s', self.analysis_filepath)
            return TabularData()
        data_table = CsvReader().read(filepath_or_fileobj=self.analysis_filepath)
        return data_table
    
    def save_table(self, data_table):
        fileobj = open(self.analysis_filepath, 'w')
        try:
            CsvWriter().write(data_table, fileobj)
        finally:
            fileobj.close()

class TxtAnalysisFile(AnalysisFile):
    def load(self):
        self.data_by_date = {}
        if not os.path.exists(self.analysis_filepath):
            log.info('Creating new analysis file: %s', self.analysis_filepath)
            return
        fileobj = open(self.analysis_filepath, 'r')
        regex = re.compile(r'^(\d{4}-\d{2}-\d{2}) : (.*)\n')
        try:
            while True:
                line = fileobj.readline()
                if line == '':
                    break
                match = regex.match(line)
                if not match:
                    if line.strip() and ' : ' in line:
                        raise AssertionError('Could not parse line: %r' % line)
                    else:
                        # just a comment
                        continue
                date_str, analysis_str = match.groups()
                date = parse_date(date_str)
                self.data_by_date[date] = analysis_str
        finally:
            fileobj.close()

    def save(self):
        fileobj = open(self.analysis_filepath, 'w')
        try:
            fileobj.write(self.run_info + '\n')
            for date, analysis in self.data_by_date.items():
                line = '%s : %s\n' % (self.format_date(date), repr(analysis))
                fileobj.write(line)
        finally:
            fileobj.close()
        

class DumpAnalysis(object):
    def __init__(self, dump_filepath):
        log.info('Analysing %s' % dump_filepath)
        self.dump_filepath = dump_filepath
        self.run()
        
    def run(self):
        self.save_date()
        self.analysis_dict = OrderedDict()
        packages = self.get_packages()
        self.analysis_dict['Total active and deleted packages'] = len(packages)
        packages = self.filter_out_deleted_packages(packages)
        self.analysis_dict['Total active packages'] = len(packages)
        pkg_bins = self.analyse_by_source(packages)
        for bin, pkgs in pkg_bins.items():
            self.analysis_dict['Packages by source: %s' % bin] = len(pkgs)
        self.print_analysis(pkg_bins)

    def save_date(self):
        self.date = parse_date(self.dump_filepath, search=True)
        log.info('Date of dumpfile: %r', self.date.strftime('%Y %m %d'))

    def get_packages(self):
        if zipfile.is_zipfile(self.dump_filepath):
            log.info('Unzipping...')
            zf = zipfile.ZipFile(self.dump_filepath)
            assert len(zf.infolist()) == 1, 'Archive must contain one file: %r' % zf.infolist()
            f = zf.open(zf.namelist()[0])
        elif self.dump_filepath.endswith('gz'):            
            f = gzip.open(self.dump_filepath, 'rb')
        else:
            f = open(self.dump_filepath, 'rb')
        log.info('Reading file...')
        json_buf = f.read()
        log.info('Parsing JSON...')
        packages = json.loads(json_buf)
        log.info('Read in packages: %i' % len(packages))
        return packages

    def filter_out_deleted_packages(self, packages):
        filtered_pkgs = []
        for pkg in packages:
            if pkg.has_key('state'):
                is_active = pkg['state'] == 'active'
            else:
                is_active = pkg['state_id'] == 1
            if is_active:
                filtered_pkgs.append(pkg)
        log.info('Deleted packages discarded: %i', (len(packages) - len(filtered_pkgs)))
        log.info('Number of active packages: %i', (len(filtered_pkgs)))
        return filtered_pkgs

    def analyse_by_source(self, packages):
        pkg_bins = defaultdict(list)
        for pkg in packages:
            import_source = pkg['extras'].get('import_source')
            if import_source:
                for prefix in import_source_prefixes:
                    if import_source.startswith(prefix):
                        import_source = import_source_prefixes[prefix]
                        break
                pkg_bins[import_source].append(pkg['name'])
                continue
            if pkg['extras'].get('INSPIRE') == 'True':
                pkg_bins['INSPIRE'].append(pkg['name'])
                continue
            pkg_bins['Manual creation using web form'].append(pkg['name'])
        return pkg_bins

    def print_analysis(self, pkg_bins):
        log.info('* Analysis by source *')
        for pkg_bin, pkgs in sorted(pkg_bins.items(), key=lambda (pkg_bin, pkgs): -len(pkgs)):
            log.info('  %s: %i (e.g. %r)', pkg_bin, len(pkgs), pkgs[0])

def command():
    usage = 'usage: %prog [options] dumpfile.json.zip'
    usage += '\nNB: dumpfile can be gzipped, zipped or json'
    usage += '\n    can be list of files and can be a wildcard.'
    parser = OptionParser(usage=usage)
    parser.add_option('--csv', dest='csv_filepath',
                      help='add analysis to CSV report FILENAME', metavar='FILENAME')
    parser.add_option('--txt', dest='txt_filepath',
                      help='add analysis to textual report FILENAME', metavar='FILENAME')
    (options, args) = parser.parse_args()
    input_file_descriptors = args
    input_filepaths = []
    for input_file_descriptor in input_file_descriptors:
        input_filepaths.extend(glob.glob(os.path.expanduser(input_file_descriptor)))

    # Open output files
    output_types = (
        # (output_filepath, analysis_file_class)
        (options.txt_filepath, TxtAnalysisFile),
        (options.csv_filepath, CsvAnalysisFile),
        )
    analysis_files = {} # analysis_file_class, analysis_file
    run_info = get_run_info()
    for output_filepath, analysis_file_class in output_types:
        if output_filepath:
            analysis_files[analysis_file_class] = analysis_file_class(output_filepath, run_info)

    for input_filepath in input_filepaths:
        # Run analysis
        analysis = DumpAnalysis(input_filepath)

        for analysis_file_class, analysis_file in analysis_files.items():
            analysis_file.add_analysis(analysis.date, analysis.analysis_dict)
            # Save
            analysis_file.save()
    log.info('Finished')
