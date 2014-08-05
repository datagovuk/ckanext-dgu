import re
import dateutil
import itertools
import os.path

import requests_cache
import lxml.html
from urlparse import urljoin

from ckanext.dgu.bin.running_stats import Stats
from ckanext.dgu.model import govuk_publications as govuk_pubs_model
from ckan import model

log = __import__('logging').getLogger(__name__)

# Note:
# * "scrape_*" methods contain all the code that actually scrapes HTML.
# These don't touch the database, so that they are easily testable, and fixed
# when the HTML changes.
# * "scrape_and_save" methods call out to the scraper methods and save to the db.

class GovukPublicationScraper(object):
    @classmethod
    def init(cls):
        if 'requests' not in dir(cls):
            cls.requests = requests_cache.CachedSession(
                'govuk_pubs', expire_after=60*60*24)  # 1 day
            # keep track of each publication found
            cls.publication_stats = Stats()

            # keep track of fields found, to help spot if the scraping of it breaks
            cls.field_stats = Stats()

    @classmethod
    def scrape_and_save_publications(cls, page=None):
        cls.init()

        pages = itertools.count(start=1) if page is None else [page]
        for page_index in pages:
            # Scrape the index of publications
            url = 'https://www.gov.uk/government/publications?page=%s' % page_index
            print url
            num_results_on_this_page_str, publication_basics_elements = \
                cls.scrape_publication_index_page(cls.requests.get(url).content)

            # check to see if we have done all the pages
            if num_results_on_this_page_str == '0':
                if page_index < 3:
                    log.error('Not enough pages of publications found - %s', page_index)
                break

            # This webpage has the 'basic' fields for each publication
            for publication_basics_element in publication_basics_elements:
                # scrape
                pub_basic = cls.scrape_publication_basics(publication_basics_element)
                try:
                    changes = cls.scrape_and_save_publication(pub_basic['url'], pub_basic['name'])
                except DuplicateNameError, e:
                    cls.publication_stats.add('Duplicate name for %s %s' %
                                              (e.object_type, e.field),
                                              '%s %s' % (e.message, pub_basic['name']))
                else:
                    if changes.get('publication') == 'Created':
                        cls.publication_stats.add('Creation', pub_basic['name'])
                    elif changes:
                        cls.publication_stats.add('Updated', pub_basic['name'])
                    else:
                        cls.publication_stats.add('Unchanged', pub_basic['name'])
        print '\nPublications:\n', cls.publication_stats
        print '\nFields:\n', cls.field_stats

    @classmethod
    def scrape_publication_index_page(cls, pub_index_content):
        doc = lxml.html.fromstring(pub_index_content)
        num_results_on_this_page_str = doc.xpath('//span[@class="count"]/text()')[0]
        publication_basics_elements = doc.xpath('//li[@class="document-row"]')
        return num_results_on_this_page_str, publication_basics_elements

    @classmethod
    def scrape_publication_basics(cls, publication_basics_element):
        row = publication_basics_element
        # Scrape identifying bits of the publication
        pub = {}
        pub['title'] = row.xpath('./h3/a/text()')[0]
        pub['url'] = cls.add_gov_uk_domain(row.xpath('./h3/a/@href')[0])
        pub['name'] = cls.extract_name_from_url(pub['url'])
        pub['govuk_id'] = cls.extract_number_from_full_govuk_id(row.xpath('./@id')[0]) # e.g. publication_370126
        # public_timestamp is either created or last_updated - it doesn't say,
        # so ignore it
        return pub

    @classmethod
    def scrape_and_save_publication(cls, pub_url, pub_name=None):
        print pub_url
        if pub_name is None:
            pub_name = cls.extract_name_from_url(pub_url)

        # Scrape the publication page itself
        pub_scraped = cls.scrape_publication_page(cls.requests.get(pub_url).content, pub_url, pub_name)

        # Write the core fields to new or existing object
        core_fields = set(pub_scraped) - set(('attachments', 'govuk_organization', 'extra_govuk_organization', 'collections'))
        changes = {}
        pub = model.Session.query(govuk_pubs_model.Publication) \
                   .filter_by(govuk_id=pub_scraped['govuk_id']) \
                   .first()
        if pub:
            # Update it
            def update_pub(field, value):
                existing_value = getattr(pub, field)
                if existing_value != value:
                    changes[field] = '%r->%r' % (existing_value, value)
                    setattr(pub, field, value)
            for field in core_fields:
                update_pub(field, pub_scraped[field])
        else:
            # just check there's not one called the same
            pub_same_name = model.Session.query(govuk_pubs_model.Publication) \
                                 .filter_by(name=pub_scraped['name']) \
                                 .first()
            if pub_same_name:
                raise DuplicateNameError('publication', 'name', 'Conflicting name with existing %r and scraped %r' % (pub_same_name, pub_scraped))
            # create it
            pub = govuk_pubs_model.Publication(**dict((field, pub_scraped[field])
                                                      for field in core_fields))
            model.Session.add(pub)
            changes['publication'] = 'Created'
            def update_pub(field, value):
                setattr(pub, field, value)

        # Attachments
        cls.update_publication_attachments(pub, pub_scraped['attachments'], changes)

        # Organization
        for org_field in ('govuk_organization', 'extra_govuk_organization'):
            if pub_scraped[org_field]:
                org = model.Session.query(govuk_pubs_model.GovukOrganization) \
                           .filter_by(url=pub_scraped[org_field]) \
                           .first()
                if not org:
                    # create it
                    try:
                        org = cls.scrape_and_save_organization(pub_scraped[org_field])
                    except GotRedirectedError:
                        print cls.field_stats.add('Organization page redirected - error',
                                           '%s %s' % (pub_name, pub_scraped[org_field]))
                        return
            else:
                org = None
            update_pub(org_field, org)

        # Collections
        collections = []
        for collection_url in pub_scraped['collections']:
            collection = model.Session.query(govuk_pubs_model.Collection) \
                              .filter_by(url=collection_url) \
                              .first()
            if not collection:
                # create it
                try:
                    collection = cls.scrape_and_save_collection(collection_url)
                except GotRedirectedError:
                    print cls.field_stats.add('Collection page redirected - error',
                                        '%s %s' % (pub_name, collection_url))
                    continue
            # TODO at some point, update collections too?
            collections.append(collection)
        update_pub('collections', collections)

        if changes:
            print 'PUB %s scraped with changes: %r' % (pub_name, changes)
        else:
            print 'PUB %s scraped with no change' % pub_name
        if changes:
            model.Session.commit()
            model.Session.remove()
        return changes

    @classmethod
    def scrape_publication_page(cls, publication_page_content, pub_url, pub_name):
        pub_doc = lxml.html.fromstring(publication_page_content)
        pub = {'url': pub_url,
               'name': pub_name}
        is_external = bool(pub_doc.xpath('//a[@rel="external"]'))

        try:
            pub['title'] = pub_doc.xpath('//main//article//h1/text()')[0]
            cls.field_stats.add('Title found', pub_name)
        except IndexError:
            cls.field_stats.add('Title not found - error', pub_name)
            pub['title'] = None

        try:
            pub['govuk_id'] = cls.extract_number_from_full_govuk_id(pub_doc.xpath('//main//article/@id')[0])
            cls.field_stats.add('Gov.uk ID found', pub_name)
        except IndexError:
            cls.field_stats.add('Gov.uk ID not found - error', pub_name)
            pub['govuk_id'] = None

        orgs = pub_doc.xpath('//dt[text()="From:"]/following-sibling::dd[@class="from"]/a/@href')
        if len(orgs) == 1:
            pub['govuk_organization'] = cls.add_gov_uk_domain(orgs[0])
            pub['extra_govuk_organization'] = None
            cls.field_stats.add('Organization found', pub_name)
        elif len(orgs) > 1:
            pub['govuk_organization'] = cls.add_gov_uk_domain(orgs[0])
            pub['extra_govuk_organization'] = cls.add_gov_uk_domain(orgs[1])
            if len(orgs) == 2:
                cls.field_stats.add('Organizations (2) found', pub_name)
            else:
                cls.field_stats.add('Organizations more than 2 found (%s) - error', '%s %s' % (pub_name, len(orgs)))
        else:
            cls.field_stats.add('Organization not found - error', pub_name)
            pub['govuk_organization'] = None
            pub['extra_govuk_organization'] = None

        try:
            pub['type'] = pub_doc.xpath('//div[@class="inner-heading"]/p[@class="type"]/text()')[0]
            cls.field_stats.add('Type found', pub_name)
        except IndexError:
            cls.field_stats.add('Type not found - check', pub_name)
            pub['type'] = ''
        else:
            if pub['type'].startswith(' - '):
                pub['type'] = re.sub('^ \- ', '', pub['type']).capitalize()

        try:
            pub['summary'] = cls.sanitize_unicode(pub_doc.xpath('//div[@class="summary"]/p/text()')[0].strip())
            cls.field_stats.add('Summary found', pub_name)
        except IndexError:
            try:
                pub['summary'] = cls.sanitize_unicode(pub_doc.xpath('//div[@class="consultation-summary"]//p/text()')[0].strip())
                cls.field_stats.add('Summary found (method 2)', pub_name)
            except IndexError:
                cls.field_stats.add('Summary not found - check', pub_name)
                pub['summary'] = ''

        detail_paras = pub_doc.xpath('//section[@id="details"]//div[@class="body"]//text()') \
            or pub_doc.xpath('//section[//text()="Consultation description"]//div[@class="content"]//text()') \
            or pub_doc.xpath('//div[@class="govspeak"]//p/text()')
        if detail_paras:
            cls.field_stats.add('Details found', pub_name)
            pub['detail'] = cls.sanitize_unicode('\n'.join(detail_para.strip() for detail_para in detail_paras if detail_para.strip()))
        else:
            cls.field_stats.add('Detail not found - check', pub_name)
            pub['detail'] = ''

        try:
            pub['published'] = pub_doc.xpath('//dt[text()="Published:"]/following-sibling::dd/abbr/@title')[0]
            cls.field_stats.add('Publish date found', pub_name)
        except IndexError:
            cls.field_stats.add('Publish date not found - error', pub_name)
            pub['published'] = ''
        else:
            pub['published'] = cls.parse_date(pub['published'])

        try:
            pub['last_updated'] = pub_doc.xpath('//dt[text()="Updated:"]/following-sibling::dd/abbr/@title')[0] or None
            cls.field_stats.add('Updated found', pub_name)
        except IndexError:
            cls.field_stats.add('Updated not found - check', pub_name)
            pub['last_updated'] = None
        else:
            if pub['last_updated']:
                pub['last_updated'] = cls.parse_date(pub['last_updated'])

        pub['attachments'] = []
        # Embedded attachment
        # e.g. https://www.gov.uk/government/publications/tuberculosis-test-for-a-uk-visa-clinics-in-brunei
        embedded_attachments = []
        for attachment in pub_doc.xpath('//section[@class = "attachment embedded"]'):
            attach = {}
            attach['govuk_id'] = cls.extract_number_from_full_govuk_id(attachment.xpath('@id')[0])
            attach['title'] = attachment.xpath('.//h2[@class="title"]/text()|.//h2[@class="title"]/a/text()')[0]
            attach['url'] = cls.add_gov_uk_domain(attachment.xpath('.//h2[@class="title"]/a/@href|.//span[@class="download"]/a/@href')[0])
            attach['filename'] = attach['url'].split('/')[-1]
            try:
                attach['format'] = attachment.xpath('.//*[@class="metadata"]//*[@class="type"]//text()')[0]
                cls.field_stats.add('Format found (method 1)', pub_name)
            except IndexError:
                try:
                    attach['format'] = attachment.xpath('.//*[@class="metadata"]/span[@class="download"]//strong/text()')[0].split('Download ')[-1]
                    cls.field_stats.add('Format found (method 2)', pub_name)
                except IndexError:
                    cls.field_stats.add('Format not found - check', pub_name)
                    pub['format'] = None

            embedded_attachments.append(attach)
        if embedded_attachments:
            cls.field_stats.add('Attachments (embedded) found', pub_name)
        # Inline attachment
        # e.g. https://www.gov.uk/government/statistical-data-sets/commodity-prices
        inline_attachments = []
        for attachment in pub_doc.xpath('//span[@class = "attachment inline"]'):
            attach = {}
            attach['govuk_id'] = cls.extract_number_from_full_govuk_id(attachment.xpath('./@id')[0])
            attach['title'] = attachment.xpath('./a/text()')[0]
            attach['url'] = attachment.xpath('./a/@href')[0]
            attach['filename'] = attach['url'].split('/')[-1]
            attach['format'] = attachment.xpath('./span[@class="type"]//text()')[0]
            inline_attachments.append(attach)
        if inline_attachments:
            cls.field_stats.add('Attachments (inline) found', pub_name)
        pub['attachments'].extend(embedded_attachments + inline_attachments)
        if not pub['attachments']:
            if is_external:
                cls.field_stats.add('Publication external so no attachments', pub_name)
            else:
                cls.field_stats.add('Attachments not found - check', pub_name)

        # Deal with multi lingual pages
        if len(pub['attachments']) == 0:
            pass #print pub['title'], pub['url']

        if 'consultations' in pub['url'] and len(pub['attachments']) > 0:
            pass #print 'XXX', pub['url']

        # Scrape the publications' collections

        pub['collections'] = set()
        for collection_url in pub_doc.xpath('//div[@class="links"]//dt[text()="Part of:"]/following-sibling::dd/a/@href'):
            if not collection_url.startswith('/government/collections'):
                print cls.field_stats.add('Ignoring "Part of" type %s' % os.path.dirname(collection_url),
                                          '%s %s' % (pub_name, collection_url))
                continue
            collection_url = cls.add_gov_uk_domain(collection_url)
            pub['collections'].add(collection_url)
        return pub

    @classmethod
    def update_publication_attachments(cls, pub, attachments, changes):
        '''Makes pub.attachments equal to the attachments listed in
        `attachments` which is a list of dicts. Records any changes in
        `changes['attachments']`.
        '''
        atts_before = pub.attachments
        atts_after = {}
        for i, att in enumerate(attachments):
            att['position'] = i
            att['publication'] = pub
            atts_after[att['govuk_id']] = att

        # Simple cases
        if not atts_before:
            if not atts_after:
                # nothing to do
                return
            # first add of attachments
            pub.attachments = [govuk_pubs_model.Attachment(**att) for att in atts_after.values()]
            model.Session.add_all(pub.attachments)
            changes['attachments'] = 'Add first %i attachments' % len(atts_after)
            return
        if not atts_after:
            # delete all attachments
            for att in atts_before:
                model.Session.delete(att)
            changes['attachments'] = 'Delete all %i attachments' % len(atts_before)
            return

        # Complicated case
        change_list = []
        keys = set(atts_after.itervalues().next().keys()) - set(['publication']) # includes position but not publication
        def attribute_differences(attribute_obj, attribute_dict):
            differences = []
            for key in keys:
                value_obj, value_dict = getattr(attribute_obj, key), attribute_dict[key]
                if value_obj != value_dict:
                     differences.append((key, value_obj, value_dict))
            return differences
        for att in atts_before:
            att_after = atts_after.get(att.govuk_id)
            if att_after:
                # attachment is kept - check for changes
                diffs = attribute_differences(att, att_after)
                if diffs:
                    diffs_str = ','.join(diff['0'] for diff in diffs)
                    change_list.append('%s:%s' % (atts_before['govuk_id'], diffs_str))
                    for key, value_before, value_after in diffs:
                        setattr(att, key, value_after)
            else:
                # attachment is no more
                model.Session.delete(att)
        # new attachments
        att_keys_to_add = set(atts_after.keys()) - set([att.govuk_id for att in atts_before])
        if att_keys_to_add:
            new_atts = [govuk_pubs_model.Attachment(**atts_after[att_key])
                        for att_key in att_keys_to_add]
            model.Session.add_all(new_atts)
            change_list.append('Add %i attachments' % len(att_keys_to_add))
        if change_list:
            changes['attachments'] = '; '.join(change_list)

    @classmethod
    def scrape_and_save_collection(cls, collection_url):
        collection = {}
        r = cls.requests.get(collection_url)
        if not r.url.startswith('https://www.gov.uk/government/collections/'):
            raise GotRedirectedError()
        if r.url != collection_url:
            raise GotRedirectedError()
        collection_scraped = cls.scrape_collection_page(r.content, collection_url)

        changes = {}
        collection = model.Session.query(govuk_pubs_model.Collection) \
                          .filter_by(url=collection_scraped['url']) \
                          .first()
        if collection:
            # update it
            def update_collection(field, value):
                existing_value = getattr(collection, field)
                if existing_value != value:
                    changes[field] = '%r->%r' % (existing_value, value)
                    setattr(collection, field, value)
            for field in collection_scraped:
                update_collection(field, collection_scraped[field])
            if changes:
                model.Session.commit()
        else:
            # just check there's not one called the same
            collection_same_name = model.Session.query(govuk_pubs_model.Collection) \
                                        .filter_by(name=collection_scraped['name']) \
                                        .first()
            if collection_same_name:
                raise DuplicateNameError('collection', 'name', 'Conflicting name with existing %r and scraped %r' % (collection_same_name, collection_scraped))
            collection_same_title = model.Session.query(govuk_pubs_model.Collection) \
                                         .filter_by(title=collection_scraped['title']) \
                                         .first()
            if collection_same_title:
                raise DuplicateNameError('collection', 'title', 'Conflicting title with existing %r and scraped %r' % (collection_same_title, collection_scraped))

            # create it (without the organization for now)
            collection_scraped_excluding_org = \
                dict((k, v) for k, v in collection_scraped.items()
                     if k != 'govuk_organization')
            collection = govuk_pubs_model.Collection(**collection_scraped_excluding_org)
            model.Session.add(collection)
            model.Session.flush()  # to get an collection.id. It will get committed with the publication
            def update_collection(field, value):
                setattr(collection, field, value)

        # Organization
        if not collection.govuk_organization or \
                collection.govuk_organization.url != collection_scraped['govuk_organization']:
            org = model.Session.query(govuk_pubs_model.GovukOrganization) \
                       .filter_by(url=collection_scraped['govuk_organization']) \
                       .first()
            if not org:
                # create it
                try:
                    org = cls.scrape_and_save_organization(collection_scraped['govuk_organization'])
                except GotRedirectedError:
                    print cls.field_stats.add('Organization page redirected - error',
                                            '%s %s' % (collection_scraped['name'], collection_scraped['govuk_organization']))
                    return
            update_collection('govuk_organization', org)

        return collection

    @classmethod
    def scrape_collection_page(cls, collection_page_content, collection_url):
        doc = lxml.html.fromstring(collection_page_content)
        collection = {}
        collection['url'] = collection_url
        collection_name = cls.extract_name_from_url(collection_url)
        collection['name'] = collection_name
        #collection['title'] = doc.xpath("//div[@class='inner-heading']/h1/text()")[0]
        try:
            collection['title'] = doc.xpath('//header//h1/text()')[0]
            cls.field_stats.add('Collection title found', collection_name)
        except IndexError:
            cls.field_stats.add('Collection title not found - error', collection_name)

        try:
            collection['summary'] = cls.sanitize_unicode(doc.xpath("//div[@class='block summary']//p/text()")[0])
            cls.field_stats.add('Collection summary found', collection_name)
        except IndexError:
            cls.field_stats.add('Collection summary not found - check', collection_name)
            collection['summary'] = None

        try:
            # URL
            collection['govuk_organization'] = cls.add_gov_uk_domain(doc.xpath('//dt[text()="From:"]/following-sibling::dd/a/@href')[0])
            cls.field_stats.add('Collection organization found', collection_name)
        except IndexError:
            cls.field_stats.add('Collection organization not found - check', collection_name)
            collection['govuk_organization'] = None
        return collection

    @classmethod
    def scrape_and_save_organization(cls, org_url):
        # e.g. https://www.gov.uk/government/organisations/skills-funding-agency
        if org_url.startswith('/government/organisations'):
            org_url = cls.add_gov_uk_domain(org_url)
        r = cls.requests.get(org_url)
        if not r.url.startswith('https://www.gov.uk/government/organisations/'):
            raise GotRedirectedError()
        if r.url != org_url:
            raise GotRedirectedError()

        org_scraped = cls.scrape_organization_page(r.content, org_url)
        print 'ORG scraped %r' % org_scraped

        changes = {}
        org = model.Session.query(govuk_pubs_model.GovukOrganization) \
                   .filter_by(govuk_id=org_scraped['govuk_id']) \
                   .first()
        if org:
            # update it
            def update_org(field, value):
                existing_value = getattr(org, field)
                if existing_value != value:
                    changes[field] = '%r->%r' % (existing_value, value)
                    setattr(org, field, value)
            for field in org_scraped:
                update_org(field, org_scraped[field])
            if changes:
                model.Session.commit()
        else:
            # just check there's not one called the same
            org_same_name = model.Session.query(govuk_pubs_model.GovukOrganization) \
                                 .filter_by(name=org_scraped['name']) \
                                 .first()
            if org_same_name:
                raise DuplicateNameError('organization', 'name', 'Conflicting name with existing %r and scraped %r' % (org_same_name, org_scraped))
            org_same_title = model.Session.query(govuk_pubs_model.GovukOrganization) \
                                  .filter_by(title=org_scraped['title']) \
                                  .first()
            if org_same_title:
                raise DuplicateNameError('organization', 'title', 'Conflicting title with existing %r and scraped %r' % (org_same_title, org_scraped))

            # create it
            org = govuk_pubs_model.GovukOrganization(**org_scraped)
            model.Session.add(org)
            model.Session.flush()  # to get an org.id. It will get committed with the publication
        return org

    @classmethod
    def scrape_organization_page(cls, page_content, org_url):
        doc = lxml.html.fromstring(page_content)
        org_dict = {}
        org_dict['url'] = org_url
        org_name = org_url.split('/')[-1]
        org_dict['name'] = org_name
        full_govuk_id = doc.xpath('//main//div[contains(concat(" ", @class, " "), " organisation ")]/@id')[0]
        org_dict['govuk_id'] = cls.extract_number_from_full_govuk_id(full_govuk_id)
        try:
            org_dict['title'] = doc.xpath('//title/text()')[0].split(' - ')[0]
            cls.field_stats.add('Organization title found', org_name)
        except IndexError:
            org_dict['title'] = None
            cls.field_stats.add('Organization title not found - error', org_name)
        try:
            org_dict['description'] = cls.sanitize_unicode(doc.xpath('//section[@id="what-we-do"]//div[@class="overview"]//p[@class="description"]//text()')[0].strip())
            cls.field_stats.add('Organization description found', org_name)
        except IndexError:
            try:
                org_dict['description'] = cls.sanitize_unicode(doc.xpath('//div[@class="description"]//div[@class="govspeak"]//p/text()')[0].strip())
                cls.field_stats.add('Organization description found (external org)', org_name)
            except IndexError:
                org_dict['description'] = None
                cls.field_stats.add('Organization description not found - error', org_name)
        return org_dict

    @classmethod
    def parse_date(cls, date_string):
        # e.g. '2014-08-01T11:24:11+01:00'
        assert isinstance(date_string, basestring)
        date = dateutil.parser.parse(date_string)
        # postgres can only store in utc.
        date_utc = date.replace(tzinfo=None) - date.utcoffset()
        return date_utc

    @classmethod
    def extract_number_from_full_govuk_id(cls, full_govuk_id):
        # e.g. publication_370126
        if '_govuk_extract_re' not in dir(cls):
            cls._govuk_extract_re = re.compile('^\w+_(\d+)$')
        match = cls._govuk_extract_re.search(full_govuk_id)
        if match.groups():
            return int(match.groups()[0])

    @classmethod
    def add_gov_uk_domain(cls, path):
        return urljoin('https://www.gov.uk', path)

    @classmethod
    def extract_name_from_url(cls, url):
        '''Works for publication, organisation, collection etc.  but
        publications might have overlapping namespaces, so it is not
        reversible.

        publication url prefixes:
        https://www.gov.uk/government/publications/
        https://www.gov.uk/government/statistics/
        https://www.gov.uk/government/consultations/
        '''
        return url.split('/')[-1]

    @classmethod
    def sanitize_unicode(cls, unicode_text):
        '''Gets rid of unnecessary unicode, like curly quotes. It is a pain
        printing to the console etc.'''
        if '_single_quote_re' not in dir(cls):
            cls._single_quote_re = re.compile(u'[\u2018\u2019]')
            cls._double_quote_re = re.compile(u'[\u201c\u201d]')
            cls._dash_re = re.compile(u'\u2013')
        unicode_text = cls._single_quote_re.sub('\'', unicode_text)
        unicode_text = cls._double_quote_re.sub('"', unicode_text)
        unicode_text = cls._dash_re.sub('-', unicode_text)
        return unicode_text

class GotRedirectedError(Exception):
    pass


class DuplicateNameError(Exception):
    def __init__(self, object_type, field, msg):
        self.object_type = object_type
        self.field = field
        super(DuplicateNameError, self).__init__(msg)
