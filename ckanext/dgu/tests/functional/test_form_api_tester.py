import os

from pylons import config
from nose.tools import assert_equal
from paste.deploy import appconfig
import paste.fixture

from ckan import plugins
from ckan import __file__ as ckan_file
from ckan.lib.create_test_data import CreateTestData
from ckan.config.middleware import make_app
from ckanext.dgu.tests.functional.form_api_tester import *

config_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(ckan_file)), '..'))

class TestFormApiTester:
    @classmethod
    def setup_class(cls):
        config = appconfig('config:test.ini', relative_to=config_dir)
        config.local_conf['ckan.plugins'] = 'dgu_form_api form_api_tester'
        wsgiapp = make_app(config.global_conf, **config.local_conf)
        cls.app = paste.fixture.TestApp(wsgiapp)
        CreateTestData.create()

    @classmethod
    def teardown_class(cls):
        plugins.reset()
        CreateTestData.delete()

    def test_create_package(self):
        create_page = self.app.get('/apitest/form/package/create')
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
        create_page = self.app.get('/apitest/form/package/edit/%s' % pkg_id)
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
