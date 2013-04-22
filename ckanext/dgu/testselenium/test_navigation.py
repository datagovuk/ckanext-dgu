import time
import selenium_test_base as t

class NavigationTests(t.TestBase):

    def test_basic_nav(self):
        self.selenium.open('/data')
        # Make sure we have a number, and it should ideally be bigger than ~8000
        # on sites using live data.
        int(self.selenium.get_text("class=result-count"))

    def test_nav_publishers(self):
        self.selenium.open('/data')
        self.selenium.click("link=Publishers")
        self.wait()
        assert 'Publishers' in self.selenium.get_title(), "Title was %s and not Publishers" % self.selenium.get_title()

        # Check the list, seems a bit dependant on the data :( maybe we should fix this.
        lnkCount = self.selenium.get_css_count("css=table.groups a")
        assert 17 == lnkCount, "There were %d links, we expected 17"  % lnkCount

        self.selenium.click("link=Publisher hierarchy")
        lnkCount = self.selenium.get_css_count("css=li.jstree-closed")
        assert lnkCount > 0, "There were no publishers in the publisher hierarchy"

        self.selenium.click("link=Publisher search")
        assert int(self.selenium.get_text("class=result-count")) > 0, \
            "There are no search results for publishers"

        self.fill_form("id=publisher-search", {'q': 'national statistics' })
        import time; time.sleep(3)
        assert int(self.selenium.get_text("class=result-count")) > 1, \
            "Could not find the office for national statistics"

        self.selenium.click("link=Publisher list")
        self.selenium.click("link=O")
        self.selenium.click("link=Office for Civil Society")
        self.wait()
        assert "Office for Civil Society" in self.selenium.get_title(),\
            "Title was not 'Office for Civil Society'"

    def test_nav_tags(self):
        # The Tags page is painfully slow, and so we should find a better to
        # wait for the page load to complete.
        self.selenium.open('/data')
        self.selenium.click("link=Tags")
        self.wait()
        assert 'Tags' in self.selenium.get_title(), "Title was %s and not Tags" % self.selenium.get_title()

        self.selenium.click("css=a.tag")
        self.wait()
        count = int(self.selenium.get_text("class=result-count"))
        assert count > 0, "There were no results for a tag"

    def test_nav_site_usage(self):
        self.selenium.open('/data')
        self.selenium.click("link=Data")
        self.wait()

        self.selenium.click("link=Other popular datasets")
        self.wait()
        assert 'Usage by Dataset' in self.selenium.get_title(), \
            "Title was %s and not 'Usage by Dataset'" % self.selenium.get_title()

        self.selenium.click("link=Site-wide")
        self.wait()
        assert 'Site usage' in self.selenium.get_title(), \
            "Title was %s and not 'Site usage'" % self.selenium.get_title()
