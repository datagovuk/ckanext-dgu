from nose.tools import assert_equal, assert_raises
import mock

from paste.fixture import Field, html_unquote, Radio, _parse_attrs, Form

from ckan import model
from ckan.lib.create_test_data import CreateTestData
from ckan.tests import WsgiAppCase, CommonFixtureMethods, url_for
from ckan.tests.html_check import HtmlCheckMethods
from ckan.tests.mock_mail_server import SmtpServerHarness
from ckanext.dgu.lib import publisher as publib
from ckanext.dgu.testtools.create_test_data import DguCreateTestData


class TestEdit(WsgiAppCase):

    @classmethod
    def setup_class(cls):
        DguCreateTestData.create_dgu_test_data()
        cls.publisher_controller = 'ckanext.dgu.controllers.publisher:PublisherController'

        # monkey patch webtest to support multiple select boxes
        Field.classes['multiple_select'] = MultipleSelect
        Form._parse_fields = _parse_fields

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def _main_div(self, html, div_name):
        start_div = html.find(u'<div role="%s"' % div_name)
        end_div = html.find(u'<!-- #%s -->' % div_name)
        if end_div == -1:
            end_div = html.find(u'<!-- /%s -->' % div_name)
        div_html = html[start_div:end_div]
        assert div_html
        return div_html

    def test_0_new_publisher(self):
        # Load form
        offset = url_for('/publisher/new')
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'sysadmin'})
        assert 'Save Changes' in res, res
        form = res.forms[1]

        # Fill in form
        form['title'] = 'New publisher'
        publisher_name = 'test-name'
        form['name'] = publisher_name
        form['description'] = 'New description'
        form['contact-name'] = 'Head of Comms'
        form['contact-email'] = 'comms@nhs.gov.uk'
        form['contact-phone'] = '01234 4567890'
        form['foi-name'] = 'Head of FOI Comms'
        form['foi-email'] = 'foi-comms@nhs.gov.uk'
        form['foi-phone'] = '0845 4567890'
        form['foi-web'] = 'http://whatdotheyknow.com'
        form['category'] = 'grouping'
        res = form.submit('save', status=302, extra_environ={'REMOTE_USER': 'sysadmin'})

        # The redirect is to /organization, but this is then handled by config/routing.
        assert_equal(res.header_dict['Location'], 'http://localhost/organization/test-name')

        # Check saved object
        publisher = model.Group.by_name(publisher_name)
        assert_equal(publisher.title, 'New publisher')
        assert_equal(publisher.description, 'New description')
        assert_equal(publisher.extras['contact-name'], 'Head of Comms')
        assert_equal(publisher.extras['contact-email'], 'comms@nhs.gov.uk')
        assert_equal(publisher.extras['contact-phone'], '01234 4567890')
        assert_equal(publisher.extras['foi-name'], 'Head of FOI Comms')
        assert_equal(publisher.extras['foi-email'], 'foi-comms@nhs.gov.uk')
        assert_equal(publisher.extras['foi-phone'], '0845 4567890')
        assert_equal(publisher.extras['foi-web'], 'http://whatdotheyknow.com')
        assert_equal(publisher.extras['category'], 'grouping')

    def test_1_edit_publisher(self):
        # Load form
        publisher_name = 'national-health-service'
        group = model.Group.by_name(publisher_name)
        offset = url_for('/publisher/edit/%s' % publisher_name)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'nhsadmin'})
        assert 'Edit Publisher' in res, res
        form = res.forms[1]
        # TODO assert_equal(form['title'].value, 'National Health Service')
        assert_equal(form['name'].value, 'national-health-service')
        assert_equal(form['description'].value, '')
        # TODO assert_equal(form['parent'].value, 'dept-health')
        assert_equal(form['contact-name'].value, '')
        assert_equal(form['contact-email'].value, 'contact@nhs.gov.uk')
        assert_equal(form['foi-name'].value, '')
        assert_equal(form['foi-email'].value, '')
        assert_equal(form['foi-web'].value, '')
        assert_equal(form['category'].value, 'grouping')
        assert_equal(form['abbreviation'].value, 'NHS')

        # Make edit
        publisher_name = 'new-name'
        form['name'] = publisher_name
        form['description'] = 'New description'
        form['contact-name'] = 'Head of Comms'
        form['contact-email'] = 'comms@nhs.gov.uk'
        form['contact-phone'] = '01234 4567890'
        form['foi-name'] = 'Head of FOI Comms'
        form['foi-email'] = 'foi-comms@nhs.gov.uk'
        form['foi-phone'] = '0845 4567890'
        form['foi-web'] = 'http://whatdotheyknow.com'
        form['category'] = 'non-ministerial-department'
        form['abbreviation'] = 'nhs'
        res = form.submit('save', status=302, extra_environ={'REMOTE_USER': 'nhsadmin'})

        # The return value is /organization, which routing then redirects to publisher
        assert_equal(res.header_dict['Location'], 'http://localhost/organization/new-name')

        # Check saved object
        publisher = model.Group.by_name(publisher_name)

        assert_equal(publisher.description, 'New description')
        assert_equal(publisher.extras['contact-name'], 'Head of Comms')
        assert_equal(publisher.extras['contact-email'], 'comms@nhs.gov.uk')
        assert_equal(publisher.extras['contact-phone'], '01234 4567890')
        assert_equal(publisher.extras['foi-name'], 'Head of FOI Comms')
        assert_equal(publisher.extras['foi-email'], 'foi-comms@nhs.gov.uk')
        assert_equal(publisher.extras['foi-phone'], '0845 4567890')
        assert_equal(publisher.extras['foi-web'], 'http://whatdotheyknow.com')
        assert_equal(publisher.extras['category'], 'non-ministerial-department')
        assert_equal(publisher.extras['abbreviation'], 'nhs')

        # restore name for other tests
        #model.repo.new_revision()
        #publisher.name = 'national-health-service'
        #model.repo.commit_and_remove()
        model.repo.rebuild_db()
        DguCreateTestData.create_dgu_test_data()

    def test_2_new_validation_error(self):
        # Load form
        offset = url_for('/publisher/new')
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'sysadmin'})
        assert 'Save Changes' in res, res
        form = res.forms[1]

        # Fill in form
        form['title'] = 'New publisher'
        form['name'] = '' # cause validation error
        form['description'] = 'New description'
        form['contact-name'] = 'Head of Comms'
        form['contact-email'] = 'comms@nhs.gov.uk'
        form['contact-phone'] = '01234 4567890'
        form['foi-name'] = 'Head of FOI Comms'
        form['foi-email'] = 'foi-comms@nhs.gov.uk'
        form['foi-phone'] = '0845 4567890'
        form['foi-web'] = 'http://whatdotheyknow.com'
        form['category'] = 'grouping'
        form['abbreviation'] = 'tn2'
        res = form.submit('save', status=200, extra_environ={'REMOTE_USER': 'sysadmin'})
        assert 'Errors in form' in res.body

        # Check redisplayed form
        form = res.forms[1]
        assert_equal(form['title'].value, 'New publisher')
        assert_equal(form['description'].value, 'New description')
        assert_equal(form['contact-name'].value, 'Head of Comms')
        assert_equal(form['contact-email'].value, 'comms@nhs.gov.uk')
        assert_equal(form['contact-phone'].value, '01234 4567890')
        assert_equal(form['foi-name'].value, 'Head of FOI Comms')
        assert_equal(form['foi-email'].value, 'foi-comms@nhs.gov.uk')
        assert_equal(form['foi-phone'].value, '0845 4567890')
        assert_equal(form['foi-web'].value, 'http://whatdotheyknow.com')
        assert_equal(form['category'].value, 'grouping')
        assert_equal(form['abbreviation'].value, 'tn2')

    def test_2_edit_validation_error(self):
        # Load form
        publisher_name = 'national-health-service'
        group = model.Group.by_name(publisher_name)
        offset = url_for('/publisher/edit/%s' % publisher_name)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'nhsadmin'})
        assert 'Edit Publisher' in res, res
        assert group.title in res, res
        form = res.forms[1]

        # Fill in form
        # TODO form['title'] = 'Edit publisher'
        form['name'] = '' # cause validation error
        form['description'] = 'New description'
        form['contact-name'] = 'Head of Comms'
        form['contact-email'] = 'comms@nhs.gov.uk'
        form['contact-phone'] = '01234 4567890'
        form['foi-name'] = 'Head of FOI Comms'
        form['foi-email'] = 'foi-comms@nhs.gov.uk'
        form['foi-phone'] = '0845 4567890'
        form['foi-web'] = 'http://whatdotheyknow.com'
        form['category'] = 'grouping'
        form['abbreviation'] = 'tn2'
        res = form.submit('save', status=200, extra_environ={'REMOTE_USER': 'sysadmin'})
        assert 'Errors in form' in res.body

        # Check redisplayed form
        form = res.forms[1]
        # TODO assert_equal(form['title'].value, 'New publisher')
        assert_equal(form['description'].value, 'New description')
        assert_equal(form['contact-name'].value, 'Head of Comms')
        assert_equal(form['contact-email'].value, 'comms@nhs.gov.uk')
        assert_equal(form['contact-phone'].value, '01234 4567890')
        assert_equal(form['foi-name'].value, 'Head of FOI Comms')
        assert_equal(form['foi-email'].value, 'foi-comms@nhs.gov.uk')
        assert_equal(form['foi-phone'].value, '0845 4567890')
        assert_equal(form['foi-web'].value, 'http://whatdotheyknow.com')
        assert_equal(form['category'].value, 'grouping')
        assert_equal(form['abbreviation'].value, 'tn2')

    def test_2_edit_publisher_does_not_affect_others(self):
        publisher_name = 'national-health-service'
        def check_related_publisher_properties():
            group = model.Group.by_name(publisher_name)
            # datasets
            assert_equal(set([grp.name for grp in group.packages()]),
                         set([u'directgov-cota']))
            # parents

            doh = model.Group.by_name('dept-health')
            child_groups_of_doh = [grp.name for grp in list(publib.go_down_tree(doh))]
            assert publisher_name in child_groups_of_doh, child_groups_of_doh
            # children

            child_groups = set([grp.name for grp in list(publib.go_down_tree(group))])
            assert set([u'newham-primary-care-trust', u'barnsley-primary-care-trust']) <= child_groups, child_groups
            # admins & editors
            assert_equal(set([user.name for user in group.members_of_type(model.User, capacity='admin')]),
                         set(('nhsadmin',)))
            assert_equal(set([user.name for user in group.members_of_type(model.User, capacity='editor')]),
                         set(('nhseditor', 'user_d101')))
        check_related_publisher_properties()

        # Load form
        group = model.Group.by_name(publisher_name)
        offset = url_for('/publisher/edit/%s' % publisher_name)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'sysadmin'})
        assert 'Edit Publisher' in res, res
        assert group.title in res, res
        form = res.forms[1]

        # Make edit
        form['description'] = 'New description'
        res = form.submit('save', status=302, extra_environ={'REMOTE_USER': 'sysadmin'})
        # This call will redirect users to /organization not /publisher, but we then redirect that call.
        assert_equal(res.header_dict['Location'], 'http://localhost/organization/national-health-service')

        # Check saved object
        publisher = model.Group.by_name(publisher_name)
        assert_equal(publisher.description, 'New description')

        check_related_publisher_properties()

    def test_3_edit_non_existent_publisher(self):
        name = u'group_does_not_exist'
        offset = url_for(controller=self.publisher_controller, action='edit', id=name)
        res = self.app.get(offset, status=404)

    def test_4_delete_publisher(self):
        group_name = 'deletetest'
        CreateTestData.create_groups([{'name': group_name, 'is_organization': True,
                                       'packages': [u'cabinet-office-energy-use']}],
                                     admin_user_name='nhsadmin')

        group = model.Group.by_name(group_name)
        offset =url_for(controller=self.publisher_controller, action='edit', id=group.id)

        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'sysadmin'})
        main_res = self._main_div(res.body, "main")
        assert 'Edit Publisher' in main_res, main_res
        assert 'value="active" selected' in main_res, main_res

        # delete
        form = res.forms[1]
        form['state'] = 'deleted'
        form['category'] = 'private' # to get it to validate
        res = form.submit('save', status=302, extra_environ={'REMOTE_USER': 'sysadmin'})

        group = model.Group.by_name(group_name)
        assert_equal(group.state, 'deleted')
        res = self.app.get(offset, status=401)

    def test_5_appoint_editor(self):
        publisher_name = 'national-health-service'
        def check_related_publisher_properties():
            group = model.Group.by_name(publisher_name)
            # datasets
            assert_equal(set([grp.name for grp in group.packages()]),
                         set([u'directgov-cota']))
            # parents
            child_groups = [grp.name for grp in model.Group.by_name('dept-health').get_children_groups('organization')]
            assert publisher_name in child_groups, child_groups

        check_related_publisher_properties()

        DguCreateTestData.create_user(name='test_user')
        assert model.User.by_name(u'test_user')
        # Load form
        group = model.Group.by_name(unicode(publisher_name))
        offset = url_for('/publisher/users/%s' % publisher_name)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'nhsadmin'})
        assert 'Edit User Permissions' in res, res
        form = res.forms[1]
        assert_equal(form['users__0__name'].value, 'nhsadmin')
        assert_equal(form['users__0__capacity'].value, 'admin')
        assert_equal(form['users__1__name'].value, 'nhseditor')
        assert_equal(form['users__1__capacity'].value, 'editor')
        assert_equal(form['users__2__name'].value, 'user_d101')
        assert_equal(form['users__2__capacity'].value, 'editor')
        assert_equal(form['users__3__name'].value, '')

        # Edit the form
        form['users__3__name'] = 'test_user'
        res = form.submit('save', status=302, extra_environ={'REMOTE_USER': 'nhsadmin'})
        assert_equal(res.header_dict['Location'], 'http://localhost/publisher/national-health-service')

        # Check saved object
        group = model.Group.by_name(unicode(publisher_name))
        assert_equal(set([user.name for user in group.members_of_type(model.User, capacity='admin')]),
                     set(('nhsadmin',)))
        assert_equal(set([user.name for user in group.members_of_type(model.User, capacity='editor')]),
                     set(('nhseditor', 'user_d101', 'test_user')))

        check_related_publisher_properties()

class TestApply(WsgiAppCase, HtmlCheckMethods, SmtpServerHarness):

    @classmethod
    def setup_class(cls):
        DguCreateTestData.create_dgu_test_data()
        cls.publisher_controller = 'ckanext.dgu.controllers.publisher:PublisherController'
        import ckanext.dgu.model.publisher_request as pr_model
        pr_model.init_tables(model.meta.engine)
        SmtpServerHarness.setup_class()

    @classmethod
    def teardown_class(cls):
        SmtpServerHarness.teardown_class()
        model.repo.rebuild_db()

    def teardown(self):
        SmtpServerHarness.smtp_thread.clear_smtp_messages()

    def test_0_basic_application(self):
        # Load form
        publisher_name = 'dept-health'
        group = model.Group.by_name(unicode(publisher_name))
        offset = url_for('/publisher/apply/%s' % publisher_name)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'user'})
        assert 'Apply for membership' in res, res
        form = res.forms[1]
        print form
        parent_publisher_id = form['parent'].value
        parent_publisher_name = model.Group.get(parent_publisher_id).name
        assert_equal(parent_publisher_name, publisher_name)
        assert_equal(form['reason'].value, '')

        # Fill in form
        form['reason'] = 'I am the director'
        res = form.submit('save', status=302, extra_environ={'REMOTE_USER': 'user'})
        assert_equal(res.header_dict['Location'], 'http://localhost/publisher/%s?__no_cache__=True' % publisher_name)

        # Check email sent
        msgs = SmtpServerHarness.smtp_thread.get_smtp_messages()
        assert_equal(len(msgs), 1)
        msg = msgs[0]
        assert_equal(msg[1], 'info@test.ckan.net') # from (ckan.mail_from in ckan/test-core.ini)
        assert_equal(msg[2], ["dohemail@localhost.local"]) # to (dgu.admin.name/email in dgu/test-core.ini)

    def assert_application_sent_to_right_person(self, publisher_name, to_email_addresses):
        offset = url_for('/publisher/apply/%s' % publisher_name)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'user'})
        assert 'Apply for membership' in res, res
        form = res.forms[1]
        form['reason'] = 'I am the director'
        res = form.submit('save', status=302, extra_environ={'REMOTE_USER': 'user'})
        msgs = SmtpServerHarness.smtp_thread.get_smtp_messages()
        assert_equal(len(msgs), 1)
        msg = msgs[0]
        assert_equal(msg[2], to_email_addresses) # to address

    def test_1_application_sent_to_publisher_admin(self):
        self.assert_application_sent_to_right_person('national-health-service', ['admin@nhs.gov.uk'])

    def test_2_application_sent_to_parent_publisher_admin(self):
        self.assert_application_sent_to_right_person('newham-primary-care-trust', ['admin@nhs.gov.uk'])

    def test_3_publisher_not_found(self):
        offset = url_for('/publisher/apply/unheardof')
        res = self.app.get(offset, status=404, extra_environ={'REMOTE_USER': 'user'})


################################
# From webtest, mostly v2.0.20 #
# MIT license                  #
################################


class NoValue(object):
    pass


def stringify(value):
    if isinstance(value, str):
        return value
    elif isinstance(value, unicode):
        return value.decode('utf8')
    else:
        return str(value)

# MultipleSelect is taken from webtest/forms.py
# but hacked because self.options is given to it by the old _parse_fields as 2
# value tuples instead of 3, so the text value is not available.


class MultipleSelect(Field):
    """Field representing ``<select multiple="multiple">``"""

    def __init__(self, *args, **attrs):
        super(MultipleSelect, self).__init__(*args, **attrs)
        self.options = []
        # Undetermined yet:
        self.selectedIndices = []
        self._forced_values = NoValue

    def force_value(self, values):
        """Like setting a value, except forces it (even for, say, hidden
        fields).
        """
        self._forced_values = values
        self.selectedIndices = []

    def select_multiple(self, value=None, texts=None):
        if value is not None and texts is not None:
            raise ValueError("Specify only one of value and texts.")

        # don't support selecting by text in this hacked version
        #if texts is not None:
        #    value = self._get_value_for_texts(texts)

        self.value = value

    def value__set(self, values):
        str_values = [stringify(value) for value in values]
        self.selectedIndices = []
        for i, (option, checked) in enumerate(self.options):
            if option in str_values:
                self.selectedIndices.append(i)
                str_values.remove(option)
        if str_values:
            raise ValueError(
                "Option(s) %r not found (from %s)"
                % (', '.join(str_values),
                   ', '.join([repr(o) for o, c in self.options])))

    def value__get(self):
        if self._forced_values is not NoValue:
            return self._forced_values
        elif self.selectedIndices:
            return [self.options[i][0] for i in self.selectedIndices]
        else:
            selected_values = []
            for option, checked in self.options:
                if checked:
                    selected_values.append(option)
            return selected_values if selected_values else None
    value = property(value__get, value__set)


# _parse_fields taken from webtest 1.4.3 forms.py
# but with the marked hack that detects multiple select

def _parse_fields(self):
    in_select = None
    in_textarea = None
    fields = {}
    for match in self._tag_re.finditer(self.text):
        end = match.group(1) == '/'
        tag = match.group(2).lower()
        if tag not in ('input', 'select', 'option', 'textarea',
                       'button'):
            continue
        if tag == 'select' and end:
            assert in_select, (
                '%r without starting select' % match.group(0))
            in_select = None
            continue
        if tag == 'textarea' and end:
            assert in_textarea, (
                "</textarea> with no <textarea> at %s" % match.start())
            in_textarea[0].value = html_unquote(self.text[in_textarea[1]:match.start()])
            in_textarea = None
            continue
        if end:
            continue
        attrs = _parse_attrs(match.group(3))
        if 'name' in attrs:
            name = attrs.pop('name')
        else:
            name = None
        if tag == 'option':
            in_select.options.append((attrs.get('value'),
                                      'selected' in attrs))
            continue
        if tag == 'input' and attrs.get('type') == 'radio':
            field = fields.get(name)
            if not field:
                field = Radio(self, tag, name, match.start(), **attrs)
                fields.setdefault(name, []).append(field)
            else:
                field = field[0]
                assert isinstance(field, Radio)
            field.options.append((attrs.get('value'),
                                  'checked' in attrs))
            continue
        tag_type = tag
        if tag == 'input':
            tag_type = attrs.get('type', 'text').lower()
        # HACK starts
        if tag_type == "select" and "multiple" in attrs:
            tag_type = "multiple_select"
        # HACK ends
        FieldClass = Field.classes.get(tag_type, Field)
        field = FieldClass(self, tag, name, match.start(), **attrs)
        if tag == 'textarea':
            assert not in_textarea, (
                "Nested textareas: %r and %r"
                % (in_textarea, match.group(0)))
            in_textarea = field, match.end()
        elif tag == 'select':
            assert not in_select, (
                "Nested selects: %r and %r"
                % (in_select, match.group(0)))
            in_select = field
        fields.setdefault(name, []).append(field)
    self.fields = fields


################################
# End of webtest bits          #
################################
