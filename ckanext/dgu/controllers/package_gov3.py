import json
import logging
from ckan.lib.base import BaseController, render, c, model, abort, request
from ckan.lib.base import redirect, _, config, h
import ckan.logic.action.create as create
import ckan.logic.action.update as update
import ckan.logic.action.get as get
from ckan.lib.navl.dictization_functions import DataError, flatten_dict, unflatten
from ckan.logic import NotFound, NotAuthorized, ValidationError
from ckan.logic import tuplize_dict, clean_dict, parse_params
from ckan.logic.auth.publisher import _groups_intersect
from ckan.logic.schema import package_form_schema
from ckan.lib.package_saver import PackageSaver
from ckan.lib.field_types import DateType, DateConvertError
from ckan.authz import Authorizer
from ckan.lib.navl.dictization_functions import Invalid
from ckanext.dgu.schema import GeoCoverageType
from ckan.lib.navl.dictization_functions import validate, missing
from ckan.lib.navl.validators import (ignore_missing,
                                      not_empty,
                                      empty,
                                      ignore,
                                      keep_extras,
                                     )
import ckan.logic.validators as val
import ckan.logic.schema as default_schema
from ckan.controllers.package import PackageController

from ckanext.dgu.validators import merge_resources, unmerge_resources, \
                                   validate_resources, \
                                   validate_additional_resource_types, \
                                   validate_data_resource_types, \
                                   validate_license

log = logging.getLogger(__name__)

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
    schema['resource_type'].insert(0, validate_additional_resource_types)
    schema['url'] = [not_empty]
    schema['description'] = [not_empty]
    return schema

def individual_resource_schema():
    schema = default_schema.default_resource_schema()
    schema['resource_type'].insert(0, validate_data_resource_types)
    schema['url'] = [not_empty]
    schema['description'] = [not_empty]
    return schema

def timeseries_resource_schema():
    schema = default_schema.default_resource_schema()
    schema['date'] = [not_empty, unicode, convert_to_extras]
    schema['resource_type'].insert(0, validate_data_resource_types)
    schema['url'] = [not_empty]
    schema['description'] = [not_empty]
    return schema

class PackageGov3Controller(PackageController):

    def history(self, id):
        """ Auth is different for DGU than for publisher default """
        if len ( c.userobj.get_groups('publisher') ) == 0:
            abort( 401, _('Unauthorized to read package history') )
        return super(PackageGov3Controller, self).history(  id )

    # TODO: rename this back, or to something better
    def _package_form(self, package_type=None):
        return 'package_gov3_form_refactor.html'

    def _setup_template_variables(self, context, data_dict=None, package_type=None):
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
        
        c.schema_fields = set(self._form_to_db_schema().keys())

    def _form_to_db_schema(self, package_type=None):

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
                'name': [not_empty, unicode]
            },

            'contact-name': [unicode, convert_to_extras],
            'contact-email': [unicode, convert_to_extras],
            'contact-phone': [unicode, convert_to_extras],

            'foi-name': [ignore_missing, unicode, convert_to_extras],
            'foi-email': [ignore_missing, unicode, convert_to_extras],
            'foi-phone': [ignore_missing, unicode, convert_to_extras],

            'published_via': [ignore_missing, unicode, convert_to_extras],
            'mandate': [ignore_missing, unicode, convert_to_extras],
            'license_id': [unicode],
            'license_id-other': [ignore_missing, unicode],

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
    
    def _db_to_form_schema(data, package_type=None):
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

            'contact-name': [convert_from_extras, ignore_missing],
            'contact-email': [convert_from_extras, ignore_missing],
            'contact-phone': [convert_from_extras, ignore_missing],

            'foi-name': [convert_from_extras, ignore_missing],
            'foi-email': [convert_from_extras, ignore_missing],
            'foi-phone': [convert_from_extras, ignore_missing],

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

    def _check_data_dict(self, data_dict, package_type=None):
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

