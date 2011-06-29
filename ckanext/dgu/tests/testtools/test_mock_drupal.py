import xmlrpclib

from nose.tools import assert_equal, assert_raises

from ckanext.dgu.tests import MockDrupalCase
from ckanext.dgu.testtools.mock_drupal import MOCK_DRUPAL_URL
        
class TestMockDrupal(MockDrupalCase):
    s = xmlrpclib.ServerProxy(MOCK_DRUPAL_URL)

    def test_user_get(self):
        user = self.s.user.get('62')
        assert isinstance(user, dict)
        assert user.has_key('name')
        assert user.has_key('publishers')
        assert isinstance(user['publishers'], dict), user['publishers']
        publisher = user['publishers'].items()[0]
        assert isinstance(publisher[0], str)
        assert_equal(publisher[0], '1')
        assert_equal(publisher[1], 'National Health Service')

    def test_user_get_error(self):
        assert_raises(xmlrpclib.Fault, self.s.user.get, 'unknown')

    def test_organisation_one(self):
        # return org name by id
        org_name = self.s.organisation.one('1')
        assert_equal(org_name, 'National Health Service')

    def test_organisation_one_error(self):
        assert_raises(xmlrpclib.Fault, self.s.organisation.one, '9999')

    def test_organisation_match(self):
        # return org id by name
        org_id = self.s.organisation.match('National Health Service')
        assert_equal(org_id, '1')

    def test_organisation_match_error(self):
        assert_raises(xmlrpclib.Fault, self.s.organisation.match, 'Wrong org name')

    def test_department_lookup(self):
        # return org id of the parent department
        org = self.s.organisation.department('2')
        assert_equal(org, {'7': 'Department of Health'})

    def test_department_lookup_error(self):
        assert_raises(xmlrpclib.Fault, self.s.organisation.department, '9999')

