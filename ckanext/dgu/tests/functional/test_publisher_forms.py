from nose.tools import assert_equal, assert_raises

from ckan import model
from ckan.lib.create_test_data import CreateTestData
from ckan.tests import WsgiAppCase, CommonFixtureMethods, url_for
from ckan.tests.html_check import HtmlCheckMethods

from ckanext.dgu.testtools.create_test_data import DguCreateTestData


class TestEdit(WsgiAppCase, HtmlCheckMethods):

    @classmethod
    def setup_class(cls):
        DguCreateTestData.create_dgu_test_data()
        cls.publisher_controller = 'ckanext.dgu.controllers.publisher:PublisherController'

        # create a test package
        cls.packagename = u'test-pkg'
        model.repo.new_revision()
        model.Session.add(model.Package(name=cls.packagename))
        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_1_edit(self):
        # Load form
        publisher_name = 'national-health-service'
        group = model.Group.by_name(publisher_name)
        offset = url_for('/publisher/edit/%s' % publisher_name)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'nhsadmin'})
        assert 'Edit: %s' % group.title in res, res
        form = res.forms['publisher-edit']
        # TODO assert_equal(form['title'].value, 'National Health Service')
        assert_equal(form['name'].value, 'national-health-service')
        assert_equal(form['description'].value, '')
        # TODO assert_equal(form['parent'].value, 'dept-health')
        assert_equal(form['contact-name'].value, '')
        assert_equal(form['contact-email'].value, 'contact@nhs.gov.uk')
        assert_equal(form['foi-name'].value, '')
        assert_equal(form['foi-email'].value, '')

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

        # restore name for other tests
        model.repo.new_revision()
        publisher.name = 'national-health-service'
        model.repo.commit_and_remove()

    def test_2_edit_does_not_affect_others(self):
        publisher_name = 'national-health-service'
        def check_related_publisher_properties():
            group = model.Group.by_name(publisher_name)
            # datasets
            assert_equal(set([grp.name for grp in group.active_packages()]),
                         set([u'directgov-cota']))
            # parents
            child_groups = set([grp['name'] for grp in model.Group.by_name('dept-health').get_children_groups('publisher')])
            assert publisher_name in child_groups
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
        form = res.forms['publisher-edit']

        # Make edit
        form['description'] = 'New description'
        res = form.submit('save', status=302, extra_environ={'REMOTE_USER': 'sysadmin'})
        assert_equal(res.header_dict['Location'], 'http://localhost/publisher/national-health-service')

        # Check saved object
        publisher = model.Group.by_name(publisher_name)
        assert_equal(publisher.description, 'New description')

        check_related_publisher_properties()

    def test_edit_non_existent(self):
        name = u'group_does_not_exist'
        offset = url_for(controller=self.publisher_controller, action='edit', id=name)
        res = self.app.get(offset, status=404)

    def test_delete(self):
        group_name = 'deletetest'
        CreateTestData.create_groups([{'name': group_name,
                                       'packages': [self.packagename]}],
                                     admin_user_name='nhsadmin')

        group = model.Group.by_name(group_name)
        offset = url_for(controller=self.publisher_controller, action='edit', id=group_name)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'sysadmin'})
        main_res = self.main_div(res)
        assert 'Edit: %s' % group.title in main_res, main_res
        assert 'value="active" selected' in main_res, main_res

        # delete
        form = res.forms['publisher-edit']
        form['state'] = 'deleted'
        res = form.submit('save', status=302, extra_environ={'REMOTE_USER': 'sysadmin'})

        group = model.Group.by_name(group_name)
        assert_equal(group.state, 'deleted')
        res = self.app.get(offset, status=302)
        res = res.follow()
        assert 'login' in res.request.url, res.request.url
