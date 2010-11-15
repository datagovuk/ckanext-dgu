from sqlalchemy.util import OrderedDict

from ckanext.dgu.scripts.change_licenses import ChangeLicenses
from ckan import model
from ckan.tests import *
from ckan.tests.wsgi_ckanclient import WsgiCkanClient
from ckan.lib.create_test_data import CreateTestData


class TestChangeLicenses(TestController):
    @classmethod
    def setup_class(self):
        # create test data
        CreateTestData.create()
        username = 'annafan'
        user = model.User.by_name(unicode(username))
        assert user
        self.testclient = WsgiCkanClient(self.app, api_key=user.apikey, base_location='/api/2')

    @classmethod
    def teardown_class(self):
        CreateTestData.delete()

    def get_licenses(self):
        q = model.Session.query(model.Package)
        return dict([(pkg.name, pkg.license_id) for pkg in q.all()])

    def test_1_change_all_pkgs(self):
        licenses_before = self.get_licenses()
        self.license_id = 'test-license'
        self.change_licenses = ChangeLicenses(self.testclient)
        self.change_licenses.change_all_packages(self.license_id)
        licenses_after = self.get_licenses()

        change_in_packages = set(licenses_before.keys()) - set(licenses_after.keys())
        assert not change_in_packages, change_in_packages
        for pkg_name in licenses_after.keys():
            assert licenses_after[pkg_name] == self.license_id, licenses_after[pkg_name]

    def test_2_test_change_oct_2010(self):
        # TODO
        pass
    
