import os, logging
import ckan.logic.action.create as create
import ckan.logic.action.update as update
import ckan.logic.action.get as get
from ckan.logic.converters import date_to_db, date_to_form, convert_to_extras, convert_from_extras
from ckan.logic import tuplize_dict, clean_dict, parse_params
import ckan.logic.schema as default_schema
from ckan.logic.schema import group_form_schema
import ckan.logic.validators as val
from ckan.lib.base import BaseController, model, abort
from ckan.lib.base import redirect, config, h
from ckan.lib.package_saver import PackageSaver
from ckan.lib.field_types import DateType, DateConvertError
from ckan.lib.navl.dictization_functions import Invalid
from ckan.lib.navl.dictization_functions import validate, missing
from ckan.lib.navl.dictization_functions import DataError, flatten_dict, unflatten
from ckan.plugins import IDatasetForm, IGroupForm, IConfigurer
from ckan.plugins import implements, SingletonPlugin
from ckanext.dgu.plugins_toolkit import c, request, render, ValidationError, NotAuthorized, _, check_access

from ckan.lib.navl.validators import (ignore_missing,
                                      not_empty,
                                      empty,
                                      ignore,
                                      keep_extras,
                                     )
from ckanext.dgu.forms.validators import validate_publisher_category, categories

log = logging.getLogger(__name__)


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


class PublisherForm(SingletonPlugin):
    """
    This plugin implements an IGroupForm for form associated with a
    publisher group. ``IConfigurer`` is used to add the local template
    path and the IGroupForm supplies the custom form.
    """
    implements(IGroupForm, inherit=True)
    implements(IConfigurer, inherit=True)

    def update_config(self, config):
        """
        This IConfigurer implementation causes CKAN to look in the
        ```templates``` directory when looking for the group_form()
        """
        here = os.path.dirname(__file__)
        rootdir = os.path.dirname(os.path.dirname(here))

    def new_template(self):
        return 'publisher/new.html'

    def index_template(self):
        return 'publisher/index.html'

    def read_template(self):
        return 'publisher/read.html'

    def history_template(self):
        return 'publisher/history.html'

    def edit_template(self):
        return 'publisher/edit.html'

    def group_form(self):
        """
        Returns a string representing the location of the template to be
        rendered.  e.g. "forms/group_form.html".
        """
        return 'publisher/edit_form.html'

    def group_types(self):
        """
        Returns an iterable of group type strings.

        If a request involving a group of one of those types is made, then
        this plugin instance will be delegated to.

        There must only be one plugin registered to each group type.  Any
        attempts to register more than one plugin instance to a given group
        type will raise an exception at startup.
        """
        return ["organization"]

    def is_fallback(self):
        """
        Returns true iff this provides the fallback behaviour, when no other
        plugin instance matches a group's type.

        As this is not the fallback controller we should return False.  If
        we were wanting to act as the fallback, we'd return True
        """
        return True

    def form_to_db_schema(self, group_type=None):
        from ckan.logic.schema import group_form_schema
        schema = {
            'foi-name': [ignore_missing, unicode, convert_to_extras],
            'foi-email': [ignore_missing, unicode, convert_to_extras],
            'foi-phone': [ignore_missing, unicode, convert_to_extras],
            'foi-web': [ignore_missing, unicode, convert_to_extras],
            'contact-name': [ignore_missing, unicode, convert_to_extras],
            'contact-email': [ignore_missing, unicode, convert_to_extras],
            'contact-phone': [ignore_missing, unicode, convert_to_extras],
            'category': [validate_publisher_category, convert_to_extras],
            'abbreviation': [ignore_missing, unicode, convert_to_extras],
        }
        schema.update( group_form_schema() )
        return schema

    def db_to_form_schema(data, package_type=None):
        from ckan.logic.schema import default_group_schema
        schema = {
            'foi-name' : [convert_from_extras, ignore_missing, unicode],
            'foi-email': [convert_from_extras, ignore_missing, unicode],
            'foi-phone': [convert_from_extras, ignore_missing, unicode],
            'foi-web': [convert_from_extras, ignore_missing, unicode],
            'contact-name' : [convert_from_extras, ignore_missing, unicode],
            'contact-email': [convert_from_extras, ignore_missing, unicode],
            'contact-phone': [convert_from_extras, ignore_missing, unicode],
            'category': [convert_from_extras, ignore_missing],
            'abbreviation': [convert_from_extras, ignore_missing, unicode],
        }
        schema.update( default_group_schema() )
        return schema


    def check_data_dict(self, data_dict):
        """
        Check if the return data is correct.

        raise a DataError if not.
        """

    def setup_template_variables(self, context, data_dict):
        pass # Moved to Publisher/OrganizationControll
