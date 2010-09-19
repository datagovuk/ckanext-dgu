import urllib2
import time

from sqlalchemy.util import OrderedDict

from ckan import model
from ckan.lib.create_test_data import CreateTestData
from ckan.tests import *
from ckan.tests.wsgi_ckanclient import WsgiCkanClient
from ckanclient import CkanClient
from ckanext.getdata.loader import PackageLoader, ReplaceByExtraField, ResourceSeries, LoaderError

USER = u'annafan'

# Set to true for quicker tests using wsgi_ckanclient
# otherwise it uses ckanclient
# (some tests still fail with ckanclient currently)
WSGI_CLIENT = True

def count_pkgs():
    return model.Session.query(model.Package).count()

class TestLoaderBase(TestController):
    def setup(self):
        CreateTestData.create_arbitrary([], extra_user_names=[USER])
        user = model.User.by_name(USER)
        assert user
        if WSGI_CLIENT:
            self.testclient = WsgiCkanClient(self.app, api_key=user.apikey)
        else:
            self.sub_proc = self._start_ckan_server('test.ini')
            self.testclient = CkanClient(base_location='http://localhost:5000/api',
                                         api_key=user.apikey)
            self._wait_for_url(url='http://localhost:5000/api')


    def teardown(self):
        if WSGI_CLIENT:
            CreateTestData.delete()
        else:
            try:
                self._stop_ckan_server(self.sub_proc)
            finally:
                CreateTestData.delete()        


class TestLoader(TestLoaderBase):
    def setup(self):
        super(TestLoader, self).setup()
        self.loader = PackageLoader(self.testclient)

    # teardown is in the base class

    def test_0_simple_load(self):
        pkg_dict = {'name':u'pkgname',
                    'title':u'Boris'}
        assert not model.Package.by_name(pkg_dict['name'])
        CreateTestData.flag_for_deletion(pkg_names=[pkg_dict['name']])
        res_pkg_dict = self.loader.load_package(pkg_dict)
        assert res_pkg_dict
        pkg = model.Package.by_name(pkg_dict['name'])
        assert res_pkg_dict == pkg.as_dict(), \
               '%r != %r' % (res_pkg_dict.items(), pkg.as_dict().items())
        assert pkg
        assert pkg.name == pkg_dict['name']
        assert pkg.title == pkg_dict['title']

    def test_1_load_several(self):
        num_pkgs = count_pkgs()
        pkg_dicts = [{'name':u'pkgname_a',
                      'title':u'BorisA'},
                     {'name':u'pkgname_b',
                      'title':u'BorisB'},
                     ]
        assert not model.Package.by_name(pkg_dicts[0]['name'])
        CreateTestData.flag_for_deletion(pkg_names=[pkg_dict['name'] for pkg_dict in pkg_dicts])
        res = self.loader.load_packages(pkg_dicts)
        assert (res['num_loaded'], res['num_errors']) == (2, 0), \
               (res['num_loaded'], res['num_errors'])
        assert count_pkgs() == num_pkgs + 2, (count_pkgs() - num_pkgs)
        for pkg_index, pkg_dict in enumerate(pkg_dicts):
            pkg_name = pkg_dict['name']
            pkg = model.Package.by_name(pkg_name)
            assert pkg.id == res['pkg_ids'][pkg_index], \
                   '%s != %s' % (pkg.id, res['pkg_ids'][pkg_index])

    def test_1_load_several_with_errors(self):
        num_pkgs = count_pkgs()
        pkg_dicts = [{'name':u'pkgnameA', # not allowed uppercase name
                      'title':u'BorisA'},
                     {'name':u'pkgnameB',
                      'title':u'BorisB'},
                     ]
        assert not model.Package.by_name(pkg_dicts[0]['name'])
        CreateTestData.flag_for_deletion(pkg_names=[pkg_dict['name'] for pkg_dict in pkg_dicts])
        res = self.loader.load_packages(pkg_dicts)
        assert (res['num_loaded'], res['num_errors']) == (0, 2), \
               (res['num_loaded'], res['num_errors'])               
        assert count_pkgs() == num_pkgs, (count_pkgs() - num_pkgs)
        assert res['pkg_ids'] == [], res['pkg_ids']

    def test_2_reload(self):
        # load the package once
        num_pkgs = count_pkgs()
        pkg_dict = {'name':u'pkgname2',
                    'title':u'Boris'}
        assert not model.Package.by_name(pkg_dict['name'])
        CreateTestData.flag_for_deletion(pkg_names=[pkg_dict['name']])
        self.loader.load_package(pkg_dict)
        pkg = model.Package.by_name(pkg_dict['name'])
        assert pkg
        assert count_pkgs() == num_pkgs + 1, (count_pkgs() - num_pkgs)

        # load the package again
        pkg_dict = {'name':u'pkgname2',
                    'title':u'Boris Becker'}
        self.loader.load_package(pkg_dict)
        pkg = model.Package.by_name(pkg_dict['name'])
        assert pkg
        assert pkg.name == pkg_dict['name']
        assert pkg.title == pkg_dict['title'], pkg.title
        assert count_pkgs() == num_pkgs + 1, (count_pkgs() - num_pkgs)


class TestLoaderUsingUniqueFields(TestLoaderBase):
    def setup(self):
        self.tsi = TestSearchIndexer()
        super(TestLoaderUsingUniqueFields, self).setup()
        settings = ReplaceByExtraField('ref')
        self.loader = PackageLoader(self.testclient, settings=settings)

    # teardown is in the base class

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
        pkg_dict = {'name':u'pkgname0changed',
                    'title':u'Boris 4',
                    'extras':{u'ref':'boris-4'}}
        CreateTestData.flag_for_deletion(pkg_names=[pkg_dict['name']])
        self.loader.load_package(pkg_dict)
        assert pkg_dict['name'] == 'pkgname0changed_'
        orig_pkg = model.Package.by_name(u'pkgname0changed')
        assert orig_pkg
        assert orig_pkg.title == u'Boris 3'
        pkg = model.Package.by_name(pkg_dict['name'])
        assert pkg
        assert pkg.name == pkg_dict['name']
        assert pkg.title == pkg_dict['title']
        assert model.Package.by_name(other_pkg_dict['name'])
        assert count_pkgs() == num_pkgs + 2, (count_pkgs() - num_pkgs)

        
class TestLoaderNoSearch(TestLoaderBase):
    '''Cope as best as possible if search indexing is flakey.'''
    def setup(self):
        '''NB, no search indexing started'''
        super(TestLoaderNoSearch, self).setup()
        settings = ReplaceByExtraField('ref')
        self.loader = PackageLoader(self.testclient, settings=settings)

    # teardown is in the base class

    def test_0_reload(self):
        # create initial package
        num_pkgs = count_pkgs()
        pkg_dict = {'name':u'pkgname0',
                    'title':u'Boris',
                    'extras':{u'ref':'boris'}}
        assert not model.Package.by_name(pkg_dict['name'])
        CreateTestData.create_arbitrary([pkg_dict])
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
        # i.e. not tempted to create pkgname0_ alongside pkgname0

        
class TestLoaderGroups(TestLoaderBase):
    def setup(self):
        super(TestLoaderGroups, self).setup()
        self.loader = PackageLoader(self.testclient)

        assert count_pkgs() == 0, count_pkgs()
        pkg_dicts = [{'name':u'pkga'},
                     {'name':u'pkgb'},
                     {'name':u'pkgc'},
                     ]
        CreateTestData.create_arbitrary(pkg_dicts)
        group_dicts = [
            {'name':u'g1', 'packages':[u'pkga']},
            {'name':u'g2'},
            {'name':u'g3'},
            ]
        CreateTestData.create_groups(group_dicts, USER)
        self.pkgs = [model.Package.by_name(pkg_dict['name']) \
                     for pkg_dict in pkg_dicts]
        self.pkg_ids = [pkg.id for pkg in self.pkgs]
        
    # teardown is in the base class

    def test_0_add_to_empty_group(self):
        pkg_name = u'pkga'
        group_name = u'g2'
        pkg = model.Package.by_name(pkg_name)
        group = model.Group.by_name(group_name)
        assert group
        assert not group.packages, group.packages
        self.loader.add_pkg_to_group(pkg.name, group.name)
        group = model.Group.by_name(group_name)
        pkg = model.Package.by_name(pkg_name)
        assert group.packages == [pkg], group.packages
        
    def test_1_add_to_non_empty_group(self):
        pkg_name = u'pkgb'
        group_name = u'g1'
        pkg = model.Package.by_name(pkg_name)
        group = model.Group.by_name(group_name)
        assert group
        assert len(group.packages) == 1, group.packages
        self.loader.add_pkg_to_group(pkg.name, group.name)
        group = model.Group.by_name(group_name)
        pkg = model.Package.by_name(pkg_name)
        assert pkg in group.packages, group.packages
        assert len(group.packages) == 2, group.packages

    def test_2_add_multiple_packages(self):
        pkg_names = [u'pkgb', u'pkgc']
        group_name = u'g2'
        pkgs = [model.Package.by_name(pkg_name) for pkg_name in pkg_names]
        group = model.Group.by_name(group_name)
        assert group
        num_pkgs_at_start = len(group.packages)
        assert num_pkgs_at_start in (0, 1), group.packages
        self.loader.add_pkgs_to_group(pkg_names, group.name)
        group = model.Group.by_name(group_name)
        pkgs = [model.Package.by_name(pkg_name) for pkg_name in pkg_names]
        for pkg in pkgs:
            assert pkg in group.packages, group.packages
        assert len(group.packages) == num_pkgs_at_start + 2, group.packages

    def test_3_add_to_missing_group(self):
        pkg_names = [u'pkgb', u'pkgc']
        try:
            self.loader.add_pkgs_to_group(pkg_names, 'random_name')
        except LoaderError, e:
            assert e.args[0] == 'Group named \'random_name\' does not exist', e.args
        else:
            assert 0, 'Should have raise a LoaderError for the missing group'
        

class TestLoaderInsertingResources(TestLoaderBase):
    def setup(self):
        self.tsi = TestSearchIndexer()
        super(TestLoaderInsertingResources, self).setup()
        settings = ResourceSeries(['title', 'department'],
                                  'ons/id/',
                                  ['country'])
        self.loader = PackageLoader(self.testclient, settings)

    # teardown is in the base class

    def test_0_reload(self):
        # create initial package
        num_pkgs = count_pkgs()
        pkg_dict = {'name':u'pollution',
                    'title':u'Pollution',
                    'extras':{u'department':'air',
                              u'country':'UK', #invariant
                              u'last_updated':'Monday', #variant
                              },
                    'resources':[{'url':'pollution.com/1',
                                  'description':'ons/id/1'}],
                    }
        bogus_dict = {'name':u'bogus',
                      'title':u'Pollution',
                      'extras':{u'department':'water',
                              u'country':'UK', 
                              u'last_updated':'Monday',
                              },
                    'resources':[{'url':'pollution.com/2',
                                  'description':'ons/id/2'}],
                    }
        assert not model.Package.by_name(pkg_dict['name'])
        assert not model.Package.by_name(bogus_dict['name'])
        CreateTestData.create_arbitrary([pkg_dict, bogus_dict])
        self.tsi.index()
        pkg = model.Package.by_name(pkg_dict['name'])
        assert pkg
        assert count_pkgs() == num_pkgs + 2, (count_pkgs() - num_pkgs)
        assert len(pkg.resources) == 1, pkg.resources

        # load the same package: same title, department, updated resource
        pkg_dict = {'name':u'pollution',
                    'title':u'Pollution',
                    'extras':{u'department':'air',
                              u'country':'UK', #invariant
                              u'last_updated':'Tuesday', #variant
                              },
                    'resources':[{'url':'pollution.com/id/1',
                                  'description':'ons/id/1'}],
                    }
        self.loader.load_package(pkg_dict)
        pkg = model.Package.by_name(pkg_dict['name'])
        assert pkg
        assert pkg.name == pkg_dict['name']
        assert pkg.title == pkg_dict['title']
        assert pkg.extras['country'] == pkg_dict['extras']['country']
        assert pkg.extras['last_updated'] == pkg_dict['extras']['last_updated']
        assert count_pkgs() == num_pkgs + 2, (count_pkgs() - num_pkgs)
        assert len(pkg.resources) == 1, pkg.resources
        assert pkg.resources[0].url == pkg_dict['resources'][0]['url'], pkg.resources[0].url
        assert pkg.resources[0].description == pkg_dict['resources'][0]['description'], pkg.resources[0]['description']

        # load the same package: same title, department, new resource
        pkg_dict2 = {'name':u'pollution',
                    'title':u'Pollution',
                    'extras':{u'department':'air',
                              u'country':'UK', #invariant
                              u'last_updated':'Tuesday', #variant
                              },
                    'resources':[{'url':'pollution.com/id/3',
                                  'description':'ons/id/3'}],
                    }
        self.loader.load_package(pkg_dict2)
        pkg = model.Package.by_name(pkg_dict2['name'])
        assert pkg
        assert pkg.name == pkg_dict2['name']
        assert pkg.title == pkg_dict2['title']
        assert pkg.extras['country'] == pkg_dict2['extras']['country']
        assert pkg.extras['last_updated'] == pkg_dict2['extras']['last_updated']
        assert count_pkgs() == num_pkgs + 2, (count_pkgs() - num_pkgs)
        assert len(pkg.resources) == 2, pkg.resources
        assert pkg.resources[0].url == pkg_dict['resources'][0]['url'], pkg.resources[0].url
        assert pkg.resources[0].description == pkg_dict['resources'][0]['description'], pkg.resources[0]['description']
        assert pkg.resources[1].url == pkg_dict2['resources'][0]['url'], pkg.resources[1].url
        assert pkg.resources[1].description == pkg_dict2['resources'][0]['description'], pkg.resources[1]['description']

        # load the different package: because of different department
        pkg_dict3 = {'name':u'pollution',
                    'title':u'Pollution',
                    'extras':{u'department':'river',
                              u'country':'UK', #invariant
                              u'last_updated':'Tuesday', #variant
                              },
                    'resources':[{'url':'pollution.com/id/3',
                                  'description':'Lots of pollution | ons/id/3'}],
                    }
        self.loader.load_package(pkg_dict3)
        assert count_pkgs() == num_pkgs + 3, (count_pkgs() - num_pkgs)
        pkg_names = [pkg.name for pkg in model.Session.query(model.Package).all()]
        pkg = model.Package.by_name(u'pollution_')
        assert pkg
        assert pkg.extras['department'] == pkg_dict3['extras']['department']

        # load the same package: but with different country
        # should just get a warning
        pkg_dict4 = {'name':u'pollution',
                    'title':u'Pollution',
                    'extras':OrderedDict([
                         (u'department', 'air'),
                         (u'country', 'UK and France'), #invariant
                         (u'last_updated', 'Tuesday'), #variant
                         ]),
                    'resources':[OrderedDict([
                         ('url', 'pollution.com/id/3'),
                         ('description', 'Lots of pollution | ons/id/3'),
                         ])],
                    }
        self.loader.load_package(pkg_dict4)
        pkg = model.Package.by_name(pkg_dict4['name'])
        assert pkg
        assert pkg.name == pkg_dict4['name']
        assert pkg.title == pkg_dict4['title']
        assert pkg.extras['country'] == pkg_dict4['extras']['country']
        assert pkg.extras['last_updated'] == pkg_dict4['extras']['last_updated']
        assert count_pkgs() == num_pkgs + 3, (count_pkgs() - num_pkgs)
        assert len(pkg.resources) == 2, pkg.resources
        assert pkg.resources[0].url == pkg_dict['resources'][0]['url'], pkg.resources[0].url
        assert pkg.resources[0].description == pkg_dict['resources'][0]['description'], pkg.resources[0]['description']
        assert pkg.resources[1].url == pkg_dict4['resources'][0]['url'], pkg.resources[1].url
        assert pkg.resources[1].description == pkg_dict4['resources'][0]['description'], pkg.resources[1]['description']

