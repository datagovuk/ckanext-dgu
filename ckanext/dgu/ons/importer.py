import xml.sax
import re
import os
import glob
from ckanext.dgu import schema
from swiss import date

guid_prefix = 'http://www.statistics.gov.uk/'

log = __import__("logging").getLogger(__name__)

class OnsImporter(object):
#NB This should derive from ckan/lib/importer:PackageImporter
    def __init__(self, filepath):
        self._filepath = filepath
        self._current_filename = os.path.basename(self._filepath)
        self._item_count = 0
        self._new_package_count = 0
        self._crown_license_id = u'uk-ogl'

    def pkg_dict(self):
        for item in OnsDataRecords(self._filepath):
            yield self.record_2_package(item)

    def record_2_package(self, item):
        assert isinstance(item, dict)

        # process item
        title, release = self._split_title(item['title'])
        munged_title = schema.name_munge(title)
        department, agency = self._source_to_department(item['hub:source-agency'])

        # Resources
        guid = item['guid'] or None
        if guid:
            if not guid.startswith(guid_prefix):
                raise RowParseError('GUID did not start with prefix %r: %r' % (guid_prefix, guid))
            guid = guid[len(guid_prefix):]
            if 'http' in guid: 
                raise RowParseError('GUID de-prefixed should not have \'http\' in it still: %r' % (guid))
        existing_resource = None
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

        extras = {
            'geographic_coverage': u'',
            'external_reference': u'',
            'temporal_granularity': u'',
            'date_updated': u'',
            'agency': u'',
            'precision': u'',
            'geographical_granularity': u'',
            'temporal_coverage_from': u'',
            'temporal_coverage_to': u'',
            'national_statistic': u'',
            'department': u'',
            'update_frequency': u'',
            'date_released': u'',
            'categories': u'',
            'series':u'',
            }
        date_released = u''
        if item['pubDate']:
            date_released = date.parse(item["pubDate"])
            if date_released.qualifier:
                log.warn('Could not read format of publication (release) date: %r' % 
                         item["pubDate"])
        extras['date_released'] = date_released.isoformat()
        extras['department'] = department or u''
        extras['agency'] = agency or u''
        extras['categories'] = item['hub:theme']
        extras['geographic_coverage'] = self._parse_geographic_coverage(item['hub:coverage'])
        extras['national_statistic'] = 'yes' if item['hub:designation'] == 'National Statistics' or item['hub:designation'] == 'National Statistics' else 'no'
        extras['geographical_granularity'] = item['hub:geographic-breakdown']
        extras['external_reference'] = u'ONSHUB'
        extras['series'] = title if release else u''
        for update_frequency_suggestion in schema.update_frequency_options:
            item_info = ('%s %s' % (item['title'], item['description'])).lower()
            if update_frequency_suggestion in item_info:
                extras['update_frequency'] = update_frequency_suggestion
            elif update_frequency_suggestion.endswith('ly'):
                if update_frequency_suggestion.rstrip('ly') in item_info:
                    extras['update_frequency'] = update_frequency_suggestion
        extras['import_source'] = 'ONS-%s' % self._current_filename 

        author = extras['department'] if extras['department'] else None
        resources = [{
                'url': download_url,
                'description': description
                }]

        # update package
        pkg_dict = {
            'name': munged_title,
            'title': title,
            'version': None,
            'url': None,
            'author': author,
            'author_email': None,
            'maintainer': None,
            'maintainer_email': None,
            'notes': notes,
            'license_id': self._crown_license_id,
            'tags': [], # post-filled
            'groups': ['ukgov'],
            'resources': resources,
            'extras': extras,
            }

        tags = schema.TagSuggester.suggest_tags(pkg_dict)
        for keyword in item['hub:ipsv'].split(';') + \
                item['hub:keywords'].split(';') + \
                item['hub:nscl'].split(';'):
            tag = schema.tag_munge(keyword)
            if tag and len(tag) > 1:
                tags.add(tag)
        tags = list(tags)
        tags.sort()
        pkg_dict['tags'] = tags

        return pkg_dict

    @staticmethod
    def _parse_geographic_coverage(coverage_str):
        geo_coverage_type = schema.GeoCoverageType.get_instance()
        coverage_str = coverage_str.replace('International', 'Global')
        geographic_coverage_db = geo_coverage_type.str_to_db(coverage_str)
        return geographic_coverage_db

    @staticmethod
    def _source_to_department(source):
        dept_given = schema.expand_abbreviations(source)
        department = None
        agency = None

        # special cases
        if '(Northern Ireland)' in dept_given or dept_given == 'Office of the First and Deputy First Minister':
            department = u'Northern Ireland Executive'
        if dept_given == 'Office for National Statistics':
            department = 'UK Statistics Authority'
            agency = dept_given
        if dept_given == 'Education':
            department = 'Department for Education'

        # search for department
        if not department:
            for dept in schema.government_depts:
                if dept_given in dept or dept_given.replace('Service', 'Services') in dept or dept_given.replace('Dept', 'Department') in dept:
                    department = unicode(dept)
                
        if department:
            assert department in schema.government_depts, department
        else:
            if dept_given and dept_given not in ['Office for National Statistics', 'Health Protection Agency', 'Information Centre for Health and Social Care', 'General Register Office for Scotland', 'Northern Ireland Statistics and Research Agency', 'National Health Service in Scotland', 'National Treatment Agency', 'Police Service of Northern Ireland (PSNI)', 'Child Maintenance and Enforcement Commission', 'Health and Safety Executive', 'NHS National Services Scotland', 'ISD Scotland (part of NHS National Services Scotland)', 'Passenger Focus', 'Office of the First and Deputy First Minister', 'Office of Qualifications and Examinations Regulation']:
                log.warn('Double check this is not a gvt department source: %s' % dept_given)
            agency = dept_given
        return department, agency

    @classmethod
    def _split_title(cls, xml_title):
        if not hasattr(cls, 'title_re'):
            cls.title_re = re.compile(r'(.*?)\s-\s(.*)')
        match = cls.title_re.match(xml_title)
        if not match:
            'Warning: Could not split title: %s' % xml_title
            return (xml_title, None)
        return [x for x in match.groups() if x]

class OnsDataRecords(object):
    def __init__(self, xml_filepath):
        self._xml_filepath = xml_filepath

    def __iter__(self):
        ons_xml = OnsXml()
        xml.sax.parse(self._xml_filepath, ons_xml)
        for record in ons_xml.items:
            yield record
    

class OnsXml(xml.sax.handler.ContentHandler):
    def startDocument(self):
        self._level = 0
        self._item_dict = {}
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
            self._item_dict = {}
        elif self._level == 4:
            self._item_dict[self._item_element] = self._item_data
            self._item_element = self._item_data = None
        self._level -= 1
