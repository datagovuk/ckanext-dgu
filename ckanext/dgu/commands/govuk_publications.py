import sys

import ckan.plugins as p


class GovukPublicationsCommand(p.toolkit.CkanCommand):
    '''
    Manage the mirror of gov.uk publications.

    The available commands are:

        initdb - Initialize the database tables for the gov.uk publication data

        list - Lists the data

        scrape - Scrape gov.uk

    e.g.

      List all reports:
      $ paster govuk_publications scrape -c development.ini

    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 2
    min_args = None

    def __init__(self, name):
        super(GovukPublicationsCommand, self).__init__(name)

    def command(self):
        import logging

        self._load_config()
        self.log = logging.getLogger('ckan.lib.cli')

        if not self.args:
            self.log.error('No arguments supplied and they are required')
            sys.stderr.write(self.usage)
            return
        else:
            cmd = self.args[0]
            if cmd == 'initdb':
                self._initdb()
            elif cmd == 'list':
                self._list()
            elif cmd == 'scrape':
                scrape()

    def _initdb(self):
        from ckanext.dgu.model import govuk_publications as govuk_pubs_model
        govuk_pubs_model.init_tables()
        self.log.info('Gov.uk Publications tables are setup')


    def _list(self):
        from ckanext.report.report_registry import ReportRegistry
        registry = ReportRegistry.instance()
        for plugin, report_name, report_title in registry.get_names():
            report = registry.get_report(report_name)
            date = report.get_cached_date()
            print '%s: %s %s' % (plugin, report_name,
                  date.strftime('%d/%m/%Y %H:%M') if date else '(not cached)')

def scrape():
    import lxml.html
    import itertools
    import requests
    import requests_cache
    from ckanext.dgu.bin.running_stats import Stats
    from urlparse import urljoin
    from ckanext.dgu.model import govuk_publications as govuk_pubs_model
    from ckan import model

    model.Session.query(govuk_pubs_model.Publication).all()


    requests_cache.install_cache('govuk_pubs', expire_after=60*60*24) # 1 day

    # keep track of each publication found
    publication_stats = Stats()

    # keep track of fields found, to help spot if the scraping of it breaks
    field_stats = Stats()

    for page_index in itertools.count(start=1):
        url = 'https://www.gov.uk/government/publications?page=%s' % page_index
        print url
        doc = lxml.html.fromstring(requests.get(url).content)
        # check to see if we have done all the pages
        if doc.xpath('//span[@class="count"]/text()')[0] == '0':
            if page_index < 3:
                log.error('Not enough pages of publications found - %s', page_index)
            break

        for row in doc.xpath('//li[@class="document-row"]'):
            # Scrape the publication
            pub = {}
            pub['title'] = row.xpath('./h3/a/text()')[0]
            pub['url'] = urljoin('https://www.gov.uk', row.xpath('./h3/a/@href')[0])
            pub_name = pub['url'].split('/')[-1]
            pub['name'] = pub_name
            subdoc = lxml.html.fromstring(requests.get(pub['url']).content)
            import pdb; pdb.set_trace()
            try:
                pub['organisation'] = subdoc.xpath('//span[@class="organisation lead"]/a/text()')[0]
                field_stats.add('Organization found', pub_name)
            except IndexError:
                field_stats.add('Organization not found - ok', pub_name)
                pub['organisation'] = ''

            try:
                pub['type'] = subdoc.xpath('//div[@class="inner-heading"]/p[@class="type"]/text()')[0]
                field_stats.add('Type found', pub_name)
            except IndexError:
                field_stats.add('Type not found - check', pub_name)
                pub['type'] = ''

            try:
                pub['summary'] = subdoc.xpath('//div[@class="summary"]/p/text()')[0]
                field_stats.add('Summary found', pub_name)
            except IndexError:
                field_stats.add('Summary not found - check', pub_name)
                pub['summary'] = ''

            try:
                pub['published'] = subdoc.xpath('//dt[text()="Published:"]/following-sibling::dd/abbr/@title')[0]
                field_stats.add('Publish date found', pub_name)
            except IndexError:
                field_stats.add('Publish date not found - check', pub_name)
                pub['published'] = ''

            try:
                pub['updated'] = subdoc.xpath('//dt[text()="Updated:"]/following-sibling::dd/abbr/@title')[0]
                field_stats.add('Updated found', pub_name)
            except IndexError:
                field_stats.add('Updated not found - check', pub_name)
                pub['updated'] = ''

            pub['attachments'] = []
            # Embedded attachment
            # e.g. https://www.gov.uk/government/publications/tuberculosis-test-for-a-uk-visa-clinics-in-brunei
            embedded_attachments = []
            for attachment in subdoc.xpath('//section[@class = "attachment embedded"]'):
                attach = {}
                attach['title'] = attachment.xpath('.//h2[@class="title"]/text()|.//h2[@class="title"]/a/text()')[0]
                attach['url'] = urljoin('https://www.gov.uk', attachment.xpath('.//h2[@class="title"]/a/@href|.//span[@class="download"]/a/@href')[0])
                attach['filename'] = attach['url'].split('/')[-1]
                embedded_attachments.append(attach)
            if embedded_attachments:
                field_stats.add('Attachments (embedded) found', pub_name)
            # Inline attachment
            # e.g.
            inline_attachments = []
            for attachment in subdoc.xpath('//span[@class = "attachment inline"]'):
                attach = {}
                attach['title'] = attachment.xpath('./a/text()')[0]
                attach['url'] = attachment.xpath('./a/@href')[0]
                attach['filename'] = attach['url'].split('/')[-1]
                inline_attachments.append(attach)
            if inline_attachments:
                field_stats.add('Attachments (inline) found', pub_name)
            pub['attachments'].append(embedded_attachments + inline_attachments)
            if not pub['attachments']:
                field_stats.add('Attachments not found', pub_name)

            # Deal with external? Maybe not?
            # Deal with multi lingual pages
            if len(pub['attachments']) == 0:
                pass #print pub['title'], pub['url']

            if 'consultations' in pub['url'] and len(pub['attachments']) > 0:
                pass #print 'XXX', pub['url']
            publications.append(pub)

            # Scrape the publications' collections

            pub['collections'] = set()
            for collection_url in subdoc.xpath('//dd[@class="document-document-collection"]/a/@href'):
                if not collection_url.startswith('/government/collections'):
                    print field_stats.add('Collection with unexpected url - error',
                                          '%s %s' % (pub_name, collection_url))
                    continue
                collection_url = urljoin('https://www.gov.uk', collection_url)

                if collection_url not in [x['url'] for x in collections]:
                    try:
                        collection_name = scrape_collection(collection_url, field_stats)
                    except GotRedirectedError:
                        print field_stats.add('Collection page redirected - error',
                                              '%s %s' % (pub_name, collection_url))
                        continue
                pub['collections'].add(collection_name)

class GotRedirectedError(Exception):
    pass

def scrape_collection(collection_url, field_stats):
    collection = {}
    r = requests.get(collection_url)
    if not r.url.startswith('https://www.gov.uk/government/collections/'):
        raise GotRedirectedError()
    if r.url != collection_url:
        raise GotRedirectedError()
    doc = lxml.html.fromstring(r.content)
    collection['url'] = collection_url
    collection_name = collection_url.split('/')[-1]
    #collection['title'] = doc.xpath("//div[@class='inner-heading']/h1/text()")[0]
    try:
        collection['title'] = doc.xpath('//header//h1/text()')[0]
        field_stats.add('Collection title found', collection_name)
    except IndexError:
        field_stats.add('Collection title not found - error', collection_name)
    try:
        collection['summary'] = doc.xpath("//div[@class='block summary']//p/text()")[0]
        field_stats.add('Collection summary found', collection_name)
    except IndexError:
        field_stats.add('Collection summary not found - check', collection_name)
        collection['summary'] = ''
    try:
        # This should probably be a many to many - see https://www.gov.uk/government/publications/uk-guarantees-scheme-prequalified-projects
        collection['organisation'] = subdoc.xpath("//span[@class='organisation lead']/a/text()")[0]
        field_stats.add('Collection organisation found', collection_name)
    except:
        field_stats.add('Collection organisation not found - error', collection_name)
        collection['organisation'] = ""
    collections.append(collection)
    return collection_name
