from ckanext.dgu.lib.govuk_links import get_urls_that_redirect_matcher


class TestUrlsThatRedirectMatcher():
    def test_upload(self):
        assert not get_urls_that_redirect_matcher().match('https://www.gov.uk/government/uploads/system/uploads/attachment_data/file/27318/20120522_mod_tax_arrangements.csv')

    def test_organisation(self):
        assert not get_urls_that_redirect_matcher().match('https://www.gov.uk/government/organisations/treasury-solicitor-s-department/about/publication-scheme')

    def test_publication(self):
        assert get_urls_that_redirect_matcher().match('https://www.gov.uk/government/publications/english-housing-survey-2011-to-2012-headline-report')
