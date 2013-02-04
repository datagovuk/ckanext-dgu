import uuid, time
import ckanext.dgu.testtools.selenium_test_base as t
from ckanext.dgu.testtools.selenium_tests.login import with_auth

class DatasetTests(t.TestBase):

    @with_auth('editor_username', 'editor_password')
    def test_create(self):
        self.selenium.open('/dataset/new')
        self.wait()

        # Info
        nm = 'Test Dataset %s' % str(uuid.uuid4())
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
        assert 'dataset/%s' % name in self.selenium.get_location(), "There was a problem creating a dataset"
        self.delete_dataset(name)


    @with_auth('editor_username', 'editor_password')
    def test_edit(self):
        """ Create, and then edit a dataset """

        self.selenium.open('/dataset/new')
        self.wait()

        # Info
        nm = 'Test Dataset %s' % str(uuid.uuid4())
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

        assert 'dataset/%s' % name in self.selenium.get_location(), "There was a problem creating a dataset"

        print 'Ready to edit the dataset now...'
        #self.selenium.click('link= Edit') - link isn't easily identifiable

        self.selenium.open('/dataset/edit/%s' % name)

        self.selenium.click('id=section-description-field')
        self.selenium.type('id=notes','Wombles live under Wimbledon common')
        self.selenium.click('id=save-button')
        self.wait()

        notes = self.selenium.get_text('css=.notes')
        assert 'Womble' in notes, "Description was not updated when editing dataset"
        self.delete_dataset(name)

    def delete_dataset(self, name):
        import ckan.model as model
        model.repo.new_revision()

        pkg = model.Package.get(name)
        if pkg:
            # Make sure we save it so it is taken out of search index
            pkg.state = 'deleted'
            model.Session.add(pkg)
            model.Session.commit()

            # Purge all of the revisions... mostly taken from admin controller
            revisions = [x[0] for x in pkg.all_related_revisions]
            revs_to_purge = [r.id for r in revisions]
            model.Session.remove()

            for id in revs_to_purge:
                revision = model.Session.query(model.Revision).get(id)
                try:
                    # TODO deleting the head revision corrupts the edit page
                    # Ensure that whatever 'head' pointer is used gets moved down to the next revision
                    model.repo.purge_revision(revision, leave_record=False)
                except Exception, inst:
                    print "Failed to delete a revision of this package"

