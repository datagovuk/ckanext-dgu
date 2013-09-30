from nose.tools import assert_equal
from ckan import model
from ckanext.dgu.lib.publisher import *
from ckanext.dgu.testtools.create_test_data import DguCreateTestData
from ckanext.dgu.plugins_toolkit import NotAuthorized
from ckan.logic import check_access

def to_names(domain_obj_list):
    objs = []
    for obj in domain_obj_list:
        objs.append(obj.name if obj else None)
    return objs

class TestParentAuth:
    @classmethod
    def setup_class(cls):
        DguCreateTestData.create_dgu_test_data()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def _check_permission(self, perm, username, object_id):
        context = {'model': model,
                   'session':model.Session,
                   'user': username}
        try:
            check_access(perm, context, {'id': object_id})
            return True
        except NotAuthorized, e:
            return False

    def _check_package_edit_permission(self, username, package_id):
        return self._check_permission( 'package_update', username, package_id )

    def _check_group_edit_permission(self, username, group_id):
        return self._check_permission( 'group_update', username, group_id )

    def test_invalid_group_auths(self):
        assert_equal(self._check_group_edit_permission('', 'dept-health'), False)
        assert_equal(self._check_group_edit_permission('nhseditor', 'dept-health'), False)
        assert_equal(self._check_group_edit_permission('nhseditor', 'national-health-service'), False)
        assert_equal(self._check_group_edit_permission('nhseditor', 'barnsley-primary-care-trust'), False)
        assert_equal(self._check_group_edit_permission('nhsadmin', 'dept-health'), False)

    def test_valid_group_auths(self):
        assert_equal(self._check_group_edit_permission('nhsadmin', 'national-health-service'), True)
        assert_equal(self._check_group_edit_permission('nhsadmin', 'barnsley-primary-care-trust'), True)


    def test_no_user(self):
        # Automatic FAIL
        assert_equal(self._check_package_edit_permission('', 'nhs-spend-over-25k-barnsleypct'), False)

    def test_sysadmin(self):
        # Automatic WIN
        assert_equal(self._check_package_edit_permission('sysadmin', 'nhs-spend-over-25k-barnsleypct'), True)

    def test_admin_of_parent(self):
        # admin of dept-health should be able to edit
        # barnsley-primary-care-trust dataset
        assert_equal(self._check_package_edit_permission('dh_admin', 'nhs-spend-over-25k-barnsleypct'), True)

    def test_admin_of_parent_one_level_up(self):
        # admin of dept-health should be able to edit
        # barnsley-primary-care-trust dataset
        assert_equal(self._check_package_edit_permission('nhsadmin', 'nhs-spend-over-25k-barnsleypct'), True)

    def test_editor_cannot_edit_parent(self):
        # admin/editor of barnsley-primary-care-trust should not be able to edit
        # a dataset from NHS (which is a parent)
        assert_equal(self._check_package_edit_permission('barnsley_admin', 'directgov-cota'), False)
        assert_equal(self._check_package_edit_permission('barnsley_editor', 'directgov-cota'), False)

    def test_not_admin_of_parent(self):
        # admin of cabinet-office should not be able to edit
        # barnsley-primary-care-trust ds
        assert_equal(self._check_package_edit_permission('co_admin', 'nhs-spend-over-25k-barnsleypct'), False)

    def test_editor_of_group(self):
        # editor of barnsley-primary-care-trust should be able to edit
        # barnsley-primary-care-trust ds
        assert_equal(self._check_package_edit_permission('barnsley_editor', 'nhs-spend-over-25k-barnsleypct'), True)

    def test_not_editor_of_group(self):
        # editor of cabinet-office should be able to edit
        # barnsley-primary-care-trust ds
        assert_equal(self._check_package_edit_permission('co_editor', 'nhs-spend-over-25k-barnsleypct'), False)


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
