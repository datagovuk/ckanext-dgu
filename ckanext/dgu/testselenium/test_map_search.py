import selenium_test_base as t

class MapSearchTests(t.TestBase):


    def test_map(self):
        self.selenium.open('/data/map-based-search')
        self.selenium.click("id=buttonDrawID")

        locator = "id=OpenLayers.Map_6_OpenLayers_Container"
        start, end = ("600,100", "660,150")

        self.selenium.mouse_down_at(locator, start)
        self.selenium.mouse_move_at(locator, end)
        self.selenium.mouse_up_at(locator, end)

        self.selenium.click('id=buttonSearchID')
        self.wait()

        total = int(self.selenium.get_text("class=result-count"))
        assert total > 0, "There were no datasets found in the bounding box"
