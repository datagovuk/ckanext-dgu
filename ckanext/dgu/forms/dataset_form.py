import json

from ckan.authz import Authorizer

from ckan.lib.base import c, model
from ckan.lib.field_types import DateType, DateConvertError
from ckan.lib.navl.dictization_functions import Invalid
from ckan.lib.navl.validators import (ignore_missing,
                                      not_empty,
                                      empty,
                                      ignore,
                                      missing,
                                      keep_extras,
                                     )

import ckan.logic.schema as default_schema
import ckan.logic.validators as val

from ckan.plugins import implements, IDatasetForm, SingletonPlugin

from ckanext.dgu.schema import GeoCoverageType
from ckanext.dgu.validators import merge_resources, unmerge_resources, \
                                   validate_resources, \
                                   validate_additional_resource_types, \
                                   validate_data_resource_types, \
                                   validate_license, \
                                   drop_if_same_as_publisher, \
                                   populate_from_publisher_if_missing

geographic_granularity = [('', ''),
                          ('national', 'national'),
                          ('regional', 'regional'),
                          ('local authority', 'local authority'),
                          ('ward', 'ward'),
                          ('point', 'point'),
                          ('other', 'other - please specify')]

update_frequency = [('', ''),
                    ('never', 'never'),
                    ('discontinued', 'discontinued'),
                    ('annual', 'annual'),
                    ('quarterly', 'quarterly'),
                    ('monthly', 'monthly'),
                    ('other', 'other - please specify')]

temporal_granularity = [("",""),
                       ("year","year"),
                       ("quarter","quarter"),
                       ("month","month"),
                       ("week","week"),
                       ("day","day"),
                       ("hour","hour"),
                       ("point","point"),
                       ("other","other - please specify")]

def additional_resource_schema():
    schema = default_schema.default_resource_schema()
    schema['format'] = [not_empty, unicode]
    schema['resource_type'].insert(0, validate_additional_resource_types)
    schema['url'] = [not_empty]
    schema['description'] = [not_empty]
    return schema

def individual_resource_schema():
    schema = default_schema.default_resource_schema()
    schema['format'] = [not_empty, unicode]
    schema['resource_type'].insert(0, validate_data_resource_types)
    schema['url'] = [not_empty]
    schema['description'] = [not_empty]
    return schema

def timeseries_resource_schema():
    schema = default_schema.default_resource_schema()
    schema['date'] = [not_empty, unicode, convert_to_extras]
    schema['format'] = [not_empty, unicode]
    schema['resource_type'].insert(0, validate_data_resource_types)
    schema['url'] = [not_empty]
    schema['description'] = [not_empty]
    return schema

class DatasetForm(SingletonPlugin):

    implements(IDatasetForm, inherit=True)

    def new_template(self):
        return 'package/new.html'

    def comments_template(self):
        return 'package/comments.html'

    def search_template(self):
        return 'package/search.html'

    def read_template(self):
        return 'package/read.html'

    def history_template(self):
        return 'package/history.html'

    def is_fallback(self):
        return True

    def package_types(self):
        return ["dgu"]

    # TODO: rename this back, or to something better
    def package_form(self, package_type=None):
        return 'package_gov3_form_refactor.html'

    def setup_template_variables(self, context, data_dict=None, package_type=None):
        c.licenses = model.Package.get_license_options()
        c.geographic_granularity = geographic_granularity
        c.update_frequency = filter(lambda f: f[0] != 'discontinued', update_frequency)
        c.temporal_granularity = temporal_granularity

        c.publishers = self.get_publishers()
        c.publishers_json = json.dumps(c.publishers)

        c.is_sysadmin = Authorizer().is_sysadmin(c.user)
        c.resource_columns = ('description', 'url', 'format')

        ## This is messy as auths take domain object not data_dict
        pkg = context.get('package') or c.pkg
        if pkg:
            c.auth_for_change_state = Authorizer().am_authorized(
                c, model.Action.CHANGE_STATE, pkg)

        c.schema_fields = set(self.form_to_db_schema().keys())

    def form_to_db_schema_options(self, options={}):
        schema = options.get('context',{}).get('schema',None)
        if schema:
            return schema
        else:
            return self.form_to_db_schema()

    def db_to_form_schema_options(self, options={}):
        context = options.get('context', {})
        schema = context.get('schema',None)
        if schema:
            return schema
        elif context.get('for_edit', False):
            return self.db_to_form_schema()
        else:
            return default_schema.package_form_schema()

    def form_to_db_schema(self, package_type=None):

        schema = {
            'title': [not_empty, unicode],
            'name': [not_empty, unicode, val.name_validator, val.package_name_validator],
            'notes': [not_empty, unicode],

            'date_released': [ignore_missing, date_to_db, convert_to_extras],
            'date_updated': [ignore_missing, date_to_db, convert_to_extras],
            'date_update_future': [ignore_missing, date_to_db, convert_to_extras],
            'update_frequency': [ignore_missing, use_other, unicode, convert_to_extras],
            'update_frequency-other': [ignore_missing],
            'precision': [ignore_missing, unicode, convert_to_extras],
            'geographic_granularity': [ignore_missing, use_other, unicode, convert_to_extras],
            'geographic_granularity-other': [ignore_missing],
            'geographic_coverage': [ignore_missing, convert_geographic_to_db, convert_to_extras],
            'temporal_granularity': [ignore_missing, use_other, unicode, convert_to_extras],
            'temporal_granularity-other': [ignore_missing],
            'temporal_coverage-from': [date_to_db, convert_to_extras],
            'temporal_coverage-to': [date_to_db, convert_to_extras],
            'url': [ignore_missing, unicode],
            'taxonomy_url': [ignore_missing, unicode, convert_to_extras],

            'additional_resources': additional_resource_schema(),
            'timeseries_resources': timeseries_resource_schema(),
            'individual_resources': individual_resource_schema(),

            'groups': {
                'name': [not_empty, val.group_id_or_name_exists, unicode],
                'id': [ignore_missing, unicode],
            },

            'contact-name': [unicode, drop_if_same_as_publisher, convert_to_extras],
            'contact-email': [unicode, drop_if_same_as_publisher, convert_to_extras],
            'contact-phone': [unicode, drop_if_same_as_publisher, convert_to_extras],

            'foi-name': [unicode, drop_if_same_as_publisher, convert_to_extras],
            'foi-email': [unicode, drop_if_same_as_publisher, convert_to_extras],
            'foi-phone': [unicode, drop_if_same_as_publisher, convert_to_extras],

            'published_via': [ignore_missing, unicode, convert_to_extras],
            'mandate': [ignore_missing, unicode, convert_to_extras],
            'license_id': [unicode],
            'access_constraints': [ignore_missing, unicode],

            'tag_string': [ignore_missing, val.tag_string_convert],
            'national_statistic': [ignore_missing, convert_to_extras],
            'state': [val.ignore_not_admin, ignore_missing],

            'primary_theme': [not_empty, unicode, val.tag_string_convert, convert_to_extras],
            'secondary_theme': [ignore_missing, val.tag_string_convert, convert_to_extras],
            'extras': default_schema.default_extras_schema(),

            '__extras': [ignore],
            '__junk': [empty],
            '__after': [validate_license, validate_resources, merge_resources]
        }
        return schema

    def db_to_form_schema(data, package_type=None):
        schema = {
            'date_released': [convert_from_extras, ignore_missing, date_to_form],
            'date_updated': [convert_from_extras, ignore_missing, date_to_form],
            'date_update_future': [convert_from_extras, ignore_missing, date_to_form],
            'update_frequency': [convert_from_extras, ignore_missing, extract_other(update_frequency)],
            'precision': [convert_from_extras, ignore_missing],
            'geographic_granularity': [convert_from_extras, ignore_missing, extract_other(geographic_granularity)],
            'geographic_coverage': [convert_from_extras, ignore_missing, convert_geographic_to_form],
            'temporal_granularity': [convert_from_extras, ignore_missing, extract_other(temporal_granularity)],
            'temporal_coverage-from': [convert_from_extras, ignore_missing, date_to_form],
            'temporal_coverage-to': [convert_from_extras, ignore_missing, date_to_form],
            'taxonomy_url': [convert_from_extras, ignore_missing],

            'resources': default_schema.default_resource_schema(),
            'extras': {
                'key': [],
                'value': [],
                '__extras': [keep_extras]
            },
            'tags': {
                '__extras': [keep_extras]
            },

            'groups': {
                'name': [not_empty, unicode]
            },

            'contact-name': [convert_from_extras, populate_from_publisher_if_missing, ignore_missing],
            'contact-email': [convert_from_extras, populate_from_publisher_if_missing, ignore_missing],
            'contact-phone': [convert_from_extras, populate_from_publisher_if_missing, ignore_missing],

            'foi-name': [convert_from_extras, populate_from_publisher_if_missing, ignore_missing],
            'foi-email': [convert_from_extras, populate_from_publisher_if_missing, ignore_missing],
            'foi-phone': [convert_from_extras, populate_from_publisher_if_missing, ignore_missing],

            'published_via': [convert_from_extras, ignore_missing],
            'mandate': [convert_from_extras, ignore_missing],
            'national_statistic': [convert_from_extras, ignore_missing],
            'primary_theme': [convert_from_extras, ignore_missing],
            'secondary_theme': [convert_from_extras, ignore_missing],
            '__after': [unmerge_resources],
            '__extras': [keep_extras],
            '__junk': [ignore],
        }
        return schema

    def check_data_dict(self, data_dict, package_type=None):
        return

    def get_publishers(self):
        from ckan.model.group import Group
        if Authorizer().is_sysadmin(c.user):
            groups = Group.all(group_type='publisher')
        elif c.userobj:
            groups = c.userobj.get_groups('publisher')
        else: # anonymous user shouldn't have access to this page anyway.
            groups = []

        # Be explicit about which fields we make available in the template
        groups = [ {
            'name': g.name,
            'id': g.id,
            'title': g.title,
            'contact-name': g.extras.get('contact-name', ''),
            'contact-email': g.extras.get('contact-email', ''),
            'contact-phone': g.extras.get('contact-phone', ''),
            'foi-name': g.extras.get('foi-name', ''),
            'foi-email': g.extras.get('foi-email', ''),
            'foi-phone': g.extras.get('foi-phone', ''),
        } for g in groups ]

        return dict( (g['name'], g) for g in groups )

def date_to_db(value, context):
    try:
        value = DateType.form_to_db(value)
    except DateConvertError, e:
        raise Invalid(str(e))
    return value

def date_to_form(value, context):
    try:
        value = DateType.db_to_form(value)
    except DateConvertError, e:
        raise Invalid(str(e))
    return value

def convert_to_extras(key, data, errors, context):

    current_index = max( [int(k[1]) for k in data.keys() \
                                    if len(k) == 3 and k[0] == 'extras'] + [-1] )

    data[('extras', current_index+1, 'key')] = key[-1]
    data[('extras', current_index+1, 'value')] = data[key]

def convert_from_extras(key, data, errors, context):

    for data_key, data_value in data.iteritems():
        if (data_key[0] == 'extras'
            and data_key[-1] == 'key'
            and data_value == key[-1]):
            data[key] = data[('extras', data_key[1], 'value')]

def use_other(key, data, errors, context):

    other_key = key[-1] + '-other'
    other_value = data.get((other_key,), '').strip()
    if other_value:
        data[key] = other_value

def extract_other(option_list):

    def other(key, data, errors, context):
        value = data[key]
        if value in dict(option_list).keys():
            return
        elif value is missing:
            data[key] = ''
            return
        else:
            data[key] = 'other'
            other_key = key[-1] + '-other'
            data[(other_key,)] = value
    return other

def convert_geographic_to_db(value, context):

    if isinstance(value, list):
        regions = value
    elif value:
        regions = [value]
    else:
        regions = []

    return GeoCoverageType.get_instance().form_to_db(regions)

def convert_geographic_to_form(value, context):

    return GeoCoverageType.get_instance().db_to_form(value)

