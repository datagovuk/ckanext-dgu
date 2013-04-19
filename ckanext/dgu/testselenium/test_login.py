import uuid
import selenium_test_base as t

class LoginTests(t.TestBase):

    def do_login(self, username, password):
        self.selenium.open('/data')
        self.selenium.click("link=Log in")
        self.wait()

        # The button with an id of 's' is only available on the
        # ckan login, not the drupal one.
        if self.selenium.get_css_count("css=#s"):
            self.fill_form("id=login",{"login": username,
                                       "password": password})
        else:
            self.fill_form("id=user-login",{"edit-name": username,
                                            "edit-pass": password})

        self.wait()
        assert "- User - CKAN" in self.selenium.get_title(),\
            "User did not log in correctly to: '%s'" % self.selenium.get_title()

    def do_logout(self):
        self.selenium.click("link=Log out")
        self.wait()

    """
    def test_basic(self, username=None, password=None):
        user = username or self.config.get('username')
        pwd = password or  self.config.get('password')

        self.do_login(user,pwd)
        self.selenium.click("link=Log out")
        self.wait()

        self.do_logout()

    def test_basic_fail(self):
        self.selenium.open('/data')

        self.selenium.click("link=Log in")
        self.wait()

        user = "Non-existent"
        pwd = "Whatever"
        self.fill_form("id=login",{"name=login": user,
                                   "password": pwd})

        self.wait()
        assert 'Login failed' in self.selenium.get_text("css=.alert-error"),\
            "The login didn't appear to fail"


    def test_signup_bad(self):

        try:
            # We may still be logged in
            do_logout()
        except:
            pass

        self.selenium.open('/data')
        self.selenium.click("link=sign up")
        self.wait()

        data = dict(name="testing", fullname="Test User",
            email="test@localhost.local",password1="pass1", password2="pass2")
        self.fill_form("id=user-edit", data, "id=save")
        self.wait()

        assert "The passwords you entered do not match" in\
         self.selenium.get_text("css=.error-explanation"), "Did not complain about mismatched passwords"



    def test_signup_good(self):
         Good signup, and then a login on the new account
        self.selenium.open('/data')
        self.selenium.click("link=sign up")
        self.wait()

        uname = "testing_%s" % str(uuid.uuid4())
        data = dict(name=uname, fullname="Test User",
            email="test@localhost.local",password1="pass1", password2="pass1")
        self.fill_form("id=user-edit", data, "id=save")
        self.wait()

        self.test_basic(username=uname, password="pass1")

        import ckan.model as model
        user_was = model.User.get(uname)
        user_was.delete()
        model.Session.commit()
        self.log.info("Deleted user %s that was created in test" % uname)
 """

class with_auth(object):
    """ Decorator to login before function, and logout afterwards """

    def __init__(self, username_key, password_key):
        self.username_key = username_key
        self.password_key = password_key

    def __call__(decorator, f):
        def inner(self, *args):
            from test_login import LoginTests
            l = LoginTests(self.selenium, self.config, self.log)

            try:
                username = self.config.get(decorator.username_key)
                password = self.config.get(decorator.password_key)
                l.do_login(username, password)
                f(self)
            finally:
                try:
                    l.do_logout()
                except:
                    pass # may already be logged out

        return inner
