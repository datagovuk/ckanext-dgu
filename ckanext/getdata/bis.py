import os.path

from collections import defaultdict

from sqlalchemy.util import OrderedDict

from ckanclient.loaders.base import CkanLoader
from ckan.lib.importer import PackageImporter, XlData, DataRecords, RowParseError
from ckan.lib import schema_gov
from ckan.lib import field_types

pkg_field_mapping = {
    'Title':'title'
    }

class BisImporter(PackageImporter):
    def import_into_package_records(self):
        package_data = XlData(self.log, filepath=self._filepath,
                                      buf=self._buf,
                                      sheet_index=0)
        sheet_names = package_data.get_sheet_names()
        assert sheet_names == ['Datasets', 'Resources']
        resource_data = XlData(self.log, filepath=self._filepath,
                                      buf=self._buf,
                                      sheet_index=sheet_names.index('Resources'))

        self._package_data_records = DataRecords(package_data, 'Title')
        self.import_resources(resource_data)

    def import_resources(self, resource_data):
        resource_data_records = DataRecords(resource_data, 'Resource Title')
        self._resources_by_ref = defaultdict(list)
        for resource_record in resource_data_records.records:
            ref = resource_record['Dataset Ref#']
            resource_dict = self.row_2_resource(resource_record)
            self._resources_by_ref[ref].append(resource_dict)

    def row_2_resource(self, row_dict):
        resource_dict = OrderedDict([
            ('url', row_dict['Resource url']),
            ('format', row_dict['Resource Format']),
            ('description', row_dict['Resource Title']),
            ])
        return resource_dict

    def row_2_package(self, row_dict):
        name = row_dict['Identifier'].replace('higher-education-statistics', 'hesa')
        contacts = row_dict['Contact information'].split('\n')
        if len(contacts) != 3:
            raise RowParseError('Unknown contacts format with %i line(s) not 3:' % (len(contacts), contact_information))
        author, ignore_phone, author_email = contacts

        license_name = row_dict['Licence'].replace('Statistcs', 'Statistics')
        license_id = self.license_2_license_id(license_name, self.log)

        ref = row_dict['Dataset Ref#']
        if not ref.startswith('BIS-'):
            raise RowParseError('Reference must start with \'BIS-\': %s' % ref)
        resources = self._resources_by_ref[ref]

        geo_coverage = schema_gov.GeoCoverageType.get_instance().str_to_db(row_dict['Geographic Coverage'])

        munged_dates = {}
        for column in ['Date Released', 'Date Updated',
                       'Temporal Coverage To', 'Temporal Coverage From']:
            val = '%s' % row_dict[column]
#            try:
#                val = field_types.DateType.form_to_db('%s' % row_dict[column])
#            except field_types.DateConvertError, e:
#                print "WARNING: Value for column '%s' of '%s' is not understood as a date format." % (column, row_dict[column])
#                val = row_dict[column]
            munged_dates[column] = val
        
        pkg_dict = OrderedDict([
            ('name', name),
            ('title', row_dict['Title']),
            ('version', row_dict['Version']),
            ('url', None),
            ('author', author),
            ('author_email', author_email),
            ('maintainer', None),
            ('maintainer_email', None),
            ('notes', row_dict['Abstract']),
            ('license_id', license_id),
            ('tags', []), # post-filled
            ('groups', []),
            ('resources', resources),
            ('extras', OrderedDict([
                ('external_reference', ref),
                ('date_released', munged_dates['Date Released']),
                ('date_updated', munged_dates['Date Updated']),
                ('temporal_granularity', row_dict['Temporal Granularity']),
                ('temporal_coverage_from', munged_dates['Temporal Coverage From']),
                ('temporal_coverage_to', munged_dates['Temporal Coverage To']),
                ('geographic_coverage', geo_coverage),
                ('geographic_granularity', row_dict['Geographic Granularity']),
                ('agency', row_dict['Agency']),
                ('precision', row_dict['Precision']),
                ('taxonomy_url', row_dict['Taxonomy url']),
                ('import_source', 'BIS-%s' % os.path.basename(self._filepath)),
                ('department', row_dict['Department']),
                ('update_frequency', row_dict['Update Frequency']),
                ('national_statistic', row_dict['National Statistic']),
                ('categories', row_dict['Categories']),
                ])),
            ])

        tags = schema_gov.TagSuggester.suggest_tags(pkg_dict)
        pkg_dict['tags'] = tags
        
#        pkg_dict = self.pkg_xl_dict_to_fs_dict(row_dict, self.log)
        return pkg_dict
        
