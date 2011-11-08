import xml.sax
import re
import os
import glob

from ckanext.importlib.importer import PackageImporter
from ckanext.dgu import schema
from ckanext.dgu.ons.producers import get_ons_producers
from datautil import date

guid_prefix = 'http://www.statistics.gov.uk/'

log = __import__("logging").getLogger(__name__)


class OnsImporter(PackageImporter):
    def __init__(self, filepaths, xmlrpc_settings=None):
        if not isinstance(filepaths, (list, tuple)):
            filepaths = [filepaths]
        self._current_filename = os.path.basename(filepaths[0])
        self._item_count = 0
        self._new_package_count = 0
        self._crown_license_id = u'uk-ogl'
        self._drupal_helper = schema.DrupalHelper(xmlrpc_settings)
        super(OnsImporter, self).__init__(filepath=filepaths)

    def import_into_package_records(self):
        # all work is done in pkg_dict
        pass

    def pkg_dict(self):
        for filepath in self._filepath:
            log.info('Importing from file: %s' % filepath)
            self._current_filename = os.path.basename(filepath)
            for item in OnsDataRecords(filepath):
                yield self.record_2_package(item)

    def record_2_package(self, item):
        assert isinstance(item, dict)

        # process item
        title, release = self._split_title(item['title'])
        munged_title = schema.name_munge(title)
        department, agency, published_by, published_via = self._cached_source_to_organisations(item['hub:source-agency'])

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
            'temporal_coverage-from': u'',
            'temporal_coverage-to': u'',
            'national_statistic': u'',
            'department': u'',
            'update_frequency': u'',
            'date_released': u'',
            'categories': u'',
            'series':u'',
            'published_by':u'',
            'published_via':u'',
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
        extras['published_by'] = published_by or u''
        extras['published_via'] = published_via or u''
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
            'groups': [],
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

    def _cached_source_to_organisations(self, source):
        return self._source_to_organisations(source, drupal_helper=self._drupal_helper)
    
    @classmethod
    def _source_to_organisations(cls, source, drupal_helper=None):
        dept_given = schema.canonise_organisation_name(source)
        department = None
        agency = None

        if not drupal_helper:
            drupal_helper = schema.DrupalHelper()
        
        # special cases
        if '(Northern Ireland)' in source or dept_given == 'Office of the First and Deputy First Minister':
            department = u'Northern Ireland Executive'
            agency = drupal_helper.cached_department_or_agency_to_organisation(dept_given, include_id=False)
            if not agency:
                log.warn('Could not find NI department: %s' % dept_given)
                agency = dept_given

        if dept_given == 'Office for National Statistics':
            department = 'UK Statistics Authority'
            agency = dept_given
        if dept_given == 'Education':
            department = 'Department for Education'

        # search for department
        if not department:
            org = drupal_helper.cached_department_or_agency_to_organisation(dept_given, include_id=False)
            if org in schema.government_depts:
                department = org
            elif org:
                agency = org
                
        if not (department or agency) and dept_given: 
            log.warn('Could not find organisation: %s' % dept_given)
            agency = dept_given

        # publishers
        orgs = [drupal_helper.cached_department_or_agency_to_organisation(org) \
                for org in [department, agency] if org]
        orgs += [u''] * (2 - len(orgs))
        published_by, published_via = orgs

        return department, agency, published_by, published_via


            
        

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
