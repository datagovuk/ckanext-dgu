import json

from nose.tools import assert_equal

from ckan.tests.pylons_controller import PylonsTestCase
import ckan.new_tests.factories as factories
import ckan.new_tests.helpers as helpers
from ckan import model

from ckanext.dgu.testtools.create_test_data import DguCreateTestData
from ckanext.dgu.lib.helpers import (dgu_linked_user, user_properties,
                                     render_partial_datestamp,
                                     render_mandates,
                                     )
from ckanext.dgu.plugins_toolkit import c, get_action

from contextlib import contextmanager

def regular_user():
    return set_user_to('user')

def publisher_user():
    return set_user_to('co_editor')

def sysadmin_user():
    return set_user_to('sysadmin')

@contextmanager
def set_user_to(username):
    old_user = c.userobj
    c.userobj = model.User.by_name(username)

    old_groups = c.groups
    c.groups = ''
    yield
    c.userobj = old_user
    c.groups = old_groups


class TestLinkedUser(PylonsTestCase):
    @classmethod
    def setup_class(cls):
        helpers.reset_db()
        PylonsTestCase.setup_class()
        DguCreateTestData.create_dgu_test_data()

    def test_view_official(self):
        # most common case
        user = 'nhseditor' # i.e. an official, needing anonymity to the public
        user_obj = model.User.by_name(unicode(user))

        with regular_user():
            assert_equal(str(dgu_linked_user(user)),
                    '<a href="/publisher/national-health-service">National Health Service</a>')
            assert_equal(str(dgu_linked_user(user_obj)),
                    '<a href="/publisher/national-health-service">National Health Service</a>')

        with publisher_user():
            assert_equal(str(dgu_linked_user(user)),
                    '<a href="/data/user/nhseditor">NHS Editor</a>')
            assert_equal(str(dgu_linked_user(user_obj)),
                    '<a href="/data/user/nhseditor">NHS Editor</a>')

        with sysadmin_user():
            assert_equal(str(dgu_linked_user(user)),
                    '<a href="/data/user/nhseditor">NHS Editor</a>')
            assert_equal(str(dgu_linked_user(user_obj)),
                    '<a href="/data/user/nhseditor">NHS Editor</a>')

    def test_view_member_of_public(self):
        # most common case
        user = 'user_d102' # a member of the public, not anonymous - public comments
        user_obj = model.User.by_name(unicode(user))

        with regular_user():
            assert_equal(str(dgu_linked_user(user)),
                    '<a href="/user/102">John Doe - a public user</a>')
            assert_equal(str(dgu_linked_user(user_obj)),
                    '<a href="/user/102">John Doe - a public user</a>')

        with publisher_user():
            assert_equal(str(dgu_linked_user(user)),
                    '<a href="/user/102">John Doe - a public user</a>')
            assert_equal(str(dgu_linked_user(user_obj)),
                    '<a href="/user/102">John Doe - a public user</a>')

        with sysadmin_user():
            assert_equal(str(dgu_linked_user(user)),
                    '<a href="/user/102">John Doe - a public user</a>')
            assert_equal(str(dgu_linked_user(user_obj)),
                    '<a href="/user/102">John Doe - a public user</a>')

    def test_view_sysadmin(self):
        # very common case
        user = 'sysadmin'
        user_obj = model.User.by_name(unicode(user))

        with regular_user():
            assert_equal(str(dgu_linked_user(user)), 'System Administrator')
            assert_equal(str(dgu_linked_user(user_obj)), 'System Administrator')

        with publisher_user():
            assert_equal(str(dgu_linked_user(user)),
                    '<a href="/data/user/sysadmin">Test Sysadmin</a>')
            assert_equal(str(dgu_linked_user(user_obj)),
                    '<a href="/data/user/sysadmin">Test Sysadmin</a>')

        with sysadmin_user():
            assert_equal(str(dgu_linked_user(user)),
                    '<a href="/data/user/sysadmin">Test Sysadmin</a>')
            assert_equal(str(dgu_linked_user(user_obj)),
                    '<a href="/data/user/sysadmin">Test Sysadmin</a>')

    def test_view_non_object_user(self):
        # created by a script, but no User object exists
        user = 'random'

        with regular_user():
            assert_equal(str(dgu_linked_user(user)), 'Staff')

        with publisher_user():
            assert_equal(str(dgu_linked_user(user)), 'random')

        with sysadmin_user():
            assert_equal(str(dgu_linked_user(user)), 'random')

    def test_view_old_drupal_edit(self):
        # Up til Jun 2012, edits through drupal were saved like this
        # "NHS North Staffordshire (uid 6107 )"
        user = 'National Health Service (uid 101 )'

        with regular_user():
            assert_equal(str(dgu_linked_user(user)),
                '<a href="/publisher/national-health-service">National Health Service</a>')

        with publisher_user():
            assert_equal(str(dgu_linked_user(user)),
                '<a href="/user/101">NHS Editor imported f...</a>')

        with sysadmin_user():
            assert_equal(str(dgu_linked_user(user)),
                '<a href="/user/101">NHS Editor imported f...</a>')

    def test_view_system_user(self):
        # created on the API
        user_dict = get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
        user = user_dict['name']

        with regular_user():
            assert_equal(str(dgu_linked_user(user)), 'System Process')

        with publisher_user():
            assert_equal(str(dgu_linked_user(user, maxlength=100)),
                '<a href="/data/user/test.ckan.net">System Process (Site user)</a>')

        with sysadmin_user():
            assert_equal(str(dgu_linked_user(user, maxlength=100)),
                '<a href="/data/user/test.ckan.net">System Process (Site user)</a>')


class TestUserProperties(PylonsTestCase):
    @classmethod
    def setup_class(cls):
        PylonsTestCase.setup_class()

    def test_name(self):
        user = factories.User()
        name, obj, drupal_id, type_, this_is_me = user_properties(user['name'])
        assert_equal(name, user['name'])

    def test_obj(self):
        user = factories.User()
        name, obj, drupal_id, type_, this_is_me = user_properties(user['name'])
        assert isinstance(obj, model.User)
        assert_equal(obj.name, user['name'])

    def test_this_is_not_me(self):
        user = factories.User()
        c.user = 'someone else'
        name, obj, drupal_id, type_, this_is_me = user_properties(user['name'])
        assert_equal(this_is_me, False)

    def test_this_is_me(self):
        user = factories.User()
        c.user = user['name']
        name, obj, drupal_id, type_, this_is_me = user_properties(user['name'])
        assert_equal(this_is_me, True)

    def test_blank_user_has_no_type(self):
        name, obj, drupal_id, type_, this_is_me = user_properties('')
        assert_equal(type_, None)

    def test_random_user_has_no_type(self):
        user = factories.User()
        name, obj, drupal_id, type_, this_is_me = user_properties(user['name'])
        assert_equal(type_, None)

    def test_sysadmin_is_official(self):
        user = factories.User(sysadmin=True)
        name, obj, drupal_id, type_, this_is_me = user_properties(user['name'])
        assert_equal(type_, 'official')

    def test_publisher_is_official(self):
        user = factories.User()
        org_users = [{'name': user['name'], 'capacity': 'editor'}]
        factories.Organization(users=org_users, category='ministerial-department')
        name, obj, drupal_id, type_, this_is_me = user_properties(user['name'])
        assert_equal(type_, 'official')


class TestRenderPartialDatestamp(object):
    def test_full_timestamp(self):
        assert_equal(render_partial_datestamp('2012-06-12T17:33:02.884649'),
                     '12/06/2012')

    def test_date(self):
        assert_equal(render_partial_datestamp('2012-06-12'), '12/06/2012')

    def test_month(self):
        assert_equal(render_partial_datestamp('2012-06'), 'Jun 2012')

    def test_year(self):
        assert_equal(render_partial_datestamp('2012'), '2012')

    def test_string(self):
        assert_equal(render_partial_datestamp('feb'), '')

    def test_invalid_date(self):
        assert_equal(render_partial_datestamp('2012-01-50'), '')


class TestRenderMandates(object):
    def test_single(self):
        assert_equal(render_mandates(
            {'mandate': json.dumps(['http://example.com'])}),
            '<a href="http://example.com" target="_blank">http://example.com</a>')

    def test_multiple(self):
        assert_equal(render_mandates(
            {'mandate': json.dumps(['http://example.com/a', 'http://example.com/b'])}),
            '<a href="http://example.com/a" target="_blank">http://example.com/a</a><br>'
            '<a href="http://example.com/b" target="_blank">http://example.com/b</a>')

    def test_escaping_umlaut(self):
        # http://www.example.org/Durst (umlaut on the u)
        assert_equal(render_mandates(
            {'mandate': json.dumps(['http://www.example.org/D\u00fcrst'])}),
            '<a href="http://www.example.org/D\\u00fcrst" target="_blank">http://www.example.org/D\\u00fcrst</a>')

    def test_escaping_spaces_and_symbols(self):
        # http://www.example.org/foo bar/qux<>?\^`{|}
        assert_equal(render_mandates(
            {'mandate': json.dumps(['http://www.example.org/foo bar/qux<>?\\\^`{|}'])}),
            '<a href="http://www.example.org/foo bar/qux&lt;&gt;?\\\\^`{|}" target="_blank">http://www.example.org/foo bar/qux&lt;&gt;?\\\\^`{|}</a>')

    def test_escaping_hash(self):
        # http://2.example.org#frag2
        assert_equal(render_mandates(
            {'mandate': json.dumps(['http://2.example.org#frag2'])}),
            '<a href="http://2.example.org#frag2" target="_blank">http://2.example.org#frag2</a>')

    def test_escaping_invalid_chars(self):
        assert_equal(render_mandates(
            {'mandate': json.dumps(['http://example.com"><script src="nasty.js">'])}),
            '<a href="http://example.com&#34;&gt;&lt;script src=&#34;nasty.js&#34;&gt;" target="_blank">http://example.com&#34;&gt;&lt;script src=&#34;nasty.js&#34;&gt;</a>')
