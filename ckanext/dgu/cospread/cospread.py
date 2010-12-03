import os.path
import datetime
import re
import logging

from collections import defaultdict

from sqlalchemy.util import OrderedDict

from ckan.lib.importer import RowParseError, ImportException
from ckan.lib.spreadsheet_importer import CsvData, XlData, SpreadsheetDataRecords, MultipleSpreadsheetDataRecords, SpreadsheetPackageImporter
from ckan.lib import schema_gov
from ckan.lib import field_types
from ckan import model

log = logging.getLogger(__name__)

class CospreadDataRecords(SpreadsheetDataRecords):
    def __init__(self, data):
        essential_title = 'Package name'
        self.column_name_map = {
            u'tags':'Tags',
            u'Download file format':'File format',
            u'Download description':'Download Description',
            u'Maintainer - E-mail address, if needed.':u'Maintainer - E-mail address',
            u'Maintainer - Blank unless not the author.':u'Maintainer - ',
            u'CO Reference':u'CO Identifier',
            u'Author - E-mail address.':'Contact - E-mail address.',
            u'Author - Permanent contact point for members of the public; not an individual.':'Contact - Permanent contact point',
            }
        self.column_name_reverse_map = dict((v, k) for k, v in self.column_name_map.iteritems())
        self.optional_columns = [u'Temporal Coverage - To\n(if needed)',
                                 u'Temporal Coverage - From',
                                 u'Download Description',
                                 u'National Statistic',
                                 u'Maintainer - E-mail address',
                                 u'Maintainer - ',
                                 u'Categories']
        self.column_spreading_titles = ['Geographical Granularity', 'Geographic coverage', 'Temporal Granularity', 'Temporal Coverage', 'Author', 'Maintainer', 'Contact']
        self.standard_or_other_columns = ['Geographical Granularity', 'Temporal Granularity']
        self.resource_keys = ['Download URL', 'File format', 'Download Description']
        super(CospreadDataRecords, self).__init__(data, essential_title)
            
    def find_titles(self, essential_title):
        row_index = 0
        titles = []
        essential_title_lower = essential_title.lower()
        while True:
            if row_index >= self._data.get_num_rows():
                raise ImportException('Could not find title row')
            row = self._data.get_row(row_index)
            if essential_title in row or essential_title_lower in row:
                next_row = self._data.get_row(row_index + 1)
                last_title = None
                for col_index, row_val in enumerate(row):
                    if not row_val:
                        title = None
                        if last_title in self.column_spreading_titles:
                            title = '%s - %s' % (last_title, next_row[col_index])
                    else:
                        title = row_val.strip().replace('  ', ' ')
                        last_title = title
                    if title in self.column_spreading_titles:
                        title = '%s - %s' % (title, next_row[col_index])
                    titles.append(title)
                return (titles, row_index + 1)
            row_index += 1

    @property
    def records(self):
        '''Returns package records.
        * Collates packages with download_url in multiple rows in resources.
        * Collapses 'Standard' / 'Other' column pairs into single value.
        '''
        current_record = None
        for record in super(CospreadDataRecords, self).records:
            if current_record and current_record['Package name'] == record['Package name']:
                # this record is another resource for the current record.
                keys_that_should_match = set(current_record.keys()) - set(self.resource_keys + ['resources'] + self.standard_or_other_columns)
                for key in keys_that_should_match:
                    alt_key = self.column_name_reverse_map.get(key)
                    if alt_key and alt_key in record:
                        record_key = alt_key
                    else:
                        record_key = key
                    assert current_record[key] == record[record_key], 'Multiple resources for package %s, but value does not match: %r!=%r' % (record['Package name'], current_record[key], record[key])
            else:
                # this record is new, so yield the old 'current_record' before
                # making this record 'current_record'.
                if current_record:
                    yield current_record
                current_record = record.copy()
                current_record['resources'] = []
                # Collapse standard/other columns into one
                for column in self.standard_or_other_columns:
                    standard = current_record['%s - Standard' % column]
                    other = current_record['%s - Other' % column]
                    if standard == 'Other (specify)' or standard == None:
                        value = other
                    else:
                        assert not other, 'Both "Standard" and "Other" values for column %r in record %r' % (column, current_record)
                        value = standard
                    current_record[column] = value
                    del current_record['%s - Standard' % column]
                    del current_record['%s - Other' % column]
                # Rename columns to standard names
                keys_to_change = set(current_record.keys()) & set(self.column_name_map.keys())
                for from_key in keys_to_change:
                    to_key = self.column_name_map[from_key]
                    current_record[to_key] = current_record[from_key]
                    del current_record[from_key]
            # Put download_url into resources
            resource = OrderedDict()
            for key in self.resource_keys:
                key_used = None
                if key in record:                
                    key_used = key
                else:
                    alt_key = self.column_name_reverse_map.get(key)
                    if alt_key and alt_key in record:
                        key_used = alt_key
                        value = record[alt_key]
                if key_used:
                    value = record[key_used]
                    resource[key] = value
                    del record[key_used]
                else:
                    if key in self.optional_columns:
                        record[key] = None
                    else:
                        raise KeyError(key)
            current_record['resources'].append(resource)
        if current_record:
            yield current_record

class MultipleCospreadDataRecords(MultipleSpreadsheetDataRecords):
    def __init__(self, data):
        if data.get_num_sheets() > 1:
            data = data.get_data_by_sheet()
        super(MultipleCospreadDataRecords, self).__init__(data, [], record_class=CospreadDataRecords)


class CospreadImporter(SpreadsheetPackageImporter):
    def __init__(self, include_given_tags=False, **kwargs):
        self.include_given_tags = include_given_tags
        self.license_map = {
            u'UK Crown Copyright with data.gov.uk rights':u'uk-ogl',
            u'\xa9 HESA. Not core Crown Copyright.':u'uk-ogl',
            u'Local Authority copyright with data.gov.uk rights':u'uk-ogl',
            u'Local Authority Copyright with data.gov.uk rights':u'uk-ogl',
            u'UK Crown Copyright':u'uk-ogl',
            u'Crown Copyright':u'uk-ogl', }
        super(CospreadImporter, self).__init__(record_params=[], record_class=CospreadDataRecords, **kwargs)

    def log(self, msg):
        super(CospreadImporter, self).log(msg)
        log.warn(msg)

    def record_2_package(self, row_dict):
        pkg_dict = OrderedDict()
        pkg_dict['title'] = row_dict['Title']
        pkg_dict['name'] = self.name_munge(row_dict.get('Package name') or u'') or self.munge(pkg_dict['title'])
        if not (pkg_dict['name'] and pkg_dict['title']):
            raise RowParseError('Both Name and Title fields must be filled: name=%r title=%r' % (pkg_dict['name'], pkg_dict['title']))
        pkg_dict['author'] = row_dict['Contact - Permanent contact point']
        pkg_dict['author_email'] = row_dict['Contact - E-mail address.']
        pkg_dict['maintainer'] = row_dict['Maintainer - ']
        pkg_dict['maintainer_email'] = row_dict['Maintainer - E-mail address']
        notes = row_dict['Notes']
        license_id = self.license_map.get(row_dict['Licence'].strip(), '')
        if not license_id and ';' in row_dict['Licence']:
            license_parts = row_dict['Licence'].split(';')
            for i, license_part in enumerate(license_parts):
                license_id = license_map.get(license_part.strip(), '')
                if license_id:
                    notes += '\n\nLicence detail: %s' % row_dict['Licence']
                    break
        if not license_id:
            license_id = 'uk-ogl'
            self.log('WARNING: license not recognised: "%s". Defaulting to: %s.' % (row_dict['Licence'], license_id))
        pkg_dict['license_id'] = license_id
        pkg_dict['url'] = self.tidy_url(row_dict['URL'])
        pkg_dict['notes'] = notes
        pkg_dict['version'] = u''
        pkg_dict['groups'] = [u'ukgov']

        pkg_dict['extras'] = OrderedDict()
        extras_dict = pkg_dict['extras']
        geo_cover = []
        geo_coverage_type = schema_gov.GeoCoverageType.get_instance()
        spreadsheet_regions = ('England', 'N. Ireland', 'Scotland', 'Wales', 'Overseas', 'Global')
        for region in spreadsheet_regions:
            munged_region = region.lower().replace('n. ', 'northern_')
            field = 'Geographic coverage - %s' % region
            if (row_dict[field] or '').lower() not in (None, '', 'no', 'False'):
                geo_cover.append(munged_region)
        extras_dict['geographic_coverage'] = geo_coverage_type.form_to_db(geo_cover)

        for column, extra_key in [
            ('Date released', 'date_released'),
            ('Date updated', 'date_updated'),
            ('Temporal Coverage - From', 'temporal_coverage_from'),
            ('Temporal Coverage - To\n(if needed)', 'temporal_coverage_to'),
            ]:
            form_value = row_dict.get(column)
            if isinstance(form_value, datetime.date):
                val = field_types.DateType.date_to_db(form_value)
            else:
                if isinstance(form_value, int):
                    form_value = str(form_value)
                # Hack for CLG data to allow '2008/09' to mean '2008', or
                # '2009' if it is a 'To' field.
                match = re.match('(\d{4})/(\d{2})', form_value or '')
                if match:
                    years = [int(year_str) for year_str in match.groups()]
                    if extra_key.endswith('_to'):
                        form_value = str(field_types.DateType.add_centurys_to_two_digit_year(year=years[1], near_year=years[0]))
                    else:
                        form_value = str(years[0])
                try:
                    val = field_types.DateType.form_to_db(form_value)
                except field_types.DateConvertError, e:
                    self.log("WARNING: Value for column '%s' of %r is not understood as a date format." % (column, form_value))
                    val = form_value
            extras_dict[extra_key] = val
            
        field_map = [
            ['CO Identifier'],
            ['Update frequency'],
            ['Temporal Granularity', schema_gov.temporal_granularity_options],
            ['Geographical Granularity', schema_gov.geographic_granularity_options],
            ['Categories', schema_gov.category_options],
            ['Taxonomy URL'],
            ['Agency responsible'],
            ['Precision'],
            ['Department', schema_gov.government_depts],
            ]
        optional_fields = ['Categories']
        for field_mapping in field_map:
            column = field_mapping[0]
            extras_key = column.lower().replace(' ', '_')
            if column == 'Agency responsible':
                extras_key = 'agency'
            elif column in ('CO Identifier', 'CO Reference'):
                if row_dict.has_key('CO Reference'):
                    column = 'CO Reference'
                extras_key = 'external_reference'
            if row_dict.has_key(column):
                val = row_dict[column]
            else:
                assert column in optional_fields, column
                val = None
            if len(field_mapping) > 1:
                # snap to suggestions
                suggestions = field_mapping[1]
                if val and val not in suggestions:
                    suggestions_lower = [sugg.lower() for sugg in suggestions]
                    if val.lower() in suggestions_lower:
                        val = suggestions[suggestions_lower.index(val.lower())]
                    elif schema_gov.expand_abbreviations(val) in suggestions:
                        val = schema_gov.expand_abbreviations(val)
                    elif val.lower() + 's' in suggestions:
                        val = val.lower() + 's'
                    elif val.replace('&', 'and').strip() in suggestions:
                        val = val.replace('&', 'and').strip()
                if val and val not in suggestions:
                    self.log("WARNING: Value for column '%s' of '%s' is not in suggestions '%s'" % (column, val, suggestions))
            extras_dict[extras_key] = val
        
        extras_dict['national_statistic'] = u'' # Ignored: row_dict['national statistic'].lower()
        extras_dict['import_source'] = 'COSPREAD-%s' % os.path.basename(self._filepath)

        resources = []
        for row_resource in row_dict['resources']:
            res_dict = OrderedDict([
                ('url', self.tidy_url(row_resource['Download URL'])),
                ('format', row_resource.get('File format', u'')),
                ('description', row_resource.get('Download Description', u'')),
                ])
            if '\n' in res_dict['url']:
                # multiple urls
                for url in res_dict['url'].split():
                    res_dict_tmp = OrderedDict(res_dict.items()) # i.e. deepcopy
                    res_dict_tmp['url'] = url
                    resources.append(res_dict_tmp)
            else:
                resources.append(res_dict)
        pkg_dict['resources'] = resources

        tags = schema_gov.TagSuggester.suggest_tags(pkg_dict)
        if self.include_given_tags:
            given_tags = schema_gov.tags_parse(row_dict['Tags'])
            tags = tags | set(given_tags)
        pkg_dict['tags'] = sorted(list(tags))

        return pkg_dict
        
    @classmethod
    def munge(self, name):
        # convert spaces and separating symbols to underscores
        name = re.sub('[\s:/]', '-', name).lower()        
        # take out not-allowed characters
        name = re.sub('[^a-z0-9-_]', '', name)
        # remove double minuses
        name = re.sub('--', '-', name)
        # if longer than max_length, keep last word if a year
        max_length = model.PACKAGE_NAME_MAX_LENGTH
        if len(name) > max_length:
            year_match = re.match('.*?[_-]((?:\d{2,4}[-/])?\d{2,4})$', name)
            if year_match:
                year = year_match.groups()[0]
                name = '%s-%s' % (name[:(max_length-len(year)-1)], year)
            else:
                name = name[:max_length]
        return name

    def name_munge(self, input_name):
        '''Munges the name field in case it is not to spec.'''
        input_name = input_name.replace(' ', '').replace('.', '_').replace('&', 'and')
        return super(CospreadImporter, self).name_munge(input_name)

    def tidy_url(self, url):
        if url and not url.startswith('http') and not url.startswith('webcal:'):
            if url.startswith('www.'):
                url = url.replace('www.', 'http://www.')
            else:
                self.log("WARNING: URL doesn't start with http: %s" % url)
        return url
