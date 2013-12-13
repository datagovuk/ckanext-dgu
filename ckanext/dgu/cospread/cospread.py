import os.path
import datetime
import re
import logging

from collections import defaultdict

from sqlalchemy.util import OrderedDict

from ckan import model
from ckanext.dgu import schema
from ckan.lib import field_types
from ckanext.importlib.importer import PackageImporter, RowParseError, ImportException
from ckanext.importlib.spreadsheet_importer import CsvData, XlData, SpreadsheetDataRecords, MultipleSpreadsheetDataRecords, SpreadsheetPackageImporter

log = logging.getLogger(__name__)

class CospreadDataRecords(SpreadsheetDataRecords):
    def __init__(self, data, generate_names=False):
        self.generate_names = generate_names
        # cospread uses a list of alternative essential_titles
        essential_titles = ['Package name', 'Abstract']
        self.title_normaliser = (
            #('Normalised title', 'regex of variations'),
            ('Package name', '(Package name|Identifier)$'),
            ('Title', 'Title$'),
            ('CO Identifier', 'CO (Identifier|Reference)$'),
            ('Notes', 'Notes|Abstract$'),
            ('Date released', 'Date released$'),
            ('Date updated', 'Date updated$'),
            ('Date update future', 'Date to be published$'),
            ('Update frequency', 'Update frequency$'),
            ('Geographical Granularity - Standard', 'Geographical Granularity - Standard$'),
            ('Geographical Granularity - Other', 'Geographical Granularity - Other$'),
            ('Geographic coverage - England', 'Geographic coverage - England$'),
            ('Geographic coverage - N. Ireland', 'Geographic coverage - N. Ireland$'),
            ('Geographic coverage - Scotland', 'Geographic coverage - Scotland$'),
            ('Geographic coverage - Wales', 'Geographic coverage - Wales$'),
            ('Geographic coverage - Overseas', 'Geographic coverage - Overseas$'),
            ('Geographic coverage - Global', 'Geographic coverage - Global$'),
            ('Temporal Granularity - Standard', 'Temporal Granularity - Standard$'),
            ('Temporal Granularity - Other', 'Temporal Granularity - Other$'),
            ('Temporal Coverage - To', 'Temporal Coverage - To'),
            ('Temporal Coverage - From', 'Temporal Coverage - From$'),
            ('Categories', 'Categories$'),
            ('National Statistic', 'National Statistic$'),
            ('Precision', 'Precision$'),
            ('URL', 'URL$'),
            ('Download URL', '(Download URL|Resources - URL)$'),
            ('File format', '(Download |Resources - )?file format$'),
            ('Download Description', '(Resources -|Download) Description$'),
            ('Taxonomy URL', 'Taxonomy URL$'),
            ('Department', 'Department$'),
            ('Agency responsible', 'Agency responsible$'),
            ('Published by', 'Published by$'),
            ('Published via', 'Published via$'),
            ('Contact - Permanent contact point', '(Contact|Author) - Permanent contact point'),
            ('Contact - E-mail address.', '(Contact|Author) - E-mail address.$'),
            ('Maintainer - ', 'Maintainer - (Blank unless not the author\.)?$'),
            ('Maintainer - E-mail address', 'Maintainer - E-mail address'),
            ('Licence', 'Licence$'),
            ('Tags', 'Tags$'),
            ('Mandate', 'Mandate$'),
            )
        # compile regexes
        self.title_normaliser = [
            (norm_title, re.compile(regex, re.I)) \
            for norm_title, regex in self.title_normaliser
            ]
        self.optional_columns = [u'Temporal Coverage - To',
                                 u'Temporal Coverage - From',
                                 u'Download Description',
                                 u'National Statistic',
                                 u'Maintainer - E-mail address',
                                 u'Maintainer - ',
                                 u'Categories']
        self.column_spreading_titles = ['Geographical Granularity', 'Geographic coverage', 'Temporal Granularity', 'Temporal Coverage', 'Author', 'Maintainer', 'Contact']
        self.standard_or_other_columns = ['Geographical Granularity', 'Temporal Granularity']
        self.resource_keys = ['Download URL', 'File format', 'Download Description']
        super(CospreadDataRecords, self).__init__(data, essential_titles)
            
    def find_titles(self, essential_titles):
        row_index = 0
        titles = []
        assert isinstance(essential_titles, (list, tuple))
        essential_title_set = set(essential_titles + \
                                  [title.lower() for title in essential_titles])
        while True:
            if row_index >= self._data.get_num_rows():
                raise ImportException('Could not find title row')
            row = self._data.get_row(row_index)
            if essential_title_set & set(row):
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

    def create_title_mapping(self):
        '''Creates a mapping between the spreadsheet\'s actual column
        titles and the normalised versions.

        Results in self.title_map and self.title_reverse_map which are
        comprehensive for this spreadsheet.

        '''
        self.title_map = OrderedDict()
        for title in self.titles:
            for norm_title, regex in self.title_normaliser:
                if regex.match(title):
                    self.title_map[title] = norm_title
                    break
            else:
                raise AssertionError('Did not recognise title: %r' % title)
        self.title_reverse_map = dict((v, k) for k, v in self.title_map.iteritems())
        # check all keys map both ways
        unmatched_keys = set(self.title_map.keys()) - set(self.title_reverse_map.values())
        if unmatched_keys:
            msg = 'Columns not identified by REs: %r' % (set(self.title_map.keys()) - set(self.title_reverse_map.values()))
            msg += '\nColumns over identified by REs: %r' % (set(self.title_reverse_map.keys()) - set(self.title_map.values()))
            raise AssertionError(msg)
            
    @property
    def records(self):
        '''Returns package records.
        * Collates packages with download_url in multiple rows in resources.
        * Collapses 'Standard' / 'Other' column pairs into single value.
        * Renames columns to standard names.
        '''
        current_record = None
        package_identity_column = 'Package name' if not self.generate_names else 'Title'
        self.create_title_mapping()
        try:
            def get_record_key(record_, standard_key):
                alt_key = self.title_reverse_map.get(standard_key)
                if alt_key and alt_key in record_:
                    return alt_key
                else:
                    return standard_key
                return record_[self.title_reverse_map[property]]
            for record in super(CospreadDataRecords, self).records:
                if current_record and \
                       current_record[package_identity_column] == \
                       record[get_record_key(record, package_identity_column)]:
                    # this record is another resource for the current record.
                    keys_that_should_match = set(current_record.keys()) - set(self.resource_keys + ['resources'] + self.standard_or_other_columns)
                    for key in keys_that_should_match:
                        record_key = get_record_key(record, key)
                        assert current_record[key] == record[record_key], 'Multiple resources for package %r, but value for key %r does not match: %r!=%r' % (record[get_record_key(record, package_identity_column)], key, current_record[key], record[record_key])
                else:
                    # this record is new, so yield the old 'current_record' before
                    # making this record 'current_record'.
                    if current_record:
                        yield current_record
                    current_record = record.copy()
                    current_record['resources'] = []
                    # Collapse 'standard/other' columns into one
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
                    # Rename column titles to normalised ones
                    for title in self.title_map.keys():
                        norm_title = self.title_map[title]
                        if norm_title != title:
                            current_record[norm_title] = current_record[title]
                            del current_record[title]
                # Put download_url into resources
                resource = OrderedDict()
                for key in self.resource_keys:
                    key_used = None
                    if key in record:                
                        key_used = key
                    else:
                        alt_key = self.title_reverse_map.get(key)
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
        except KeyError, e:
            print 'Could not find spreadsheet title %r.\nrecord keys: %r.\ncurrent_record keys: %r' % (e.message, record.keys(), current_record.keys())
            raise
        if current_record:
            yield current_record

class MultipleCospreadDataRecords(MultipleSpreadsheetDataRecords):
    def __init__(self, data):
        if data.get_num_sheets() > 1:
            data = data.get_data_by_sheet()
        super(MultipleCospreadDataRecords, self).__init__(data, [], record_class=CospreadDataRecords)


class CospreadImporter(SpreadsheetPackageImporter):
    license_map = {
            u'UK Crown Copyright with data.gov.uk rights':u'uk-ogl',
            u'\xa9 HESA. Not core Crown Copyright.':u'uk-ogl',
            u'Local Authority copyright with data.gov.uk rights':u'uk-ogl',
            u'Local Authority Copyright with data.gov.uk rights':u'uk-ogl',
            u'UK Crown Copyright':u'uk-ogl',
            u'Crown Copyright':u'uk-ogl',
            u'UK Open Government Licence (OGL)':u'uk-ogl',
            u'UK Open Government License (OGL)':u'uk-ogl',
            u'Met Office licence':u'met-office-cp',
            u'Met Office UK Climate Projections Licence Agreement':u'met-office-cp',
        }
    
    def __init__(self, include_given_tags=False, xmlrpc_settings=None,
                 generate_names=False,
                 **kwargs):
        self.include_given_tags = include_given_tags
        super(CospreadImporter, self).__init__(record_params=[generate_names], record_class=CospreadDataRecords, **kwargs)

    @classmethod
    def log(self, msg):
        super(CospreadImporter, self).log(msg)
        log.warn(msg)

    def record_2_package(self, row_dict):
        pkg_dict = OrderedDict()
        pkg_dict['title'] = row_dict['Title']
        pkg_dict['name'] = self.name_munge(row_dict.get('Package name') or u'') or self.munge(pkg_dict['title'])
        if not (pkg_dict['name'] and pkg_dict['title']):
            raise RowParseError('Both Name and Title fields must be filled: name=%r title=%r' % (pkg_dict['name'], pkg_dict['title']))
        log.info('Package: %s' % pkg_dict['name'])
        pkg_dict['author'] = row_dict['Contact - Permanent contact point']
        pkg_dict['author_email'] = row_dict['Contact - E-mail address.']
        is_maintainer = bool('maintainer' in ' '.join(row_dict.keys()).lower())
        pkg_dict['maintainer'] = row_dict['Maintainer - '] if is_maintainer else None
        pkg_dict['maintainer_email'] = row_dict['Maintainer - E-mail address'] if is_maintainer else None
        notes = row_dict['Notes']
        license_id, additional_notes = self.get_license_id(row_dict['Licence'])
        if additional_notes:
            notes += additional_notes
        pkg_dict['license_id'] = license_id
        pkg_dict['url'] = self.tidy_url(row_dict['URL'])
        pkg_dict['notes'] = notes
        pkg_dict['version'] = u''
        pkg_dict['groups'] = [u'ukgov']
        
        pkg_dict['extras'] = OrderedDict()
        extras_dict = pkg_dict['extras']
        geo_cover = []
        geo_coverage_type = schema.GeoCoverageType.get_instance()
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
            ('Date update future', 'date_update_future'),
            ('Temporal Coverage - From', 'temporal_coverage-from'),
            ('Temporal Coverage - To', 'temporal_coverage-to'),
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
                    if extra_key.endswith('-to'):
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
            ['Update frequency', schema.update_frequency_options],
            ['Temporal Granularity', schema.temporal_granularity_options],
            ['Geographical Granularity', schema.geographic_granularity_options],
            ['Taxonomy URL'],
            ['Agency responsible'],
            ['Precision'],
            ['Department', schema.government_depts],
            ['Published by'],
            ['Published via'],
            ['Mandate'],
            ]
        optional_fields = ['Categories', 'CO Identifier', 'Agency responsible',
                           'Department', 'Published by', 'Published via',
                           'Mandate',]
        for field_mapping in field_map:
            column = field_mapping[0]
            extras_key = column.lower().replace(' ', '_')
            if column == 'Agency responsible':
                extras_key = 'agency'
            elif column in ('CO Identifier', 'CO Reference'):
                if row_dict.has_key('CO Reference'):
                    column = 'CO Reference'
                extras_key = 'external_reference'
            elif column == 'Geographical Granularity':
                extras_key = 'geographic_granularity'
            if row_dict.has_key(column):
                val = row_dict[column]
            else:
                assert column in optional_fields, column
                val = None
            if len(field_mapping) > 1:
                # snap to suggestions
                suggestions = field_mapping[1]
                if val and val not in suggestions:
                    val = val.strip()
                    suggestions_lower = [sugg.lower() for sugg in suggestions]
                    if val.lower() in suggestions_lower:
                        val = suggestions[suggestions_lower.index(val.lower())]
                    elif schema.canonise_organisation_name(val) in suggestions:
                        val = schema.canonise_organisation_name(val)
                    elif val.lower() + 's' in suggestions:
                        val = val.lower() + 's'
                    elif val.lower().rstrip('s') in suggestions:
                        val = val.lower().rstrip('s')
                    elif val.replace('&', 'and') in suggestions:
                        val = val.replace('&', 'and')
                    elif val.lower() == 'annually' and 'annual' in suggestions:
                        val = 'annual'
                    elif val.lower() == 'year' and 'annual' in suggestions:
                        val = 'annual'
                if val and val not in suggestions:
                    self.log("WARNING: Value for column '%s' of '%s' is not in suggestions '%s'" % (column, val, suggestions))
            extras_dict[extras_key] = val

        orgs = []
        for key in ['published_by', 'published_via', 'department', 'agency']:
            org_name = extras_dict.get(key)
            if org_name:
                # FIXME just use CKAN orgs instead of this
                #org = self._drupal_helper.cached_department_or_agency_to_organisation(org_name)
                if org:
                    orgs.append(org)
        # limit/pad number of orgs to be 2
        orgs = (orgs + [u''] * 4)[:2]
        extras_dict['published_by'], extras_dict['published_via'] = orgs
        # do not have department/agency fields any more
        del extras_dict['department']
        del extras_dict['agency']

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

        tags = schema.TagSuggester.suggest_tags(pkg_dict)
        if self.include_given_tags:
            given_tags = schema.tags_parse(row_dict['Tags'])
            tags = tags | set(given_tags)
        pkg_dict['tags'] = sorted(list(tags))

        return pkg_dict

    @classmethod
    def _drupal_client(cls, xmlrpc_settings=None):
        if not hasattr(cls, '_drupal_client_cache'):
            cls._drupal_client_cache = DrupalClient(xmlrpc_settings)
        return cls._drupal_client_cache

    @classmethod
    def get_license_id(cls, license_name):
        additional_notes = None
        license_id = cls.license_map.get(license_name.strip(), '')
        if not license_id and ';' in license_name:
            license_parts = license_name.split(';')
            for i, license_part in enumerate(license_parts):
                license_id = cls.license_map.get(license_part.strip(), '')
                if license_id:
                    additional_notes = '\n\nLicence detail: %s' % license_name
                    break
        if not license_id:
            license_id = 'uk-ogl'
            cls.log('WARNING: license not recognised: "%s". Defaulting to: %s.' % (license_name, license_id))
        return license_id, additional_notes
        
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

    @classmethod
    def name_munge(self, input_name):
        '''Munges the name field in case it is not to spec.'''
        input_name = input_name.replace(' ', '').replace('.', '_').replace('&', 'and')
        return super(CospreadImporter, self).name_munge(input_name)

    @classmethod
    def tidy_url(cls, url):
        if url and not url.startswith('http') and not url.startswith('webcal:'):
            if url.startswith('www.'):
                url = url.replace('www.', 'http://www.')
            else:
                cls.log("WARNING: URL doesn't start with http: %s" % url)
        return url
