from genshi.input import HTML

from ckan import model
from ckan.lib.create_test_data import CreateTestData
from ckanext.dgu.stream_filters import harvest_filter

from ckanext.dgu.tests import HarvestFixture
from ckan.tests.html_check import HtmlCheckMethods

basic_package_page = '''
<html>
  <body class="hide-sidebar">
    <!-- Downloads and resources -->
    <div class="resources subsection">
      <h3>Downloads &amp; Resources</h3>
      <table>
        <tr>
            <th>Description</th>
            <th>Format</th>
            <th>Hash</th>
        </tr>
          <tr>
              <td>
                <a href="http://site.com/data.csv" target="_blank">Description of the data</a>
              </td>
              <td>csv</td>
              <td>abc123</td>
          </tr>
      </table>
    </div>
  </body>
<html>
'''

class TestHarvestFilter(HtmlCheckMethods, HarvestFixture):
    @classmethod
    def setup_class(cls):
        HarvestFixture.setup_class()
        cls.pkg_page = HTML(basic_package_page)

    def test_basic(self):

        pkg = model.Package.by_name(u'annakarenina')
        harvest_object_id = pkg.extras.get('harvest_object_id')
        harvest_xml_url = '/api/2/rest/harvestobject/%s/xml' % harvest_object_id
        harvest_html_url = '/api/2/rest/harvestobject/%s/html' % harvest_object_id

        # before filter
        pkg_page = HTML(self.pkg_page).render()
        self.check_named_element(pkg_page, 'a', '!href="%s"' % harvest_xml_url)
        self.check_named_element(pkg_page, 'a', '!href="%s"' % harvest_html_url)

        anna = model.Package.by_name(u'annakarenina')
        res = harvest_filter(HTML(self.pkg_page), anna)
        res = res.render('html').decode('utf8')
        print res

        # after filter
        self.check_named_element(res, 'a', 'href="%s"' % harvest_xml_url)
        self.check_named_element(res, 'a', 'href="%s"' % harvest_html_url)


# test disabled - archive filter never written
class _TestArchiveFilter(HtmlCheckMethods):
    @classmethod
    def setup_class(cls):
        cls.pkg_page = HTML(basic_package_page)

    def test_basic(self):
        self.pkg_url = 'http://site.com/data.csv'
        self.archive_url = 'http://webarchive.nationalarchives.gov.uk/tna/+/' + self.pkg_url

        # before filter
        # <a href="http://www.annakarenina.com/download/x=1&amp;y=2" target="_blank">Full text. Needs escaping: " Umlaut: u</a>
        self.pkg_page = HTML(self.pkg_page).render()
        self.check_named_element(self.pkg_page, 'a', 'href="%s"' % self.pkg_url)
        self.check_named_element(self.pkg_page, 'a', '!href="%s"' % self.archive_url)

        res = archive_filter(HTML(self.pkg_page))
        res = res.render('html').decode('utf8')
        print res
        # after filter
        self.check_named_element(res, 'a', 'href="%s"' % self.pkg_url)
        self.check_named_element(res, 'a', 'href="%s"' % self.archive_url)

