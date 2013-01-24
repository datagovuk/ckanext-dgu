from selenium import selenium
from selenium.webdriver.support.wait import WebDriverWait

class TestBase(object):
    """
        Provides a base class for tests which contains both the selenium
        object used to run the tests, and helper methods such as wait()

        Documentation on the selenium object can be found at:
        http://selenium.googlecode.com/svn/trunk/docs/api/py/selenium/selenium.selenium.html
    """

    def __init__(self, selenium, config, log):
        self.selenium = selenium
        self.config = config
        self.log = log
        super(TestBase, self).__init__()

    def wait(self, max_wait=20):
        """ Waits for the current page to load. Default was originally 10 seconds
            but login is particularly slow for me and so have changed to 20 """
        self.selenium.wait_for_page_to_load(max_wait*1000)

    def fill_form(self, frm_locator, data, submit=None):
        """
            Fills in a form (specified using frm_locator) and takes
            the data from the 'data' dict.  For the key in each entry
            of the data dict it uses either the identifier locator or
            if specified (by the presence of =) the key as the entire
            locator.

            If a locator is specified using 'submit' then that is clicked
            in order to submit the form, otherwise the form is told to
            submit itself.
        """
        for k,v in data.iteritems():
            key = k if '=' in k else "identifier=%s" % (k,)
            self.selenium.type(key, v)

        if submit:
            self.selenium.click(submit)
            self.wait()
        else:
            self.selenium.submit(frm_locator)
