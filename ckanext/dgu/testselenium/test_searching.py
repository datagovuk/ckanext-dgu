# -*- coding: utf-8 -*-

import selenium_test_base as t

class TestSearch(t.TestBase):

    def test_basic_search(self):
        self.selenium.open('/data/search')
        total = int(self.selenium.get_text("class=result-count"))
        assert total > 0, "There were no datasets to find"

        self.fill_form('id=dataset-search', {'q': 'tariff codes'})
        assert total > 0, "There were no datasets found"

    def test_resource_search(self):
        self.selenium.open('/data/search')
        self.selenium.click("link=CSV")
        total = int(self.selenium.get_text("class=result-count"))
        assert total > 0, "There were no CSV resources found"

    def test_tag_search(self):
        self.selenium.open('/data/search')
        self.selenium.click("link=NERC_DDC")
        total = int(self.selenium.get_text("class=result-count"))
        assert total > 0, "There were no NERC_DDC tagged datasets found"

    def test_license_search(self):
        self.selenium.open('/data/search?q=tariff+codes&license_id-is-ogl=true')
        total = int(self.selenium.get_text("class=result-count"))
        assert total > 0, "There were no OGL datasets found"

    def test_publisher_search(self):
        self.selenium.open('/data/search')
        self.selenium.click("link=British Geological Survey")
        total = int(self.selenium.get_text("class=result-count"))
        assert total > 0, "There were no CSV resources found"

    def test_uklp_type_search(self):
        self.selenium.open('/data/search?resource-type=dataset&amp;q=tariff+codes')
        total = int(self.selenium.get_text("class=result-count"))
        assert total > 0, "There were no NERC_DDC tagged datasets found"

