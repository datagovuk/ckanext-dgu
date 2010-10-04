from sqlalchemy.util import OrderedDict
from pylons.i18n import _, ungettext, N_, gettext

from ckan.forms import common
from ckan.forms import package
from ckan.forms import package_gov
from ckanext.dgu import schema as schema_gov
from ckan.lib.helpers import literal

# Setup the fieldset
def build_package_gov_form_v3(is_admin=False, statistics=False, inventory=False):
    assert not (statistics and inventory) # can't be both
    builder = package.build_package_form()

    # Extra fields
    builder.add_field(common.TextExtraField('external_reference'))
    builder.add_field(common.DateExtraField('date_planned_publication'))
    builder.add_field(common.DateExtraField('date_released'))
    builder.add_field(common.DateExtraField('date_updated'))
    builder.add_field(common.TextExtraField('update_frequency'))
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
    if statistics:
        builder.add_field(common.CheckboxExtraField('national_statistic'))
        builder.add_field(common.SuggestedTextExtraField('series'))
    if inventory:
        builder.add_field(common.DateExtraField('disposal'))
        builder.add_field(common.SuggestedTextExtraField('permanent_preservation'), options=schema_gov.yes_no_not_yet_options)
        builder.add_field(common.CheckboxExtraField('disclosure_foi'))
        builder.add_field(common.CheckboxExtraField('disclosure_eir'))
        builder.add_field(common.CheckboxExtraField('disclosure_dpa'))

    # Labels and instructions
    builder.set_field_text('name', 'Identifier', instructions='This is a public unique identifier for the dataset.', further_instructions='It should be roughly readable, with dashes separating words. If the data relates to a period of time, include that in the name. Indicate broad geographical coverage to distinguish from those datasets for another country.', hints='Format: Two or more lowercase alphanumeric, dash (-) or underscore (_) characters. e.g. uk-road-traffic-statistics')
    builder.set_field_text('title', instructions='This is the title of the data set. It is not a description - save that for the Abstract element. Do not give a trailing full stop.')
    builder.set_field_text('external_reference', 'Inventory identifier', instructions='This is the identifier for the dataset allocated by the data.gov.uk team, for tracking purposes.')
    builder.set_field_text('notes', 'Abstract', instructions='This element is the main description of the dataset, and often displayed with the package title. In particular, it should start with a short sentence that describes the data set succinctly, because the first few words alone may be used in some views of the data sets.')
    builder.set_field_text('date_released', instructions='This should be the date of the official release of the initial version of the dataset (this is probably not the date that it is uploaded to data.gov.uk). Be careful not to confuse a new \'version\' of some data with a new dataset covering another time period or geographic area.')
    builder.set_field_text('date_updated', instructions='This should be the date of release of the most recent version of the dataset (not necessarily the date when it was updated on data.gov.uk). As with \'Date released\', this is for updates to a particular dataset, such as corrections or refinements, not for that of a new time period.')
    builder.set_field_text('update_frequency', instructions='This should be how frequently the datasets is updated with new versions. For one-off data, use \'never\'. For those once updated but now discontinued, use \'discontinued\'.')
    builder.set_field_text('precision', instructions='This should indicate to users the level of precision in the data, to avoid over-interpretation.', hints='e.g. \'per cent to two decimal places\'')
    builder.set_field_text('geographic_granularity', instructions='This should give the lowest level of geographic granularity given in the dataset. \'Point\' means datasets given down to the level of the entities being reported on (such as school, hospital, or police station). If none of the choices is appropriate, please specify in the \'other\' element. Where the granularity varies, please select the lowest and note this in the \'other\' element. ')
    builder.set_field_text('geographic_coverage', instructions='This should show the geographic coverage of this dataset. Where a dataset covers multiple columns, the system will automatically group these (e.g. \'England\', \'Scotland\' and \'Wales\' all being \'Yes\' would be shown as \'Great Britain\').')
    builder.set_field_text('temporal_granularity', instructions='This should give the lowest level of temporal granularity, expressed as an interval of time, given in the dataset. \'Points\' means temporal intervals given down to the level of the entities being reported on (for example, reporting on coastal sea levels in tide tables; the time intervals are high and low tide, therefore the choice would be \'points\'). If none of the choices are appropriate, please specify in the \'other\' element. Where the granularity varies, please select the lowest interval.')
    builder.set_field_text('temporal_coverage', instructions='This should show the temporal coverage of this dataset. If available, please indicate the time as well as the date. Where data covers only a single day, the \'To\' sub-element can be left blank.', hints='e.g. 23:28 21/03/2007 - 07:31 03/10/2009')
    builder.set_field_text('url', instructions='This is the Internet link to a web page for the data.', hints='e.g. http://www.somedept.gov.uk/growth-figures.html')
    builder.set_field_text('taxonomy_url', instructions='This is an Internet link to a web page describing for re-users the taxonomies used in the dataset, if any, to ensure they understand any terms used.', hints='e.g. http://www.somedept.gov.uk/growth-figures-technical-details.html')
    builder.set_field_text('department', instructions='This is the Department under which the dataset is collected and published (but not necessarily directly undertaking this - use the Agency element where this applies).')
    builder.set_field_text('agency', instructions='This is the agency or arms-length body responsible for the data collection. Please use the full title of the body without any abbreviations, so that all items from it appear together.', hints='e.g. Environment Agency')
    builder.set_field_text('license_id', instructions='This should match the licence under which the dataset is released. For most situations of central Departments\' and Local Authority data, this should be the \'Open Government Licence\'. If you wish to release the data under a different licence, please contact the Making Public Data Public team.')
    builder.set_field_text('publisher', instructions='Unit responsible for publishing the data (May be different from Unit responsible for creating the data)')
    builder.set_field_text('author', 'Contact', instructions='This is the permanent contact point for the public to enquire about this particular dataset. This should be the name of the section of the agency or Department responsible, and should not be a named person. Particular care should be taken in choosing this element.')
    builder.set_field_text('author_email', 'Contact email', instructions='This should be a generic official e-mail address for members of the public to contact, to match the Author element. A new e-mail address may need to be created for this function.')
    if statistics:
        builder.set_field_text('national_statistic', 'National Statistic', instructions='This should indicate if the dataset is a National Statistic, so that this can be highlighted.')
        builder.set_field_text('series', instructions='Data is part of a series or collection need for National Statistics, for example \'Wages Weekly Index\'')
    if inventory:
        builder.set_field_text('date_planned_publication', 'Planned publication date', instructions='To be used when adding data intended for future publication to the Inventory')
        builder.set_field_text('disposal', instructions='A future date when it is intended to remove the data from the department\'s system , eventually replaced with the actual date the disposal  was implemented', hints='DD/MM/YYYY')
        builder.set_field_text('permanent_preservation', 'Selected for permanent preservation', instructions='Data, whose sensitivity currently prevents publication, selected by the National Archives as worthy of permanent preservation.  (It is intended that published data will automatically be preserved in the UK Government Web Archive.)')
        builder.set_field_text('disclosure_foi', instructions='Indicates whether or not data is exempt from publication by virtue of the Freedom of Information Act 2000.')
        builder.set_field_text('disclosure_eir', instructions='Indicates wheter or not data is exempt from publication by virtue of the Environmental Information Regulations 2004.')
        builder.set_field_text('disclosure_dpa', instructions='Indicates whether or not data is exempt from publication by virtue of  the Data Protection Act 1998, taking into account that personal data whilst not of itself disclosive, may, if combined with other data in the public domain, become so.')
    builder.set_field_text('mandate', instructions='URI to Legislation website, e.g., to section of Act that mandates collection/creation of data.  For example Public Record Act s.2 : http://www.legislation.gov.uk/id/ukpga/Eliz2/6-7/51/section/2')
##    builder.set_field_text('resources_url', instructions='This is the Internet link directly to the data - by selecting this link in a web browser, the user will immediately download the full data set. Note that datasets are not hosted by the project, but by the responsible department', hints='e.g. http://www.somedept.gov.uk/growth-figures-2009.csv')
##    builder.set_field_text('resources_format', instructions='This should give the file format in which the data is supplied. If the data is being supplied in multiple formats, please supply a separate entry for that form, differing only in \'Resource format\' and \'Resource URL\' elements. If you wish to supply the data in a form not listed here, please contact the central Making Public Data Public team as specified above.', hints='Choices: RDF | CSV | XBRL | SDMX | HTML+RDFa | HTML')
    builder.set_field_text('resources', instructions=literal('<b>URL:</b> This is the Internet link directly to the data - by selecting this link in a web browser, the user will immediately download the full data set. Note that datasets are not hosted by the project, but by the responsible department<br/> e.g. http://www.somedept.gov.uk/growth-figures-2009.csv<br/><b>Format:</b> This should give the file format in which the data is supplied. If the data is being supplied in multiple formats, please supply a separate entry for that form, differing only in \'Resource format\' and \'Resource URL\' elements. If you wish to supply the data in a form not listed here, please contact the central Making Public Data Public team as specified above.<br/>Choices: RDF | CSV | XBRL | SDMX | HTML+RDFa | HTML'))
    builder.set_field_text('tags', instructions='Tags can be thought of as the way that the packages are categorised, so are of primary importance. One or more tags should be added to give the government department and geographic location the data covers, as well as general descriptive words. The Integrated Public Sector Vocabulary may be helpful in forming these.', hints='Format: Two or more lowercase alphanumeric or dash (-) characters; different tags separated by spaces. As tags cannot contain spaces, use dashes instead. e.g. for a dataset containing statistics on burns to the arms in the UK in 2009: nhs uk arm burns medical-statistics')
    # Options/settings
    builder.set_field_option('tags', 'with_renderer', package_gov.SuggestTagRenderer)
    
    # Layout
    field_groups = OrderedDict([
        (_('Basic information'), ['name', 'title', 'external_reference',
                                  'notes']),
        (_('Details'), ['date_released', 'date_updated', 'update_frequency',
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
    if statistics:
        field_groups['More details'].append('national_statistic')
    if inventory:
        field_groups['Details'].insert('date_planned_publication', 0)
        field_groups['Details'].insert('disposal', 3)
        field_groups['Details'].insert('permanent_preservation', 4)
        field_groups['More details'].insert('disclosure_foi', 6)
        field_groups['More details'].insert('disclosure_eir', 7)
        field_groups['More details'].insert('disclosure_dpa', 8)
    if is_admin:
        field_groups['More details'].append('state')
    builder.set_displayed_fields(field_groups)
    return builder
    # Strings for i18n:
    # (none - not translated at the moment)

fieldsets = {} # fieldset cache

def get_gov3_fieldset(is_admin=False):
    '''Returns the standard fieldset
    '''
    if not fieldsets:
        # fill cache
        fieldsets['package_gov_fs'] = build_package_gov_form_v3().get_fieldset()
        fieldsets['package_gov_fs_admin'] = build_package_gov_form_v3(is_admin=True).get_fieldset()

    if is_admin:
        fs = fieldsets['package_gov_fs_admin']
    else:
        fs = fieldsets['package_gov_fs']
    return fs
