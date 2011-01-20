import os

from pylons import config
from nose.tools import assert_equal
import paste.fixture

from ckan import plugins
from ckan.lib.create_test_data import CreateTestData

from ckanext.dgu.tests import WsgiAppCase
from ckanext.dgu.tests.functional.form_api_tester import *

class TestFormApiTester(WsgiAppCase):
    @classmethod
    def setup_class(cls):
        CreateTestData.create()

    @classmethod
    def teardown_class(cls):
        plugins.reset()
        CreateTestData.delete()

    def test_create_package(self):
        create_page = self.app.get('/apitest/form/package/create?user_id=62')
        create_page.mustcontain('User:')
        create_page.mustcontain('Package--name')
        form = create_page.forms['test']
        test_name = 'test-name'
        form['Package--name'] = test_name
        res = form.submit()
        pkg = model.Package.by_name(unicode(test_name))
        assert pkg
        assert '201 Created' in res, res.body

    def test_edit_package(self):
        pkg_id = model.Package.by_name(u'annakarenina').id
        create_page = self.app.get('/apitest/form/package/edit/%s?user_id=62' % pkg_id)
        create_page.mustcontain('User:')
        create_page.mustcontain('Package-%s-name' % pkg_id)
        create_page.mustcontain('annakarenina')
        form = create_page.forms['test']
        test_title = 'New title'
        form['Package-%s-title' % pkg_id] = test_title
        res = form.submit()
        pkg = model.Package.by_name(u'annakarenina')
        assert_equal(pkg.title, test_title)
        assert '200 OK' in res, res.body
