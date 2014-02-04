import xml.sax
import re
import os
import HTMLParser

from ckanext.importlib.importer import PackageImporter, RowParseError
from ckanext.dgu import schema
from ckanext.dgu.lib.theme import categorize_package, PRIMARY_THEME, SECONDARY_THEMES
from datautildate import date

guid_prefix = 'http://www.statistics.gov.uk/hub/id/'

log = __import__("logging").getLogger(__name__)


class OnsImporter(PackageImporter):
    def __init__(self, filepaths, ckanclient, stats, filter_=None):
        if not isinstance(filepaths, (list, tuple)):
            filepaths = [filepaths]
        self._current_filename = os.path.basename(filepaths[0]) \
                                 if filepaths else None
        self._item_count = 0
        self._new_package_count = 0
        self._crown_license_id = u'uk-ogl'
        self._ckanclient = ckanclient
        self._filter = filter_ or {}
        for key in self._filter.keys():
            if key == 'publisher':
                filter_['publisher'] = self._source_to_publisher(filter_['publisher'])
            else:
                raise NotImplementedError
        self._stats = stats
        super(OnsImporter, self).__init__(filepath=filepaths)

    def import_into_package_records(self):
        # all work is done in pkg_dict
        pass

    def pkg_dict(self):
        for filepath in self._filepath:
            log.info('Importing from file: %s', filepath)
            self._current_filename = os.path.basename(filepath)
            count_imported = count_not_imported = 0
            for item in OnsDataRecords(filepath):
                log.info('Item %s %s', item['guid'][-9:], item['pubDate'])
                # record_2_package might raise RowParseError if bad guid
                pkg_dict = self.record_2_package(item)
                if pkg_dict:
                    yield pkg_dict
                    count_imported += 1
                else:
                    count_not_imported += 1
            log.info('%i/%i records were imported from file: %s',
                     count_imported,
                     count_imported + count_not_imported, filepath)

    def _add_stat(self, message, item):
        item_id = '%s (%s)' % (item['title'], item['pubDate'])
        return self._stats.add(message, item_id)

    def record_2_package(self, item):
        assert isinstance(item, dict)
        title, release = self._split_title(item['title'])
        munged_title = schema.name_munge(title)
        publisher_id = self._source_to_publisher(item['hub:source-agency'])
        if not publisher_id:
            log.warn('Did not find publisher for source-agency: %s', item['hub:source-agency'])

        if 'publisher' in self._filter and publisher_id != self._filter['publisher']:
            self._add_stat('Filtered out publisher', item)
            log.info('Ignoring item from publisher: %s', item['hub:source-agency'])
            return

        # Resources
        guid = item['guid'] or None
        if guid:
            if not guid.startswith(guid_prefix):
                raise RowParseError('GUID did not start with prefix %r: %r' % (guid_prefix, guid))
            guid = guid[len(guid_prefix):]
            if 'http' in guid:
                raise RowParseError('GUID de-prefixed should not have \'http\' in it still: %r' % (guid))
        download_url = item.get('link', None)

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
            'precision': u'',
            'geographic_granularity': u'',
            'temporal_coverage-from': u'',
            'temporal_coverage-to': u'',
            'national_statistic': u'',
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
        extras['categories'] = item['hub:theme']
        extras['geographic_coverage'] = self._parse_geographic_coverage(item['hub:coverage'])
        extras['national_statistic'] = 'yes' if item['hub:designation'] == 'National Statistics' or item['hub:designation'] == 'National Statistics' else 'no'
        extras['geographic_granularity'] = item['hub:geographic-breakdown']
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

        resources = [{
            'url': download_url,
            'description': release,
            'hub-id': guid,
            'publish-date': date_released.as_datetime().strftime('%Y-%m-%d'),
            }]

        # update package
        pkg_dict = {
            'name': munged_title,
            'title': title,
            'version': None,
            'url': None,
            'maintainer': None,
            'maintainer_email': None,
            'notes': notes,
            'license_id': self._crown_license_id,
            'tags': [], # post-filled
            'owner_org': publisher_id,
            'resources': resources,
            'extras': extras,
            }

        tags = schema.TagSuggester.suggest_tags(pkg_dict)
        for keyword in item['hub:ipsv'].split(';') + \
                self._split_keywords(item['hub:keywords']) + \
                item['hub:nscl'].split(';'):
            tag = schema.tag_munge(keyword)
            if tag and len(tag) > 1:
                tags.add(tag)
        tags = list(tags)
        tags.sort()
        pkg_dict['tags'] = tags

        themes = categorize_package(pkg_dict)
        log.debug('%s given themes: %r', munged_title, themes)
        if themes:
            pkg_dict['extras'][PRIMARY_THEME] = themes[0]
            if len(themes) == 2:
                pkg_dict['extras'][SECONDARY_THEMES] = '["%s"]' % themes[1]

        return pkg_dict

    @classmethod
    def _split_keywords(cls, keyword_str):
        # some HTML-encoded characters in here, like '&amp;'
        if not '_html_parser' in dir(cls):
            cls._html_parser = HTMLParser.HTMLParser()
        keyword_str = cls._html_parser.unescape(keyword_str)
        # ampersand in particular would be better as a word
        if '&' in keyword_str:
            pos = keyword_str.find('&')
            keyword_str = keyword_str[:pos].strip() + ' and ' + keyword_str[pos+1:].strip()
        # some keyword lists are comma separated and some are semi-colon!
        if ';' in keyword_str:
            # semi-colon separated
            keywords = keyword_str.split(';')
        else:
            # comma separated
            keywords = keyword_str.split(', ')
        # sometimes there is trailing punctuation
        keywords = [keyword.strip(' .,') for keyword in keywords]
        return keywords

    @staticmethod
    def _parse_geographic_coverage(coverage_str):
        geo_coverage_type = schema.GeoCoverageType.get_instance()
        coverage_str = coverage_str.replace('International', 'Global')
        geographic_coverage_db = geo_coverage_type.str_to_db(coverage_str)
        return geographic_coverage_db

    def _source_to_publisher(self, source):
        # wrapper for _source_to_publisher_ so that it can be
        # used by tests without instantiating the class
        return self._source_to_publisher_(source, self._ckanclient)

    @classmethod
    def _source_to_publisher_(cls, source, ckanclient):
        '''
        For a given ONS Source, returns the equivalent DGU publisher ID.
        If it cannot find it, returns None.
        '''
        # map the name
        publisher_name = schema.canonise_organisation_name(source)

        # search for the name in live list of publishers
        # Start with a narrow search
        log.info('Searching for %r', publisher_name)
        result = ckanclient.action('group_search', query=publisher_name, exact=True)
        if not result['count']:
            # Now broaden it out
            result = ckanclient.action('group_search', query=publisher_name, exact=False)

        if not result['count']:
            log.warn('Could not find source in DGU publishers: "%s" (mapped from "%s")', publisher_name, source)
            return None
        if result['count'] > 1:
            log.warn('Multiple publishers matched "%s" (mapped from "%s"): %s', publisher_name, source,
                     [(pub['name'], pub['title']) for pub in result['results']])
        else:
            log.info('..Publisher found: %s', result['results'][0]['name'])

        return result['results'][0]['id']

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
