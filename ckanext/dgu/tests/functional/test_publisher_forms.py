from nose.tools import assert_equal, assert_raises

from ckan import model
from ckan.lib.create_test_data import CreateTestData
from ckan.tests import WsgiAppCase, CommonFixtureMethods, url_for
from ckan.tests.html_check import HtmlCheckMethods
from ckan.tests.mock_mail_server import SmtpServerHarness
from ckanext.dgu.lib import publisher as publib
from ckanext.dgu.testtools.create_test_data import DguCreateTestData


class TestEdit(WsgiAppCase, HtmlCheckMethods):

    @classmethod
    def setup_class(cls):
        DguCreateTestData.create_dgu_test_data()
        cls.publisher_controller = 'ckanext.dgu.controllers.publisher:PublisherController'

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_0_new_publisher(self):
        # Load form
        offset = url_for('/publisher/new')
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'sysadmin'})
        assert 'Add A Publisher' in res, res
        form = res.forms[0]

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
        assert_equal(res.header_dict['Location'], 'http://localhost/publisher/test-name')

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
        assert 'Edit: %s' % group.title in res, res
        form = res.forms[0]
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
        form['category'] = 'alb'
        form['abbreviation'] = 'nhs'
        res = form.submit('save', status=302, extra_environ={'REMOTE_USER': 'nhsadmin'})
        assert_equal(res.header_dict['Location'], 'http://localhost/publisher/new-name')

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
        assert_equal(publisher.extras['category'], 'alb')
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
        assert 'Add A Publisher' in res, res
        form = res.forms[0]

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
        form = res.forms[0]
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
        assert 'Edit: %s' % group.title in res, res
        form = res.forms[0]

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
        form = res.forms[0]
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
            assert_equal(set([grp.name for grp in group.active_packages()]),
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
        assert 'Edit: %s' % group.title in res, res
        form = res.forms[0]

        # Make edit
        form['description'] = 'New description'
        res = form.submit('save', status=302, extra_environ={'REMOTE_USER': 'sysadmin'})
        assert_equal(res.header_dict['Location'], 'http://localhost/publisher/national-health-service')

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
        CreateTestData.create_groups([{'name': group_name,
                                       'packages': [u'cabinet-office-energy-use']}],
                                     admin_user_name='nhsadmin')

        group = model.Group.by_name(group_name)
        offset = url_for(controller=self.publisher_controller, action='edit', id=group_name)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'sysadmin'})
        main_res = self.main_div(res)
        assert 'Edit: %s' % group.title in main_res, main_res
        assert 'value="active" selected' in main_res, main_res

        # delete
        form = res.forms[0]
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
            assert_equal(set([grp.name for grp in group.active_packages()]),
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
        assert 'Users: %s' % group.title in res, res
        form = res.forms[0]
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
        form = res.forms[0]
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
        form = res.forms[0]
        form['reason'] = 'I am the director'
        res = form.submit('save', status=302, extra_environ={'REMOTE_USER': 'user'})
        msgs = SmtpServerHarness.smtp_thread.get_smtp_messages()
        assert_equal(len(msgs), 1)
        msg = msgs[0]
        assert_equal(msg[2], to_email_addresses) # to address

    def test_1_application_sent_to_publisher_admin(self):
        self.assert_application_sent_to_right_person('national-health-service', ['admin@nhs.gov.uk'])

    def test_2_application_sent_to_parent_publisher_admin(self):
        self.assert_application_sent_to_right_person('barnsley-primary-care-trust', ['admin@nhs.gov.uk'])

    def test_3_publisher_not_found(self):
        offset = url_for('/publisher/apply/unheardof')
        res = self.app.get(offset, status=404, extra_environ={'REMOTE_USER': 'user'})
