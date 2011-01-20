import xmlrpclib

from ckanext.dgu.tests import MockDrupalCase
        
class TestMockDrupal(MockDrupalCase):
    def test_user_get(self):
        s = xmlrpclib.ServerProxy('http://localhost:8000/services/xmlrpc')
        user = s.user.get('62')
        assert isinstance(user, dict)
        assert user.has_key('name')
        assert user.has_key('publishers')
        assert isinstance(user['publishers'], dict)
