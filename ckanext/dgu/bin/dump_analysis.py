import zipfile
import gzip
import json
from collections import defaultdict
import datetime
import os
import logging
import re
import glob
import requests

from datautil.tabular import TabularData, CsvReader, CsvWriter
from sqlalchemy.util import OrderedDict
from paste.deploy.converters import asbool

from ckanext.importlib import command

log = logging.getLogger('ckanext.dgu.bin.dump_analysis')

total_label = 'Total datasets'
manual_creation = 'Manual creation using web form'
import_source_prefixes = {
    'ONS': 'National Statistics Publication Hub feed',
    'COSPREAD': 'Spreadsheet upload',
    'Manual': manual_creation, # originally inputted manually, but reloaded using a spreadsheet

    'DATA4NR': 'Data for Neighbourhoods and Regeneration import',
    }
unpublished = 'Spreadsheet upload for unpublished datasets'
OLD_THEMES = {
    'Transportation': 'Transport',
    'Finance': 'Government Spending',
    'Spending Data': 'Government Spending',
    'Spending': 'Government Spending',
    'Economy': 'Business & Economy',
    'Crime': 'Crime & Justice',
    'Administration': 'Government',
    'Location': 'Environment',
    'Geography': 'Environment',
    }
THEMES = ('Society', 'Government Spending', 'Education', 'Crime & Justice', 'Environment', 'Towns & Cities', 'Mapping', 'Health', 'Government', 'Defence', 'Business & Economy', 'Transport')


date_converters = (
    (re.compile('(\d{4})(\d{2})(\d{2})'), '%Y%m%d'),
    (re.compile('(\d{4})-(\d{2})-(\d{2})'), '%Y-%m-%d'),
    )

class DumpAnalysisOptions(dict):
    '''If calling DumpAnalysis not from the command-line, use this
    class for the options'''
    def __init__(self, **initial_options):
        self['examples'] = '1'
        self.update(**initial_options)
        
    def __getattr__(self, key):
        if self.has_key(key):
            return self[key]
        else:
            return None

def parse_date(date_str, search=False):
    assert isinstance(date_str, basestring)
    for date_regex, date_format in date_converters:
        matcher = date_regex.search if search else date_regex.match
        match = matcher(date_str)
        if match:
            date = datetime.datetime.strptime(match.group(), date_format)
            return date.date()
    raise ValueError('Cannot parse date: %r' % date_str)

def format_date(date):
    assert isinstance(date, datetime.date)
    return date.strftime('%Y-%m-%d')

def get_run_info():
    run_info  = 'This analysis is produced by a script\n'
    run_info += 'Date last updated: %r\n' % format_date(datetime.date.today())
    run_info += 'Script filename: %r\n' % os.path.basename(__file__)
    run_info += 'Script repository: http://github.com/datagovuk/ckanext-dgu\n'
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

    def add_analysis(self, date, analysis_dict):
        '''Takes an analysis and updates self.data_by_date.'''
        assert isinstance(date, datetime.date)
        assert isinstance(analysis_dict, dict)
        self.data_by_date[date] = analysis_dict

    def get_data_by_date_sorted(self):
        '''Returns the data as a list of tuples (date, analysis),
        sorted by date.'''
        return sorted(self.data_by_date.items(),
                      key=lambda (date, analysis): date)

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
        # Work out what to have in the header row
        if self.data_by_date:
            header = ['date']
            for date in self.data_by_date:
                for column in self.data_by_date[date].keys():
                    if column not in header:
                        header.append(column)
        else:
            header = []
        # Put the total last
        if total_label in header:
            header.pop(header.index(total_label))
            header.append(total_label)

        # Write the rows
        data_rows = []
        for date, analysis in self.get_data_by_date_sorted():
            data_row = [format_date(date)]
            for title in header[1:]:
                data_row.append(analysis.get(title, ''))
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
            for date, analysis in self.get_data_by_date_sorted():
                if isinstance(analysis, basestring):
                    analysis_str = analysis
                elif isinstance(analysis, dict):
                    # use json.dumps instead of repr to keep ordering
                    analysis_str = json.dumps(analysis)
                else:
                    analysis_str = repr(analysis)
                line = '%s : %s\n' % (format_date(date), analysis_str)
                fileobj.write(line)
        finally:
            fileobj.close()
        

class DumpAnalysis(object):
    '''
    Reads a JSON dump file and runs analysis according to the options, and
    saves it in self.analysis_dict
    '''
    def __init__(self, dump_filepath, analysis_type):
        log.info('Analysing %s' % dump_filepath)
        self.dump_filepath = dump_filepath
        self.analysis_type = analysis_type
        self.run()
        
    def run(self):
        self.save_date()
        self.analysis_dict = OrderedDict()
        packages = self.get_packages()
        packages = self.filter_out_deleted_packages(packages)

        if self.analysis_type == 'source':
            pkg_bins = self.analyse_by_source(packages)
        elif self.analysis_type == 'publisher-category':
            pkg_bins = self.analyse_by_publisher_category(packages)
        elif self.analysis_type == 'ons-publisher':
            ons_packages = self.filter_by_ons_packages(packages)
            pkg_bins = self.analyse_by_publisher(ons_packages)
        elif self.analysis_type == 'theme':
            pkg_bins = self.analyse_by_theme(packages)
        else:
            raise NotImplementedError(self.analysis_type)
            
        for bin, pkgs in pkg_bins.items():
            self.analysis_dict[bin] = len(pkgs)
        
        self.analysis_dict[total_label] = len(packages)
        self.print_analysis(pkg_bins)

    def save_date(self):
        try:
            self.date = parse_date(self.dump_filepath, search=True)
        except ValueError:
            # only worry about this later on if we save to a file.
            self.date = None
        datestr = format_date(self.date) if self.date else None
        log.info('Date of dumpfile: %r', datestr)

    def get_packages(self):
        '''Returns the packages listed in the JSON dump file'''
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
        log.info('Deleted datasets discarded: %i', (len(packages) - len(filtered_pkgs)))
        log.info('Number of active datsets: %i', (len(filtered_pkgs)))
        return filtered_pkgs

    def filter_by_ons_packages(self, packages):
        filtered_pkgs = []
        ons_prefix = 'ONS'
        for pkg in packages:
            import_source = pkg['extras'].get('import_source')
            if import_source and import_source.startswith(ons_prefix):
                filtered_pkgs.append(pkg)
        log.info('Number of Pub Hub packages: %i', (len(filtered_pkgs)))
        return filtered_pkgs

    def analyse_by_source(self, packages):
        # Setup the bins in correct order
        pkg_bins = OrderedDict()
        for bin in ('Manual creation using web form',
                    'Data for Neighbourhoods and Regeneration import',
                    'Spreadsheet upload',
                    'National Statistics Publication Hub feed',
                    'UK Location Programme',
                    'Spreadsheet upload for unpublished datasets',
                    ):
            pkg_bins[bin] = []

        # Allocate packages to bins
        for pkg in packages:
            import_source = pkg['extras'].get('import_source')
            if import_source:
                for prefix in import_source_prefixes:
                    if import_source.startswith(prefix):
                        import_source = import_source_prefixes[prefix]
                        break
                pkg_bins[import_source].append(pkg['name'])
                continue
            if (pkg['extras'].get('UKLP') or pkg['extras'].get('INSPIRE')) == 'True':
                pkg_bins['UK Location Programme'].append(pkg['name'])
                continue
            if (pkg.get('url') or '').startswith('http://www.data4nr.net/resources/'):
                import_source = import_source_prefixes['DATA4NR']
                pkg_bins[import_source].append(pkg['name'])
                continue
            if pkg['extras'].get('co_id'):
                import_source = import_source_prefixes['COSPREAD']
                pkg_bins[import_source].append(pkg['name'])
                continue
            if asbool(pkg['extras'].get('unpublished')):
                import_source = unpublished
                pkg_bins[import_source].append(pkg['name'])
                continue
            pkg_bins[manual_creation].append(pkg['name'])
        return pkg_bins

    @classmethod
    def _get_publisher(cls, pkg):
        # e.g. 'owner_org': u'e53c6d81-b763-4eff-909f-3ffaa8327490'
        # used 2013-11-01 - 2014-06-01
        if 'owner_org' in pkg:
            org_id = pkg.get('owner_org')
            return cls._get_org_by_id(org_id)['name']

        # e.g. 'groups': [u'isd-scotland']
        # used 2012-07-01 - 2013-10-01
        groups = set(pkg['groups']) - set(('ukgov',))
        if groups:
            return cls._get_org_by_name(groups.pop())

        # e.g. Police Service of Northern Ireland [16348]
        # used 2011-03-01 - 2012-06-01
        publisher = pkg['extras'].get('published_by')
        if publisher:
            if not hasattr(cls, '_remove_id_regex'):
                cls._remove_id_regex = re.compile(' \[\d+\]')
            publisher = cls._remove_id_regex.sub('', publisher)
            return cls._get_org_by_name(publisher)

        # e.g. pkg['extras'].get('agency') = u'Police Service of Northern Ireland (PSNI)'
        # pkg[u'author']: u'Communities and Local Government (CLG)'
        # (Publisher names are in Drupal)
        # used 2010-01-21 - 2011-02-01
        title = pkg['extras'].get('agency') or pkg['extras'].get('department') or pkg['author']
        if not hasattr(cls, '_remove_abbrev_regex'):
            cls._remove_abbrev_regex = re.compile(' \([^\)]+\)')
            cls._org_map = {
                'Information Centre - Clinical and Health Outcomes Knowledge Base': 'NHS Information Centre for Health and Social Care',
                'Information Centre for Health and Social Care': 'NHS Information Centre for Health and Social Care',
                'NHS Information Centre for health and social care': 'NHS Information Centre for Health and Social Care',
                'DCLG Floor Targets Interactive': 'Department for Communities and Local Government',
                'Neighbourhood Statistics': 'Office for National Statistics',
                'Business Registers Unit': 'Office for National Statistics',
                'Nomis': 'Office for National Statistics',
                'Business Registers Unit / Neighbourhood Statistics': 'Office for National Statistics',
                'Welsh Assembly Government': 'Welsh Government',
                'Health & Social Care Information Centre': 'NHS Information Centre for Health and Social Care ',
                'Communities and Local Government': 'Department for Communities and Local Government',
                'National Health Service in Scotland': 'NHS Scotland',
                'UK Hydrographic Office': 'United Kingdom Hydrographic Office',
                'FERA': 'The Food and Environment Research Agency',
                'HM Customs and Revenue': 'Her Majesty\'s Revenue and Customs'
                }

        title = cls._remove_abbrev_regex.sub('', title)
        if title in cls._org_map:
            title = cls._org_map[title]
        org = cls._get_org_by_title(title)
        if org:
            return org
        else:
            print 'WARN not recognized: "%s"' % title
            return None

    def analyse_by_publisher(self, packages):
        pkg_bins = defaultdict(list)
        for pkg in packages:
            org = self._get_publisher(pkg)
            if org:
                pkg_bins[org['title']].append(pkg['name'])
                continue
            pkg_bins['No value'].append(pkg['name'])
        return pkg_bins

    def analyse_by_publisher_category(self, packages):
        pkg_bins = defaultdict(list)
        for pkg in packages:
            org = self._get_publisher(pkg)
            if org:
                import pdb; pdb.set_trace()
                category = org.get('category') or 'No value'
            else:
                category = 'Publisher not identified'
            pkg_bins[category].append(pkg['name'])
        return pkg_bins

    def analyse_by_theme(self, packages):
        pkg_bins = defaultdict(list)
        for pkg in packages:
            theme = pkg['extras'].get('theme-primary')
            if (not theme) or (not theme.strip()):
                pkg_bins['No value'].append(pkg['name'])
                continue
            # Fix old names for themes so they are consistent
            if theme in OLD_THEMES:
                theme = OLD_THEMES[theme]
            if theme not in THEMES:
                theme = 'Other: %s' % theme
            pkg_bins[theme].append(pkg['name'])
        return pkg_bins

    def print_analysis(self, pkg_bins):
        log.info('* Analysis by source *')
        for pkg_bin, pkgs in sorted(pkg_bins.items(), key=lambda (pkg_bin, pkgs): -len(pkgs)):
            log.info('  %s: %i (e.g. %r)', pkg_bin, len(pkgs), pkgs[:2])

    @classmethod
    def _load_orgs_if_needed(cls):
        if not hasattr(cls, '_orgs_by_id'):
            res = requests.get('http://data.gov.uk/api/action/organization_list?all_fields=1')
            assert res.ok
            org_dicts = res.json()['result']
            cls._orgs_by_id = {}
            cls._orgs_by_name = {}
            cls._orgs_by_title = {}
            for org_dict in org_dicts:
                cls._orgs_by_id[org_dict['id']] = org_dict
                cls._orgs_by_name[org_dict['name']] = org_dict
                cls._orgs_by_title[org_dict['title']] = org_dict

    @classmethod
    def _get_org_by_id(cls, org_id):
        cls._load_orgs_if_needed()
        return cls._orgs_by_id[org_id]

    @classmethod
    def _get_org_by_name(cls, org_name):
        cls._load_orgs_if_needed()
        return cls._orgs_by_name[org_name]

    @classmethod
    def _get_org_by_title(cls, org_title):
        cls._load_orgs_if_needed()
        org = cls._orgs_by_title.get(org_title)
        # Else try nomenklatura?
        return org


ANALYSIS_TYPES = ('source', 'ons-publisher', 'publisher-category', 'theme')

class Command(command.Command):
    usage = 'usage: %prog [options] <analysis_type> dumpfile.json.zip'
    usage += '\n  where:'
    usage += '\n  * analysis_type is one of: %s' % ' '.join(ANALYSIS_TYPES)
    usage += '\n  * dumpfile can be gzipped, zipped or json and can use wildcards.'

    def add_options(self):
        self.parser.add_option('--csv', dest='csv_filepath',
                               help='add analysis to CSV report FILENAME',
                               metavar='FILENAME')
        self.parser.add_option('--txt', dest='txt_filepath',
                               help='add analysis to textual report FILENAME',
                               metavar='FILENAME')
        self.parser.add_option('--examples', dest='examples',
                               default='1',
                               help='show NUMBER of examples for each category',
                               metavar='NUMBER')

    def parse_args(self):
        super(Command, self).parse_args()
        if not self.args[0] in ANALYSIS_TYPES:
            self.parser.error('Analysis type not recognised')
 
    def command(self):
        analysis_type, input_file_descriptor = self.args
        input_filepaths = glob.glob(os.path.expanduser(input_file_descriptor))

        # Open output files
        output_types = (
            # (output_filepath, analysis_file_class)
            (self.options.txt_filepath, TxtAnalysisFile),
            (self.options.csv_filepath, CsvAnalysisFile),
            )
        analysis_files = {} # analysis_file_class, analysis_file
        run_info = get_run_info()
        for output_filepath, analysis_file_class in output_types:
            if output_filepath:
                analysis_files[analysis_file_class] = analysis_file_class(output_filepath, run_info)

        for input_filepath in input_filepaths:
            # Run analysis
            analysis = DumpAnalysis(input_filepath, analysis_type)

            if analysis_files:
                assert analysis.date, 'The results are requested to be saved to '
                'an analysis file which is sorted by date, but could not find '
                'a date in the input filename: %s' % input_filepath

            for analysis_file_class, analysis_file in analysis_files.items():
                analysis_file.add_analysis(analysis.date, analysis.analysis_dict)
                # Save
                analysis_file.save()
        log.info('Finished')

def command():
    Command().command()
