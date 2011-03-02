import re

import formalchemy
from formalchemy import helpers as h
from sqlalchemy.util import OrderedDict
from pylons.i18n import _, ungettext, N_, gettext

from ckan.forms import common
from ckan.forms import package
from ckan import model
from ckan.lib import field_types
from ckan.lib.helpers import literal


geographic_granularity_options = ['national', 'regional', 'local authority', 'ward', 'point']

region_options = ('England', 'Scotland', 'Wales', 'Northern Ireland', 'Overseas', 'Global')

region_groupings = {'United Kingdom':['England', 'Scotland', 'Wales', 'Northern Ireland'], 'Great Britain':['England', 'Scotland', 'Wales']}

region_abbreviations = {'UK':'United Kingdom', 'N. Ireland':'Northern Ireland', 'GB':'Great Britain'}

tag_pool = ['accident', 'road', 'traffic', 'health', 'illness', 'disease', 'population', 'school', 'accommodation', 'children', 'married', 'emissions', 'benefit', 'alcohol', 'deaths', 'mortality', 'disability', 'unemployment', 'employment', 'armed forces', 'asylum', 'cancer', 'births', 'burglary', 'child', 'tax credit', 'criminal damage', 'drug', 'earnings', 'education', 'economic', 'fire', 'fraud', 'forgery', 'fuel', 'green', 'greenhouse gas', 'homeless', 'hospital', 'waiting list', 'housing', 'care', 'income', 'census', 'mental health', 'disablement allowance', 'jobseekers allowance', 'national curriculum', 'older people', 'living environment', 'higher education', 'living environment', 'school absence', 'local authority', 'carbon dioxide', 'energy', 'teachers', 'fostering', 'tide', 'gas', 'electricity', 'transport', 'veterinary', 'fishing', 'export', 'fisheries', 'pest', 'recycling', 'waste', 'crime', 'anti-social behaviour', 'police', 'refugee', 'identity card', 'immigration', 'planning', 'communities', 'lettings', 'finance', 'ethnicity', 'trading standards', 'trade', 'business', 'child protection', 'jobs', 'weather', 'climate', 'rainfall', 'cloud', 'snow', 'humidity', 'pressure', 'precipitation', 'sunshine', 'frost', 'temperature']

tag_search_fields = ['name', 'title', 'notes', 'categories', 'agency']

class GeoCoverageType(object):
    @staticmethod
    def get_instance():
        if not hasattr(GeoCoverageType, 'instance'):
            GeoCoverageType.instance = GeoCoverageType.Singleton()
        return GeoCoverageType.instance

    class Singleton(object):
        def __init__(self):
            regions_str = region_options
            self.groupings = region_groupings
            self.regions = [(region_str, GeoCoverageType.munge(region_str)) for region_str in regions_str]
            self.regions_munged = [GeoCoverageType.munge(region_str) for region_str in regions_str]

        def munged_regions_to_printable_region_names(self, munged_regions):
            incl_regions = []
            for region_str, region_munged in self.regions:
                if region_munged in munged_regions:
                    incl_regions.append(region_str)
            for grouping_str, regions_str in self.groupings.items():
                all_regions_in = True
                for region_str in regions_str:
                    if region_str not in incl_regions:
                        all_regions_in = False
                        break
                if all_regions_in:
                    for region_str in regions_str:
                        incl_regions.remove(region_str)
                    incl_regions.append('%s (%s)' % (grouping_str, ', '.join(regions_str)))
            return ', '.join(incl_regions)

        def str_to_db(self, regions_str):
            for abbrev, region in region_abbreviations.items():
                regions_str = regions_str.replace(abbrev, region)
            for grouping, regions in region_groupings.items():
                regions_str = regions_str.replace(grouping, ' '.join(regions))
            regions_munged = []
            for region, region_munged in self.regions:
                if region in regions_str:
                    regions_munged.append(region_munged)
            return self.form_to_db(regions_munged)

        def form_to_db(self, form_regions):
            assert isinstance(form_regions, list)
            coded_regions = u''
            for region_str, region_munged in self.regions:
                coded_regions += '1' if region_munged in form_regions else '0'
            regions_str = self.munged_regions_to_printable_region_names(form_regions)
            return '%s: %s' % (coded_regions, regions_str)

        def db_to_form(self, form_regions):
            '''
            @param form_regions e.g. 110000: England, Scotland
            @return e.g. ["england", "scotland"]
            '''
            regions = []
            if len(form_regions)>len(self.regions):
                for i, region in enumerate(self.regions):
                    region_str, region_munged = region
                    if form_regions[i] == '1':
                        regions.append(region_munged)
            return regions

    @staticmethod
    def munge(region):
        return region.lower().replace(' ', '_')

    def __getattr__(self, name):
        return getattr(self.instance, name)

class GeoCoverageExtraField(common.ConfiguredField):
    def get_configured(self):
        return self.GeoCoverageField(self.name).with_renderer(self.GeoCoverageRenderer)

    class GeoCoverageField(formalchemy.Field):
        def sync(self):
            if not self.is_readonly():
                pkg = self.model
                form_regions = self._deserialize() or []
                regions_db = GeoCoverageType.get_instance().form_to_db(form_regions)
                pkg.extras[self.name] = regions_db

    class GeoCoverageRenderer(formalchemy.fields.FieldRenderer):
        def _get_value(self):
            form_regions = self.value # params
            if not form_regions:
                extras = self.field.parent.model.extras # db
                db_regions = extras.get(self.field.name, []) or []
                form_regions = GeoCoverageType.get_instance().db_to_form(db_regions)
            return form_regions

        def render(self, **kwargs):
            value = self._get_value()
            kwargs['size'] = '40'
            html = u''
            for i, region in enumerate(GeoCoverageType.get_instance().regions):
                region_str, region_munged = region
                id = '%s-%s' % (self.name, region_munged)
                checked = region_munged in value
                cb = literal(h.check_box(id, True, checked=checked, **kwargs))
                html += literal('<label for="%s">%s %s</label>') % (id, cb, region_str)
            return html

        def render_readonly(self, **kwargs):
            munged_regions = self._get_value()
            printable_region_names = GeoCoverageType.get_instance().munged_regions_to_printable_region_names(munged_regions)
            return common.field_readonly_renderer(self.field.key, printable_region_names)

        def _serialized_value(self):
            # interpret params like this:
            # 'Package--geographic_coverage-wales', u'True'
            # return list of covered regions
            covered_regions = []
            for region in GeoCoverageType.get_instance().regions_munged:
                if self.params.get(self.name + '-' + region, u'') == u'True':
                    covered_regions.append(region)
            return covered_regions

        def deserialize(self):
            return self._serialized_value()

class SuggestTagRenderer(common.TagField.TagEditRenderer):
    def render(self, **kwargs):
        fs = self.field.parent
        pkg_dict = {}
        for field_name, field in fs.render_fields.items():
            pkg_dict[field_name] = field.renderer.value
        tag_suggestions = suggest_tags(pkg_dict)
        html = literal(_("<div>Suggestions (preview refreshes): %s</div>")) % ' '.join(tag_suggestions)
        html += common.TagField.TagEditRenderer.render(self, **kwargs)
        return html
        
class PublisherField(common.SelectExtraField):
    '''Select from a list of publishers, but always include the existing
    publisher, as you are always allowed to not change the publisher.
    '''
    
    def validate(self, value, field=None):
        if not value:
            # if value is required then this is checked by 'required' validator
            return
        if value not in [id_ for label, id_ in self.options] and \
               value != field.model_value:
            raise formalchemy.ValidationError('Value %r is not one of the options.' % id_)

    class SelectRenderer(common.SelectExtraField.SelectRenderer):
        def render(self, options, **kwargs):
            # @param options - an iterable of (label, value)
            is_option_pairs = options and isinstance(options[0], (tuple, list))
            option_values = [value for label, value in options] \
                            if is_option_pairs else options
            # ensure the existing self.value is listed
            if self.value and self.value not in option_values:
                if is_option_pairs or not options:
                    label = re.sub(' \[\d+\]', ' *', self.value)
                    options.append((label, self.value))
                else:
                    options.append(self.value)
            if not self.field.is_required():
                options = list(options)
                if is_option_pairs:
                    null_option = self.field._null_option
                else:
                    null_option = self.field._null_option[1]
                options.insert(0, self.field._null_option)
            return formalchemy.fields.SelectFieldRenderer.render(self, options, **kwargs)

def suggest_tags(suggest_tags):
    tags = set()
    for field_name in tag_search_fields:
        if pkg_dict.has_key(field_name):
            text = pkg_dict[field_name]
        else:
            if pkg_dict.has_key('extras'):
                text = pkg_dict['extras'][field_name]                
        if text and isinstance(text, (str, unicode)):
            for keyword in tag_pool:
                if keyword in text:
                    tags.add(tag_munge(keyword))
    return tags
