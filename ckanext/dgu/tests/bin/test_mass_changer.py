from nose.plugins.skip import SkipTest

from ckan import model
from ckan.tests import *
from ckan.tests.wsgi_ckanclient import WsgiCkanClient
from ckan.lib.create_test_data import CreateTestData

from ckanext.dgu.bin.mass_changer import *

raise SkipTest('MassChanger deprecated')

class TestMassChanger(TestController):
    @classmethod
    def setup_class(self):
        # create test data
        CreateTestData.create()
        username = 'annafan'
        user = model.User.by_name(unicode(username))
        assert user
        self.testclient = WsgiCkanClient(self.app, api_key=user.apikey, base_location='/api/2')

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_0_change_pkg(self):
        anna_before = self.anna.as_dict()
        war_before = self.war.as_dict()
        self.assert_equal(anna_before['license_id'], 'other-open')
        self.assert_equal(war_before['license_id'], None)

        # do the change
        new_license_id = 'test-license'        
        instructions = [
            ChangeInstruction(BasicPackageMatcher('name', 'annakarenina'),
                              BasicPackageChanger('license_id', new_license_id))
            ]
        self.mass_changer = MassChanger(self.testclient, instructions)
        self.mass_changer.run()

        # check anna has new license
        pkg = model.Package.by_name(u'annakarenina')
        anna_after = self.anna.as_dict()
        war_after = self.war.as_dict()
        self.assert_equal(anna_after['license_id'], new_license_id)
        self.assert_equal(war_after['license_id'], war_before['license_id'])

        # check no other properties have changed
        for pkg_dict_before, pkg_dict_after in [(anna_before, anna_after),
                                                (war_before, war_after)]:
            keys = set(pkg_dict_before.keys())
            assert keys == set(pkg_dict_after.keys()), set(pkg_dict_after.keys()) ^ set(pkg_dict_before.keys())
            for key in keys:
                if key not in ['license_id', 'license', 'revision_id',
                               'metadata_modified']:
                    assert pkg_dict_before[key] == pkg_dict_after[key], \
                           '%s %s: %r!=%r' % (pkg_dict_before['name'], key, pkg_dict_before[key], pkg_dict_after[key])

    def test_1_multiple_instructions(self):
        extra_field = 'genre'
        anna_before = self.anna.as_dict()
        war_before = self.war.as_dict()
        self.assert_equal(anna_before['extras'][extra_field], 'romantic novel')
        assert not war_before['extras'].has_key(extra_field)

        # do the change
        new_anna_value = 'test-anna' 
        new_value = 'test'
        instructions = [
            ChangeInstruction(BasicPackageMatcher(extra_field, 'romantic novel'),
                              BasicPackageChanger(extra_field, new_anna_value)),
            ChangeInstruction(AnyPackageMatcher(),
                              BasicPackageChanger(extra_field, new_value)),
            ]
        self.mass_changer = MassChanger(self.testclient, instructions)
        self.mass_changer.run()

        # check new licenses
        pkg = model.Package.by_name(u'annakarenina')
        anna_after = self.anna.as_dict()
        war_after = self.war.as_dict()
        self.assert_equal(anna_after['extras'][extra_field], new_anna_value)
        self.assert_equal(war_after['extras'][extra_field], new_value)

    def test_2_no_change(self):
        extra_field = 'original media'
        anna_before = self.anna.as_dict()
        war_before = self.war.as_dict()
        self.assert_equal(anna_before['extras'][extra_field], 'book')
        assert not war_before['extras'].has_key(extra_field)

        # do the change
        new_anna_value = 'test-anna' 
        new_value = 'test'
        instructions = [
            ChangeInstruction(BasicPackageMatcher('name', 'annakarenina'),
                              NoopPackageChanger()),
            ChangeInstruction(AnyPackageMatcher(),
                              BasicPackageChanger(extra_field, new_value)),
            ]
        self.mass_changer = MassChanger(self.testclient, instructions)
        self.mass_changer.run()

        # check new licenses
        pkg = model.Package.by_name(u'annakarenina')
        anna_after = self.anna.as_dict()
        war_after = self.war.as_dict()
        self.assert_equal(anna_after['extras'][extra_field], 'book')
        self.assert_equal(war_after['extras'][extra_field], new_value)

    def test_3_copy_field(self):
        anna_before = self.anna.as_dict()
        self.assert_equal(anna_before['name'], 'annakarenina')
        self.assert_equal(anna_before['title'], 'A Novel By Tolstoy')

        # do the change
        instructions = [
            ChangeInstruction(BasicPackageMatcher('name', 'annakarenina'),
                              BasicPackageChanger('title', '%(name)s'))
            ]
        self.mass_changer = MassChanger(self.testclient, instructions)
        self.mass_changer.run()

        # check anna has new license
        anna_after = self.anna.as_dict()
        self.assert_equal(anna_after['title'], 'annakarenina')

    def test_4_create_resource(self):
        pkg_before = self.anna.as_dict()
        self.assert_equal(len(pkg_before['resources']), 2)

        # do the change
        instructions = [
            ChangeInstruction(BasicPackageMatcher('name', 'annakarenina'),
                              CreateResource(url='http://res.xls',
                                             format='XLS',
                                             description='Full text'))
            ]
        self.mass_changer = MassChanger(self.testclient, instructions)
        self.mass_changer.run()

        # check change
        pkg_after = self.anna.as_dict()
        new_res = pkg_after['resources'][2]
        self.assert_equal(new_res['url'], 'http://res.xls')
        self.assert_equal(new_res['format'], 'XLS')
        self.assert_equal(new_res['description'], 'Full text')

