import copy

from pylons import config

from nose.plugins.skip import SkipTest

from ckan import model
from ckan.tests import TestController
from ckan.tests.wsgi_ckanclient import WsgiCkanClient
from ckan.lib.create_test_data import CreateTestData

from ckanext.dgu.bin.national_statistic_filter import NSFilter
from ckanext.dgu.tests import PackageDictUtil

class TestFilter(TestController):
    @classmethod
    def setup_class(self):
        # create test data
        username = 'tester'
        self.pkgs = [
            {'name': "ons_pkg",
             "extras": {
                 "import_source": "ONS-ons_data_7_days_to_2011-05-10",
                 "notes": "<p>Designation: National Statistics\n</p>",
                 "national_statistic": "yes",
                 }
             },
            {'name': "ons_but_not_ns",
             "extras": {
                 "import_source": "ONS-ons_data_7_days_to_2011-05-10",
                 "notes": "<p>Designation: Excellent Statistics\n</p>",
                 "national_statistic": "yes",
                 }
             },
            {'name': "not_ns_or_ons",
             "extras": {
                 "import_source": "ONS-ons_data_7_days_to_2011-05-10",
                 "national_statistic": "no",
                 }
             },
            {'name': "not_ns",
             "extras": {
                 "import_source": "",
                 "national_statistic": "no",
                 }
             },
            {'name': "local-authority-spend-over-500-london-borough-of-hackney",
             "title": "Payments to suppliers with a value over \u00a3500 from London Borough of Hackney",
             "extras": {
                 "temporal_coverage-to": "2011-06-30",
                 "temporal_coverage-from": "2010-09-01",
                 "temporal_granularity": "month",
                 "date_released": "2010-09-14",
                 "geographic_coverage": "000000: ",
                 "taxonomy_url": "",
                 "openness_score": "0",
                 "external_reference": "",
                 "date_updated": "2011-07-26",
                 "published_via": "", "agency": "",
                 "precision": "per cent to two decimal places",
                 "geographic_granularity": "local authority",
                 "department": "London Borough of Hackney",
                 "published_by": "London Borough of Hackney [15165]",
                 "national_statistic": "yes",
                 "openness_score_last_checked": "2011-06-06T17:02:46.802271",
                 "mandate": "", "date_update_future": "",
                 "update_frequency": "monthly",
                 "categories": "Government"}
             },            
            ]
        
        CreateTestData.create_arbitrary(self.pkgs,
                                        extra_user_names=[username])

        user = model.User.by_name(unicode(username))
        assert user
        
        self.testclient = WsgiCkanClient(self.app, api_key=user.apikey)

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()


    def test_filter(self):
        # Skip this test until the mock data reflects the new permission model
        # (each dataset *needs* to belong to a group
        raise SkipTest, 'Skip until mock data reflects new permission model'

        if 'sqlite' in config.get('sqlalchemy.url'):
            # Ian thinks this failed for him due to a timestamp not being converted
            # to a datetime object, and being left as a unicode object.
            # Could also be related to Sqlalchemy 0.7.x.
            raise SkipTest

        ns_filter = NSFilter(self.testclient, dry_run=False, force=False)
        ns_filter.filter()

        def assert_pkg_stayed_the_same(package_name, pkg_dict):
            pkg = model.Package.by_name(unicode(package_name))
            PackageDictUtil.assert_subset(pkg.as_dict(), pkg_dict)
            
        def assert_pkg_filtered(package_name, pkg_dict):
            pkg = model.Package.by_name(unicode(package_name))
            expected_pkg = copy.deepcopy(pkg_dict)
            expected_pkg['extras']['national_statistic'] = 'no'
            PackageDictUtil.assert_subset(pkg.as_dict(), expected_pkg)
        
        assert_pkg_stayed_the_same('ons_pkg', self.pkgs[0])
        assert_pkg_filtered('ons_but_not_ns', self.pkgs[1])
        assert_pkg_stayed_the_same('not_ns_or_ons', self.pkgs[2])
        assert_pkg_stayed_the_same('not_ns', self.pkgs[3])
        assert_pkg_filtered('local-authority-spend-over-500-london-borough-of-hackney', self.pkgs[4])
