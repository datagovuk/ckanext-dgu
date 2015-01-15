import re
import json

from ckan.lib.base import c, model
from ckan.lib.field_types import DateType, DateConvertError
from ckan.lib.navl.dictization_functions import Invalid

import ckan.logic.schema as default_schema
import ckan.logic.validators as val

import ckan.plugins as p
import ckan.plugins.toolkit as tk
from ckanext.dgu.lib import publisher as publib
from ckanext.dgu.lib import helpers as dgu_helpers
from ckanext.dgu.schema import GeoCoverageType
from ckanext.dgu.forms.validators import merge_resources, unmerge_resources, \
     validate_resources, \
     validate_additional_resource_types, \
     validate_data_resource_types, \
     validate_license, \
     drop_if_same_as_publisher, \
     populate_from_publisher_if_missing, \
     remove_blank_resources, \
     allow_empty_if_inventory
from ckan.lib.navl.dictization_functions import missing

#convert_from_extras = tk.get_validator('convert_from_extras')
ignore_missing = tk.get_validator('ignore_missing')
not_empty = tk.get_validator('not_empty')
empty = tk.get_validator('empty')
ignore = tk.get_validator('ignore')
keep_extras = tk.get_validator('keep_extras')
not_missing = tk.get_validator('not_missing')

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

temporal_granularity = [("", ""),
                        ("year", "year"),
                        ("quarter", "quarter"),
                        ("month", "month"),
                        ("week", "week"),
                        ("day", "day"),
                        ("hour", "hour"),
                        ("point", "point"),
                        ("other", "other - please specify")]


def resources_schema():
    schema = default_schema.default_resource_schema()
    # don't convert values to ints - that doesn't work for extensions
    # (see conversation with John Glover)
    schema.update({
        'created': [ignore_missing],
        'position': [ignore_missing],
        'last_modified': [ignore_missing],
        'cache_last_updated': [ignore_missing],
        'webstore_last_updated': [ignore_missing],
    })
    return schema

def resources_schema_to_form():
    schema = resources_schema().copy()
    schema['date'] = [ignore_missing,date_to_form]
    return schema

def additional_resource_schema():
    schema = resources_schema()
    schema['format'] = [not_empty, unicode]
    schema['resource_type'].insert(0, validate_additional_resource_types)
    schema['url'] = [not_empty]
    schema['description'] = [not_empty]
    return schema


def individual_resource_schema():
    schema = resources_schema()
    schema['format'] = [not_empty, unicode]
    schema['resource_type'].insert(0, validate_data_resource_types)
    schema['url'] = [not_empty]
    schema['description'] = [not_empty]
    return schema


def timeseries_resource_schema():
    schema = resources_schema()
    schema['date'] = [not_empty, unicode, convert_to_extras, date_to_db]
    schema['format'] = [not_empty, unicode]
    schema['resource_type'].insert(0, validate_data_resource_types)
    schema['url'] = [not_empty]
    schema['description'] = [not_empty]
    return schema


class DatasetForm(p.SingletonPlugin):

    p.implements(p.IDatasetForm, inherit=True)

    # We don't customize the schema here - instead it is done in the validate
    # function, because there it has the context.
    #def create_package_schema(self):
    #def update_package_schema(self):

    def show_package_schema(self):
        return self.db_to_form_schema()

    def new_template(self):
        return 'package/new.html'

    def edit_template(self):
        return 'package/edit.html'

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
        return ["dataset"]

    def package_form(self, package_type=None):
        return 'package/edit_form.html'

    def setup_template_variables(self, context, data_dict=None,
                                 package_type=None):
        is_edit_or_new_form = 'save' in context
        if is_edit_or_new_form:
            # These expensive calls are needed for the edit/new form (not
            # package read).
            # It's not ideal to use c - normally use a helper - but it makes
            # sense here since several different templates use c.publishers.
            c.publishers = self.get_publishers()
            c.publishers_json = json.dumps(c.publishers)

    # Override the form validation to be able to vary the schema by the type of
    # package and user
    def validate(self, context, data_dict, schema, action):
        if action in ('package_update', 'package_create'):
            # If the caller to package_update specified a schema (e.g.
            # harvesters specify the default schema) then we don't want to
            # override that.
            if not context.get('schema'):
                schema = self.form_to_db_schema_options(context)
                if 'api_version' in context:
                    # Tag validation is looser than CKAN default
                    schema['tags'] = tags_schema()
        return tk.navl_validate(data_dict, schema, context)

    def form_to_db_schema_options(self, context):
        '''Returns the schema for the customized DGU form.'''
        schema = self.form_to_db_schema()
        # Sysadmins can save UKLP datasets with looser validation
        # constraints.  This is because UKLP datasets are created using
        # a custom schema passed in from the harvester.  However, when it
        # comes to re-saving the dataset via the dataset form, there are
        # some validation requirements we need to drop.  That's what this
        # section of code does.
        pkg = context.get('package')
        if dgu_helpers.is_sysadmin_by_context(context) and \
           pkg and pkg.extras.get('UKLP') == 'True':
            self._uklp_sysadmin_schema_updates(schema)
        if pkg and pkg.extras.get('external_reference') == 'ONSHUB':
            self._ons_schema_updates(schema)
        return schema

    def _uklp_sysadmin_schema_updates(self, schema):
        schema.update(
          {
            'theme-primary': [ignore_missing, unicode, convert_to_extras],
            'temporal_coverage-from': [ignore_missing, unicode, convert_to_extras],
            'temporal_coverage-to': [ignore_missing, unicode, convert_to_extras],
            'access_constraints': [ignore_missing, unicode, convert_to_extras],
            'groups': {
                'name': [ignore_missing, validate_group_id_or_name_exists_if_not_blank, unicode],
                'id': [ignore_missing, unicode],
            },
          }
          )
        for resources in ('additional_resources',
                          'timeseries_resources',
                          'individual_resources'):
            schema[resources]['format'] = [unicode]  # i.e. optional

    def _ons_schema_updates(self, schema):
        schema.update(
            {
                'theme-primary': [ignore_missing, unicode, convert_to_extras],
            })
        for resources in ('additional_resources',
                          'timeseries_resources',
                          'individual_resources'):
            schema[resources]['format'] = [unicode]  # i.e. optional

    @property
    def _resource_format_optional(self):
        return {
            'theme-primary': [ignore_missing, unicode, convert_to_extras],
        }

    def db_to_form_schema_options(self, options={}):
        context = options.get('context', {})
        schema = context.get('schema', None)
        if schema:
            return schema
        else:
            return self.db_to_form_schema()

    @classmethod
    def form_to_db_schema(cls, package_type=None):

        schema = {
            'title': [not_empty, unicode],
            'name': [not_empty, unicode, val.name_validator, val.package_name_validator],
            'notes': [not_empty, unicode],

            'date_released': [ignore_missing, date_to_db, convert_to_extras],
            'date_updated': [ignore_missing, date_to_db, convert_to_extras],
            'date_update_future': [ignore_missing, date_to_db, convert_to_extras],
            'last_major_modification': [ignore_missing, date_to_db, convert_to_extras],
            'update_frequency': [ignore_missing, use_other, unicode, convert_to_extras],
            'update_frequency-other': [ignore_missing],
            'precision': [ignore_missing, unicode, convert_to_extras],
            'geographic_granularity': [ignore_missing, use_other, unicode, convert_to_extras],
            'geographic_granularity-other': [ignore_missing],
            'geographic_coverage': [ignore_missing, convert_geographic_to_db, convert_to_extras],
            'temporal_granularity': [ignore_missing, use_other, unicode, convert_to_extras],
            'temporal_granularity-other': [ignore_missing],
            'temporal_coverage-from': [ignore_missing, date_to_db, convert_to_extras],
            'temporal_coverage-to': [ignore_missing, date_to_db, convert_to_extras],
            'url': [ignore_missing, unicode],
            'taxonomy_url': [ignore_missing, unicode, convert_to_extras],

            'additional_resources': additional_resource_schema(),
            'timeseries_resources': timeseries_resource_schema(),
            'individual_resources': individual_resource_schema(),

            'owner_org': [val.owner_org_validator, unicode],
            'groups': {
                'name': [not_empty, val.group_id_or_name_exists, unicode],
                'id': [ignore_missing, unicode],
            },

            'contact-name': [ignore_missing, unicode, drop_if_same_as_publisher, convert_to_extras],
            'contact-email': [ignore_missing, unicode, drop_if_same_as_publisher, convert_to_extras],
            'contact-phone': [ignore_missing, unicode, drop_if_same_as_publisher, convert_to_extras],

            'foi-name': [ignore_missing, unicode, drop_if_same_as_publisher, convert_to_extras],
            'foi-email': [ignore_missing, unicode, drop_if_same_as_publisher, convert_to_extras],
            'foi-phone': [ignore_missing, unicode, drop_if_same_as_publisher, convert_to_extras],
            'foi-web': [ignore_missing, unicode, drop_if_same_as_publisher, convert_to_extras],

            'published_via': [ignore_missing, unicode, convert_to_extras],
            'mandate': [ignore_missing, to_json, convert_to_extras],
            'license_id': [unicode],
            'access_constraints': [ignore_missing, unicode],

            'tags': tags_schema(),
            'tag_string': [ignore_missing, val.tag_string_convert],
            'national_statistic': [ignore_missing, convert_to_extras],
            'state': [val.ignore_not_admin, ignore_missing],

            'unpublished': [ignore_missing, bool, convert_to_extras],
            'core-dataset': [ignore_missing, bool, convert_to_extras],
            'release-notes': [ignore_missing, unicode, convert_to_extras],
            'publish-date': [ignore_missing, date_to_db, convert_to_extras],
            'publish-restricted': [ignore_missing, bool, convert_to_extras],

            'theme-primary': [ignore_missing, unicode, convert_to_extras],
            'theme-secondary': [ignore_missing, to_json, convert_to_extras],
            'extras': default_schema.default_extras_schema(),

            # This is needed by the core CKAN update_resource, but isn't found by it because
            # we do the work in __after.
            'resources': resources_schema(),

            '__extras': [ignore],
            '__junk': [empty],
            '__after': [validate_license, remove_blank_resources, validate_resources, merge_resources]
        }
        return schema

    def db_to_form_schema(data, package_type=None):
        schema = {
            'date_released': [convert_from_extras, ignore_missing, date_to_form],
            'date_updated': [convert_from_extras, ignore_missing, date_to_form],
            'last_major_modification': [convert_from_extras, ignore_missing, date_to_form],
            'date_update_future': [convert_from_extras, ignore_missing, date_to_form],
            'update_frequency': [convert_from_extras, ignore_missing, extract_other(update_frequency)],
            'precision': [convert_from_extras, ignore_missing],
            'geographic_granularity': [convert_from_extras, ignore_missing, extract_other(geographic_granularity)],
            'geographic_coverage': [convert_from_extras, ignore_missing, convert_geographic_to_form],
            'temporal_granularity': [convert_from_extras, ignore_missing, extract_other(temporal_granularity)],
            'temporal_coverage-from': [convert_from_extras, ignore_missing, date_to_form],
            'temporal_coverage-to': [convert_from_extras, ignore_missing, date_to_form],
            'taxonomy_url': [convert_from_extras, ignore_missing],

            'resources': resources_schema_to_form(),
            'extras': {
                'key': [],
                'value': [],
                '__extras': [keep_extras]
            },
            'tags': {
                '__extras': [keep_extras]
            },

            'organization': [],
            'owner_org': [],

            'groups': {
                'name': [not_empty, unicode]
            },

            'contact-name': [convert_from_extras, populate_from_publisher_if_missing, ignore_missing],
            'contact-email': [convert_from_extras, populate_from_publisher_if_missing, ignore_missing],
            'contact-phone': [convert_from_extras, populate_from_publisher_if_missing, ignore_missing],

            'foi-name': [convert_from_extras, populate_from_publisher_if_missing, ignore_missing],
            'foi-email': [convert_from_extras, populate_from_publisher_if_missing, ignore_missing],
            'foi-phone': [convert_from_extras, populate_from_publisher_if_missing, ignore_missing],
            'foi-web': [convert_from_extras, populate_from_publisher_if_missing, ignore_missing],

            'unpublished': [convert_from_extras, ignore_missing],
            'core-dataset': [convert_from_extras, ignore_missing],
            'release-notes': [convert_from_extras, ignore_missing],
            'publish-date': [convert_from_extras, ignore_missing, date_to_form],
            'publish-restricted': [convert_from_extras, ignore_missing],

            'published_via': [convert_from_extras, ignore_missing],
            'mandate': [convert_from_extras, from_json, ignore_missing],
            'national_statistic': [convert_from_extras, ignore_missing],
            'theme-primary': [convert_from_extras, ignore_missing],
            'theme-secondary': [convert_from_extras, ignore_missing],
            '__after': [unmerge_resources],
            '__extras': [keep_extras],
            '__junk': [ignore],
        }
        return schema

    def check_data_dict(self, data_dict, package_type=None):
        return

    def get_publishers(self):
        from ckan.model.group import Group

        if dgu_helpers.is_sysadmin():
            groups = Group.all(group_type='organization')
        elif c.userobj:
            # need to get c.userobj again as it may be detached from the
            # session since the last time we called get_groups (it caches)
            c.userobj = model.User.by_name(c.user)

            # For each group where the user is an admin, we should also include
            # all of the child publishers.
            admin_groups = set()
            for g in c.userobj.get_groups('organization', 'admin'):
                for pub in publib.go_down_tree(g):
                    admin_groups.add(pub)

            editor_groups = c.userobj.get_groups('organization', 'editor')
            groups = list(admin_groups) + editor_groups
        else:  # anonymous user shouldn't have access to this page anyway.
            groups = []

        # Be explicit about which fields we make available in the template
        groups = [{
            'name': g.name,
            'id': g.id,
            'title': g.title,
            'contact-name': g.extras.get('contact-name', ''),
            'contact-email': g.extras.get('contact-email', ''),
            'contact-phone': g.extras.get('contact-phone', ''),
            'foi-name': g.extras.get('foi-name', ''),
            'foi-email': g.extras.get('foi-email', ''),
            'foi-phone': g.extras.get('foi-phone', ''),
            'foi-web': g.extras.get('foi-web', ''),
        } for g in groups]

        return dict((g['name'], g) for g in groups)


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

    current_index = max([int(k[1]) for k in data.keys()
                         if len(k) == 3 and k[0] == 'extras'] + [-1])

    data[('extras', current_index+1, 'key')] = key[-1]
    data[('extras', current_index+1, 'value')] = data[key]


def convert_from_extras(key, data, errors, context):

    for data_key, data_value in data.iteritems():
        if (data_key[0] == 'extras'
            and data_key[-1] == 'key'
            and data_value == key[-1]):
            data[key] = data[('extras', data_key[1], 'value')]

def to_json(key, data, errors, context):
    try:
        encoded = json.dumps(data[key])
        data[key] = encoded
    except:
        pass

def from_json(key, data, errors, context):
    try:
        decoded = json.loads(data[key])
        data[key] = decoded
    except:
        pass


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


def validate_group_id_or_name_exists_if_not_blank(value, context):
    if not value.strip():
        return True
    return val.group_id_or_name_exists(value, context)


def tag_name_extended_validator(value, context):
    tagname_match = re.compile('[\w \-.()\':&/,+=\[\]]*$', re.UNICODE)
    if not tagname_match.match(value):
        raise Invalid(('Tag "%s" must be alphanumeric '
            'characters or symbols: -_.()\':&/,+=[]') % (value))
    return value

def tags_schema():
    # Allow tags of 1 character e.g. B (chemical name for Boron)
    schema = {
        'name': [not_missing,
                 not_empty,
                 unicode,
                 tag_name_extended_validator,
                 ],
        'revision_timestamp': [ignore],
        'state': [ignore],
    }
    return schema
