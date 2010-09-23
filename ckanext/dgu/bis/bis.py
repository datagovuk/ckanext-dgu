import os.path

from collections import defaultdict

from sqlalchemy.util import OrderedDict

from ckanext.loader import *
from ckan.lib.importer import RowParseError
from ckan.lib.spreadsheet_importer import XlData, SpreadsheetDataRecords, SpreadsheetPackageImporter
from ckan.lib import schema_gov
from ckan.lib import field_types
from ckan import model


class BisLoader(PackageLoader):
    def __init__(self, ckanclient):
        settings = ReplaceByExtraField('external_reference')
        super(BisLoader, self).__init__(ckanclient, settings)


class BisImporter(SpreadsheetPackageImporter):
    def import_into_package_records(self):
        package_data = XlData(self.log, filepath=self._filepath,
                                      buf=self._buf,
                                      sheet_index=0)
        sheet_names = package_data.get_sheet_names()
        assert sheet_names == ['Datasets', 'Resources']
        resource_data = XlData(self.log, filepath=self._filepath,
                                      buf=self._buf,
                                      sheet_index=sheet_names.index('Resources'))

        self._package_data_records = SpreadsheetDataRecords(package_data, 'Title')
        self.import_resources(resource_data)

    def import_resources(self, resource_data):
        resource_data_records = SpreadsheetDataRecords(resource_data, 'Resource Title')
        self._resources_by_ref = defaultdict(list)
        for resource_record in resource_data_records.records:
            ref = resource_record['Dataset Ref#']
            resource_dict = self.row_2_resource(resource_record)
            self._resources_by_ref[ref].append(resource_dict)

    def row_2_resource(self, row_dict):
        url = self.tidy_url(row_dict['Resource url'], self.log)
        resource_dict = OrderedDict([
            ('url', url),
            ('format', row_dict['Resource Format']),
            ('description', row_dict['Resource Title']),
            ])
        return resource_dict

    def row_2_package(self, row_dict):
        name = (row_dict.get('Identifier') or u'').replace('higher-education-statistics', 'hesa')
        name = self.name_munge(name)
        title = row_dict['Title']
        if not (name and title):
            raise RowParseError('Both Name and Title fields must be filled: name=%r title=%r' % (name, title))
        contacts = row_dict['Contact information'].split('\n')
        if len(contacts) != 3:
            raise RowParseError('Unknown contacts format with %i line(s) not 3:' % (len(contacts), contact_information))
        author, ignore_phone, author_email = contacts

        license_name = row_dict['Licence'].replace('Statistcs', 'Statistics')
        license_id = self.license_2_license_id(license_name, self.log)
        if not license_id:
            raise RowParseError('No license recognised for: %r' % license_name)

        ref = row_dict['Dataset Ref#']
        if not ref.startswith('BIS-'):
            raise RowParseError('Reference must start with \'BIS-\': %s' % ref)
        resources = self._resources_by_ref[ref]

        geo_coverage = schema_gov.GeoCoverageType.get_instance().str_to_db(row_dict['Geographic Coverage'])

        munged_dates = {}
        for column in ['Date Released', 'Date Updated',
                       'Temporal Coverage To', 'Temporal Coverage From']:
            val = '%s' % row_dict[column]
            munged_dates[column] = val

        taxonomy_url = row_dict['Taxonomy url']
        if taxonomy_url and taxonomy_url != '-':
            taxonomy_url = self.tidy_url(taxonomy_url, self.log)
            
        national_statistic = u'no'
        if row_dict['National Statistic'] != national_statistic:
            self.log('Warning: Ignoring national statistic for non-ONS data: %s' % row_dict['National Statistic'])

        pkg_dict = OrderedDict([
            ('name', name),
            ('title', title),
            ('version', row_dict['Version'][:model.PACKAGE_VERSION_MAX_LENGTH]),
            ('url', None),
            ('author', author),
            ('author_email', author_email),
            ('maintainer', None),
            ('maintainer_email', None),
            ('notes', row_dict['Abstract']),
            ('license_id', license_id),
            ('tags', []), # post-filled
            ('groups', ['ukgov']),
            ('resources', resources),
            ('extras', OrderedDict([
                ('external_reference', ref),
                ('date_released', munged_dates['Date Released']),
                ('date_updated', munged_dates['Date Updated']),
                ('temporal_granularity', row_dict['Temporal Granularity']),
                ('temporal_coverage_from', munged_dates['Temporal Coverage From']),
                ('temporal_coverage_to', munged_dates['Temporal Coverage To']),
                ('geographic_coverage', geo_coverage),
                ('geographical_granularity', row_dict['Geographic Granularity']),
                ('agency', row_dict['Agency']),
                ('precision', row_dict['Precision']),
                ('taxonomy_url', taxonomy_url),
                ('import_source', 'BIS-%s' % os.path.basename(self._filepath)),
                ('department', row_dict['Department']),
                ('update_frequency', row_dict['Update Frequency']),
                ('national_statistic', national_statistic),
                ('categories', row_dict['Categories']),
                ])),
            ])

        tags = schema_gov.TagSuggester.suggest_tags(pkg_dict)
        [tags.add(tag) for tag in schema_gov.tags_parse(row_dict['Tags'])]
        tags = list(tags)
        tags.sort()
        pkg_dict['tags'] = tags

        # snap to suggestions
        field_suggestions = [
            ['temporal_granularity', schema_gov.temporal_granularity_options],
            ['geographical_granularity', schema_gov.geographic_granularity_options],
            ['categories', schema_gov.category_options],
            ['department', schema_gov.government_depts],
            ]
        for field, suggestions in field_suggestions:
            val = pkg_dict['extras'][field]
            if val and val != '-' and val not in suggestions:
                suggestions_lower = [sugg.lower() for sugg in suggestions]
                if val.lower() in suggestions_lower:
                    val = suggestions[suggestions_lower.index(val.lower())]
                elif schema_gov.expand_abbreviations(val) in suggestions:
                    val = schema_gov.expand_abbreviations(val)
                elif val.lower() + 's' in suggestions:
                    val = val.lower() + 's'
                elif val.replace('&', 'and').strip() in suggestions:
                    val = val.replace('&', 'and').strip()
            if val and val != '-' and val not in suggestions:
                self.log("WARNING: Value for column '%s' of '%s' is not in suggestions '%s'" % (column, val, suggestions))
            pkg_dict['extras'][field] = val

        return pkg_dict
        
    @classmethod
    def name_munge(self, input_name):
        input_name = input_name.replace('-by-qualification-aim-mode-of-study-gender-and-', '-')
        return super(BisImporter, self).name_munge(input_name)
