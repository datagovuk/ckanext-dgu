import selenium_test_base as t

class MapPreviewTests(t.TestBase):


    def test_preview(self):
        self.selenium.open('/dataset/scheduled-ancient-monuments-in-wales-gis-polygon-dataset')
        self.selenium.click('link=Preview on Map')

        # Links are to external services, so we'll wait a little longer than usual
        self.wait(max_wait=30)

        assert 'Map Based Preview'  in self.selenium.get_title(), \
            "'Map Based Preview' did not appear in the page title"
