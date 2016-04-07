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
                                     get_resource_formats,
                                     dgu_format_icon,
                                     dgu_format_name,
                                     detect_license_id,
                                     get_license_from_id,
                                     linkify,
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


class TestGetResourceFormats(object):
    def test_is_json(self):
        assert_equal(get_resource_formats()[:2], '["')

    def test_first_few_values(self):
        assert_equal(
            sorted(json.loads(get_resource_formats()))[:10],
            [u'API', u'ArcGIS Map Preview', u'ArcGIS Map Service',
             u'ArcGIS Online Map', u'Atom Feed', u'BIN',
             u'BMP', u'CSV', u'DCR', u'DOC'])


class TestFormatIcon(object):
    def test_is_literal(self):
        assert_equal(str(type(dgu_format_icon('Csv'))),
                     "<class 'webhelpers.html.builder.literal'>")

    def test_link_for_csv(self):
        assert_equal(
            str(dgu_format_icon('Csv')),
            '<img src="/images/fugue/document-invoice.png" height="16px" width="16px" alt="None" class="inline-icon " /> ')

    def test_link_for_word(self):
        assert_equal(
            str(dgu_format_icon('word')),
            '<img src="/images/fugue/document-word.png" height="16px" width="16px" alt="None" class="inline-icon " /> ')

    def test_link_for_unknown_format(self):
        assert_equal(
            str(dgu_format_icon('unknown')),
            '<img src="/images/fugue/document.png" height="16px" width="16px" alt="None" class="inline-icon " /> ')


class TestFormatName(object):
    def test_csv(self):
        assert_equal(dgu_format_name('Csv'), 'CSV')

    def test_word(self):
        assert_equal(dgu_format_name('word'), 'DOC')

    def test_link_for_unknown_format(self):
        assert_equal(dgu_format_name('unknown'), 'unknown')


class TestGetLicenseById(object):
    def test_known(self):
        assert_equal(get_license_from_id('uk-ogl').title,
                     u'UK Open Government Licence (OGL)')

    def test_ukknown(self):
        assert_equal(get_license_from_id('made-up'), None)

    def test_blank(self):
        assert_equal(get_license_from_id(''), None)


class TestDetectLicenseId(object):
    def test_blank(self):
        assert_equal(detect_license_id(''), ('', None))

    def test_not_ogl(self):
        assert_equal(detect_license_id('Data is freely available for research or commercial use providing that the originators are acknowledged in any publications produced.'),
                     ('', None))

    def test_not_ogl2(self):
        assert_equal(detect_license_id('bogl'),
                     ('', None))

    def test_ogl(self):
        assert_equal(detect_license_id('Open Government Licence'),
                     ('uk-ogl', True))

    def test_ogl_mispelt(self):
        assert_equal(detect_license_id('Open Government License'),
                     ('uk-ogl', True))

    def test_ogl_abbreviation(self):
        assert_equal(detect_license_id('OGL Licence'),
                     ('uk-ogl', True))

    def test_ogl_abbreviation_in_parens(self):
        assert_equal(detect_license_id('Some licence (OGL)'),
                     ('uk-ogl', False))

    def test_ogl_url_in_parens(self):
        assert_equal(detect_license_id('Some licence (http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)'),
                     ('uk-ogl', False))

    def test_ogl_url_with_trailing_semicolon(self):
        assert_equal(detect_license_id('Some licence (http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/; More terms'),
                     ('uk-ogl', False))

    def test_ogl_and_require_citation(self):
        assert_equal(detect_license_id('Use of data subject to the Terms and Conditions of the OGL (Open Government Licence) and you must cite "Natural England" as the source.'),
                     ('uk-ogl', False))

    def test_ogl_and_require_citation2(self):
        assert_equal(detect_license_id('Released under the Open Government Licence (OGL), citation of "Natural England" as the source required.'),
                     ('uk-ogl', False))

    def test_ogl_with_other_url(self):
        assert_equal(detect_license_id('By using this data you are accepting the terms of the Natural England-OS Open Government Licence (https://www.gov.uk/government/uploads/system/uploads/attachment_data/file/391764/OGL-NE-OS.pdf). For further info contact Natural England (UK +44) 0 845 600 3900 enquiries@naturalengland.org.uk <https://www.gov.uk/government/uploads/system/uploads/attachment_data/file/391764/OGL-NE-OS.pdf>'),
                     ('uk-ogl', False))

    def test_ogl_url(self):
        assert_equal(detect_license_id('http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/'),
                     ('uk-ogl', True))

    def test_ogl_variations_are_wholy_ogl_1(self):
        assert_equal(detect_license_id('Open Government Licence v3.0'),
                     ('uk-ogl', True))

    def test_ogl_variations_are_wholy_ogl_2(self):
        assert_equal(detect_license_id('Open government license for public sector information.; http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/'),
                     ('uk-ogl', True))

    def test_ogl_variations_are_wholy_ogl_3(self):
        assert_equal(detect_license_id('Link to the Open Government Licence; Licence; http://www.nationalarchives.gov.uk/doc/open-government-licence/'),
                     ('uk-ogl', True))

    def test_ogl_variations_are_wholy_ogl_4(self):
        assert_equal(detect_license_id('Link to the Open Government Licence; Link to the Ordnance Survey Open Data Licence; Licence; http://www.ordnancesurvey.co.uk/oswebsite/docs/licences/os-opendata-licence.pdf; http://www.nationalarchives.gov.uk/doc/open-government-licence/'),
                     ('uk-ogl', True))

    def test_ogl_variations_are_wholy_ogl_5(self):
        assert_equal(detect_license_id('Open Government Licence.; http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/'),
                     ('uk-ogl', True))

    def test_ogl_variations_are_wholy_ogl_6(self):
        assert_equal(detect_license_id('Use of data subject to the Terms and Conditions of the OGL (Open Government Licence): data is free to use for provided the source is acknowledged as specified in said document.'),
                     ('uk-ogl', True))

    def test_ogl_variations_are_wholy_ogl_7(self):
        assert_equal(detect_license_id('Released under the Open Government Licence (OGL), citation of publisher and online resource required on reuse.'),
                     ('uk-ogl', True))

    def test_ogl_variations_are_wholy_ogl_8(self):
        assert_equal(detect_license_id('Link to the Open Government Licence; Licence; http://www.nationalarchives.gov.uk/doc/open-government-licence/'),
                     ('uk-ogl', True))

    def test_ogl_variations_are_wholy_ogl_9(self):
        assert_equal(detect_license_id('Link to the Open Government Licence; Link to the Ordnance Survey Open Data Licence; http://www.ordnancesurvey.co.uk/oswebsite/docs/licences/os-opendata-licence.pdf; http://www.nationalarchives.gov.uk/doc/open-government-licence/'),
                     ('uk-ogl', True))

    def test_ogl_variations_are_wholy_ogl_10(self):
        assert_equal(detect_license_id('Link to the Open Government Licence; Link to the Ordnance Survey Open Data Licence; Licence; http://www.ordnancesurvey.co.uk/oswebsite/docs/licences/os-opendata-licence.pdf; http://www.nationalarchives.gov.uk/doc/open-government-licence/'),
                     ('uk-ogl', True))

    def test_ogl_variations_are_wholy_ogl_11(self):
        assert_equal(detect_license_id('Open Government Licence.; http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/'),
                     ('uk-ogl', True))

    def test_ogl_variations_are_wholy_ogl_12(self):
        assert_equal(detect_license_id('Open Government Licence; None'),
                     ('uk-ogl', True))

    def test_ogl_variations_are_wholy_ogl_13(self):
        assert_equal(detect_license_id('Open Government Licence; http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/'),
                     ('uk-ogl', True))

    def test_ogl_variations_are_wholy_ogl_14(self):
        assert_equal(detect_license_id('Open Government Licences and agreements explained; http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/;'),
                     ('uk-ogl', True))

    def test_ogl_variations_are_wholy_ogl_15(self):
        assert_equal(detect_license_id('In accessing or using this data, you are deemed to have accepted the terms of the UK Open Government Licence v3.0. - http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/'),
                     ('uk-ogl', True))

    def test_ogl_variations_are_wholy_ogl_16(self):
        assert_equal(detect_license_id('Open Government Licence: attribution required; http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/'),
                     ('uk-ogl', True))

    def test_ogl_variations_are_wholy_ogl_17(self):
        assert_equal(detect_license_id('Public data (Crown Copyright) - Open Government Licence Terms and Conditions apply'),
                     ('uk-ogl', True))

    def test_ne(self):
        # should not really say it is OGL, but the slash and dash are seen as word boundaries
        assert_equal(detect_license_id('https://www.gov.uk/government/uploads/system/uploads/attachment_data/file/391764/OGL-NE-OS.pdf'),
                     ('uk-ogl', False))


class TestLinkify(object):
    def test_no_link(self):
        assert_equal(linkify('no link'), 'no link')

    def test_just_a_link(self):
        assert_equal(linkify('http://example.com/page.html'),
                     '<a href="http://example.com/page.html" target="_blank">'
                     'http://example.com/page.html</a>')

    def test_link_in_text(self):
        assert_equal(linkify('Hello http://example.com/page.html link'),
                     'Hello '
                     '<a href="http://example.com/page.html" target="_blank">'
                     'http://example.com/page.html</a> link')

    def test_trailing_dot_excluded_from_link(self):
        assert_equal(linkify('Hello http://example.com/page.html. link'),
                     'Hello '
                     '<a href="http://example.com/page.html" target="_blank">'
                     'http://example.com/page.html</a>. link')

    def test_trailing_semicolon_excluded_from_link(self):
        # Semi-colons break up bits of licences harvested e.g. GEMINI
        assert_equal(linkify('Hello http://example.com/page.html; link'),
                     'Hello '
                     '<a href="http://example.com/page.html" target="_blank">'
                     'http://example.com/page.html</a>; link')

    def test_brackets_excluded_from_link(self):
        # Licences harvested from GEMINI will have anchors put in brackets like
        # this
        assert_equal(linkify('Hello (http://example.com/page.html) hello'),
                     'Hello '
                     '(<a href="http://example.com/page.html" target="_blank">'
                     'http://example.com/page.html</a>) hello')
