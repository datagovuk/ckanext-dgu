import Cookie

from nose.tools import assert_equal
from ckan import model

from ckanext.dgu.middleware import drupal_extract_cookie, is_ckan_signed_in, AuthAPIMiddleware
from ckanext.dgu.drupalclient import DrupalClient
from ckanext.dgu.tests import MockDrupalCase


class TestCookie:
    @classmethod
    def setup_class(cls):
        cls.drupal_cookie = '__utmz=217959684.1298907582.2.1.utmcsr=google|utmccn=(organic)|utmcmd=organic|utmctr=coi%20office%20information; __utma=217959684.1645507268.1266337989.1266337989.1298907782.2; SESS9854552e7c5dba5831db083c5372623c=ae257e890935e0cc123ccc71797668e4; DRXtrArgs=bob; DRXtrArgs2=ed3d3918bf63e9c41ea81a2e5a2364ba;'
        cls.ckan_cookie = '__utmz=217959684.1298907582.2.1.utmcsr=google|utmccn=(organic)|utmcmd=organic|utmctr=coi%20office%20information; __utma=217959684.1645507268.1266337989.1266337989.1298907782.2; SESS9854552e7c5dba5831db083c5372623c=ae257e890935e0cc123ccc71797668e4; DRXtrArgs=bob; DRXtrArgs2=ed3d3918bf63e9c41ea81a2e5a2364ba; auth_tkt="a578c4a0d21bdbde7f80cd271d60b66f4ceabc3f4466!";'

    def test_drupal_extract_cookie(self):        
        res = drupal_extract_cookie(self.drupal_cookie)
        assert_equal(res, 'ae257e890935e0cc123ccc71797668e4')

    def test_is_ckan_signed_in(self):
        res = is_ckan_signed_in(self.ckan_cookie)
        assert_equal(res, True)        

    def test_is_ckan_signed_in_no_cookie(self):
        res = is_ckan_signed_in(self.drupal_cookie)
        assert_equal(res, False)

class MockApp:
    def __init__(self):
        self.calls = []
        
    def __call__(self, environ, new_start_response):
        # pass-through, but logs arguments, so tests can check them.
        self.calls.append((environ, new_start_response))
        return self

def mock_start_response(status, headers, exc_info):
    headers.append(('Existing_header', 'existing_header_value;'))
    return (status, headers, exc_info)

class MockAuthTkt:
    cookie_name = 'bob'
    cookie_value = 'ab48fe' # based on the identity usually

    def __init__(self):
        self.remembered = []

    def remember(self, environ, identity):
        self.remembered.append((environ, identity))
        set_cookie = '%s=%s; Path=/;' % (self.cookie_name, self.cookie_value)
        return [('Set-Cookie', set_cookie)]
    
class TestAuthAPIMiddleware(MockDrupalCase):
    @classmethod
    def setup_class(cls):
        MockDrupalCase.setup_class()

        # delete user
        user = model.User.by_name(u'62')
        if user:
            user.delete()
            model.Session.commit_and_remove()
        
    def test_1_sign_in(self):
        self.cookie_string = 'Cookie: __utma=217959684.178461911.1286034407.1286034407.1286178542.2; __utmz=217959684.1286178542.2.2.utmcsr=google|utmccn=(organic)|utmcmd=organic|utmctr=coi%20london; DRXtrArgs=James+Gardner; DRXtrArgs2=3e174e7f1e1d3fab5ca138c0a023e13a; SESS9854522e7c5dba5831db083c5372623c=4160a72a4d6831abec1ac57d7b5a59eb;"'
        assert not is_ckan_signed_in(self.cookie_string)
        app = MockApp()
        app_conf = None
        self.middleware = AuthAPIMiddleware(app, app_conf)
        # (the drupal client defaults to mock drupal instance)

        # make request with the Drupal cookie
        self.mock_auth_tkt = MockAuthTkt()
        environ = {'HTTP_COOKIE': self.cookie_string,
                   'repoze.who.plugins': {'auth_tkt': self.mock_auth_tkt}}
        start_response = mock_start_response
        self.res = self.middleware(environ, start_response)

        # check environ has Drupal user info
        assert isinstance(self.res, MockApp)
        assert_equal(len(self.res.calls), 1)
        environ = self.res.calls[0][0]
        assert_equal(environ['drupal.uid'], '62')
        assert_equal(environ['drupal.publishers']['1'], 'National Health Service')
        assert len(environ['drupal.publishers']) > 5, environ['drupal.publishers']
        assert_equal(environ['drupal.name'], 'testname')

        # check the ckan user was created
        user = model.User.by_name(u'62')
        assert user
        assert_equal(user.fullname, u'testname')

        # check environ's HTTP_COOKIE has CKAN user info for the app to use
        cookies = Cookie.SimpleCookie()
        cookies.load(environ['HTTP_COOKIE'])

        assert_equal(cookies['ckan_user'].value, '62')
        assert_equal(cookies['ckan_display_name'].value, 'testname')
        assert_equal(cookies['ckan_apikey'].value, user.apikey)

        # check response has Set-Cookie instructions which tell the browser
        # to store for the future
        start_response = self.res.calls[0][1]
        status, headers, exc_info = (1, [], None)
        res = start_response(status, headers, exc_info)
        headers = res[1]
        assert_equal(headers, [('Set-Cookie', 'bob=ab48fe; Path=/;'),
                               ('Set-Cookie', 'ckan_apikey="%s"; Path=/;' % user.apikey),
                               ('Set-Cookie', 'ckan_display_name="testname"; Path=/;'),
                               ('Set-Cookie', 'ckan_user="62"; Path=/;'),
                               ('Existing_header', 'existing_header_value;')])

        # check auth_tkt was told to remember the Drupal user info
        assert_equal(len(self.mock_auth_tkt.remembered), 1)
        assert_equal(len(self.mock_auth_tkt.remembered[0]), 2)
        auth = self.mock_auth_tkt.remembered[0][0]
        # {'drupal.name': 'testname',
        #  'HTTP_COOKIE': 'ckan_apikey="4adaefba-b307-408c-a14a-c6a49c9e9965"; ckan_display_name="testname"; ckan_user="62"',
        #  'drupal.uid': '62',
        #  'drupal.publishers': {'1': 'National Health Service', '3': 'Department for Education', '2': 'Ealing PCT', '5': 'Department for Business, Innovation and Skills', '4': 'Department of Energy and Climate Change', '6': 'Department for Communities and Local Government'},
        #  'repoze.who.plugins': {'auth_tkt': <ckanext.dgu.tests.test_middleware.MockAuthTkt instance at 0xa4cdfec>}}
        auth_keys = set(auth.keys())
        expected_keys = set(('drupal.name', 'drupal.uid', 'drupal.publishers', 'HTTP_COOKIE'))
        missing_keys = expected_keys - auth_keys
        assert not missing_keys, missing_keys
        assert_equal(auth['drupal.name'], 'testname')
        assert_equal(auth['drupal.uid'], '62')
        assert len(environ['drupal.publishers']) > 5, environ['drupal.publishers']
        assert_equal(auth['drupal.publishers']['1'], 'National Health Service')
        assert_equal(auth['HTTP_COOKIE'], 'ckan_apikey="%s"; ckan_display_name="testname"; ckan_user="62"' % user.apikey)
        
    def test_2_already_signed_in(self):
        user = model.User.by_name(u'62')
        if not user:            
            user = model.User(
                name=u'62', 
                fullname=u'testname', 
                about=u'Drupal auto-generated user',
            )
            model.Session.add(user)
            model.repo.commit_and_remove()
        user = model.User.by_name(u'62')
        assert user
        self.cookie_string = 'Cookie: __utma=217959684.178461911.1286034407.1286034407.1286178542.2; __utmz=217959684.1286178542.2.2.utmcsr=google|utmccn=(organic)|utmcmd=organic|utmctr=coi%%20london; DRXtrArgs=James+Gardner; DRXtrArgs2=3e174e7f1e1d3fab5ca138c0a023e13a; SESS9854522e7c5dba5831db083c5372623c=4160a72a4d6831abec1ac57d7b5a59eb; auth_tkt="a578c4a0d21bdbde7f80cd271d60b66f4ceabc3f4466!"; ckan_apikey="%s"; ckan_display_name="testname"; ckan_user="62";"' % user.apikey
        assert is_ckan_signed_in(self.cookie_string)
        app = MockApp()
        app_conf = None
        self.middleware = AuthAPIMiddleware(app, app_conf)
        # (the drupal client defaults to mock drupal instance)

        # make request with the Drupal cookie
        self.mock_auth_tkt = MockAuthTkt()
        environ = {'HTTP_COOKIE': self.cookie_string,
                   'repoze.who.plugins': {'auth_tkt': self.mock_auth_tkt}}
        start_response = mock_start_response
        self.res = self.middleware(environ, start_response)

        # environ doesn't have Drupal user info this time
        assert isinstance(self.res, MockApp)
        assert_equal(len(self.res.calls), 1)
        environ = self.res.calls[0][0]
        assert_equal(environ['drupal.uid'], None)

        # check the ckan user was created
        user = model.User.by_name(u'62')
        assert user
        assert_equal(user.fullname, u'testname')

        # check environ's HTTP_COOKIE has CKAN user info for the app to use
        cookies = Cookie.SimpleCookie()
        cookies.load(str(environ['HTTP_COOKIE']))

        assert_equal(cookies['ckan_user'].value, '62')
        assert_equal(cookies['ckan_display_name'].value, 'testname')
        assert_equal(cookies['ckan_apikey'].value, user.apikey)

        # response has no need for Set-Cookie instructions as cookie already
        # there
        start_response = self.res.calls[0][1]
        status, headers, exc_info = (1, [], None)
        res = start_response(status, headers, exc_info)
        headers = res[1]
        assert_equal(headers, [('Existing_header', 'existing_header_value;')])

        # no need for auth_tkt to be told to remember the Drupal user info
        assert_equal(len(self.mock_auth_tkt.remembered), 0)

