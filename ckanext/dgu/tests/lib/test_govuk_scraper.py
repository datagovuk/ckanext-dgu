import os
import datetime
from pprint import pprint

from nose.tools import assert_equal
import requests_cache

from ckan import model
from ckan.tests import assert_in
from ckanext.dgu.bin.running_stats import Stats
from ckanext.dgu.lib.govuk_scraper import GovukPublicationScraper
from ckanext.dgu.model import govuk_publications as govuk_pubs_model


class TestScrapeOnly:
    '''This is a test only of the scraping code (not the processing of the
    scraped data or update of the db), using HTML that is real and current. The
    HTML is saved to the repo so it is repeatable, and changes to real HTML can
    be tracked over time.
    To ensure the scrapers are up-to-date with the site, update the HTML in the repo:

    curl https://www.gov.uk/government/publications -o ckanext/dgu/tests/lib/govuk_html/publication_index.html
    curl https://www.gov.uk/government/publications/individualised-learner-record-ilr-check-that-data-is-accurate -o ckanext/dgu/tests/lib/govuk_html/publication_page.html
    curl https://www.gov.uk/government/collections/individualised-learner-record-ilr -o ckanext/dgu/tests/lib/govuk_html/collection_page.html
    curl https://www.gov.uk/government/organisations/skills-funding-agency -o ckanext/dgu/tests/lib/govuk_html/organization_page.html
    curl https://www.gov.uk/government/publications/passport-impact-indicators-csv-version -o ckanext/dgu/tests/lib/govuk_html/publication_csv.html
    curl https://www.gov.uk/government/publications/water-and-sewerage-companies-in-england-environmental-performance-report -o ckanext/dgu/tests/lib/govuk_html/publication_type.html
    curl https://www.gov.uk/government/statistical-data-sets/commodity-prices -o ckanext/dgu/tests/lib/govuk_html/publication_attachments_inline.html
    curl https://www.gov.uk/government/statistical-data-sets/transport-and-disability-tsgb12 -o ckanext/dgu/tests/lib/govuk_html/publication_attachments_unmarked.html
    curl https://www.gov.uk/government/publications/uk-guarantees-scheme-prequalified-projects -o ckanext/dgu/tests/lib/govuk_html/publication_two_organizations.html
    curl https://www.gov.uk/government/publications/nhs-trusts-and-foundation-trusts-in-special-measures-1-year-on -o ckanext/dgu/tests/lib/govuk_html/publication_three_organizations.html
         https://www.gov.uk/government/organisations/the-scottish-government
    curl https://www.gov.uk/government/organisations/the-scottish-government -o ckanext/dgu/tests/lib/govuk_html/organization_external.html
    '''
    @classmethod
    def setup_class(cls):
        GovukPublicationScraper.init()
        #assert_equal.__self__.maxDiff = None

    def setup(self):
        GovukPublicationScraper.reset_stats()

    def test_scrape_publication_index_page(self):
        html = get_html_content('publication_index.html')
        index = GovukPublicationScraper.scrape_publication_index_page(html)
        assert_equal(index['num_results_on_this_page_str'], '95,416')
        assert isinstance(index['publication_basics_elements'], list)
        assert_equal(len(index['publication_basics_elements']), 40)
        assert_equal(index['publication_basics_elements'][0].tag, 'li')

    def test_scrape_publication_basics(self):
        html = get_html_content('publication_index.html')
        index = GovukPublicationScraper.scrape_publication_index_page(html)
        element = index['publication_basics_elements'][0]
        pub = GovukPublicationScraper.scrape_publication_basics(element)
        pprint(pub)
        assert_equal(pub,
            {'govuk_id': '673835',
             'name': 'consultations/gda-of-hitachi-ge-nuclear-energy-ltds-uk-advanced-boiling-water-reactor',
             'title': u'GDA of Hitachi-GE Nuclear Energy Ltd\u2019s UK Advanced Boiling Water Reactor',
             'url': 'https://www.gov.uk/government/consultations/gda-of-hitachi-ge-nuclear-energy-ltds-uk-advanced-boiling-water-reactor'}
            )

    def test_scrape_publication_page(self):
        html = get_html_content('publication_page.html')
        pub = GovukPublicationScraper.scrape_publication_page(html, '/pub_url', 'pub_name')
        # truncate some fields
        pub['attachments'] = [pub['attachments'][0]]
        pub['detail'] = pub['detail'][:100] + '...'
        pprint(pub)
        assert_equal(
{'attachments': [
                  {'filename': 'OneDrive_For_BusinessData_returns_presentation__Dec_Draft__004_.pdf',
                  'format': 'PDF',
                  'govuk_id': '1712098',
                  'title': 'Data returns overview: December 2015.',
                  'url': 'https://www.gov.uk/government/uploads/system/uploads/attachment_data/file/484643/OneDrive_For_BusinessData_returns_presentation__Dec_Draft__004_.pdf'}
],
 'collections': set(['https://www.gov.uk/government/collections/individualised-learner-record-ilr']),
 'detail': u'Funding Information System (FIS)\nFIS is one of a number of software packages freely available to fur...',
 'govuk_id': '659121',
 'last_updated': datetime.datetime(2016, 9, 9, 8, 33, 15),
 'name': 'pub_name',
 'govuk_organizations': ['https://www.gov.uk/government/organisations/skills-funding-agency'],
 'published': datetime.datetime(2014, 2, 25, 13, 50),
 'summary': 'Information about the Funding Information System (FIS), to help further education (FE) providers validate ILR data.',
 'title': 'Individualised Learner Record (ILR): check that data is accurate',
 'type': 'Guidance',
 'url': '/pub_url'
            }, pub)
        assert_equal(fields_not_found(), [])

    def test_scrape_collection_page(self):
        html = get_html_content('collection_page.html')
        collection = GovukPublicationScraper.scrape_collection_page(html, 'https://www.gov.uk/government/collections/collection_url')
        pprint(collection, indent=12)
        assert_equal(collection, {
            'name': 'collection_url',
            'govuk_organization': 'https://www.gov.uk/government/organisations/skills-funding-agency',
            'summary': 'Information to help further education (FE) providers collect, return and check the quality of Individualised Learner Record (ILR) and other learner data.',
            'title': 'Individualised Learner Record (ILR)',
            'url': 'https://www.gov.uk/government/collections/collection_url'
            })
        assert_equal(fields_not_found(), [])

    def test_scrape_organization_page(self):
        html = get_html_content('organization_page.html')
        org = GovukPublicationScraper.scrape_organization_page(html, '/org_url')
        pprint(org, indent=12)
        assert_equal(org, {
           'description': u'We fund skills training for further education (FE) in England. We support over 1,000 colleges, private training organisations, and employers with \xa33.2 billion of funding each year.',
           'govuk_id': '86',
           'name': 'org_url',
           'title': 'Skills Funding Agency',
           'url': '/org_url'
            })
        assert_equal(fields_not_found(), [])

    # Special cases

    def test_publication_with_csv(self):
        html = get_html_content('publication_csv.html')
        pub = GovukPublicationScraper.scrape_publication_page(html, '/pub_url', 'pub_name')
        pprint(pub['attachments'], indent=12)
        assert_equal(pub['attachments'][0]['format'], 'CSV')
        assert_equal(fields_not_found(),
                     ["Updated not found - check: 1 ['pub_name']"])

    def test_publication_type(self):
        html = get_html_content('publication_type.html')
        pub = GovukPublicationScraper.scrape_publication_page(html, '/pub_url', 'pub_name')
        pprint(pub)
        assert_equal(pub['type'], 'Corporate report')
        assert_equal(fields_not_found(), [])

    def test_publication_attachments_inline(self):
        html = get_html_content('publication_attachments_inline.html')
        pub = GovukPublicationScraper.scrape_publication_page(html, '/pub_url', 'pub_name')
        pprint(pub['attachments'])
        assert_equal(pub['attachments'],
[{'filename': 'commodityprices-straights-08may14.xls',
  'format': 'MS Excel Spreadsheet',
  'govuk_id': '663276',
  'title': 'Animal feed (straights) - monthly',
  'url': '/government/uploads/system/uploads/attachment_data/file/308848/commodityprices-straights-08may14.xls'},
 {'filename': 'commodityprices-bananas-01aug14.xls',
  'format': 'MS Excel Spreadsheet',
  'govuk_id': '663277',
  'title': 'Bananas (wholesale prices) - weekly',
  'url': '/government/uploads/system/uploads/attachment_data/file/339879/commodityprices-bananas-01aug14.xls'},
 {'filename': 'commodityprices-tbcomp-30jun14.xls',
  'format': 'MS Excel Spreadsheet',
  'govuk_id': '663278',
  'title': 'Cattle compensation prices - monthly',
  'url': '/government/uploads/system/uploads/attachment_data/file/325412/commodityprices-tbcomp-30jun14.xls'},
 {'filename': 'commodityprices-poultryeggs-31jul14.ods',
  'format': 'ODS',
  'govuk_id': '663279',
  'title': 'Eggs and poultry (wholesale prices) - weekly',
  'url': '/government/uploads/system/uploads/attachment_data/file/338690/commodityprices-poultryeggs-31jul14.ods'},
 {'filename': 'commodityprices-hay-03jul14.xls',
  'format': 'MS Excel Spreadsheet',
  'govuk_id': '663280',
  'title': 'Hay and straw - monthly',
  'url': '/government/uploads/system/uploads/attachment_data/file/326380/commodityprices-hay-03jul14.xls'},
 {'filename': 'commodityprices-livestckmth-08jul14.xls',
  'format': 'MS Excel Spreadsheet',
  'govuk_id': '663281',
  'title': 'Livestock (store stock, England & Wales) - monthly',
  'url': '/government/uploads/system/uploads/attachment_data/file/328333/commodityprices-livestckmth-08jul14.xls'},
 {'filename': 'commodityprices-feed-03jul14.xls',
  'format': 'MS Excel Spreadsheet',
  'govuk_id': '663286',
  'title': 'Other animal feedingstuffs - monthly',
  'url': '/government/uploads/system/uploads/attachment_data/file/326385/commodityprices-feed-03jul14.xls'},
 {'filename': 'commodityprices-wpcereal-31jul14.xls',
  'format': 'MS Excel Spreadsheet',
  'govuk_id': '663282',
  'title': 'Price series for cereals - weekly',
  'url': '/government/uploads/system/uploads/attachment_data/file/339181/commodityprices-wpcereal-31jul14.xls'},
 {'filename': 'commodityprices-wpother-31jul14.xls',
  'format': 'MS Excel Spreadsheet',
  'govuk_id': '663283',
  'title': 'Price series for poultry, eggs, butter, cheese, potatoes and sugar - weekly',
  'url': '/government/uploads/system/uploads/attachment_data/file/339182/commodityprices-wpother-31jul14.xls'},
 {'filename': 'commodityprices-wplivest-31jul14.xls',
  'format': 'MS Excel Spreadsheet',
  'govuk_id': '663284',
  'title': 'Price series for finished cattle, sheep and pigs - weekly',
  'url': '/government/uploads/system/uploads/attachment_data/file/339183/commodityprices-wplivest-31jul14.xls'},
 {'filename': 'commodityprices-cereals-04aug14.xls',
  'format': 'MS Excel Spreadsheet',
  'govuk_id': '663285',
  'title': 'Quantities sold and price of cereals (England & Wales) - weekly',
  'url': '/government/uploads/system/uploads/attachment_data/file/340921/commodityprices-cereals-04aug14.xls'}]
            )
        assert_equal(pub['detail'], 'Prices for selected agricultural and horticultural produce are published on a weekly or monthly basis in the following spreadsheets. The data source depends on the item but includes prices taken from trade journals or other organisations in addition to prices collected by the Department for Environment, Food and Rural Affairs (Defra).\nChanges to the Eggs and Poultry (wholesale) prices from April 2014.  Minor amendments have been made to the categories of data collected. Most noticeable is that frozen chicken now reports imported prices rather than home-grown.\nFor further information please contact:\nDefra Helpline: 03459 33 55 77 (Monday to Friday: 8am to 6pm)')
        assert_equal(fields_not_found(), [])

    def test_publication_attachments_unmarked(self):
        html = get_html_content('publication_attachments_unmarked.html')
        pub = GovukPublicationScraper.scrape_publication_page(html, '/pub_url', 'pub_name')
        pprint(pub['attachments'])
        assert_equal(pub['attachments'][:2], [
{'filename': 'nts0622.xls',
  'format': None,
  'govuk_id': None,
  'title': 'Table TSGB1201 (NTS0622)',
  'url': 'https://www.gov.uk/government/uploads/system/uploads/attachment_data/file/9962/nts0622.xls'},
 {'filename': 'nts0709.xls',
  'format': None,
  'govuk_id': None,
  'title': 'Table TSGB1201 (NTS0622)',
  'url': 'https://www.gov.uk/government/uploads/system/uploads/attachment_data/file/259015/nts0709.xls'},
            ])
        assert_equal(fields_not_found(), ["Updated not found - check: 1 ['pub_name']"])

    def test_publication_two_organizations(self):
        html = get_html_content('publication_two_organizations.html')
        pub = GovukPublicationScraper.scrape_publication_page(html, '/pub_url', 'pub_name')
        pprint(pub)
        assert_equal(pub['govuk_organizations'],
                     ['https://www.gov.uk/government/organisations/infrastructure-uk',
                      'https://www.gov.uk/government/organisations/hm-treasury'])
        assert_equal(fields_not_found(), [])

    def test_publication_three_organizations(self):
        html = get_html_content('publication_three_organizations.html')
        pub = GovukPublicationScraper.scrape_publication_page(html, '/pub_url', 'pub_name')
        pprint(pub)
        assert_equal(pub['govuk_organizations'], [
            'https://www.gov.uk/government/organisations/monitor',
            'https://www.gov.uk/government/organisations/nhs-trust-development-authority',
            'https://www.gov.uk/government/organisations/care-quality-commission'
            ])
        assert_equal(fields_not_found(), ["Updated not found - check: 1 ['pub_name']"])

    def test_organization_external(self):
        html = get_html_content('organization_external.html')
        org = GovukPublicationScraper.scrape_organization_page(html, '/pub_url')
        pprint(org)
        assert_equal(org['description'], 'The devolved government for Scotland is responsible for most of the issues of day-to-day concern to the people of Scotland, including health, education, justice, rural affairs, and transport.')
        assert_equal(fields_not_found(), [])

    # Utilities

    def test_parse_date_at_offset(self):
        assert_equal(GovukPublicationScraper.parse_date('2014-02-25T13:50:00+01:00'),
                datetime.datetime(2014, 2, 25, 12, 50))

    def test_parse_date_at_zero_offset(self):
        assert_equal(GovukPublicationScraper.parse_date('2014-02-25T13:50:00+00:00'),
                datetime.datetime(2014, 2, 25, 13, 50))

    def test_extract_name_from_url(self):
        assert_equal(GovukPublicationScraper.extract_name_from_url(
            'https://www.gov.uk/government/publications/jobseekers-allowance-sanctions-independent-review-government-response'),
            'publications/jobseekers-allowance-sanctions-independent-review-government-response')
        assert_equal(GovukPublicationScraper.extract_name_from_url(
            'https://www.gov.uk/government/organisations/department-for-work-pensions'),
            'department-for-work-pensions')
        assert_equal(GovukPublicationScraper.extract_name_from_url(
            'https://www.gov.uk/government/collections/farm-business-survey'),
            'farm-business-survey')
        assert_equal(GovukPublicationScraper.extract_name_from_url(
            'https://www.gov.uk/government/statistics/clinical-commissioning-group-ccg-prescribing-data-july-to-sept-2014'),
            'statistics/clinical-commissioning-group-ccg-prescribing-data-july-to-sept-2014')

    def test_extract_name_from_url_catchall(self):
        assert_equal(GovukPublicationScraper.extract_name_from_url(
            'https://www.gov.uk/something-new'),
            'www.gov.uk/something-new')

    def test_extract_number_from_full_govuk_id(self):
        assert_equal(GovukPublicationScraper.extract_number_from_full_govuk_id('publication_370126'),
                     '370126')

    def test_sanitize_unicode(self):
        assert_equal(GovukPublicationScraper.sanitize_unicode(u'\u2018single\u2019 \u201cdouble\u201d'), u'\'single\' "double"')
        assert_equal(GovukPublicationScraper.sanitize_unicode(u'Land Registry description en-dash: \u2013'), u'Land Registry description en-dash: -')

    def test_extract_url_object_type(self):
        assert_equal(GovukPublicationScraper.extract_url_object_type(
            'https://www.gov.uk/government/publications/xyz'),
            'publications')
        assert_equal(GovukPublicationScraper.extract_url_object_type(
            'https://www.gov.uk/government/statistics/xyz'),
            'statistics')

    def test_extract_url_object_type_catchall(self):
        assert_equal(GovukPublicationScraper.extract_url_object_type(
            'https://www.gov.uk/no-idea'),
            None)

class TestScrapeAndSave:
    '''Tests the logic of processing the dict it returns and saving it. Assumes
    the scraper itself works.

    Uses a checked-in requests_cache so that it can be run quickly and
    off-line. However it could usefully be updated regularly, by deleting the
    file:

        rm ckanext/dgu/tests/lib/govuk_html/html_cache.TestScrapeAndSave.sqlite

    Try to use test URLs which don't change over time.
    '''
    @classmethod
    def setup_class(cls):
        govuk_pubs_model.init_tables()
        GovukPublicationScraper.init()
        cache_filepath = os.path.join(os.path.dirname(__file__), 'govuk_html',
                                      'html_cache.' + cls.__name__)
        GovukPublicationScraper.requests = requests_cache.CachedSession(
                cache_filepath) # doesn't expire

    def setup(self):
        GovukPublicationScraper.reset_stats()

    def teardown(self):
        govuk_pubs_model.rebuild()
        model.repo.rebuild_db()

    @classmethod
    def teardown_class(cls):
        model.Session.rollback()

    def test_scrape_and_save_collection__create(self):
        # scrape and save
        url = 'https://www.gov.uk/government/collections/spend-over-25000-2013'
        try:
            collection = GovukPublicationScraper.scrape_and_save_collection(url)
        except TypeError, e:
            if 'CaseInsensitiveDict is not a subtype of dict' in str(e):
                assert 0, 'Your version of requests is newer than that which '\
                    'created the requests cache file. See this test class\'s '\
                    'docstring to see how to delete it.'

        # check
        assert_equal(collection.name, 'spend-over-25000-2013')
        assert_equal(collection.url, url)
        assert_equal(collection.title, u'MOJ spend over \xa325,000: 2013')
        assert_equal(collection.summary, u'Guidance on Ministry of Justice and its associated arms length bodies spending over \xa325,000 data 2013.')
        assert_equal(collection.govuk_organization.name, 'ministry-of-justice')
        # check stats for creation
        assert_equal(GovukPublicationScraper.collection_stats,
                {'Created': ['spend-over-25000-2013']})
        assert_equal(GovukPublicationScraper.organization_stats,
                {'Created': ['ministry-of-justice']})
        # check they were created
        model.Session.commit()
        assert govuk_pubs_model.Collection.by_name('spend-over-25000-2013')
        assert govuk_pubs_model.GovukOrganization.by_name('ministry-of-justice')

    def test_scrape_and_save_collection__update(self):
        # create collection and org to start with
        url = 'https://www.gov.uk/government/collections/spend-over-25000-2013'
        GovukPublicationScraper.scrape_and_save_collection(url)
        GovukPublicationScraper.reset_stats()

        # scrape and save
        GovukPublicationScraper.scrape_and_save_collection(url)

        # collection left unchanged
        assert_equal(GovukPublicationScraper.collection_stats,
                {'Unchanged': ['spend-over-25000-2013']})
        # didn't scrape the org at all - already in the db
        assert_equal(GovukPublicationScraper.organization_stats,
                {})

    def test_scrape_and_save_organization__create(self):
        url = 'https://www.gov.uk/government/organisations/cabinet-office'
        org = GovukPublicationScraper.scrape_and_save_organization(url)
        assert_equal(org.govuk_id, '2')
        assert_equal(org.name, 'cabinet-office')
        assert_equal(org.url, url)
        assert_equal(org.title, 'Cabinet Office')
        assert org.description.startswith('We support the Prime Minister'), org.description
        # check they were created
        assert_equal(dict(GovukPublicationScraper.organization_stats),
                     {'Created': ['cabinet-office']})
        # now commit
        model.Session.commit()
        assert govuk_pubs_model.GovukOrganization.by_name('cabinet-office')

    def test_scrape_and_save_organization__update(self):
        # create org to start with
        url = 'https://www.gov.uk/government/organisations/cabinet-office'
        GovukPublicationScraper.scrape_and_save_organization(url)
        GovukPublicationScraper.reset_stats()

        # scrape and save
        GovukPublicationScraper.scrape_and_save_organization(url)

        # organization left unchanged
        assert_equal(dict(GovukPublicationScraper.organization_stats),
                     {'Unchanged': ['cabinet-office']})

    def test_scrape_and_save_publication__create(self):
        # scrape and save
        url = 'https://www.gov.uk/government/publications/hmcts-spend-over-25000-2013'
        changes = GovukPublicationScraper.scrape_and_save_publication(url)

        # check
        assert_equal(changes, {'attachments': 'Add first 4 attachments',
                               'publication': 'Created'})
        pub = govuk_pubs_model.Publication.by_name('publications/hmcts-spend-over-25000-2013')
        assert_equal(pub.govuk_id, '327733')
        assert_equal(pub.name, 'publications/hmcts-spend-over-25000-2013')
        assert_equal(pub.url, url)
        assert_equal(pub.type, 'Transparency data')
        assert_equal(pub.title, u'HMCTS spend over \xa325,000 - 2013')
        assert_equal(pub.summary, u'Details of HMCTS spend over \xa325,000 from Sept to Dec 2013.')
        assert_equal(pub.detail, u'These documents contain details of HMCTS spend over \xa325,000 from Sept to Dec 2013. Previous months\' data are contained within Ministry of Justice data files.')
        assert_equal([o.name for o in pub.govuk_organizations], ['ministry-of-justice'])
        assert_equal([c.name for c in pub.collections], ['spend-over-25000-2013'])
        # check stats for creation
        assert_equal(dict(GovukPublicationScraper.publication_stats),
                {'Created': ['publications/hmcts-spend-over-25000-2013']})
        assert_equal(dict(GovukPublicationScraper.collection_stats),
                {'Created': ['spend-over-25000-2013']})
        assert_equal(dict(GovukPublicationScraper.organization_stats),
                {'Created': ['ministry-of-justice']})
        assert govuk_pubs_model.Collection.by_name('spend-over-25000-2013')
        assert govuk_pubs_model.GovukOrganization.by_name('ministry-of-justice')

    def test_scrape_and_save_publication__update(self):
        # create publication, collection and org to start with
        url = 'https://www.gov.uk/government/publications/hmcts-spend-over-25000-2013'
        GovukPublicationScraper.scrape_and_save_publication(url)
        GovukPublicationScraper.reset_stats()

        # scrape and save
        changes = GovukPublicationScraper.scrape_and_save_publication(url)

        # check
        assert_equal(changes, {})

        # check stats for update
        assert_equal(dict(GovukPublicationScraper.publication_stats),
                {'Unchanged': ['publications/hmcts-spend-over-25000-2013']})
        assert_equal(dict(GovukPublicationScraper.collection_stats),
                {})
        assert_equal(dict(GovukPublicationScraper.organization_stats),
                {})

    def test_scrape_and_save_publications(self):
        # scrape and save
        GovukPublicationScraper.scrape_and_save_publications(
                search_filter='keywords=hmcts-spend-over-25000-2013&from_date=1%2F5%2F14&to_date=2%2F5%2F14', publication_limit=3)

        # check stats for creation
        assert_in('publications/hmcts-spend-over-25000-2013',
                  dict(GovukPublicationScraper.publication_stats)['Created'])
        assert_in('spend-over-25000-2013',
                dict(GovukPublicationScraper.collection_stats)['Created'])
        assert_in('ministry-of-justice',
                dict(GovukPublicationScraper.organization_stats)['Created'])
        pub = govuk_pubs_model.Publication.by_name('publications/hmcts-spend-over-25000-2013')
        assert_equal(pub.govuk_id, '327733')
        assert govuk_pubs_model.Collection.by_name('spend-over-25000-2013')
        assert govuk_pubs_model.GovukOrganization.by_name('ministry-of-justice')

def get_html_content(test_filename):
    test_filepath = os.path.join(os.path.dirname(__file__), 'govuk_html', test_filename)
    with open(test_filepath) as f:
        html = f.read()
    # quick checks in case urls have changed
    assert 'Page not found' not in html
    assert 'edirect' not in html
    assert 'Moved Permanently' not in html
    return html

def fields_not_found():
    not_found = []
    for category in GovukPublicationScraper.field_stats:
        if 'not found' in category:
            not_found.append('%s: %s' % (category, GovukPublicationScraper.field_stats.report_value(category)[0]))
    return not_found
