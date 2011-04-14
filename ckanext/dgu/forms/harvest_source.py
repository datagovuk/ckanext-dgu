import formalchemy
from formalchemy import helpers as fa_h
import ckan.lib.helpers as h

from ckan.forms.builder import FormBuilder
from sqlalchemy.util import OrderedDict

from ckanext.harvest.model import HarvestSource

import ckan.model as model
from ckan.forms import common
from ckan.lib.helpers import literal

__all__ = ['get_harvest_source_fieldset']

def harvest_source_url_validator(val, field=None):
    if not val.strip().startswith('http://'):
        raise formalchemy.ValidationError('Harvest source URL is invalid (must start with "http://").')

def harvest_source_type_validator(val, field=None):
    if not val.strip().lower() in ['gemini','geminiwaf','geminidoc']:
        raise formalchemy.ValidationError('Unknown Harvest Source Type: %s. Please choose between Gemini, GeminiWaf, GeminiDoc' % val)

def build_harvest_source_form():
    builder = FormBuilder(HarvestSource)
    builder.set_field_text('url', 'URL for source of metadata', literal("""
        <br/>This should include the <tt>http://</tt> part of the URL and can point to either:
        <ul>
            <li>A server's CSW interface (Type: Gemini)</li>
            <li>A Web Accessible Folder (WAF) displaying a list of GEMINI 2.1 documents (Type: GeminiWaf)</li>
            <li>A single GEMINI 2.1 document (Type: GeminiDoc)</li>
        </ul>
        <br />
        """
    ))
    builder.set_field_option('url', 'validate', harvest_source_url_validator)
    builder.set_field_option('url', 'with_html', {'size':'80'})
    builder.set_field_option('description', 'textarea', {'size':'60x5'})
    builder.set_field_text('description', 'Description', literal('''
        You can add your own notes here about what the URL above represents to remind you later.
        '''
    ))
    builder.set_field_text('type', 'Source Type', literal('''
        Please provide the source type according to the types described above.
        '''
    ))
    builder.set_field_option('type', 'validate', harvest_source_type_validator)
    builder.set_field_option('type', 'dropdown', {'options':['Gemini','GeminiWaf','GeminiDoc']})
#    displayed_fields = ['url','type','active','description']
    displayed_fields = ['url','type','description']
    builder.set_displayed_fields(OrderedDict([('Details', displayed_fields)]))
    builder.set_label_prettifier(common.prettify)
    return builder  

fieldsets = {}
def get_harvest_source_fieldset(name='harvest_source_fs'):
    if not fieldsets:
        fieldsets['harvest_source_fs'] = build_harvest_source_form().get_fieldset()
    return fieldsets[name]

