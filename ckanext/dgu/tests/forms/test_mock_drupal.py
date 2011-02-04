import xmlrpclib

from nose.tools import assert_equal, assert_raises

from ckanext.dgu.tests import MockDrupalCase
        
class TestMockDrupal(MockDrupalCase):
    s = xmlrpclib.ServerProxy('http://localhost:8000/services/xmlrpc')

    def test_user_get(self):
        user = self.s.user.get('62')
        assert isinstance(user, dict)
        assert user.has_key('name')
        assert user.has_key('publishers')
        assert isinstance(user['publishers'], dict)
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

    def test_organisation_match(self):
        # return org id by name
        org_id = self.s.organisation.match('National Health Service')
        assert_equal(org_id, '1')
