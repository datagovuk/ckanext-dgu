from ckan import model
from ckan.lib.create_test_data import CreateTestData
from ckan.tests import *
from ckan.tests.wsgi_ckanclient import WsgiCkanClient
from ckanext.getdata.loader import PackageLoader

USER = u'annafan'

def count_pkgs():
    return model.Session.query(model.Package).count()

class TestLoader(TestController):
    def setup(self):
        CreateTestData.create_arbitrary([], extra_user_names=[USER])
        user = model.User.by_name(USER)
        assert user
        self.testclient = WsgiCkanClient(self.app, api_key=user.apikey)
        self.loader = PackageLoader(self.testclient)

    def teardown(self):
        CreateTestData.delete()        
    
    def test_0_simple_load(self):
        pkg_dict = {'name':u'pkgname',
                    'title':u'Boris'}
        assert not model.Package.by_name(pkg_dict['name'])
        CreateTestData.flag_for_deletion(pkg_names=[pkg_dict['name']])
        self.loader.load_package(pkg_dict)
        pkg = model.Package.by_name(pkg_dict['name'])
        assert pkg
        assert pkg.name == pkg_dict['name']
        assert pkg.title == pkg_dict['title']

    def test_1_reload(self):
        # load the package once
        num_pkgs = count_pkgs()
        pkg_dict = {'name':u'pkgname1',
                    'title':u'Boris'}
        assert not model.Package.by_name(pkg_dict['name'])
        CreateTestData.flag_for_deletion(pkg_names=[pkg_dict['name']])
        self.loader.load_package(pkg_dict)
        pkg = model.Package.by_name(pkg_dict['name'])
        assert pkg
        assert count_pkgs() == num_pkgs + 1, (count_pkgs() - num_pkgs)

        # load the package again
        pkg_dict = {'name':u'pkgname1',
                    'title':u'Boris Becker'}
        self.loader.load_package(pkg_dict)
        pkg = model.Package.by_name(pkg_dict['name'])
        assert pkg
        assert pkg.name == pkg_dict['name']
        assert pkg.title == pkg_dict['title']
        assert count_pkgs() == num_pkgs + 1, (count_pkgs() - num_pkgs)

class TestLoaderUsingUniqueFields(TestController):
    def setup(self):
        self.tsi = TestSearchIndexer()
        CreateTestData.create_arbitrary([], extra_user_names=[USER])
        user = model.User.by_name(USER)
        assert user
        self.testclient = WsgiCkanClient(self.app, api_key=user.apikey)
        self.loader = PackageLoader(self.testclient, unique_extra_field='ref')

    def teardown(self):
        CreateTestData.delete()        

    def test_0_reload(self):
        # create initial package
        num_pkgs = count_pkgs()
        pkg_dict = {'name':u'pkgname0',
                    'title':u'Boris',
                    'extras':{u'ref':'boris'}}
        assert not model.Package.by_name(pkg_dict['name'])
        CreateTestData.create_arbitrary([pkg_dict])
        self.tsi.index()
        pkg = model.Package.by_name(pkg_dict['name'])
        assert pkg
        assert count_pkgs() == num_pkgs + 1, (count_pkgs() - num_pkgs)

        # load the package with same name and ref
        pkg_dict = {'name':u'pkgname0',
                    'title':u'Boris 2',
                    'extras':{u'ref':'boris'}}
        self.loader.load_package(pkg_dict)
        pkg = model.Package.by_name(pkg_dict['name'])
        assert pkg
        assert pkg.name == pkg_dict['name']
        assert pkg.title == pkg_dict['title']
        assert count_pkgs() == num_pkgs + 1, (count_pkgs() - num_pkgs)

        # load the package with different name, same ref
        pkg_dict = {'name':u'pkgname0changed',
                    'title':u'Boris 3',
                    'extras':{u'ref':'boris'}}
        CreateTestData.flag_for_deletion(pkg_names=[pkg_dict['name']])
        self.loader.load_package(pkg_dict)
        pkg = model.Package.by_name(pkg_dict['name'])
        assert pkg
        assert pkg.name == pkg_dict['name']
        assert pkg.title == pkg_dict['title']
        assert count_pkgs() == num_pkgs + 1, (count_pkgs() - num_pkgs)

        # load the package with same name, different ref - new package
        other_pkg_dict = pkg_dict
        pkg_dict = {'name':u'pkgname0',
                    'title':u'Boris 4',
                    'extras':{u'ref':'boris-changed'}}
        CreateTestData.flag_for_deletion(pkg_names=[pkg_dict['name']])
        self.loader.load_package(pkg_dict)
        pkg = model.Package.by_name(pkg_dict['name'])
        assert pkg
        assert pkg.name == pkg_dict['name']
        assert pkg.title == pkg_dict['title']
        assert model.Package.by_name(other_pkg_dict['name'])
        assert count_pkgs() == num_pkgs + 2, (count_pkgs() - num_pkgs)
        

        
