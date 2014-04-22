from nose.tools import assert_equal
from pylons import config

from ckan.tests.pylons_controller import PylonsTestCase
from ckan import model

from ckanext.dgu.testtools.create_test_data import DguCreateTestData
from ckanext.dgu.lib.helpers import dgu_linked_user
from ckanext.dgu.plugins_toolkit import c, get_action

class TestLinkedUser(PylonsTestCase):
    @classmethod
    def setup_class(cls):
        PylonsTestCase.setup_class()
        DguCreateTestData.create_dgu_test_data()

    def test_view_official(self):
        # most common case
        user = 'nhseditor' # i.e. an official, needing anonymity to the public
        user_obj = model.User.by_name(unicode(user))

        c.is_an_official = False
        assert_equal(str(dgu_linked_user(user)),
                '<a href="/publisher/national-health-service">National Health Service</a>')
        assert_equal(str(dgu_linked_user(user_obj)),
                '<a href="/publisher/national-health-service">National Health Service</a>')

        c.is_an_official = True
        assert_equal(str(dgu_linked_user(user)),
                '<a href="/data/user/nhseditor">NHS Editor</a>')
        assert_equal(str(dgu_linked_user(user_obj)),
                '<a href="/data/user/nhseditor">NHS Editor</a>')

    def test_view_member_of_public(self):
        # most common case
        user = 'user_d102' # a member of the public, not anonymous - public comments
        user_obj = model.User.by_name(unicode(user))

        c.is_an_official = False
        assert_equal(str(dgu_linked_user(user)),
                '<a href="/users/102">John Doe - a public user</a>')
        assert_equal(str(dgu_linked_user(user_obj)),
                '<a href="/users/102">John Doe - a public user</a>')

        c.is_an_official = True
        assert_equal(str(dgu_linked_user(user)),
                '<a href="/users/102">John Doe - a public user</a>')
        assert_equal(str(dgu_linked_user(user_obj)),
                '<a href="/users/102">John Doe - a public user</a>')

    def test_view_sysadmin(self):
        # very common case
        user = 'sysadmin'
        user_obj = model.User.by_name(unicode(user))

        c.is_an_official = False
        assert_equal(str(dgu_linked_user(user)), 'System Administrator')
        assert_equal(str(dgu_linked_user(user_obj)), 'System Administrator')

        c.is_an_official = True
        assert_equal(str(dgu_linked_user(user)),
                '<a href="/data/user/sysadmin">Test Sysadmin</a>')
        assert_equal(str(dgu_linked_user(user_obj)),
                '<a href="/data/user/sysadmin">Test Sysadmin</a>')

    def test_view_non_object_user(self):
        # created by a script, but no User object exists
        user = 'random'

        c.is_an_official = False
        assert_equal(str(dgu_linked_user(user)), 'Staff')

        c.is_an_official = True
        assert_equal(str(dgu_linked_user(user)), 'random')

    def test_view_old_drupal_edit(self):
        # Up til Jun 2012, edits through drupal were saved like this
        # "NHS North Staffordshire (uid 6107 )"
        user = 'National Health Service (uid 101 )'

        c.is_an_official = False
        assert_equal(str(dgu_linked_user(user)),
                '<a href="/publisher/national-health-service">National Health Service</a>')

        c.is_an_official = True
        assert_equal(str(dgu_linked_user(user)),
                '<a href="/data/user/user_d101">NHS Editor imported f...</a>')

    def test_view_system_user(self):
        # created on the API
        user_dict = get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
        user = user_dict['name']

        c.is_an_official = False
        assert_equal(str(dgu_linked_user(user)), 'System Process')

        c.is_an_official = True
        assert_equal(str(dgu_linked_user(user, maxlength=100)),
                '<a href="/data/user/test.ckan.net">System Process (Site user)</a>')

