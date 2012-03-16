from sqlalchemy.util import OrderedDict

from ckanext.dgu.bin.change_licenses import ChangeLicenses
from ckan import model
from ckan.tests import *
from ckan.tests.wsgi_ckanclient import WsgiCkanClient
from ckan.lib.create_test_data import CreateTestData

from pylons import config

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
    def teardown_class(cls):
        model.Session.remove()
        model.repo.rebuild_db()

    def get_licenses(self):
        q = model.Session.query(model.Package)
        return dict([(pkg.name, pkg.license_id) for pkg in q.all()])

    def test_1_change_all_pkgs(self):
        # Skip this test until the mock data reflects the new permission model
        # (each dataset *needs* to belong to a group
        raise SkipTest, 'Skip until mock data reflects new permission model'

        if 'sqlite' in config.get('sqlalchemy.url'):
            # Ian thinks this failed for him due to a timestamp not being converted
            # to a datetime object, and being left as a unicode object.
            # Could also be related to Sqlalchemy 0.7.x.
            raise SkipTest

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
    
