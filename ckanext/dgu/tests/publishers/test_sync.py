from nose.tools import assert_equal

from ckan import model
from ckan.lib.create_test_data import CreateTestData

from ckanext.dgu.publishers import sync
from ckanext.dgu.drupalclient import DrupalClient

from ckanext.dgu.tests import MockDrupalCase

class TestSync(MockDrupalCase):
    lots_of_publishers = True

    def test_group_by_drupal_id(self):
        CreateTestData.create_groups([
            {'name': 'nhs',
             'drupal_id': '1'},
            {'name': 'mod',
             'drupal_id': '2'},
            {'name': 'london',
             'drupal_id': '3'},
            ])
        try:
            group = sync.group_by_drupal_id(2)
            assert group
            assert_equal(group.name, 'mod')
        finally:
            model.repo.rebuild_db()
    
    def test_sync_one(self):
        groups = model.Session.query(model.Group)
        assert groups.count() == 0
        
        rev = model.repo.new_revision()
        rev.author = 'okfn_maintenance'
        rev.message = 'Syncing organisations.'
        
        drupal_client = DrupalClient()        
        sync.sync_organisation(drupal_client, '16203') #HESA

        model.repo.commit_and_remove()

        groups = model.Session.query(model.Group)
        assert_equal(groups.count(), 2)
        group_hesa = model.Group.get(u'higher-education-statistics-agency')
        group_bis = model.Group.get(u'department-for-business-innovation-and-skills')
        assert group_hesa
        assert group_bis
        assert_equal(group_hesa.title, 'Higher Education Statistics Agency')
        assert_equal(group_hesa.extras['drupal_id'], '16203')
        assert_equal(group_hesa.extras['department_id'], group_bis.id)
        assert_equal(group_bis.title, 'Department for Business, Innovation and Skills')
        assert_equal(group_bis.extras['drupal_id'], '11399')
        assert_equal(group_bis.extras['department_id'], group_bis.id)
