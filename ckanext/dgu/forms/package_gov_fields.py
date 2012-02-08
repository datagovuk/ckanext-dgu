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

from ckanext.dgu.schema import GeoCoverageType

geographic_granularity_options = ['national', 'regional', 'local authority', 'ward', 'point']

tag_pool = ['accident', 'road', 'traffic', 'health', 'illness', 'disease', 'population', 'school', 'accommodation', 'children', 'married', 'emissions', 'benefit', 'alcohol', 'deaths', 'mortality', 'disability', 'unemployment', 'employment', 'armed forces', 'asylum', 'cancer', 'births', 'burglary', 'child', 'tax credit', 'criminal damage', 'drug', 'earnings', 'education', 'economic', 'fire', 'fraud', 'forgery', 'fuel', 'green', 'greenhouse gas', 'homeless', 'hospital', 'waiting list', 'housing', 'care', 'income', 'census', 'mental health', 'disablement allowance', 'jobseekers allowance', 'national curriculum', 'older people', 'living environment', 'higher education', 'living environment', 'school absence', 'local authority', 'carbon dioxide', 'energy', 'teachers', 'fostering', 'tide', 'gas', 'electricity', 'transport', 'veterinary', 'fishing', 'export', 'fisheries', 'pest', 'recycling', 'waste', 'crime', 'anti-social behaviour', 'police', 'refugee', 'identity card', 'immigration', 'planning', 'communities', 'lettings', 'finance', 'ethnicity', 'trading standards', 'trade', 'business', 'child protection', 'jobs', 'weather', 'climate', 'rainfall', 'cloud', 'snow', 'humidity', 'pressure', 'precipitation', 'sunshine', 'frost', 'temperature']

tag_search_fields = ['name', 'title', 'notes', 'categories', 'agency']

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

def national_statistic_validator(value, field=None):
    if value != 'yes':
        return
    fs = field.parent
    for publisher_field in ('published_by', 'published_via'):
        pub = fs[publisher_field].value
        if pub and 'Office for National Statistics' in pub:
            return
    raise formalchemy.ValidationError(
        "'National Statistic' should only be checked if the package is "
        "'published by' or 'published via' the Office for National Statistics.")

