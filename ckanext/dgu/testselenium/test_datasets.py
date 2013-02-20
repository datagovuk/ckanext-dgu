import uuid, time
import selenium_test_base as t
from test_login import with_auth

class DatasetTests(t.TestBase):

    @with_auth('editor_username', 'editor_password')
    def test_create(self):
        self.selenium.open('/dataset/new')
        self.wait()

        # Info
        nm = self.config['create_name']
        self.selenium.type('id=title', nm)
        name = self.selenium.get_value("id=name")
        self.selenium.click('id=next-button')

        # Data files
        self.selenium.type("id=individual_resources__0__description", "Test resource")
        self.selenium.type("id=individual_resources__0__url", "http://data.gov.uk/data/site-usage")
        #click(individual_resources__0__validate-resource-button) and sleep for 5
        # or
        self.selenium.type("id=individual_resources__0__format", "HTML")
        self.selenium.click('id=next-button')

        # Description
        self.selenium.type("id=notes", "This is a test dataset")
        self.selenium.click('id=next-button')

        # License, we'll use the default
        self.selenium.click('id=next-button')

        # Publisher
        labels = self.selenium.get_select_options("id=groups__0__name")
        self.selenium.select("id=groups__0__name", "label=%s" % labels[1])
        self.selenium.click('id=next-button')

        labels = self.selenium.get_select_options("id=theme-primary")
        self.selenium.select("id=theme-primary", "label=%s" % labels[1])
        self.selenium.click('id=next-button')

        # Additional Resources, we won't add any yet
        self.selenium.click('id=next-button')

        # Temporal coverage
        self.selenium.type("id=temporal_coverage-from", "01/01/2012")
        self.selenium.type("id=temporal_coverage-to", "01/01/2013")
        self.selenium.click('id=next-button')

        self.selenium.check('id=global')

        self.selenium.click('id=save-button')
        self.wait()
        assert 'dataset/%s' % name in self.selenium.get_location(), \
            "There was a problem creating a dataset" + self.selenium.get_html_source()


    @with_auth('editor_username', 'editor_password')
    def test_edit(self):
        """ Create, and then edit a dataset """

        self.selenium.open('/dataset/new')
        self.wait()

        # Info
        nm = self.config['edit_name']
        self.selenium.type('id=title', nm)
        name = self.selenium.get_value("id=name")
        self.selenium.click('id=next-button')

        # Data files
        self.selenium.click('id=next-button')

        # Description
        self.selenium.type("id=notes", "This is a test dataset")
        self.selenium.click('id=next-button')

        # License, we'll use the default
        self.selenium.click('id=next-button')

        # Publisher
        labels = self.selenium.get_select_options("id=groups__0__name")
        self.selenium.select("id=groups__0__name", "label=%s" % labels[1])
        self.selenium.click('id=next-button')

        labels = self.selenium.get_select_options("id=theme-primary")
        self.selenium.select("id=theme-primary", "label=%s" % labels[1])
        self.selenium.click('id=next-button')
        self.selenium.click('id=save-button')
        self.wait()

        assert 'dataset/%s' % name in self.selenium.get_location(), \
            "There was a problem editing a dataset" + self.selenium.get_html_source()

        print 'Ready to edit the dataset now...'
        #self.selenium.click('link= Edit') - link isn't easily identifiable

        self.selenium.open('/dataset/edit/%s' % name)

        self.selenium.click('id=section-description-field')
        self.selenium.type('id=notes','Wombles live under Wimbledon common')
        self.selenium.click('id=save-button')
        self.wait()

        notes = self.selenium.get_text('css=.notes')
        assert 'Womble' in notes, "Description was not updated when editing dataset"

