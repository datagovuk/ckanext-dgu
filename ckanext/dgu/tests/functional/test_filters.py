from genshi.input import HTML
from nose.tools import assert_equal

from ckan.lib.package_saver import PackageSaver
from ckan.lib.create_test_data import CreateTestData
from ckan.lib.base import render, c, h, g
import ckan.logic.action.get as get
from ckan import model

from ckanext.dgu.stream_filters import harvest_filter

from ckan.tests import TestController as ControllerTestCase
from ckan.tests.pylons_controller import PylonsTestCase
from ckan.tests.html_check import HtmlCheckMethods
from ckanext.dgu.tests import HarvestFixture

class TestHarvestFilter(PylonsTestCase, HtmlCheckMethods,
                        ControllerTestCase, HarvestFixture):
    @classmethod
    def setup_class(cls):
        PylonsTestCase.setup_class()
        HarvestFixture.setup_class()

        # prepare to render package page
        user = model.PSEUDO_USER__VISITOR
        c.pkg = model.Package.by_name(u'annakarenina')
        c.locale = 'en'
        c.body_class = 'hide-sidebar'
        c.controller = 'package'
        c.action = 'read'
        c.user = user
        c.is_preview = False
        c.hide_welcome_message = False
        context = {'model': model, 'session': model.Session,
                   'user': c.user,
                   'id':c.pkg.id,
                   'package':c.pkg}
        c.pkg_dict = get.package_show(context)
        
        # Render package view page
        # (filter should not be called on this occasion)
        PackageSaver().render_package(c.pkg_dict,
                                      context)
        cls.pkg_page = render('package/read.html')

        # Expected URLs
        cls.harvest_xml_url = '/api/2/rest/harvestobject/test-guid/xml'
        cls.harvest_html_url = '/api/2/rest/harvestobject/test-guid/html'
    
    def test_basic(self):
        pkg_id = c.pkg.id

        # before filter
        # <a href="http://www.annakarenina.com/download/x=1&amp;y=2" target="_blank">Full text. Needs escaping: " Umlaut: u</a>
        self.check_named_element(self.pkg_page, 'a', '!href="%s"' % self.harvest_xml_url)
        self.check_named_element(self.pkg_page, 'a', '!href="%s"' % self.harvest_html_url)

        res = harvest_filter(HTML(self.pkg_page), c.pkg)
        res = res.render('html').decode('utf8')
        main_res = self.main_div(res)

        # after filter
        self.check_named_element(res, 'a', 'href="%s"' % self.harvest_xml_url)
        self.check_named_element(res, 'a', 'href="%s"' % self.harvest_html_url)

    def test_link_to_xml(self):
        res = self.app.get(self.harvest_xml_url)
        assert_equal(res.body, '<xml>test content</xml>')

    def test_link_to_html(self):
        res = self.app.get(self.harvest_html_url)
        assert 'GEMINI record' in res.body
        assert 'error' not in res.body
        
