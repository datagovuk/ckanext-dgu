import re

class FieldNames:
    def add(self, field_names):
        self._field_names.extend(field_names)
    def add_after(self, field_name_to_insert_after, field_name_to_insert):
        index = self._field_names.index(field_name_to_insert_after)
        self._field_names.insert(index + 1, field_name_to_insert)
    def add_at_start(self, field_name_to_insert):
        self._field_names.insert(0, field_name_to_insert)
    def remove(self, field_names):
        for field_name in field_names:
            self._field_names.remove(field_name)
    def __iter__(self):
        for field_name in self._field_names:
            yield field_name

class DatasetFieldNames(FieldNames):
    # For building a list of the fields to display and their order
    def __init__(self):
        # core fields
        self._field_names = ['mandate', 'temporal_coverage', 'geographic_coverage', 'date-added-computed', 'date-updated-computed']
        # Never display: 'name', 'version', 'maintainer', 'maintainer_email', 'url', 'author', 'author_email', 'published_by', 'published_via'
        # Displayed elsewhere in templates: 'title', 'license', 'contact', 'foi_contact', 'notes', 'tags', 'groups'

class ResourceFieldNames(FieldNames):
    # For building a list of the fields to display and their order
    def __init__(self):
        # core fields
        self._field_names = ['url', 'date-updated-computed', 'scraper_url', 'scraped']

class DisplayableFields:
    # For collecting the key and value to display each field
    def __init__(self, field_names, field_value_map, pkg_extras):
        self._fields_requiring_values = ['scraper_url', 'scraped']
        self.fields = []
        for field_name in field_names:
            value_dict = field_value_map.get(field_name, {})
            value_dict['name'] = field_name
            if not 'label' in value_dict:
               value_dict['label'] = re.sub('[-_]', ' ', field_name).capitalize()
               value_dict['value'] = pkg_extras.get(field_name)
            self.fields.append(value_dict)
        # move blank values last
        blank_values = []
        for field in self.fields[:]:
            if not field.get('value'):
                if not field.get('name', '') in self._fields_requiring_values:
                    blank_values.append(field)
                self.fields.remove(field)
        self.fields.extend(blank_values)
    def __iter__(self):
        for field in self.fields:
            value_attributes = {'property': field.get('property')} if 'property' in field else {}
            if 'value_title' in field:
                value_attributes['title'] = field['value_title']
            label_attributes = {'title': field['label_title']} if 'label_title' in field else {}
            yield (field, label_attributes, value_attributes)
