import uuid, time
import selenium_test_base as t
from test_login import with_auth

class PublisherTests(t.TestBase):

    def get_publishers_for_user(self, username):
        import ckan.model as model
        user = model.User.get(username)
        if not user:
            raise Exception("Failed to find the user in order to get the publishers")
        return [g.name for g in user.get_groups('publisher', 'admin')]

    @with_auth('editor_username', 'editor_password')
    def test_edit(self):
        username = self.config.get('editor_username')
        groups = self.get_publishers_for_user(username)
        group = groups[0] if groups else None
        if not group:
            raise Exception("%s does not have admin rights to amy publishers" % username)

        self.selenium.open('/publisher/%s' % group)
        self.selenium.click('link=Edit')
        self.wait()
        assert 'Edit: ' in self.selenium.get_title(), "Failed to load the edit publisher page"

        old_desc = self.selenium.get_value("id=notes")
        self.log.info( "Old: %s" % old_desc)

        self.selenium.type('id=notes', "Test description")
        self.selenium.click('id=save')
        self.wait()

        try:
            error = self.selenium.get_value('css=error-explanation')
            assert False, "An error was raised trying to save the publisher: %s" % error
        except:
            pass

        desc = self.selenium.get_text("css=.notes")
        self.log.info("Desc: %s" % desc)
        assert "Test description" in desc, "Description wasn't updated in publisher edit"

        self.selenium.open('/publisher/%s' % group)
        self.selenium.click('link=Edit')
        self.wait()
        assert 'Edit: ' in self.selenium.get_title(), "Failed to load the edit publisher page"

        self.selenium.type('id=notes', old_desc or "")
        self.selenium.click("id=save")
        self.wait()

        try:
            desc = self.selenium.get_text("css=.notes")
            # The description might not be shown if it is empty, but if it wasn't and
            # we can't see it then that is a fail.
            if desc:
                assert old_desc in desc, "Description wasn't updated in publisher edit"
        except:
            # If we failed to get the description, but we had a valid one to set
            # then re-raise the exception
            if old_desc:
                raise

    @with_auth('editor_username', 'editor_password')
    def test_edit_users(self):
        to_add =  self.config.get('user_to_add')
        username = self.config.get('editor_username')
        if not to_add:
            self.log.info( "Skipping 'test_edit_users'. No configured user to add")
            return

        groups = self.get_publishers_for_user(username)
        group = groups[0] if groups else None
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

        # Check the database to see how many members this publisher now has, and remove
        # the one for the latest user we just added.
        import ckan.model as model
        model.repo.new_revision()

        publisher = model.Group.get(group)
        user = model.User.get(to_add)
        member = model.Session.query(model.Member).filter(model.Member.table_name=='user')\
            .filter(model.Member.group_id==publisher.id).filter(model.Member.table_id==user.id).first()
        if member:
            member.delete()
            model.Session.commit()




