from nose.tools import assert_equal

from ckan.tests.pylons_controller import PylonsTestCase
from ckan import model

from ckanext.dgu.testtools.create_test_data import DguCreateTestData
from ckanext.dgu.lib.helpers import dgu_linked_user
from ckanext.dgu.plugins_toolkit import c

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
                '<a href="/publisher/national-health-service">National Heal...</a>')
        assert_equal(str(dgu_linked_user(user_obj)),
                '<a href="/publisher/national-health-service">National Heal...</a>')

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
                '<a href="/users/John%20Doe%20-%20a%20public%20user">John Doe - a ...</a>')
        assert_equal(str(dgu_linked_user(user_obj)),
                '<a href="/users/John%20Doe%20-%20a%20public%20user">John Doe - a ...</a>')

        c.is_an_official = True
        assert_equal(str(dgu_linked_user(user)),
                '<a href="/users/John%20Doe%20-%20a%20public%20user">John Doe - a ...</a>')
        assert_equal(str(dgu_linked_user(user_obj)),
                '<a href="/users/John%20Doe%20-%20a%20public%20user">John Doe - a ...</a>')

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
                '<a href="/publisher/national-health-service">National Heal...</a>')

        c.is_an_official = True
        assert_equal(str(dgu_linked_user(user)),
                '<a href="/data/user/user_d101">NHS Editor im...</a>')

