import xml.sax
import re
import os
import glob
import logging

import ckan.model as model
from ckan.lib import schema_gov
from ckan.lib import field_types
from ckan.lib.importer import PackageImporter, DataRecords, RowParseError

from sqlalchemy.util import OrderedDict

guid_prefix = 'http://www.statistics.gov.uk/'

class OnsImporter(PackageImporter):
    def import_into_package_records(self):
        xml_filepath = self._filepath
        self._basic_setup()
#        self._log(logging.info, 'Loading ONS file: %s' % self._filepath)
        self._current_filename = os.path.basename(self._filepath)
        self._package_data_records = OnsDataRecords(self._filepath)
#        self._log(logging.info, 'Loaded %i lines with %i new packages' % (self._item_count, self._new_package_count))

    def record_2_package(self, item):
        assert isinstance(item, dict)

        # process item
        title, release = self._split_title(item['title'])
        munged_title = schema_gov.name_munge(title)
        department = self._source_to_department(item['hub:source-agency'])
##        if pkg and pkg.extras.get('department') != department:
##            munged_title = schema_gov.name_munge('%s - %s' % (title, department))
##            pkg = model.Package.by_name(munged_title)

        # Resources
        guid = item['guid'] or None
        if guid:
            if not guid.startswith(guid_prefix):
                raise RowParseError('GUID did not start with prefix %r: %r' % (guid_prefix, guid))
            guid = guid[len(guid_prefix):]
            if 'http' in guid: 
                raise RowParseError('GUID de-prefixed should not have \'http\' in it still: %r' % (guid))
        existing_resource = None
##        if guid and pkg:
##            for res in pkg.resources:
##                if res.description:
##                    for desc_bit in res.description.split('|'):
##                        if desc_bit.strip() == guid:
##                            existing_resource = res
##                            break
        download_url = item.get('link', None)
        descriptors = []
        if release:
            descriptors.append(release)
        if guid:
            descriptors.append(guid)
        description = ' | '.join(descriptors)

        notes_list = []
        if item['description']:
            notes_list.append(item['description'])
        for column, name in [('hub:source-agency', 'Source agency'),
                             ('hub:designation', 'Designation'),
                             ('hub:language', 'Language'),
                             ('hub:altTitle', 'Alternative title'),
                       ]:
            if item[column]:
                notes_list.append('%s: %s' % (name, item[column]))
        notes = '\n\n'.join(notes_list)

        extras = OrderedDict([
            ('geographic_coverage', u''),
            ('external_reference', u''),
            ('temporal_granularity', u''),
            ('date_updated', u''),
            ('agency', u''),
            ('precision', u''),
            ('geographical_granularity', u''),
            ('temporal_coverage_from', u''),
            ('temporal_coverage_to', u''),
            ('national_statistic', u''),
            ('department', u''),
            ('update_frequency', u''),
            ('date_released', u''),
            ('categories', u''),
            ])
        date_released = u''
        if item['pubDate']:
            try:
                iso_date = field_types.DateType.strip_iso_timezone(item['pubDate'])
                date_released = field_types.DateType.iso_to_db(iso_date, '%a, %d %b %Y %H:%M:%S')
            except TypeError, e:
                self.log('Warning: Could not read format of publication (release) date: %r' % e.args)
        extras['date_released'] = date_released
        extras['department'] = self._source_to_department(item['hub:source-agency'])
        extras['agency'] = item['hub:source-agency'] if not extras['department'] else u''
        extras['categories'] = item['hub:theme']
        geo_coverage_type = schema_gov.GeoCoverageType.get_instance()
        extras['geographic_coverage'] = geo_coverage_type.str_to_db(item['hub:coverage'])
        extras['national_statistic'] = 'yes' if item['hub:designation'] == 'National Statistics' or item['hub:designation'] == 'National Statistics' else 'no'
        extras['geographical_granularity'] = item['hub:geographic-breakdown']
        extras['external_reference'] = u'ONSHUB'
        for update_frequency_suggestion in schema_gov.update_frequency_suggestions:
            item_info = ('%s %s' % (item['title'], item['description'])).lower()
            if update_frequency_suggestion in item_info:
                extras['update_frequency'] = update_frequency_suggestion
            elif update_frequency_suggestion.endswith('ly'):
                if update_frequency_suggestion.rstrip('ly') in item_info:
                    extras['update_frequency'] = update_frequency_suggestion
        extras['import_source'] = 'ONS-%s' % self._current_filename 

        author = extras['department'] if extras['department'] else None
        resources = [OrderedDict((('url', download_url),
                                 ('description', description)))]

        # update package
##        if not pkg:
##            pkg = model.Package(name=munged_title)
##            model.Session.add(pkg)
##            self._new_package_count += 1
##            is_new_package = True
##            rev = self._new_revision('New package %s' % munged_title)

##        else:
##            rev = self._new_revision('Edit package %s' % munged_title)
##            is_new_package = False
        pkg_dict = OrderedDict([
            ('name', munged_title),
            ('title', title),
            ('version', None),
            ('url', None),
            ('author', author),
            ('author_email', None),
            ('maintainer', None),
            ('maintainer_email', None),
            ('notes', notes),
            ('license_id', self._crown_license_id),
            ('tags', []), # post-filled
            ('groups', ['ukgov']),
            ('resources', resources),
            ('extras', extras),
            ])

        tags = schema_gov.TagSuggester.suggest_tags(pkg_dict)
        for keyword in item['hub:ipsv'].split(';') + \
                item['hub:keywords'].split(';') + \
                item['hub:nscl'].split(';'):
            tags.add(schema_gov.tag_munge(keyword))
        tags = list(tags)
        tags.sort()
        pkg_dict['tags'] = tags

        return pkg_dict

    def _source_to_department(self, source):
        dept_given = schema_gov.expand_abbreviations(source)
        department = None
        if '(Northern Ireland)' in dept_given:
            department = u'Northern Ireland Executive'
        for dept in schema_gov.government_depts:
            if dept_given in dept or dept_given.replace('Service', 'Services') in dept or dept_given.replace('Dept', 'Department') in dept:
                department = unicode(dept)
                
        if department:
            assert department in schema_gov.government_depts, department
            return department
        else:
            if dept_given and dept_given not in ['Office for National Statistics', 'Health Protection Agency', 'Information Centre for Health and Social Care', 'General Register Office for Scotland', 'Northern Ireland Statistics and Research Agency', 'National Health Service in Scotland', 'National Treatment Agency', 'Police Service of Northern Ireland (PSNI)', 'Child Maintenance and Enforcement Commission', 'Health and Safety Executive', 'NHS National Services Scotland', 'ISD Scotland (part of NHS National Services Scotland)']:
                self.log('Warning: Double check this is not a gvt department source: %s' % dept_given)
            return None
        
    def _split_title(self, xml_title):
        if not hasattr(self, 'title_re'):
            self.title_re = re.compile(r'([^-]+)\s-\s(.*)')
        match = self.title_re.match(xml_title)
        if not match:
            'Warning: Could not split title: %s' % xml_title
            return (xml_title, None)
        return match.groups()

    def _basic_setup(self):
        self._item_count = 0
        self._new_package_count = 0
        self._crown_license_id = u'ukcrown-withrights'


class OnsDataRecords(DataRecords):
    def __init__(self, xml_filepath):
        self._xml_filepath = xml_filepath
        
    @property
    def records(self):
        ons_xml = OnsXml()
        xml.sax.parse(self._xml_filepath, ons_xml)
        for record in ons_xml.items:
            yield record
    

class OnsXml(xml.sax.handler.ContentHandler):
    def startDocument(self):
        self._level = 0
        self._item_dict = OrderedDict()
        self.items = []
        
    def startElement(self, name, attrs):
        self._level += 1
        if self._level == 1:
            if name == 'rss':
                pass
            else:
                print 'Warning: Not expecting element %s at level %i' % (name, self._level)
        elif self._level == 2:
            if name == 'channel':
                pass
            else:
                print 'Warning: Not expecting element %s at level %i' % (name, self._level)
        elif self._level == 3:
            if name == 'item':
                assert not self._item_dict
            elif name in ('title', 'link', 'description', 'language', 'pubDate', 'atom:link'):
                pass
        elif self._level == 4:
            assert name in ('title', 'link', 'description', 'pubDate', 'guid',
                            'hub:source-agency', 'hub:theme', 'hub:coverage',
                            'hub:designation', 'hub:geographic-breakdown',
                            'hub:ipsv', 'hub:keywords', 'hub:altTitle',
                            'hub:language',
                            'hub:nscl'), name
            self._item_element = name
            self._item_data = u''

    def characters(self, chrs):
        if self._level == 4:
            self._item_data += chrs

    def endElement(self, name):
        if self._level == 3:
            if self._item_dict:
                self.items.append(self._item_dict)
            self._item_dict = OrderedDict()
        elif self._level == 4:
            self._item_dict[self._item_element] = self._item_data
            self._item_element = self._item_data = None
        self._level -= 1
