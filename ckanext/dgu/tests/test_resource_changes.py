
import datetime
from nose.tools import assert_equal
from nose.plugins.skip import SkipTest

from ckan import model
from ckan.lib.create_test_data import CreateTestData
from ckan.logic import get_action
from ckan.tests import TestController as ControllerTestCase
from ckanext.dgu.testtools.create_test_data import DguCreateTestData


# No  last_major_modification in cadastreni-wms
# nhs-spend-over-25k-barnsleypct
# directgov-cota

class TestResourceChanges(ControllerTestCase):

    @classmethod
    def setup_class(cls):
        DguCreateTestData.create_dgu_test_data()
        model.repo.new_revision()


    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_new_resource(self):
        c = { "model": model, "session": model.Session, "user": "admin"}

        p = model.Package.get("directgov-cota")
        p.add_resource(url="http://fake_url/", format="HTML", description="A test resource")
        model.Session.add(p)
        model.Session.commit()

        p = model.Package.get("directgov-cota")

        today = datetime.datetime.now().strftime("%Y-%m-%d")
        assert len(p.resources) == 2, "Resource wasn't added"
        assert "last_major_modification" in p.extras
        assert p.extras["last_major_modification"] == today


    def test_delete_resource(self):
        c = { "model": model, "session": model.Session, "user": "admin"}

        p = model.Package.get("cabinet-office-energy-use")
        count = len(p.resources)
        
        r = p.resources[0]
        r.state = 'deleted'

        model.Session.add(r)
        model.Session.add(p)
        model.Session.commit()

        p = model.Package.get("cabinet-office-energy-use")

        today = datetime.datetime.now().strftime("%Y-%m-%d")
        assert len(p.resources) != count, "Resource wasn't deleted"
        assert "last_major_modification" in p.extras
        assert p.extras["last_major_modification"] == today


    def test_resource_url_change(self):
        c = { "model": model, "session": model.Session, "user": "admin"}

        p = model.Package.get("nhs-spend-over-25k-barnsleypct")

        r = p.resources[0]
        r.url = "http://google.com/"

        model.Session.add(r)
        model.Session.add(p)
        model.Session.commit()

        p = model.Package.get("nhs-spend-over-25k-barnsleypct")
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        assert "last_major_modification" in p.extras
        assert p.extras["last_major_modification"] == today

