import os
import datetime
from dateutil.tz import tzoffset, tzlocal
from pprint import pprint

from nose.tools import assert_equal

from ckanext.dgu.bin.running_stats import Stats
from ckanext.dgu.lib.govuk_publications import GovukPublicationScraper


class TestScrapeRealPages:
    '''This is a test that the scrapers work on HTML that is real and current. The HTML is saved to the repo so it is repeatable, and changes to real HTML can be tracked over time.
    To ensure the scrapers are up-to-date with the site, update the HTML in the repo:

    curl https://www.gov.uk/government/publications -o ckanext/dgu/tests/lib/govuk_html/publication_index.html
    curl https://www.gov.uk/government/publications/individualised-learner-record-ilr-check-that-data-is-accurate -o ckanext/dgu/tests/lib/govuk_html/publication_page.html
    curl https://www.gov.uk/government/collections/individualised-learner-record-ilr -o ckanext/dgu/tests/lib/govuk_html/collection_page.html
    curl https://www.gov.uk/government/organisations/skills-funding-agency -o ckanext/dgu/tests/lib/govuk_html/organization_page.html
    '''
    @classmethod
    def setup_class(cls):
        GovukPublicationScraper.init()
        #assert_equal.__self__.maxDiff = None

    def test_scrape_publication_index_page(self):
        html = get_html_content('publication_index.html')
        index = GovukPublicationScraper.scrape_publication_index_page(html)
        assert_equal(index[0], '56,250')
        assert isinstance(index[1], list)
        assert_equal(len(index[1]), 40)
        assert_equal(index[1][0].tag, 'li')

    def test_scrape_publication_basics(self):
        html = get_html_content('publication_index.html')
        index = GovukPublicationScraper.scrape_publication_index_page(html)
        element = index[1][0]
        pub = GovukPublicationScraper.scrape_publication_basics(element)
        assert_equal(pub, {
            'govuk_id': 369795,
            'last_updated': datetime.datetime(2014, 8, 4, 11, 7, 36, tzinfo=tzoffset(None, 3600)),
            'name': 'reduced-rate-certificate-for-metal-packaging',
            'title': 'Reduced rate certificate for metal packaging',
            'url': 'https://www.gov.uk/government/publications/reduced-rate-certificate-for-metal-packaging'
            })

    def test_scrape_publication_page(self):
        reset_stats()
        html = get_html_content('publication_page.html')
        pub = GovukPublicationScraper.scrape_publication_page(html, 'pub_url', 'pub_name')
        pprint(pub)
        assert_equal(pub, {
'attachments': [[{'filename': 'FIS_user_guide_known_issue_201415_v6_31_July_2014.xlsx',
                   'title': 'FIS 2014 to 2015 known issues: v6 31 July 2014',
                   'url': 'https://www.gov.uk/government/uploads/system/uploads/attachment_data/file/340217/FIS_user_guide_known_issue_201415_v6_31_July_2014.xlsx'},
                  {'filename': 'nat-FISUserguide-ug-fis_KnownIssues-v7_23May2014.xlsx',
                   'title': 'FIS Known issues guide v7.0  23 May 2014',
                   'url': 'https://www.gov.uk/government/uploads/system/uploads/attachment_data/file/313847/nat-FISUserguide-ug-fis_KnownIssues-v7_23May2014.xlsx'},
                  {'filename': 'nat-FIS_User_guidance-ug-fis-v1-0_20May2014.pdf',
                   'title': 'FIS user guide: v1.0 21 May 2014',
                   'url': 'https://www.gov.uk/government/uploads/system/uploads/attachment_data/file/313116/nat-FIS_User_guidance-ug-fis-v1-0_20May2014.pdf'},
                  {'filename': 'FIS_installation_guidance_v1.2_July_2014.pdf',
                   'title': 'FIS installation guide: v1.2 24 July 2014',
                   'url': 'https://www.gov.uk/government/uploads/system/uploads/attachment_data/file/337487/FIS_installation_guidance_v1.2_July_2014.pdf'},
                  {'filename': 'FIS_Uninstallation_guide_05_March_2014.pdf',
                   'title': 'FIS uninstallation guide March 2014',
                   'url': 'https://www.gov.uk/government/uploads/system/uploads/attachment_data/file/314263/FIS_Uninstallation_guide_05_March_2014.pdf'},
                  {'filename': 'FIS_release_guide_31_July_2014_v1.3.pdf',
                   'title': 'FIS release guide: v1.3 31 July 2014',
                   'url': 'https://www.gov.uk/government/uploads/system/uploads/attachment_data/file/340005/FIS_release_guide_31_July_2014_v1.3.pdf'},
                  {'filename': 'FIS_database_Guidance_v1_2_February_2014.xls',
                   'title': 'FIS database guide: version 1 (20 February 2014)',
                   'url': 'https://www.gov.uk/government/uploads/system/uploads/attachment_data/file/285557/FIS_database_Guidance_v1_2_February_2014.xls'},
                  {'filename': 'FISamalgamationguidancev1_019December2013.pdf',
                   'title': 'FIS file amalgamation guide: version 1 (20 December 2013)',
                   'url': 'https://www.gov.uk/government/uploads/system/uploads/attachment_data/file/284049/FISamalgamationguidancev1_019December2013.pdf'},
                  {'filename': 'Funding_Information_System_v24_pol_process_update_ver4.pdf',
                   'title': 'FIS providers online (POL) process update: version 24 (13 February 2014)',
                   'url': 'https://www.gov.uk/government/uploads/system/uploads/attachment_data/file/287697/Funding_Information_System_v24_pol_process_update_ver4.pdf'},
                  {'filename': 'FIS_SFA_reports_guidance_FIS_27January2014_v1-0.pdf',
                   'title': 'FIS SFA reports guide: version 1 (January 2014)',
                   'url': 'https://www.gov.uk/government/uploads/system/uploads/attachment_data/file/287659/FIS_SFA_reports_guidance_FIS_27January2014_v1-0.pdf'},
                  {'filename': 'FIS_EFA_reports_guidance_FIS_27January2014_v1-0.pdf',
                   'title': 'FIS EFA reports guide: version 1 (January 2014)',
                   'url': 'https://www.gov.uk/government/uploads/system/uploads/attachment_data/file/287661/FIS_EFA_reports_guidance_FIS_27January2014_v1-0.pdf'},
                  {'filename': 'Funding_Calculation_2013_14_FM35_20140205v2.pdf',
                   'title': 'Technical specification of the main calculation for further education funding by the Skills Funding Agency in 2013 to 2014',
                   'url': 'https://www.gov.uk/government/uploads/system/uploads/attachment_data/file/284051/Funding_Calculation_2013_14_FM35_20140205v2.pdf'},
                  {'filename': 'EFA_2013_14_Funding_Calculation_Specification_V1_2_13_03_2014.pdf',
                   'title': 'Technical specification of the calculation for further education funding by the Education Funding Agency (EFA) in 2013 to 2014: version 1.2 (April 2014)',
                   'url': 'https://www.gov.uk/government/uploads/system/uploads/attachment_data/file/301088/EFA_2013_14_Funding_Calculation_Specification_V1_2_13_03_2014.pdf'}]],
 'collections': set(['https://www.gov.uk/government/collections/individualised-learner-record-ilr']),
 'last_updated': datetime.datetime(2014, 8, 1, 11, 24, 11, tzinfo=tzoffset(None, 3600)),
 'name': 'pub_name',
 'org_url': 'https://www.gov.uk/government/organisations/skills-funding-agency',
 'published': datetime.datetime(2014, 2, 25, 13, 50, tzinfo=tzlocal()),
 'summary': 'Information about the Funding Information System (FIS), to help further education (FE) providers validate ILR data.',
 'type': 'Guidance',
 'url': 'pub_url'
            })
        assert_equal(fields_not_found(), [])

    def test_scrape_collection_page(self):
        reset_stats()
        html = get_html_content('collection_page.html')
        collection = GovukPublicationScraper.scrape_collection_page(html, '/collection_url')
        pprint(collection, indent=12)
        assert_equal(collection, {
            'organization': 'https://www.gov.uk/government/organisations/skills-funding-agency',
            'summary': 'Information to help further education (FE) providers collect, return and check the quality of Individualised Learner Record (ILR) and other learner data.',
            'title': 'Individualised Learner Record (ILR)',
            'url': '/collection_url'
            })
        assert_equal(fields_not_found(), [])

    def test_scrape_organization_page(self):
        reset_stats()
        html = get_html_content('organization_page.html')
        org = GovukPublicationScraper.scrape_organization_page(html, '/org_url')
        pprint(org, indent=12)
        assert_equal(org, {
           'govuk_id': 86,
           'name': 'org_url',
           'title': 'Skills Funding Agency',
           'url': '/org_url'
            })
        assert_equal(fields_not_found(), [])

    def test_parse_date_at_offset(self):
        assert_equal(GovukPublicationScraper.parse_date('2014-02-25T13:50:00+01:00'),
                datetime.datetime(2014, 2, 25, 13, 50, tzinfo=tzoffset(None, 3600)))

    def test_parse_date_at_zero_offset(self):
        assert_equal(GovukPublicationScraper.parse_date('2014-02-25T13:50:00+00:00'),
                datetime.datetime(2014, 2, 25, 13, 50, tzinfo=tzoffset(None, 0)))

    def test_extract_number_from_full_govuk_id(self):
        assert_equal(GovukPublicationScraper.extract_number_from_full_govuk_id('publication_370126'),
                     370126)

def get_html_content(test_filename):
    test_filepath = os.path.join(os.path.dirname(__file__), 'govuk_html', test_filename)
    with open(test_filepath) as f:
        return f.read()

def reset_stats():
    GovukPublicationScraper.field_stats = Stats()
    GovukPublicationScraper.publication_stats = Stats()

def fields_not_found():
    not_found = []
    for category in GovukPublicationScraper.field_stats:
        if 'not found' in category:
            not_found.append(GovukPublicationScraper.field_stats.report_value(category))
    return not_found
