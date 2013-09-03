import re
import datetime
import copy

import dateutil.parser
from nose.tools import assert_equal
from nose.plugins.skip import SkipTest

from ckan import model
from ckan.lib.create_test_data import CreateTestData
from ckan.lib.search import show
from ckan.logic import get_action
from ckan.tests import TestController as ControllerTestCase, setup_test_search_index, is_search_supported
from ckanext.dgu.tests import assert_solr_schema_is_the_dgu_variant
from ckanext.dgu.bin.initial_last_major_modification import Tool

def _modification_time(pkg):
    return dateutil.parser.parse(pkg.extras['last_major_modification'])

def _modification_time_in_the_search_index(pkg):
    pkg_dict = show(pkg.name)
    mod_time_str = pkg_dict['last_major_modification']
    return dateutil.parser.parse(mod_time_str).replace(tzinfo=None)

def round_down_to_milliseconds(time_):
    # i.e. the last 3 digits of the microseconds are set to 0
    return time_.replace(microsecond=int(time_.microsecond/1000)*1000)

def get_pkg_fixture(name):
    return {
        'name': name,
        'additional_resources': [{'description': u'Full text.',
                                  'format': u'plain text',
                                  'hash': u'abc123',
                                  'url': u'http://www.annakarenina.com/download/'},
                                 ],
        'title': u'A Novel By Tolstoy',
        'license_id': u'other-open',
        'access_constraints': u'',
        'contact-name': u'',
        'contact-email': u'',
        'contact-phone': u'',
        'foi-name': u'',
        'foi-email': u'',
        'foi-phone': u'',
        'foi-web': u'',
        'notes': u'Test',
        }

class TestResourceChanges(ControllerTestCase):

    @classmethod
    def setup_class(cls):
        CreateTestData.create_user('sysadmin')
        model.add_user_to_role(model.User.by_name(u'sysadmin'),
                               model.Role.ADMIN, model.System())
        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    @classmethod
    def _mark_the_time(cls):
        cls.time_mark = datetime.datetime.utcnow()

    @classmethod
    def _has_modification_time_been_updated_since_the_mark(cls, pkg):
        return cls.time_mark <= _modification_time(pkg) <= datetime.datetime.utcnow()

    @classmethod
    def _assert_post_determined_modification_time_is_correct(cls, pkg):
        #c = {"model": model, "session": model.Session, "user": "sysadmin"}
        #pkg_dict = get_action('package_show')(c, data_dict={'id': pkg.id})
        post_determined_mod_time = Tool.determine_last_major_modification(pkg)
        #post_determined_mod_time = dateutil.parser.parse(post_determined_mod_time_str)
        mod_time = _modification_time(pkg)
        assert_equal(mod_time, post_determined_mod_time)

    def test_new_package_without_resources(self):
        self._mark_the_time()
        CreateTestData.create_arbitrary({'name': 'testpkg'})
        pkg = model.Package.get('testpkg')
        assert pkg
        assert self._has_modification_time_been_updated_since_the_mark(pkg)
        self._assert_post_determined_modification_time_is_correct(pkg)

    def test_new_package_with_resources(self):
        self._mark_the_time()
        CreateTestData.create_arbitrary({'name': 'testpkg2',
                                         'resources': [{'url': 'http://ff.com'}]
                                         })
        pkg = model.Package.get('testpkg2')
        assert self._has_modification_time_been_updated_since_the_mark(pkg)
        self._assert_post_determined_modification_time_is_correct(pkg)

    def test_edit_package(self):
        CreateTestData.create_arbitrary({'name': 'testpkg5',
                                         'resources': [{'url': 'http://ff.com'}]
                                         })
        pkg = model.Package.get('testpkg5')
        self._mark_the_time()
        model.repo.new_revision()
        pkg.notes = 'A change'
        model.repo.commit_and_remove()
        pkg = model.Package.get('testpkg5')
        assert not self._has_modification_time_been_updated_since_the_mark(pkg)
        self._assert_post_determined_modification_time_is_correct(pkg)

    def test_new_resource(self):
        CreateTestData.create_arbitrary({'name': 'testpkg4',
                                         'resources': [{'url': 'http://ff.com'}]
                                         })
        self._mark_the_time()
        model.repo.new_revision()
        p = model.Package.get("testpkg4")
        p.add_resource(url="http://fake_url/", format="HTML", description="A test resource")
        model.Session.add(p)
        model.repo.commit_and_remove()
        
        pkg = model.Package.get("testpkg4")
        assert len(pkg.resources) == 2, "Resource wasn't added"
        assert "last_major_modification" in pkg.extras
        assert self._has_modification_time_been_updated_since_the_mark(pkg)
        self._assert_post_determined_modification_time_is_correct(pkg)

    def test_delete_resource(self):
        CreateTestData.create_arbitrary({'name': 'testpkg3',
                                         'resources': [{'url': 'http://ff.com'}]
                                         })
        p = model.Package.get("testpkg3")
        num_resources = len(p.resources)
        
        self._mark_the_time()
        model.repo.new_revision()
        r = p.resources[0]
        r.state = 'deleted'
        model.repo.commit_and_remove()

        pkg = model.Package.get("testpkg3")

        assert len(pkg.resources) != num_resources, "Resource wasn't deleted"
        assert self._has_modification_time_been_updated_since_the_mark(pkg)
        self._assert_post_determined_modification_time_is_correct(pkg)

    def test_resource_url_change(self):
        c = { "model": model, "session": model.Session, "user": "sysadmin",
              'extras_as_string': True, # else package_extras_save expects json
              }
        pkg_dict = get_pkg_fixture('pkg_fixture')
        pkg = get_action('package_create')(c, data_dict=pkg_dict)
        assert pkg

        # IResourceUrlChange only works when the change goes through the logic layer
        # so can't just change at the ORM level

        pkg_dict['additional_resources'][0]['url'] = 'http://google.com/'

        # Need to set the resource ID or it thinks it is a new resource.
        # In the form it is like this - the ID is in there, hidden.
        pkg_dict['additional_resources'][0]['id'] = pkg['resources'][0]['id']

        self._mark_the_time()
        get_action('package_update')(c, data_dict=pkg_dict)
        
        pkg = model.Package.get('pkg_fixture')
        assert_equal(pkg.resources[0].url, 'http://google.com/')
        assert self._has_modification_time_been_updated_since_the_mark(pkg)
        self._assert_post_determined_modification_time_is_correct(pkg)

    def test_resource_other_properties_change(self):
        c = { "model": model, "session": model.Session, "user": "sysadmin",
              'extras_as_string': True, # else package_extras_save expects json
              }
        pkg_dict = get_pkg_fixture('pkg_fixture2')
        pkg = get_action('package_create')(c, data_dict=pkg_dict)
        assert pkg

        # IResourceUrlChange only works when the change goes through the logic layer
        # so can't just change at the ORM level

        pkg_dict['additional_resources'][0]['description'] = 'Got changed'
        pkg_dict['additional_resources'][0]['format'] = 'CSV'
        pkg_dict['additional_resources'][0]['hash'] = 'changed'

        # Need to set the resource ID or it thinks it is a new resource.
        # In the form it is like this - the ID is in there, hidden.
        pkg_dict['additional_resources'][0]['id'] = pkg['resources'][0]['id']

        self._mark_the_time()
        get_action('package_update')(c, data_dict=pkg_dict)

        pkg = model.Package.get('pkg_fixture2')
        assert_equal(pkg.resources[0].description, 'Got changed')
        assert_equal(pkg.resources[0].format, 'CSV')
        assert_equal(pkg.resources[0].hash, 'changed')
        assert not self._has_modification_time_been_updated_since_the_mark(pkg)
        self._assert_post_determined_modification_time_is_correct(pkg)

class TestResourceChangesSolr(ControllerTestCase):
    # Similar tests to TestResourceChanges, only instead of checking
    # the update of the modification time on the package, it checks
    # it is correct in the SOLR index

    @classmethod
    def setup_class(cls):
        setup_test_search_index()
        assert_solr_schema_is_the_dgu_variant()

        CreateTestData.create_user('sysadmin')
        model.add_user_to_role(model.User.by_name(u'sysadmin'),
                               model.Role.ADMIN, model.System())
        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    @classmethod
    def _assert_search_index_has_correct_modification_time(cls, pkg):
        # SOLR only keeps three digits of the microseconds
        assert_equal(_modification_time_in_the_search_index(pkg),
                     round_down_to_milliseconds(_modification_time(pkg)))

    def test_new_package(self):
        CreateTestData.create_arbitrary({'name': 'testpkg'})
        pkg = model.Package.get('testpkg')
        assert pkg
        self._assert_search_index_has_correct_modification_time(pkg)

    def test_edit_package(self):
        CreateTestData.create_arbitrary({'name': 'testpkg5',
                                         'resources': [{'url': 'http://ff.com'}]
                                         })
        pkg = model.Package.get('testpkg5')
        model.repo.new_revision()
        pkg.notes = 'A change'
        model.repo.commit_and_remove()
        pkg = model.Package.get('testpkg5')
        self._assert_search_index_has_correct_modification_time(pkg)

    def test_new_resource(self):
        CreateTestData.create_arbitrary({'name': 'testpkg4',
                                         'resources': [{'url': 'http://ff.com'}]
                                         })
        model.repo.new_revision()
        p = model.Package.get("testpkg4")
        p.add_resource(url="http://fake_url/", format="HTML", description="A test resource")
        model.Session.add(p)
        model.repo.commit_and_remove()

        pkg = model.Package.get("testpkg4")
        self._assert_search_index_has_correct_modification_time(pkg)

    def test_delete_resource(self):
        CreateTestData.create_arbitrary({'name': 'testpkg3',
                                         'resources': [{'url': 'http://ff.com'}]
                                         })
        p = model.Package.get("testpkg3")
        num_resources = len(p.resources)

        model.repo.new_revision()
        r = p.resources[0]
        r.state = 'deleted'
        model.repo.commit_and_remove()

        p = model.Package.get("testpkg3")

        assert len(p.resources) != num_resources, "Resource wasn't deleted"
        self._assert_search_index_has_correct_modification_time(p)

    def test_resource_url_change(self):
        c = { "model": model, "session": model.Session, "user": "sysadmin",
              'extras_as_string': True, # else package_extras_save expects json
              }
        pkg_dict = get_pkg_fixture('pkg_fixture')
        pkg = get_action('package_create')(c, data_dict=pkg_dict)
        assert pkg

        # IResourceUrlChange only works when the change goes through the logic layer
        # so can't just change at the ORM level

        pkg_dict['additional_resources'][0]['url'] = 'http://google.com/'

        # Need to set the resource ID or it thinks it is a new resource.
        # In the form it is like this - the ID is in there, hidden.
        pkg_dict['additional_resources'][0]['id'] = pkg['resources'][0]['id']

        get_action('package_update')(c, data_dict=pkg_dict)

        p = model.Package.get('pkg_fixture')
        assert_equal(p.resources[0].url, 'http://google.com/')
        self._assert_search_index_has_correct_modification_time(p)

    def test_resource_other_properties_change(self):
        c = { "model": model, "session": model.Session, "user": "sysadmin",
              'extras_as_string': True, # else package_extras_save expects json
              }
        pkg_dict = get_pkg_fixture('pkg_fixture2')
        pkg = get_action('package_create')(c, data_dict=pkg_dict)
        assert pkg

        # IResourceUrlChange only works when the change goes through the logic layer
        # so can't just change at the ORM level

        pkg_dict['additional_resources'][0]['description'] = 'Got changed'
        pkg_dict['additional_resources'][0]['format'] = 'CSV'
        pkg_dict['additional_resources'][0]['hash'] = 'changed'

        # Need to set the resource ID or it thinks it is a new resource.
        # In the form it is like this - the ID is in there, hidden.
        pkg_dict['additional_resources'][0]['id'] = pkg['resources'][0]['id']

        get_action('package_update')(c, data_dict=pkg_dict)

        p = model.Package.get('pkg_fixture2')
        assert_equal(p.resources[0].description, 'Got changed')
        assert_equal(p.resources[0].format, 'CSV')
        assert_equal(p.resources[0].hash, 'changed')
        self._assert_search_index_has_correct_modification_time(p)
