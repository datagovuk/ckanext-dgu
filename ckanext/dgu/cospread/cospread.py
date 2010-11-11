import os.path

from collections import defaultdict

from sqlalchemy.util import OrderedDict

from ckanext.loader import *
from ckan.lib.importer import RowParseError
from ckan.lib.spreadsheet_importer import CsvData, SpreadsheetDataRecords, SpreadsheetPackageImporter
from ckan.lib import schema_gov
from ckan.lib import field_types
from ckan import model


class CospreadLoader(PackageLoader):
    def __init__(self, ckanclient):
        settings = ReplaceByExtraField('external_reference')
        super(CospreadLoader, self).__init__(ckanclient, settings)

class CospreadDataRecords(SpreadsheetDataRecords):
    def __init__(self, data):
        essential_title = 'Package name'
        self.column_spreading_titles = ['Geographical Granularity', 'Geographic coverage', 'Temporal Granularity', 'Temporal Coverage', 'Author', 'Maintainer', 'Contact']
        self.standard_or_other_columns = ['Geographical Granularity', 'Temporal Granularity']
        self.resource_keys = ['Download URL', 'File format']

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
                # this record is another resource the current record.
                keys_that_should_match = set(current_record.keys()) - set(self.resource_keys + ['resources'] + self.standard_or_other_columns)
                for key in keys_that_should_match:
                    assert current_record[key] == record[key], 'Multiple resources for package %s, but value does not match: %r!=%r' % (record['Package name'], current_record[key], record[key])
            else:
                # this record is new, so yield the old 'current_record' before
                # making this record 'current_record'.
                if current_record:
                    yield current_record
                current_record = record.copy()
                # Collapse standard/other columns into one
                for column in self.standard_or_other_columns:
                    standard = current_record['%s - Standard' % column]
                    other = current_record['%s - Other' % column]
                    if standard == 'Other (specify)':
                        value = other
                    else:
                        assert not other, 'Both "Standard" and "Other" values for column %r in record %r' % (column, current_record)
                        value = standard
                    current_record[column] = value
                    del current_record['%s - Standard' % column]
                    del current_record['%s - Other' % column]
                # Get rid of download_url
                for key in self.resource_keys:
                    del current_record[key]
                current_record['resources'] = []
            # Put download_url into resources
            current_record['resources'].append(OrderedDict((k, record[k]) for k in self.resource_keys))
        if current_record:
            yield current_record


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
        super(CospreadImporter, self).__init__(**kwargs)

    def import_into_package_records(self):
        package_data = CsvData(self.log, filepath=self._filepath,
                               buf=self._buf)
        self._package_data_records = CospreadDataRecords(package_data)

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
        pkg_dict['geographical_granularity'] = row_dict['Geographical Granularity']
        pkg_dict['temporal_granularity'] = row_dict['Temporal Granularity']
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
            print 'Warning: license not recognised: "%s". Defaulting to: %s.' % (row_dict['Licence'], license_id)
        pkg_dict['license_id'] = license_id
        pkg_dict['url'] = self.tidy_url(row_dict['URL'])
        pkg_dict['notes'] = notes
        if self.include_given_tags:
            given_tags = schema_gov.tags_parse(row_dict['Tags'])
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
            if row_dict[field] == u'Yes':
                geo_cover.append(munged_region)
        extras_dict['geographic_coverage'] = geo_coverage_type.form_to_db(geo_cover)
        
        for column in ['Date released', 'Date updated']:
            try:
                val = field_types.DateType.form_to_db(row_dict[column])
            except field_types.DateConvertError, e:
                print "WARNING: Value for column '%s' of '%s' is not understood as a date format." % (column, row_dict[column])
                val = row_dict[column]
            extras_dict[column.lower().replace(' ', '_')] = val
            
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
        for field_mapping in field_map:
            column = field_mapping[0]
            extras_key = column.lower().replace(' ', '_')
            if column == 'Agency responsible':
                extras_key = 'agency'
            elif column in ('CO Identifier', 'CO Reference'):
                if row_dict.has_key('CO Reference'):
                    column = 'CO Reference'
                extras_key = 'external_reference'
            val = row_dict[column]
            if len(field_mapping) > 1:
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
                    print "WARNING: Value for column '%s' of '%s' is not in suggestions '%s'" % (column, val, suggestions)
            extras_dict[extras_key] = val
        
        extras_dict['national_statistic'] = u'' # Ignored: row_dict['national statistic'].lower()
        extras_dict['import_source'] = 'COSPREAD-%s' % os.path.basename(self._filepath)
        for field in ['temporal_coverage_from', 'temporal_coverage_to']:
            extras_dict[field] = u''

        resources = []
        for row_resource in row_dict['resources']:
            res_dict = OrderedDict([
                ('url', self.tidy_url(row_resource['Download URL'])),
                ('format', row_resource.get('File format', u'')),
                ('description', row_resource.get('Description', u'')),
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

        ##

##        geo_coverage = schema_gov.GeoCoverageType.get_instance().str_to_db(row_dict['Geographic Coverage'])

##        munged_dates = {}
##        for column in ['Date Released', 'Date Updated',
##                       'Temporal Coverage To', 'Temporal Coverage From']:
##            val = '%s' % row_dict[column]
##            munged_dates[column] = val

##        taxonomy_url = row_dict['Taxonomy url']
##        if taxonomy_url and taxonomy_url != '-':
##            taxonomy_url = self.tidy_url(taxonomy_url, self.log)
            
##        national_statistic = u'no'
##        if row_dict['National Statistic'] != national_statistic:
##            self.log('Warning: Ignoring national statistic for non-ONS data: %s' % row_dict['National Statistic'])

##        pkg_dict = OrderedDict([
##            ('name', name),
##            ('title', title),
##            ('version', row_dict['Version'][:model.PACKAGE_VERSION_MAX_LENGTH]),
##            ('url', None),
##            ('author', author),
##            ('author_email', author_email),
##            ('maintainer', None),
##            ('maintainer_email', None),
##            ('notes', row_dict['Abstract']),
##            ('license_id', license_id),
##            ('tags', []), # post-filled
##            ('groups', ['ukgov']),
##            ('resources', resources),
##            ('extras', OrderedDict([
##                ('external_reference', ref),
##                ('date_released', munged_dates['Date Released']),
##                ('date_updated', munged_dates['Date Updated']),
##                ('temporal_granularity', row_dict['Temporal Granularity']),
##                ('temporal_coverage_from', munged_dates['Temporal Coverage From']),
##                ('temporal_coverage_to', munged_dates['Temporal Coverage To']),
##                ('geographic_coverage', geo_coverage),
##                ('geographical_granularity', row_dict['Geographic Granularity']),
##                ('agency', row_dict['Agency']),
##                ('precision', row_dict['Precision']),
##                ('taxonomy_url', taxonomy_url),
##                ('import_source', 'COSPREAD-%s' % os.path.basename(self._filepath)),
##                ('department', row_dict['Department']),
##                ('update_frequency', row_dict['Update Frequency']),
##                ('national_statistic', national_statistic),
##                ('categories', row_dict['Categories']),
##                ])),
##            ])

        tags = schema_gov.TagSuggester.suggest_tags(pkg_dict)
        [tags.add(tag) for tag in schema_gov.tags_parse(row_dict['Tags'])]
        if self.include_given_tags:
            tags = tags | set(given_tags)
        pkg_dict['tags'] = sorted(list(tags))

##        # snap to suggestions
##        field_suggestions = [
##            ['temporal_granularity', schema_gov.temporal_granularity_options],
##            ['geographical_granularity', schema_gov.geographic_granularity_options],
##            ['categories', schema_gov.category_options],
##            ['department', schema_gov.government_depts],
##            ]
##        for field, suggestions in field_suggestions:
##            val = pkg_dict['extras'][field]
##            if val and val != '-' and val not in suggestions:
##                suggestions_lower = [sugg.lower() for sugg in suggestions]
##                if val.lower() in suggestions_lower:
##                    val = suggestions[suggestions_lower.index(val.lower())]
##                elif schema_gov.expand_abbreviations(val) in suggestions:
##                    val = schema_gov.expand_abbreviations(val)
##                elif val.lower() + 's' in suggestions:
##                    val = val.lower() + 's'
##                elif val.replace('&', 'and').strip() in suggestions:
##                    val = val.replace('&', 'and').strip()
##            if val and val != '-' and val not in suggestions:
##                self.log("WARNING: Value for column '%s' of '%s' is not in suggestions '%s'" % (column, val, suggestions))
##            pkg_dict['extras'][field] = val

        return pkg_dict
        
    def name_munge(self, input_name):
        '''Munges the name field in case it is not to spec.'''
        input_name = input_name.replace(' ', '').replace('.', '_').replace('&', 'and')
        return super(CospreadImporter, self).name_munge(input_name)

    def tidy_url(self, url):
        if url and not url.startswith('http') and not url.startswith('webcal:'):
            if url.startswith('www.'):
                url = url.replace('www.', 'http://www.')
            else:
                print "Warning: URL doesn't start with http: %s" % url
        return url
