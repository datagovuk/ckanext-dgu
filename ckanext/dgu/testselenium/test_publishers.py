import uuid, time
import selenium_test_base as t
from test_login import with_auth

class PublisherTests(t.TestBase):

    @with_auth('editor_username', 'editor_password')
    def test_edit(self):
        username = self.config.get('editor_username')
        group = self.config.get('publisher')
        if not group:
            raise Exception("%s does not have admin rights to amy publishers" % username)

        self.selenium.open('/publisher/%s' % group)
        self.selenium.click('link=Edit')
        self.wait()
        assert 'Edit: ' in self.selenium.get_title(), "Failed to load the edit publisher page"

        labels = self.selenium.get_select_options("id=category")
        self.selenium.select("id=category", "label=%s" % labels[1])

        self.selenium.type('id=notes', "Test description")
        self.selenium.click('id=save')
        self.wait()

        try:
            error = self.selenium.get_value('css=error-explanation')
            assert False, "An error was raised trying to save the publisher: %s" % error
        except:
            pass

        desc = self.selenium.get_text("css=div.notes")
        self.log.info("Desc: %s" % desc)
        assert "Test description" in desc, "Description wasn't updated in publisher edit"


    @with_auth('editor_username', 'editor_password')
    def test_edit_users(self):
        to_add =  self.config.get('user_to_add')
        username = self.config.get('editor_username')
        if not to_add:
            self.log.info( "Skipping 'test_edit_users'. No configured user to add")
            return

        group = self.config.get('publisher')
        if not group:
            raise Exception("%s does not have admin rights to amy publishers" % username)

        self.selenium.open('/publisher/%s' % group)
        self.selenium.click('link=Edit user permissions')
        self.wait()
        assert 'Users: ' in self.selenium.get_title(), "Failed to load the edit publisher users page"

        # Count the users using the delete button.
        count = self.selenium.get_css_count(".btn-danger")

        self.selenium.type('id=users__{count}__name'.format(count=count), to_add)
        self.selenium.click('id=save')
        self.wait()

