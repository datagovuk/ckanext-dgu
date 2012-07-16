from nose.tools import assert_equal
from ckan import model
from ckanext.dgu.lib.publisher import *
from ckanext.dgu.testtools.create_test_data import DguCreateTestData

def to_names(domain_obj_list):
    objs = []
    for obj in domain_obj_list:
        objs.append(obj.name if obj else None)
    return objs

class TestGetParents:
    @classmethod
    def setup_class(cls):
        DguCreateTestData.create_dgu_test_data()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_doh(self):
        assert_equal(to_names(get_parents(model.Group.get(u'dept-health'))),
                     [])
    def test_nhs(self):
        assert_equal(to_names(get_parents(model.Group.get(u'national-health-service'))),
                     ['dept-health'])
    def test_barnsley(self):
        assert_equal(to_names(get_parents(model.Group.get(u'barnsley-primary-care-trust'))),
                     ['national-health-service'])

class TestGoUpTree:
    @classmethod
    def setup_class(cls):
        DguCreateTestData.create_dgu_test_data()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_doh(self):
        assert_equal(to_names(go_up_tree(model.Group.get(u'dept-health'))),
                     ['dept-health'])

    def test_nhs(self):
        assert_equal(to_names(go_up_tree(model.Group.get(u'national-health-service'))),
                     ['national-health-service', 'dept-health'])

    def test_barnsley(self):
        assert_equal(to_names(go_up_tree(model.Group.get(u'barnsley-primary-care-trust'))),
                     ['barnsley-primary-care-trust', 'national-health-service', 'dept-health'])                

class TestGoDownTree:
    @classmethod
    def setup_class(cls):
        DguCreateTestData.create_dgu_test_data()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_doh(self):
        assert_equal(set(to_names(go_down_tree(model.Group.get(u'dept-health')))),
                     set(['dept-health', 'national-health-service', 'barnsley-primary-care-trust', 'newham-primary-care-trust']))

    def test_nhs(self):
        assert_equal(to_names(go_down_tree(model.Group.get(u'national-health-service'))),
                     ['national-health-service', 'barnsley-primary-care-trust', 'newham-primary-care-trust'])

    def test_barnsley(self):
        assert_equal(to_names(go_down_tree(model.Group.get(u'barnsley-primary-care-trust'))),
                     ['barnsley-primary-care-trust'])
