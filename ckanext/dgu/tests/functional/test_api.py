import copy
from nose.tools import assert_equal

from ckan import model
from ckan.lib.munge import munge_title_to_name
from ckan.lib.helpers import json
from ckan.logic import get_action
from ckan.tests import TestController as ControllerTestCase
from ckanext.dgu.testtools.create_test_data import DguCreateTestData

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

    def get_package_fixture(self, name):
        pkg = copy.deepcopy(DguCreateTestData._packages[0])
        pkg['name'] = munge_title_to_name(name)
        return pkg
        
    def test_get_package(self):
        offset = '/api/rest/package/%s' % self.pkg_name
        result = self.app.get(offset, status=[200])
        content_type = result.header_dict['Content-Type']
        assert 'application/json' in content_type, content_type
        res = json.loads(result.body)
        assert_equal(res['name'], self.pkg_name)
        assert_equal(res['id'], self.pkg_id)
        assert_equal(res['notes'], 'Cabinet Office head office energy use updated from on-site meters showing use, cost and carbon impact.')
        assert_equal(res['license_id'], 'uk-ogl')
        assert_equal(res['license'], u'UK Open Government Licence (OGL)')
        assert_equal(set(res['tags']), set(("cabinet-office", "consumption", "energy", "energy-consumption", "energy-use", "hq-building", "live-data-page", "real-time")))
        assert_equal(res['groups'], ['cabinet-office'])
        extras = res['extras']
        expected_extra_keys = set((
            'agency', 'categories', 'department', 'date_released',
            'date_updated', 'date_update_future', 'external_reference',
            'geographic_coverage', 'geographic_granularity',
            'national_statistic', 'published_via', 'precision',
            'temporal_coverage-to', 'temporal_coverage-from',
            'temporal_granularity', 'taxonomy_url', 'update_frequency'))
        assert set(extras.keys()) >= expected_extra_keys, set(extras.keys()) - expected_extra_keys
        assert_equal(extras.get('date_released'), '2010-07-30')
        assert_equal(len(res['resources']), 1)
        resource = res['resources'][0]
        assert_equal(resource['description'], "70 Whitehall energy data")
        assert_equal(resource['url'], "http://data.carbonculture.net/orgs/cabinet-office/70-whitehall/reports/elec00.csv")
        assert_equal(resource['format'], "CSV")

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
        assert_equal(res['extras'].get('date_released'), test_pkg['extras']['date_released'])
        assert_equal(res['resources'][0].get('description'), test_pkg['resources'][0]['description'])
        assert_equal(set(res['tags']), set(test_pkg['tags']))

        # check package was created ok
        pkg = model.Package.by_name(test_pkg['name'])
        pkg_dict = get_action('package_show')(self.context, {'id': test_pkg['name']})
        assert_equal(pkg.name, test_pkg['name'])
        assert_equal(pkg.title, test_pkg['title'])
        assert_equal([grp['name'] for grp in pkg_dict['groups']], test_pkg['groups'])
        assert_equal(pkg.extras.get('date_released'), test_pkg['extras']['date_released'])
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
        assert_can_create('sysadmin', 'nhs')
        assert_can_create('sysadmin', '')
        assert_can_create('nhseditor', 'nhs')
        assert_cannot_create('nhseditor', 'dept-health')
        assert_cannot_create('nhseditor', 'barnsley-pct')
        assert_can_create('nhsadmin', 'nhs')
        assert_cannot_create('nhsadmin', 'dept-health')
        assert_cannot_create('nhsadmin', 'barnsley-pct')
        assert_cannot_create('user', 'nhs')
        assert_cannot_create('user', 'dept-health')
        assert_cannot_create('user', 'barnsley-pct')
        assert_cannot_create('user', '')
        assert_cannot_create('', '')
        assert_cannot_create('', 'nhs')
        
    def test_edit_permissions(self):
        pass
