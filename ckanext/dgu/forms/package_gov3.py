from sqlalchemy.util import OrderedDict
from pylons.i18n import _, ungettext, N_, gettext
from pylons import config

from ckan.forms import common
from ckan.forms import package
from ckan.forms import package_gov
from ckan.forms.builder import FormBuilder
from ckan.forms.common import ResourcesField, TagField, GroupSelectField, package_name_validator
from ckan import model
from ckanext.dgu import schema as schema_gov
from ckan.lib.helpers import literal

# Setup the fieldset
def build_package_gov_form_v3(is_admin=False, user_editable_groups=None,
                              statistics=False, inventory=False, **kwargs):
    assert not (statistics and inventory) # can't be both

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
    builder.add_field(common.SuggestedTextExtraField('update_frequency', options=schema_gov.update_frequency_options))
    builder.add_field(common.SuggestedTextExtraField('geographic_granularity', options=schema_gov.geographic_granularity_options))
    builder.add_field(package_gov.GeoCoverageExtraField('geographic_coverage'))
    builder.add_field(common.SuggestedTextExtraField('temporal_granularity', options=schema_gov.temporal_granularity_options))
    builder.add_field(common.DateRangeExtraField('temporal_coverage'))
    builder.add_field(common.TextExtraField('precision'))
    builder.add_field(common.SuggestedTextExtraField('department', options=schema_gov.government_depts))
    builder.add_field(common.TextExtraField('agency'))
    builder.add_field(common.TextExtraField('taxonomy_url'))
    builder.add_field(common.TextExtraField('mandate'))
    builder.add_field(common.TextExtraField('publisher'))
    builder.add_field(common.CoreField('license_id', value='uk-ogl'))
#   TODO Remove National Statistic from core form, when we can choose the
#   form
#    if statistics:
    if True:
        builder.add_field(common.CheckboxExtraField('national_statistic'))
    if statistics:
        builder.add_field(common.SuggestedTextExtraField('series'))
    if inventory:
        builder.add_field(common.DateExtraField('date_disposal'))
        builder.add_field(common.DateExtraField('date_planned_publication'))
        builder.add_field(common.SuggestedTextExtraField('permanent_preservation'), options=schema_gov.yes_no_not_yet_options)
        builder.add_field(common.CheckboxExtraField('disclosure_foi'))
        builder.add_field(common.CheckboxExtraField('disclosure_eir'))
        builder.add_field(common.CheckboxExtraField('disclosure_dpa'))

    # Labels and instructions
    builder.set_field_text('title', instructions='The title of the data set.', further_instructions='The main subject of the data should be included with a lay term. For cross-government data requirements, such as spend data specify the public body the data belongs to or its geographical coverage, in order to distinguish your data from other similar datasets in data.gov.uk. If the data relates to a period of time, include that in the name, although this would not be appropriate for data which is updated over time. It is not a description - save that for the Abstract element. Do not give a trailing full stop.', hints=literal('e.g. Payments to suppliers with a value over &pound;500 from Harlow Council'))
    builder.set_field_text('name', 'Identifier', instructions='A public unique identifier for the dataset', further_instructions='It should be roughly readable, with dashes separating words.', hints='Format: Two or more lowercase alphanumeric, dash (-) or underscore (_) characters. e.g. uk-road-traffic-statistics-2008 or local-authority-spend-over-500-harlow')
    builder.set_field_text('notes', 'Abstract', instructions='The main description of the dataset', further_instructions='It is often displayed with the package title. In particular, it should start with a short sentence that describes the data set succinctly, because the first few words alone may be used in some views of the data sets. Here is the place to state if there are any limitations or deficiencies to the data in order to enable users to evaluate the information; even incomplete data may be adequate for some users.')
    builder.set_field_text('date_released', instructions='The date of the official release of the initial version of the dataset', further_instructions='This is probably not the date that it is uploaded to data.gov.uk. Be careful not to confuse a new \'version\' of some data with a new dataset covering another time period or geographic area.', hints='DD/MM/YYYY')
    builder.set_field_text('date_updated', instructions='The date of release of the most recent version of the dataset', further_instructions='This is not necessarily the date when it was updated on data.gov.uk. As with \'Date released\', this is for updates to a particular dataset, such as corrections or refinements, not for that of a new time period.', hints='DD/MM/YYYY')
    builder.set_field_text('date_update_future', 'Date to be published', instructions='When the dataset will be updated in the future, if appropriate', hints='DD/MM/YYYY')
    builder.set_field_text('update_frequency', instructions='How frequently the dataset is updated with new versions', further_instructions='For one-off data, use \'never\'. For those once updated but now discontinued, use \'discontinued\'.')
    builder.set_field_text('precision', instructions='Indicate the level of precision in the data, to avoid over-interpretation.', hints="e.g. 'per cent to two decimal places' or 'as supplied by respondents'")
    builder.set_field_text('geographic_granularity', instructions='The lowest level of geographic detail', further_instructions="This should give the lowest level of geographic detail given in the dataset if it is aggregated. If the data is not aggregated, and so the dataset goes down to the level of the entities being reported on (such as school, hospital, or police station), use 'point'. If none of the choices is appropriate or the granularity varies, please specify in the 'other' element.")
    builder.set_field_text('geographic_coverage', instructions='The geographic coverage of this dataset', further_instructions='Where a dataset covers multiple areas, the system will automatically group these (e.g. \'England\', \'Scotland\' and \'Wales\' all being \'Yes\' would be shown as \'Great Britain\').')
    builder.set_field_text('temporal_granularity', instructions='The lowest level of temporal detail granularity', further_instructions="This should give the lowest level of temporal detail given in the dataset if it is aggregated, expressed as an interval of time. If the data is not aggregated over time, and so the dataset goes down to the instants that reported events occurred (such as the timings of high and low tides), use 'point'. If none of the choices is appropriate or the granularity varies, please specify in the 'other' element.")
    builder.set_field_text('temporal_coverage', instructions='The temporal coverage of this dataset.', further_instructions='If available, please indicate the time as well as the date. Where data covers only a single day, the \'To\' sub-element can be left blank.', hints='e.g. 21/03/2007 - 03/10/2009 or 07:45 31/03/2006')
    builder.set_field_text('url', instructions='The Internet link to a web page discussing the dataset.', hints='e.g. http://www.somedept.gov.uk/growth-figures.html')
    builder.set_field_text('taxonomy_url', instructions='An Internet link to a web page describing the taxonomies used in the dataset, if any, to ensure they understand any terms used.', hints='e.g. http://www.somedept.gov.uk/growth-figures-technical-details.html')
    builder.set_field_text('department', instructions='The Department under which the dataset is collected and published', further_instructions='Note, this department is not necessarily directly undertaking the collection/publication itself - use the Agency element where this applies.')
    builder.set_field_text('agency', instructions='The agency or arms-length body responsible for the data collection', further_instructions='Please use the full title of the body without any abbreviations, so that all items from it appear together. The data.gov.uk system will automatically capture this where appropriate.', hints='e.g. Environment Agency')
    builder.set_field_text('publisher', instructions='The public body credited with the publication of this data', further_instructions="An 'over-ride' for the system, to determine the correct public body to credit, when it might not be clear if this is the Agency or Department. This could be used where the public branding of the work of an agency is as its parent department.")
    builder.set_field_text('author', 'Contact', instructions='The permanent contact point for the public to enquire about this particular dataset. In addition, the Public Data and Transparency Team will use it for any suggestions for changes, feedback, reports of mistakes in the datasets or metadata.', further_instructions='This should be the name of the section of the agency or Department responsible, and should not be a named person. Particular care should be taken in choosing this element.', hints='Examples: Statistics team, Public consultation unit, FOI contact point')
    builder.set_field_text('author_email', 'Contact email', instructions='A generic official e-mail address for members of the public to contact, to match the \'Contact\' element.', further_instructions='A new e-mail address may need to be created for this function.')
#    if statistics:
    if True:
        builder.set_field_text('national_statistic', 'National Statistic', instructions='Indicate if the dataset is a National Statistic', further_instructions='This is so that it can be highlighted.')
    if statistics:
        builder.set_field_text('series', instructions='The name of a series or collection that this data is part of.', further_instructions='This is needed for National Statistics. For example \'Wages Weekly Index\'.')
    if inventory:
        builder.set_field_text('date_disposal', instructions='Date of removal of the data from the public body\'s systems.', further_instructions='This is a future date when it is intended to remove the data, eventually replaced with the actual date the disposal was implemented (if appropriate).', hints='DD/MM/YYYY')
        builder.set_field_text('date_planned_publication', 'Planned publication date', instructions='To be used when adding data intended for future publication to the Inventory', hints='DD/MM/YYYY')
        builder.set_field_text('permanent_preservation', 'Selected for permanent preservation', instructions='Data, whose sensitivity currently prevents publication, selected by the National Archives as worthy of permanent preservation.  (It is intended that published data will automatically be preserved in the UK Government Web Archive.)')
        builder.set_field_text('disclosure_foi', instructions='Indicates whether or not data is exempt from publication by virtue of the Freedom of Information Act 2000.')
        builder.set_field_text('disclosure_eir', instructions='Indicates wheter or not data is exempt from publication by virtue of the Environmental Information Regulations 2004.')
        builder.set_field_text('disclosure_dpa', instructions='Indicates whether or not data is exempt from publication by virtue of  the Data Protection Act 1998, taking into account that personal data whilst not of itself disclosive, may, if combined with other data in the public domain, become so.')
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
    builder.set_field_option('department', 'required')
    builder.set_field_option('license_id', 'required')
    builder.set_field_option('tags', 'with_renderer', package_gov.SuggestTagRenderer)

    if restrict:
        for field_name in ('name', 'department', 'national_statistic'):
            builder.set_field_option(field_name, 'readonly', True)
    
    # Layout
    field_groups = OrderedDict([
        (_('Basic information'), ['title', 'name',
                                  'notes']),
        (_('Details'), ['date_released', 'date_updated', 'date_update_future',
                        'update_frequency',
                        'precision', 
                        'geographic_granularity', 'geographic_coverage',
                        'temporal_granularity', 'temporal_coverage',
                        'url', 'taxonomy_url']),
        (_('Resources'), ['resources']),
        (_('More details'), ['department', 'agency',
                             'author', 'author_email',
                             'mandate', 'license_id',
                             'tags']),
        ])
#    if statistics:
    field_groups['More details'].append('national_statistic')
    if statistics:
        field_groups['More details'].append('series')
    if inventory:
        field_groups['Details'].insert('date_planned_publication', 0)
        field_groups['Details'].insert('date_disposal', 4)
        field_groups['Details'].insert('permanent_preservation', 5)
        field_groups['More details'].insert('disclosure_foi', 6)
        field_groups['More details'].insert('disclosure_eir', 7)
        field_groups['More details'].insert('disclosure_dpa', 8)
    if is_admin:
        field_groups['More details'].append('state')
    builder.set_label_prettifier(package.prettify)
    builder.set_displayed_fields(field_groups)
    return builder
    # Strings for i18n:
    # (none - not translated at the moment)

def get_gov3_fieldset(is_admin=False, user_editable_groups=None, **kwargs):
    '''Returns the standard fieldset
    '''
    return build_package_gov_form_v3(is_admin=is_admin, user_editable_groups=user_editable_groups, **kwargs).get_fieldset()
