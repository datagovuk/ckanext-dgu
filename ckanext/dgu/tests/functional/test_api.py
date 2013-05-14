import copy
from nose.tools import assert_equal
from nose.plugins.skip import SkipTest
from urllib import urlencode

from ckan import model
from ckan.lib.munge import munge_title_to_name
from ckan.lib.helpers import json
from ckan.lib.create_test_data import CreateTestData
from ckan.logic import get_action
from ckan.tests import TestController as ControllerTestCase
from ckan.tests import TestSearchIndexer
from ckanext.dgu.testtools.create_test_data import DguCreateTestData
import ckan.lib.search as search

class TestRestApi(ControllerTestCase):
    @classmethod
    def setup_class(cls):
        DguCreateTestData.create_dgu_test_data()
        cls.pkg_name = DguCreateTestData.form_package().name
        cls.pkg_id = DguCreateTestData.form_package().id
        cls.extra_environ_editor = {
            'Authorization': str(model.User.by_name('nhseditor').apikey)}
        cls.extra_environ_admin = {
            'Authorization': str(model.User.by_name('nhsadmin').apikey)}
        cls.extra_environ_sysadmin = {
            'Authorization': str(model.User.by_name('sysadmin').apikey)}
        cls.context = {'model': model, 'session': model.Session,
                       'user': ''}

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def get_package_fixture(self, name_to_give_the_package):
        pkg = copy.deepcopy(DguCreateTestData._packages[0])
        pkg['name'] = munge_title_to_name(name_to_give_the_package)
        return pkg

    def test_get_package(self):
        offset = '/api/rest/package/%s' % self.pkg_name
        result = self.app.get(offset, status=[200])
        content_type = result.header_dict['Content-Type']
        assert 'application/json' in content_type, content_type
        res = json.loads(result.body)
        assert_equal(res['name'], self.pkg_name)
        assert_equal(res['id'], self.pkg_id)
        assert_equal(res['notes'], u'Ratings for all articles on the Directgov website.  One data file is available per day. Sets of files are organised by month on the download page')
        assert_equal(res['license_id'], 'uk-ogl')
        assert_equal(res['license'], u'UK Open Government Licence (OGL)')
        assert_equal(set(res['tags']), set(["article", "cota", "directgov", "information", "ranking", "rating"]))
        assert_equal(res['groups'], ['national-health-service'])
        extras = res['extras']
        expected_extra_keys = set((
            'access_constraints', 'contact-email', 'contact-name', 'contact-phone',
            'foi-email', 'foi-name', 'foi-phone', 'foi-web',
            'geographic_coverage', 'mandate', 'temporal_coverage-to',
            'temporal_coverage-from', 'temporal_granularity'))
        assert set(extras.keys()) >= expected_extra_keys, set(extras.keys()) - expected_extra_keys
        assert_equal(extras.get('temporal_coverage-from'), '2010-01-01')
        assert_equal(len(res['resources']), 1)
        resource = res['resources'][0]
        assert_equal(resource['description'], "Directgov Article Ratings")
        assert_equal(resource['url'], "http://innovate-apps.direct.gov.uk/cota/")
        assert_equal(resource['format'], "HTML")

    def test_create_package(self):
        test_pkg = self.get_package_fixture('test1')
        offset = '/api/rest/package'
        postparams = '%s=1' % json.dumps(test_pkg)
        result = self.app.post(offset, postparams, status=[201], extra_environ=self.extra_environ_sysadmin)

        # check returned dict is correct
        res = json.loads(result.body)
        assert_equal(res['name'], test_pkg['name'])
        assert res['id']
        assert_equal(res['title'], test_pkg['title'])
        assert_equal(res['license_id'], test_pkg['license_id'])
        assert_equal(res['groups'], test_pkg['groups'])
        assert_equal(res['extras'].get('temporal_coverage-to'), test_pkg['extras']['temporal_coverage-to'])
        assert_equal(res['resources'][0].get('description'), test_pkg['resources'][0]['description'])
        assert_equal(set(res['tags']), set(test_pkg['tags']))

        # check package was created ok
        pkg = model.Package.by_name(test_pkg['name'])
        pkg_dict = get_action('package_show')(self.context, {'id': test_pkg['name']})
        assert_equal(pkg.name, test_pkg['name'])
        assert_equal(pkg.title, test_pkg['title'])
        assert_equal([grp['name'] for grp in pkg_dict['groups']], test_pkg['groups'])
        assert_equal(pkg.extras.get('temporal_coverage-to'), test_pkg['extras']['temporal_coverage-to'])
        assert_equal(pkg.resources[0].description, test_pkg['resources'][0]['description'])
        assert_equal(set([tag['name'] for tag in pkg_dict['tags']]), set(test_pkg['tags']))

    def test_edit_package(self):
        # create the package to be edited
        pkg_name = 'test4'
        test_pkg = self.get_package_fixture(pkg_name)
        pkg = CreateTestData.create_arbitrary(test_pkg)

        # edit it
        offset = '/api/rest/package/%s' % pkg_name
        edited_pkg = copy.deepcopy(test_pkg)
        edited_pkg['title'] = 'Edited title'
        postparams = '%s=1' % json.dumps(edited_pkg)
        result = self.app.put(offset, postparams, status=[200], extra_environ=self.extra_environ_sysadmin)

        # check returned dict is correct
        res = json.loads(result.body)
        assert_equal(res['name'], test_pkg['name'])
        assert res['id']
        assert_equal(res['title'], 'Edited title')
        assert_equal(res['license_id'], test_pkg['license_id'])
        assert_equal(res['groups'], test_pkg['groups'])
        assert_equal(res['extras'].get('temporal_coverage-to'), test_pkg['extras']['temporal_coverage-to'])
        assert_equal(res['resources'][0].get('description'), test_pkg['resources'][0]['description'])
        assert_equal(set(res['tags']), set(test_pkg['tags']))

        # check package was edited ok
        pkg = model.Package.by_name(test_pkg['name'])
        pkg_dict = get_action('package_show')(self.context, {'id': test_pkg['name']})
        assert_equal(pkg.name, test_pkg['name'])
        assert_equal(pkg.title, 'Edited title')
        assert_equal([grp['name'] for grp in pkg_dict['groups']], test_pkg['groups'])
        assert_equal(pkg.extras.get('temporal_coverage-to'), test_pkg['extras']['temporal_coverage-to'])
        assert_equal(pkg.resources[0].description, test_pkg['resources'][0]['description'])
        assert_equal(set([tag['name'] for tag in pkg_dict['tags']]), set(test_pkg['tags']))

    def test_create_permissions(self):
        def assert_create(user_name, publisher_name, status=201):
            test_pkg = self.get_package_fixture('test2' + user_name + publisher_name)
            test_pkg['groups'] = [publisher_name] if publisher_name else []
            offset = '/api/rest/package'
            postparams = '%s=1' % json.dumps(test_pkg)
            if user_name:
                extra_environ = {'Authorization': str(model.User.by_name(user_name).apikey)}
            else:
                extra_environ = {}
            result = self.app.post(offset, postparams, status=[status], extra_environ=extra_environ)
        def assert_can_create(user_name, publisher_name):
            assert_create(user_name, publisher_name, 201)
        def assert_cannot_create(user_name, publisher_name):
            assert_create(user_name, publisher_name, 403)
        assert_can_create('sysadmin', 'national-health-service')
        assert_can_create('sysadmin', '')
        assert_can_create('nhseditor', 'national-health-service')
        assert_can_create('nhsadmin', 'barnsley-primary-care-trust')  # Admin can create in sub-groups
        assert_cannot_create('nhseditor', 'dept-health')

        assert_cannot_create('nhseditor', 'barnsley-primary-care-trust')
        assert_can_create('nhsadmin', 'national-health-service')
        assert_cannot_create('nhsadmin', 'dept-health')
        assert_cannot_create('user', 'national-health-service')
        assert_cannot_create('user', 'dept-health')
        assert_cannot_create('user', 'barnsley-primary-care-trust')
        assert_cannot_create('user', '')
        assert_cannot_create('', '')
        assert_cannot_create('', 'national-health-service')

    def test_edit_permissions(self):
        def assert_edit(user_name, publisher_name, status=200):
            # create a package to edit
            pkg_name = 'test3' + user_name + publisher_name
            test_pkg = self.get_package_fixture(pkg_name)
            test_pkg['groups'] = [publisher_name] if publisher_name else []
            pkg = CreateTestData.create_arbitrary(test_pkg)

            # edit it
            offset = '/api/rest/package/%s' % pkg_name
            edited_pkg = copy.deepcopy(test_pkg)
            edited_pkg['title'] += ' edited'
            postparams = '%s=1' % json.dumps(edited_pkg)
            if user_name:
                extra_environ = {'Authorization': str(model.User.by_name(user_name).apikey)}
            else:
                extra_environ = {}
            result = self.app.put(offset, postparams, status=[status], extra_environ=extra_environ)
        def assert_can_edit(user_name, publisher_name):
            assert_edit(user_name, publisher_name, 200)
        def assert_cannot_edit(user_name, publisher_name):
            assert_edit(user_name, publisher_name, 403)
        assert_can_edit('sysadmin', 'national-health-service')
        assert_can_edit('sysadmin', '')
        assert_can_edit('nhseditor', 'national-health-service')
        assert_can_edit('nhsadmin', 'national-health-service') # Admin can edit own group
        assert_can_edit('nhsadmin', 'barnsley-primary-care-trust') # Admin can edit sub-groups
        assert_cannot_edit('nhseditor', 'dept-health')
        assert_cannot_edit('nhseditor', 'barnsley-primary-care-trust')
        assert_cannot_edit('nhsadmin', 'dept-health')
        assert_cannot_edit('user', 'national-health-service')
        assert_cannot_edit('user', 'dept-health')
        assert_cannot_edit('user', 'barnsley-primary-care-trust')
        assert_cannot_edit('user', '')
        assert_cannot_edit('', '')
        assert_cannot_edit('', 'national-health-service')

#TODO
# Check non-allowed theme-primary/secondary

class TestDguApi(ControllerTestCase, TestSearchIndexer):
    @classmethod
    def setup_class(cls):
        search.clear()
        cls.tsi = TestSearchIndexer()
        DguCreateTestData.create_dgu_test_data()
        DguCreateTestData.create_arbitrary({'name': 'latest',
                                            'notes': '<b>Latest</b> dataset.',
                                            'groups': ['national-health-service']})
        cls.tsi.index()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_dataset_count(self):
        offset = '/api/util/dataset-count'
        result = self.app.get(offset, status=[200])
        content_type = result.header_dict['Content-Type']
        assert 'application/json' in content_type, content_type
        res = json.loads(result.body)
        assert isinstance(res, int), res
        assert 3 < res < 10, res

    def test_latest_datasets(self):
        offset = '/api/util/latest-datasets'
        result = self.app.get(offset, status=[200])
        content_type = result.header_dict['Content-Type']
        assert 'application/json' in content_type, content_type
        res = json.loads(result.body)
        assert isinstance(res, list), res
        assert 6 <= len(res) <= 10, len(res) # default number of revisions returned
        pkg = res[0]
        assert_equal(pkg['name'], 'latest')
        assert_equal(pkg['notes'], '<b>Latest</b> dataset.')
        assert_equal(pkg['publisher_title'], 'National Health Service')
        assert set(pkg.keys()) >= set(('title', 'dataset_link', 'notes', 'publisher_title', 'publisher_link', 'metadata_modified')), pkg.keys()

        # try dataset_link
        res = self.app.get(pkg['dataset_link'], status=[200])
        assert 'latest' in res.body

        # try publisher_link
        res = self.app.get(pkg['publisher_link'], status=[200])
        assert 'National Health Service' in res.body, res

def pkg_id(pkg_name):
    return model.Package.by_name(pkg_name).id

class TestDrupalApi(ControllerTestCase, TestSearchIndexer):
    # i.e. the CKAN API that Drupal accesses
    @classmethod
    def setup_class(cls):
        DguCreateTestData.create_dgu_test_data()
        DguCreateTestData.create_arbitrary({'name': 'latest',
                                            'notes': '<b>Latest</b> dataset.',
                                            'tags': ['tag1', 'tag2'],
                                            'extras': {'key': 'value'},
                                            'groups': ['national-health-service']})
        cls._assert_revision_created()
        model.Session.remove() # ensure last revision appears


    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def _last_revision(self):
        '''Asks the Revision API to return the last revision.'''
        rev = model.Session.query(model.Revision) \
              .order_by(model.Revision.timestamp.desc()) \
              .first()
        offset = '/api/util/revisions?since-revision-id=%s' % rev.id
        result = self.app.get(offset, status=[200])
        res = json.loads(result.body)
        assert isinstance(res, dict), res
        return res

    @classmethod
    def _assert_revision_created(cls):
        '''Asserts that a revision has been created since last time
        this method was run.'''
        latest_rev = model.Session.query(model.Revision) \
                     .order_by(model.Revision.timestamp.desc()) \
                     .first()
        if '_previous_rev' in dir(cls):
            assert latest_rev != cls._previous_rev
        cls._previous_rev = latest_rev

    def test_revision__package_create(self):
        rev = model.repo.new_revision()
        model.Session.add(model.Package(name='latest1', notes='<b>Latest1</b> dataset.'))
        model.repo.commit_and_remove()
        self._assert_revision_created()
        res = self._last_revision()
        assert_equal(res['datasets'][0]['name'], 'latest1')

    def test_revision__package_edit(self):
        rev = model.repo.new_revision()
        model.Package.by_name('latest').version='changed'
        model.repo.commit_and_remove()
        self._assert_revision_created()
        res = self._last_revision()
        assert_equal(res['datasets'][0]['name'], 'latest')

    def test_revision__tag(self):
        rev = model.repo.new_revision()
        tag = model.Tag.by_name('tag1')
        model.Package.by_name('latest').remove_tag(tag)
        model.repo.commit_and_remove()
        self._assert_revision_created()
        res = self._last_revision()
        assert_equal(res['datasets'][0]['name'], 'latest')

    def test_revision__extra(self):
        rev = model.repo.new_revision()
        model.Package.by_name('latest').extras = {u'genre':'romantic novel'}
        model.repo.commit_and_remove()
        self._assert_revision_created()
        res = self._last_revision()
        assert_equal(res['datasets'][0]['name'], 'latest')

    def test_revision__resource_addition(self):
        rev = model.repo.new_revision()
        res = model.Resource(description="April to September 2010",
                             format="CSV",
                             url="http://www.barnsley.nhs.uk/spend.csv")
        model.Session.add(res)
        model.Package.by_name('latest').resource_groups_all[0].resources_all.append(res)
        model.repo.commit_and_remove()
        self._assert_revision_created()
        res = self._last_revision()
        assert_equal(res['datasets'][0]['name'], 'latest')

    def test_revision__group(self):
        rev = model.repo.new_revision()
        pkg = model.Package.by_name('latest')
        group = model.Group.by_name('dept-health')

        # Delete the revision first
        model.Session.query(model.MemberRevision).filter_by(table_id=pkg.id).delete()
        membership1 = model.Session.query(model.Member).filter_by(table_id=pkg.id).delete()
        model.Session.add(model.Member(group=group, table_id=pkg.id, table_name='package'))
        model.repo.commit_and_remove()
        self._assert_revision_created()
        res = self._last_revision()
        assert_equal(res['datasets'][0]['name'], 'latest')

    def _get_revisions(self):
        return model.Session.query(model.Revision) \
              .order_by(model.Revision.timestamp.asc()) \
              .all()

    def _get_last_and_penultimate_revisions(self):
        # Get the last revision and penultimate one.
        # The last one is empty, created needlessly by
        # create_arbitrary. The last but one revision has the package revision in it.
        # If other tests run first, then the last revision has the package in it in
        # some form or another.
        revs = self._get_revisions()
        return revs[-1], revs[-2]

    def test_revisions__since_revision_id__latest(self):
        last_rev, rev = self._get_last_and_penultimate_revisions()
        offset = '/api/util/revisions?since-revision-id=%s' % rev.id
        result = self.app.get(offset, status=[200])
        res = json.loads(result.body)
        assert isinstance(res, dict), res
        assert set(res.keys()) >= set(('since_timestamp', 'datasets')), res.keys()
        assert_equal(res['since_revision_id'], rev.id)
        assert_equal(res['newest_revision_id'], last_rev.id)
        assert_equal(res['number_of_revisions'], 2)
        assert_equal(res['results_limited'], False)
        pkgs = res['datasets']
        pkg = pkgs[0]
        assert_equal(pkg['name'], 'latest')
        assert_equal(pkg['notes'].strip(), 'Latest dataset.')
        assert pkg['publisher_title'] in ('National Health Service', 'Department of Health'), pkg['publisher_title']
        assert set(pkg.keys()) >= set(('title', 'dataset_link', 'notes', 'publisher_title', 'publisher_link')), pkg.keys()

        # try dataset_link
        if model.engine_is_sqlite():
            raise SkipTest("Link tests need postgres")
        res = self.app.get(pkg['dataset_link'], status=[200])
        assert 'latest' in res.body

        # try publisher_link
        res = self.app.get(pkg['publisher_link'], status=[200])
        assert 'National Health Service' in res.body, res

    def test_revisions__since_timestamp(self):
        last_rev, rev = self._get_last_and_penultimate_revisions()
        offset = '/api/util/revisions?%s' % urlencode({'since-timestamp': rev.timestamp})
        result = self.app.get(offset, status=[200])
        res = json.loads(result.body)
        assert isinstance(res, dict), res
        assert set(res.keys()) >= set(('since_timestamp', 'datasets')), res.keys()
        assert_equal(res['since_revision_id'], rev.id)
        assert_equal(res['newest_revision_id'], last_rev.id)
        assert_equal(res['number_of_revisions'], 2)
        assert_equal(res['results_limited'], False)

    def test_revisions__in_last_x_minutes(self):
        offset = '/api/util/revisions?in-the-last-x-minutes=5'
        result = self.app.get(offset, status=[200])
        res = json.loads(result.body)
        assert isinstance(res, dict), res
        assert set(res.keys()) >= set(('since_timestamp', 'datasets')), res.keys()
        revs = self._get_revisions()
        assert_equal(res['since_revision_id'], revs[0].id)
        assert_equal(res['newest_revision_id'], revs[-1].id)
        assert 10 < res['number_of_revisions'] < 20, res['number_of_revisions']
        assert res['results_limited'] == True, res['results_limited']
