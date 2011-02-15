from pylons import config
from nose.tools import assert_equal

from ckanext.dgu.tests import MockDrupalCase
from ckanext.dgu.testtools.mock_drupal import get_mock_drupal_config
from ckanext.dgu.drupalclient import DrupalClient

class TestDrupalConnection(MockDrupalCase):
    def test_get_url(self):
        assert config['dgu.xmlrpc_domain']
        url = DrupalClient.get_xmlrpc_url()
        assert_equal(url, 'http://testuser:testpassword@localhost:8000/services/xmlrpc')

    def test_get_user_properties(self):
        drupal_config = get_mock_drupal_config()
        test_user_id = '62'
        expected_user = drupal_config['test_users'][test_user_id]
        client = DrupalClient()
        user = client.get_user_properties(test_user_id)
        assert user
        assert isinstance(user, dict)
        assert_equal(user['name'], expected_user['name'])
        expected_publishers = expected_user['publishers']
        assert_equal(user['publishers'], expected_publishers)
