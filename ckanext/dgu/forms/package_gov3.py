from sqlalchemy.util import OrderedDict
from pylons.i18n import _, ungettext, N_, gettext
from pylons import c, config
from pylons.templating import render_genshi as render
import formalchemy
from formalchemy.fields import Field
import re

from ckan.forms import common
from ckan.forms import package
from ckan.forms.builder import FormBuilder
from ckan.forms.common import ConfiguredField, TagField, GroupSelectField, package_name_validator
from ckan import model
from ckan.lib.helpers import literal

from ckanext.dgu import schema as schema
from ckanext.dgu.forms import package_gov_fields

# Setup the fieldset
def build_package_gov_form_v3(is_admin=False, user_editable_groups=None,
                              publishers=None,
                              statistics=False,
                              **kwargs):
    '''Returns a fieldset for the government packages conforming to metadata v3.
    @param publishers - dictionary of publishers from Drupal: {ID: label}
    '''
    # Restrict fields
    restrict = str(kwargs.get('restrict', False)).lower() not in \
               ('0', 'no', 'false', 0, False)
    
    builder = FormBuilder(model.Package)

    # Extra fields
    builder.add_field(GroupSelectField('groups', allow_empty=True, user_editable_groups=user_editable_groups))
    builder.add_field(ResourcesField('resources', hidden_label=True, fields_required=set(['url', 'format'])))
    builder.add_field(TagField('tags'))
    builder.add_field(common.TextExtraField('external_reference'))
    builder.add_field(common.DateExtraField('date_released'))
    builder.add_field(common.DateExtraField('date_updated'))
    builder.add_field(common.DateExtraField('date_update_future'))
    builder.add_field(common.SuggestedTextExtraField('update_frequency', options=schema.update_frequency_options))
    builder.add_field(common.SuggestedTextExtraField('geographic_granularity', options=schema.geographic_granularity_options))
    builder.add_field(package_gov_fields.GeoCoverageExtraField('geographic_coverage'))
    builder.add_field(common.SuggestedTextExtraField('temporal_granularity', options=schema.temporal_granularity_options))
    builder.add_field(common.DateRangeExtraField('temporal_coverage'))
    builder.add_field(common.TextExtraField('precision'))
    builder.add_field(common.TextExtraField('taxonomy_url'))
    builder.add_field(common.TextExtraField('mandate'))
    #builder.add_field(common.SuggestedTextExtraField('department', options=schema.government_depts))
    #builder.add_field(common.TextExtraField('agency'))
    # options are iterators of: (label, value)
    publisher_options = [(str(label), "%s [%s]" % (label, value)) for value, label in (publishers or {}).items()]
    publisher_options.sort()
    builder.add_field(package_gov_fields.PublisherField('published_by', options=publisher_options))
    builder.add_field(package_gov_fields.PublisherField('published_via', options=publisher_options))
    builder.add_field(common.CoreField('license_id', value='uk-ogl'))
    builder.add_field(common.CheckboxExtraField('national_statistic'))

    # Labels and instructions
    builder.set_field_text('title', instructions='The title of the data set.', further_instructions='The main subject of the data should be clear. For cross-government data requirements, such as spend data, specify the public body the data belongs to or its geographical coverage, in order to distinguish your data from other similar datasets in data.gov.uk. If the data relates to a period of time, include that in the name, although this would not be appropriate for data which is updated over time. It is not a description - save that for the Abstract element. Do not give a trailing full stop.', hints=literal('e.g. Payments to suppliers with a value over &pound;500 from Harlow Council'))
    builder.set_field_text('name', 'Identifier', instructions='A public unique identifier for the dataset', further_instructions='It should be roughly readable, with dashes separating words.', hints='Format: Two or more lowercase alphanumeric, dash (-) or underscore (_) characters. e.g. uk-road-traffic-statistics-2008 or local-authority-spend-over-500-harlow')
    builder.set_field_text('notes', 'Abstract', instructions='The main description of the dataset', further_instructions='It is often displayed with the package title. In particular, it should start with a short sentence that describes the data set succinctly, because the first few words alone may be used in some views of the data sets. Here is the place to state if there are any limitations or deficiencies to the data in order to enable users to evaluate the information; even incomplete data may be adequate for some users.')
    builder.set_field_text('date_released', instructions='The date of the official release of the initial version of the dataset', further_instructions='This is probably not the date that it is uploaded to data.gov.uk. Be careful not to confuse a new \'version\' of some data with a new dataset covering another time period or geographic area.', hints='DD/MM/YYYY')
    builder.set_field_text('date_updated', instructions='The date of release of the most recent version of the dataset', further_instructions='This is not necessarily the date when it was updated on data.gov.uk. As with \'Date released\', this is for updates to a particular dataset, such as corrections or refinements, not for that of a new time period.', hints='DD/MM/YYYY')
    builder.set_field_text('date_update_future', 'Date to be published', instructions='When the dataset will be updated in the future, if appropriate', hints='DD/MM/YYYY')
    builder.set_field_text('update_frequency', instructions='How frequently the dataset is updated with new versions', further_instructions='For one-off data, use \'never\'. For those once updated but now discontinued, use \'discontinued\'.')
    builder.set_field_text('precision', instructions='Indicate the level of precision in the data, to avoid over-interpretation.', hints="e.g. 'per cent to two decimal places' or 'as supplied by respondents'")
    builder.set_field_text('geographic_granularity', instructions='The lowest level of geographic detail', further_instructions="This should give the lowest level of geographic detail given in the dataset if it is aggregated. If the data is not aggregated, and so the dataset goes down to the level of the entities being reported on (such as school, hospital, or police station), use 'point'. If none of the choices is appropriate or the granularity varies, please specify in the 'other' element.")
    builder.set_field_text('geographic_coverage', instructions='The geographic coverage of this dataset.', further_instructions='Where a dataset covers multiple areas, the system will automatically group these (e.g. \'England\', \'Scotland\' and \'Wales\' all being selected would be shown as \'Great Britain\').')
    builder.set_field_text('temporal_granularity', instructions='The lowest level of temporal detail granularity', further_instructions="This should give the lowest level of temporal detail given in the dataset if it is aggregated, expressed as an interval of time. If the data is not aggregated over time, and so the dataset goes down to the instants that reported events occurred (such as the timings of high and low tides), use 'point'. If none of the choices is appropriate or the granularity varies, please specify in the 'other' element.")
    builder.set_field_text('temporal_coverage', instructions='The temporal coverage of this dataset.', further_instructions='If available, please indicate the time as well as the date. Where data covers only a single day, the \'To\' sub-element can be left blank.', hints='e.g. 21/03/2007 - 03/10/2009 or 07:45 31/03/2006')
    builder.set_field_text('url', instructions='The Internet link to a web page discussing the dataset.', hints='e.g. http://www.somedept.gov.uk/growth-figures.html')
    builder.set_field_text('taxonomy_url', instructions='An Internet link to a web page describing the taxonomies used in the dataset, if any, to ensure they understand any terms used.', hints='e.g. http://www.somedept.gov.uk/growth-figures-technical-details.html')
    #builder.set_field_text('department', instructions='The Department under which the dataset is collected and published', further_instructions='Note, this department is not necessarily directly undertaking the collection/publication itself - use the Agency element where this applies.')
    #builder.set_field_text('agency', instructions='The agency or arms-length body responsible for the data collection', further_instructions='Please use the full title of the body without any abbreviations, so that all items from it appear together. The data.gov.uk system will automatically capture this where appropriate.', hints='e.g. Environment Agency')
    builder.set_field_text('published_by', instructions='The organisation (usually a public body) credited with or associated with the publication of this data.', further_instructions='Often datasets are associated with both a government department and an outside agency, in which case this field should store the department and "Published via" should store the agency. When an organisation is not listed, please request it using the form found in your data.gov.uk user page under the "Publishers" tab. An asterisk (*) denotes an pre-existing value for this field, which is allowed, but the current user\'s permissions would not be able to change a package\s publisher to this value.')
    builder.set_field_text('published_via', instructions='A second organisation that is credited with or associated with the publication of this data.', further_instructions='Often datasets are associated with both a government department and an outside agency, in which case the "Published by" field should store the department and this field should store the agency. When an organisation is not listed, please request it using the form found in your data.gov.uk user page under the "Publishers" tab. An asterisk (*) denotes an pre-existing value for this field, which is allowed, but the current user\'s permissions would not be able to change a package\s publisher to this value.')
    builder.set_field_text('author', 'Contact', instructions='The permanent contact point for the public to enquire about this particular dataset. In addition, the Public Data and Transparency Team will use it for any suggestions for changes, feedback, reports of mistakes in the datasets or metadata.', further_instructions='This should be the name of the section of the agency or Department responsible, and should not be a named person. Particular care should be taken in choosing this element.', hints='Examples: Statistics team, Public consultation unit, FOI contact point')
    builder.set_field_text('author_email', 'Contact email', instructions='A generic official e-mail address for members of the public to contact, to match the \'Contact\' element.', further_instructions='A new e-mail address may need to be created for this function.')
    builder.set_field_text('national_statistic', 'National Statistic', instructions='Indicate if the dataset is a National Statistic', further_instructions='This is so that it can be highlighted.')
    builder.set_field_text('mandate', instructions='An Internet link to the enabling legislation that serves as the mandate for the collection or creation of this data, if appropriate.', further_instructions='This should be taken from The National Archives\' Legislation website, and where possible be a link directly to the relevant section of the Act.', hints='For example Public Record Act s.2 would be: http://www.legislation.gov.uk/id/ukpga/Eliz2/6-7/51/section/2')
    builder.set_field_text('license_id', 'Licence', instructions='The licence under which the dataset is released.', further_instructions=literal('For most situations of central Departments\' and Local Authority data, this should be the \'Open Government Licence\'. If you wish to release the data under a different licence, please contact the <a href="mailto:PublicData@nationalarchives.gsi.gov.uk">Public Data and Transparency Team</a>.'))
    builder.set_field_text('resources', instructions='The files containing the data or address of the APIs for accessing it', further_instructions=literal('These can be repeated as required. For example if the data is being supplied in multiple formats, or split into different areas or time periods, each file is a different \'resource\' which should be described differently. They will all appear on the dataset page on data.gov.uk together.<br/> <b>URL:</b> This is the Internet link directly to the data - by selecting this link in a web browser, the user will immediately download the full data set. Note that datasets are not hosted by data.gov.uk, but by the responsible department<br/> e.g. http://www.somedept.gov.uk/growth-figures-2009.csv<br/><b>Format:</b> This should give the file format in which the data is supplied. You may supply the data in a form not listed here, constrained by the <a href="http://data.gov.uk/blog/new-public-sector-transparency-board-and-public-data-transparency-principles" target="_blank">Public Sector Transparency Board\'s principles</a> that require that all data is available in an \'open and standardised format\' that can be read by a machine. Data can also be released in formats that are not machine-processable (e.g. PDF) alongside this.<br/>'), hints='Format choices: CSV | RDF | XML | XBRL | SDMX | HTML+RDFa | Other as appropriate')
    builder.set_field_text('tags', instructions='Tags can be thought of as the way that the packages are categorised, so are of primary importance.', further_instructions=literal('One or more tags should be added to give the government department and geographic location the data covers, as well as general descriptive words. The <a href="http://www.esd.org.uk/standards/ipsv_abridged/" target="_blank">Integrated Public Sector Vocabulary</a> may be helpful in forming these.'), hints='Format: Two or more lowercase alphanumeric or dash (-) characters; different tags separated by spaces. As tags cannot contain spaces, use dashes instead. e.g. for a dataset containing statistics on burns to the arms in the UK in 2009: nhs uk arm burns medical-statistics')
    # Options/settings
    builder.set_field_option('name', 'validate', package_name_validator)
    builder.set_field_option('license_id', 'dropdown', {'options':[('', None)] + model.Package.get_license_options()})
    builder.set_field_option('state', 'dropdown', {'options':model.State.all})
    builder.set_field_option('notes', 'textarea', {'size':'60x15'})
    builder.set_field_option('title', 'required')
    builder.set_field_option('notes', 'required')
    builder.set_field_option('published_by', 'required') 
    builder.set_field_option('license_id', 'required')
    builder.set_field_option('national_statistic', 'validate',
                             package_gov_fields.national_statistic_validator)
    
    if restrict:
        builder.set_field_option('national_statistic', 'readonly', True)
    
    # Layout
    field_groups = OrderedDict([
        ('Basic information', ['title', 'name',
                                  'notes']),
        ('Details', ['date_released', 'date_updated', 'date_update_future',
                        'update_frequency',
                        'precision', 
                        'geographic_granularity', 'geographic_coverage',
                        'temporal_granularity', 'temporal_coverage',
                        'url', 'taxonomy_url']),
        ('Resources', ['resources']),
        ('More details', ['published_by', 'published_via',
                             'author', 'author_email',
                             'mandate', 'license_id',
                             'tags']),
        ])
    field_groups['More details'].append('national_statistic')
    if is_admin:
        field_groups['More details'].append('state')
    builder.set_label_prettifier(package.prettify)
    builder.set_displayed_fields(field_groups)
    return builder
    # Strings for i18n:
    # (none - not translated at the moment)

def get_gov3_fieldset(is_admin=False, user_editable_groups=None,
                      publishers=None, **kwargs):
    '''Returns the standard fieldset
    '''
    return build_package_gov_form_v3( \
        is_admin=is_admin, user_editable_groups=user_editable_groups,
        publishers=publishers, **kwargs).get_fieldset()

# ResourcesField copied into here from ckan/forms/common.py so that
# the rendered fields (c.columns) can be fixed, to avoid issues with
# the new fields that have appeared since. Also, this form will not
# be around much longer in either place in the code.
class ResourcesField(ConfiguredField):
    '''A form field for multiple dataset resources.'''

    def __init__(self, name, hidden_label=False, fields_required=None):
        super(ResourcesField, self).__init__(name)
        self._hidden_label = hidden_label
        self.fields_required = fields_required or set(['url'])
        assert isinstance(self.fields_required, set)

    def resource_validator(self, val, field=None):
        resources_data = val
        assert isinstance(resources_data, list)
        not_nothing_regex = re.compile('\S')
        errormsg = _('Dataset resource(s) incomplete.')
        not_nothing_validator = formalchemy.validators.regex(not_nothing_regex,
                                                             errormsg)
        for resource_data in resources_data:
            assert isinstance(resource_data, dict)
            for field in self.fields_required:
                value = resource_data.get(field, '')
                not_nothing_validator(value, field)
            
    def get_configured(self):
        field = self.ResourcesField_(self.name).with_renderer(self.ResourcesRenderer).validate(self.resource_validator)
        field._hidden_label = self._hidden_label
        field.fields_required = self.fields_required
        field.set(multiple=True)
        return field

    class ResourcesField_(formalchemy.Field):
        def sync(self):
            if not self.is_readonly():
                pkg = self.model
                res_dicts = self._deserialize() or []
                pkg.update_resources(res_dicts, autoflush=False)

        def requires_label(self):
            return not self._hidden_label
        requires_label = property(requires_label)

        @property
        def raw_value(self):
            # need this because it is a property
            return getattr(self.model, self.name)

        def is_required(self, field_name=None):
            if not field_name:
                return False
            else:
                return field_name in self.fields_required


    class ResourcesRenderer(formalchemy.fields.FieldRenderer):
        def render(self, **kwargs):
            c.resources = self.value or []
            # [:] does a copy, so we don't change original
            c.resources = c.resources[:]
            c.resources.extend([None])
            c.id = self.name
            c.columns = ('url', 'format', 'description')
            c.field = self.field
            c.fieldset = self.field.parent
            return render('form_resources.html')            

        def stringify_value(self, v):
            # actually returns dict here for _value
            # multiple=True means v is a Resource
            res_dict = {}
            if v:
                assert isinstance(v, model.Resource)
                for col in model.Resource.get_columns() + ['id']:
                    res_dict[col] = getattr(v, col)
            return res_dict

        def _serialized_value(self):
            package = self.field.parent.model
            params = self.params
            new_resources = []
            rest_key = self.name

            # REST param format
            # e.g. 'Dataset-1-resources': [{u'url':u'http://ww...
            if params.has_key(rest_key) and any(params.getall(rest_key)):
                new_resources = params.getall(rest_key)[:] # copy, so don't edit orig

            # formalchemy form param format
            # e.g. 'Dataset-1-resources-0-url': u'http://ww...'
            row = 0
            # The base columns historically defaulted to empty strings
            # not None (Null). This is why they are seperate here.
            base_columns = ['url', 'format', 'description', 'hash', 'id']
            while True:
                if not params.has_key('%s-%i-url' % (self.name, row)):
                    break
                new_resource = {}
                blank_row = True
                for col in model.Resource.get_columns() + ['id']:
                    if col in base_columns:
                        value = params.get('%s-%i-%s' % (self.name, row, col), u'')
                    else:
                        value = params.get('%s-%i-%s' % (self.name, row, col))
                    new_resource[col] = value
                    if col != 'id' and value:
                        blank_row = False
                if not blank_row:
                    new_resources.append(new_resource)
                row += 1
            return new_resources


