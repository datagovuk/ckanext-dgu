import uuid
import ckanext.dgu.testtools.selenium_test_base as t

class LoginTests(t.TestBase):

    def test_basic(self, username=None, password=None):
        """ Test a known working login """
        self.selenium.open('/data')
        self.selenium.click("link=Log in")
        self.wait()

        user = username or self.config.get('username')
        pwd = password or  self.config.get('password')
        self.fill_form("id=login",{"name=login": user,
                                   "password": pwd})

        self.wait()
        assert "- User - CKAN" in self.selenium.get_title(),\
            "User did not log in correctly" % self.selenium.get_title()
        self.selenium.click("link=Log out")
        self.wait()

    def test_basic_fail(self):
        """ Test a known working login """
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
        """ Sign up for a bad account """
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
        """ Good signup, and then a login on the new account """
        self.selenium.open('/data')
        self.selenium.click("link=sign up")
        self.wait()

        uname = "testing_%s" % str(uuid.uuid4())
        data = dict(name=uname, fullname="Test User",
            email="test@localhost.local",password1="pass1", password2="pass1")
        self.fill_form("id=user-edit", data, "id=save")
        self.wait()

        self.test_basic(username=uname, password="pass1")

        # Cleanup user uname

