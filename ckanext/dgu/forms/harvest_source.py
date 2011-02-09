import formalchemy
from formalchemy import helpers as fa_h
import ckan.lib.helpers as h

from ckan.forms.builder import FormBuilder
from sqlalchemy.util import OrderedDict
import ckan.model as model
from ckan.forms import common
from ckan.lib.helpers import literal

__all__ = ['get_harvest_source_fieldset']

def harvest_source_url_validator(val, field=None):
    if not val.strip().startswith('http://'):
        raise formalchemy.ValidationError('Harvest source URL is invalid (must start with "http://").')

def build_harvest_source_form():
    builder = FormBuilder(model.HarvestSource)
    builder.set_field_text('url', 'URL for source of metadata', literal('''
        <br/>This should include the <tt>http://</tt> part of the URL and can point to either:
        <ul>
            <li>A server's CSW interface</li>
            <li>A Web Accessible Folder (WAF) displaying a list of GEMINI 2.1 documents</li>
            <li>A single GEMINI 2.1 document</li>
        </ul>
        <br />
        '''
    ))
    builder.set_field_option('url', 'validate', harvest_source_url_validator)
    builder.set_field_option('url', 'with_html', {'size':'80'})
    builder.set_field_option('description', 'textarea', {'size':'60x5'})
    builder.set_field_text('description', 'Description', literal('''
        You can add your own notes here about what the URL above represents to remind you later.
        '''
    ))
    displayed_fields = ['url', 'description']
    builder.set_displayed_fields(OrderedDict([('Details', displayed_fields)]))
    builder.set_label_prettifier(common.prettify)
    return builder  

fieldsets = {}
def get_harvest_source_fieldset(name='harvest_source_fs'):
    if not fieldsets:
        fieldsets['harvest_source_fs'] = build_harvest_source_form().get_fieldset()
    return fieldsets[name]

