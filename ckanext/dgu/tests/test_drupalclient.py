from pylons import config
from nose.tools import assert_equal, assert_raises

from ckanext.dgu.tests import MockDrupalCase
from ckanext.dgu.testtools.mock_drupal import get_mock_drupal_config
from ckanext.dgu.drupalclient import DrupalClient, DrupalKeyError

class TestDrupalConnection(MockDrupalCase):
    def test_get_url(self):
        assert config['dgu.xmlrpc_domain']
        url = DrupalClient.get_xmlrpc_url()
        assert_equal(url, 'http://localhost:8000/services/xmlrpc')

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

    def test_match_organisation(self):
        drupal_config = get_mock_drupal_config()
        client = DrupalClient()
        org_id = client.match_organisation('Ealing PCT')
        assert_equal(org_id, '2')

        assert_raises(DrupalKeyError, client.match_organisation, '')
        assert_raises(DrupalKeyError, client.match_organisation, None)

    def test_get_organisation(self):
        drupal_config = get_mock_drupal_config()
        client = DrupalClient()

        org_name = client.get_organisation_name('2')
        assert_equal(org_name, 'Ealing PCT')
        org_name = client.get_organisation_name(2)
        assert_equal(org_name, 'Ealing PCT')

        assert_raises(DrupalKeyError, client.get_organisation_name, '999')
        assert_raises(DrupalKeyError, client.get_organisation_name, '')
        assert_raises(DrupalKeyError, client.get_organisation_name, None)
