import os
from nose.tools import assert_equal, assert_raises

from ckan import model
from ckan.lib.create_test_data import CreateTestData
from ckan.tests import WsgiAppCase, CommonFixtureMethods, url_for
from ckan.tests.html_check import HtmlCheckMethods
from ckan.tests.mock_mail_server import SmtpServerHarness
from ckanext.dgu.lib import publisher as publib
from ckanext.dgu.testtools.create_test_data import DguCreateTestData


class TestInventory(WsgiAppCase, HtmlCheckMethods):

    @classmethod
    def setup_class(cls):
        DguCreateTestData.create_dgu_test_data()
        cls.inv_controller = 'ckanext.dgu.controllers.inventory:InventoryController'

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_inventory_auth(self):
        offset = url_for('/inventory/national-health-service/edit')

        # Should be able to access
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'sysadmin'})
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'nhsadmin'})

        # Should not be able to access
        res = self.app.get(offset, status=401, extra_environ={'REMOTE_USER': 'barnsley_admin'})
        res = self.app.get(offset, status=401, extra_environ={'REMOTE_USER': 'nhseditor'})
        res = self.app.get(offset, status=401, extra_environ={'REMOTE_USER': 'co_editor'})
        res = self.app.get(offset, status=401, extra_environ={'REMOTE_USER': ''})


    def test_inventory_auth_levels(self):
        offset = url_for('/inventory/barnsley-primary-care-trust/edit')

        # Should be able to access
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'sysadmin'})
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'nhsadmin'})
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'barnsley_admin'})

        # Should not be able to access
        res = self.app.get(offset, status=401, extra_environ={'REMOTE_USER': 'nhseditor'})
        res = self.app.get(offset, status=401, extra_environ={'REMOTE_USER': 'co_editor'})
        res = self.app.get(offset, status=401, extra_environ={'REMOTE_USER': ''})


    def test_get_download(self):
        offset = url_for('/inventory/national-health-service/edit')

        # Should be able to access
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'sysadmin'})
        form = res.forms[0]

        # Sneaking in another quick auth check although probably not that serious
        res = form.submit(status=401, extra_environ={'REMOTE_USER': 'co_editor'})
        res = form.submit(status=200, extra_environ={'REMOTE_USER': 'sysadmin'})
        item_count = res.body.count('\n') - 1 # -1 for header
        assert item_count == 1, res.body

        form['include_sub'] = 'checked'
        res = form.submit(status=200, extra_environ={'REMOTE_USER': 'sysadmin'})
        item_count = res.body.count('\n') - 1 # -1 for header
        assert item_count == 2, item_count

    def test_upload(self):
        import tempfile
        offset = url_for('/inventory/national-health-service/edit')

        # Should be able to access
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'sysadmin'})
        form = res.forms[1]

        # Sneaking in another quick auth check although probably not that serious
        res = form.submit(status=401, extra_environ={'REMOTE_USER': 'co_editor'})

        # Expect redirect when no file specified
        res = form.submit(status=302, extra_environ={'REMOTE_USER': 'nhsadmin'})

        # Upload an actual file.  Write an empty one to disk first..
        handle, filename = tempfile.mkstemp(suffix='.csv')
        os.close(handle)
        try:
            res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'sysadmin'})
            form = res.forms[1]
            res = form.submit(status=200, extra_environ={'REMOTE_USER': 'nhsadmin'}, upload_files=[("upload", filename)])
            assert 'alert-danger' in res.body, res.body  # Not enough content
        finally:
            if os.path.exists(filename):
                os.unlink(filename)

        # Upload an actual file.  Write an invalid one to disk first..
        handle, filename = tempfile.mkstemp(suffix='.csv')
        os.write(handle, "Test, Test")
        os.close(handle)

        try:
            res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'sysadmin'})
            form = res.forms[1]
            res = form.submit(status=200, extra_environ={'REMOTE_USER': 'nhsadmin'}, upload_files=[("upload", filename)])
            assert 'Upload error' in res.body, res.body  # Not enough columns
        finally:
            if os.path.exists(filename):
                os.unlink(filename)

        # Upload an actually valid file.
        handle, filename = tempfile.mkstemp(suffix='.csv')
        os.write(handle, "Title,Description,Owner,Date\r\n")
        os.write(handle, '"Test Dataset", "A description", "National Health Service", "21/02/1973"')
        os.close(handle)

        try:
            res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'sysadmin'})
            form = res.forms[1]
            res = form.submit(status=200, extra_environ={'REMOTE_USER': 'nhsadmin'}, upload_files=[("upload", filename)])
            content = res.body
            assert "Import was successful" in content, content
            assert "Test Dataset" in content, content
            assert "Added" in content, content
        finally:
            if os.path.exists(filename):
                os.unlink(filename)



