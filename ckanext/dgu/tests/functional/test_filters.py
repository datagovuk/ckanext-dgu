from genshi.input import HTML
from nose.tools import assert_equal
import pylons

from ckan.lib.package_saver import PackageSaver
from ckan.lib.create_test_data import CreateTestData
from ckan.lib.base import h, g
from ckan import model

from ckan.tests import TestController as ControllerTestCase
from ckan.tests.pylons_controller import PylonsTestCase
from ckan.tests.html_check import HtmlCheckMethods
from ckanext.dgu.tests import HarvestFixture
from ckanext.dgu.plugins_toolkit import render, c, get_action

class FilterTestCase(PylonsTestCase, HtmlCheckMethods,
                        ControllerTestCase, HarvestFixture):
    @classmethod
    def setup_class(cls):
        model.repo.rebuild_db()
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
                   'package':c.pkg}
        c.pkg_dict = get_action('package_show')(context, {'id':c.pkg.id})

        # inject a mock PATH_INFO into the environ in order
        # that the template can be rendered correctly.
        # See 'ckan/templates/layout_base.html'
        import pylons
        pylons.request.environ.update({'PATH_INFO': '/dataset'})

        # Render package view page
        # (filter should not be called on this occasion)
        PackageSaver().render_package(c.pkg_dict,
                                      context)
        cls.pkg_page = render('package/read.html',
                              extra_vars={'session': pylons.session})

        # Expected URLs
        harvest_object_id = c.pkg.extras.get('harvest_object_id')
        cls.harvest_xml_url = '/api/2/rest/harvestobject/%s/xml' % harvest_object_id
        cls.harvest_html_url = '/api/2/rest/harvestobject/%s/html' % harvest_object_id

    @classmethod
    def teardown_class(cls):
        HarvestFixture.teardown_class()

class TestHarvestFilter(FilterTestCase):

    def test_link_to_xml(self):
        res = self.app.get(self.harvest_xml_url)
        assert_equal(res.body, '<xml>test content</xml>')

    def test_link_to_html(self):
        res = self.app.get(self.harvest_html_url)
        assert 'GEMINI record' in res.body
        assert 'error' not in res.body

