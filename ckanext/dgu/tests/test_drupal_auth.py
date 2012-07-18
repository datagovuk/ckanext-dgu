import datetime

import Cookie
from nose.tools import assert_equal

from ckan import model

from ckanext.dgu.authentication.drupal_auth import DrupalAuthMiddleware
from ckanext.dgu.drupalclient import DrupalClient
from ckanext.dgu.tests import MockDrupalCase

class TestCookie:
    @classmethod
    def setup_class(cls):
        cls.drupal_cookie = '__utmz=217959684.1298907582.2.1.utmcsr=google|utmccn=(organic)|utmcmd=organic|utmctr=coi%20office%20information; __utma=217959684.1645507268.1266337989.1266337989.1298907782.2; SESSff851ac67dd7b161b4807a4288bdeaba=ae257e890935e0cc123ccc71797668e4; DRXtrArgs=bob; DRXtrArgs2=ed3d3918bf63e9c41ea81a2e5a2364ba;'
        cls.drupal_cookies = 'SESSwrong=abc; SESSff851ac67dd7b161b4807a4288bdeaba=ae257e890935e0cc123ccc71797668e4; SESSwrongtoo=def;'
        cls.drupal_and_ckan_cookies = '__utmz=217959684.1298907582.2.1.utmcsr=google|utmccn=(organic)|utmcmd=organic|utmctr=coi%20office%20information; __utma=217959684.1645507268.1266337989.1266337989.1298907782.2; SESSff851ac67dd7b161b4807a4288bdeaba=ae257e890935e0cc123ccc71797668e4; DRXtrArgs=bob; DRXtrArgs2=ed3d3918bf63e9c41ea81a2e5a2364ba; auth_tkt="a578c4a0d21bdbde7f80cd271d60b66f4ceabc3f4466!";'
        cls.environ = {'SERVER_NAME': 'testserver.org'}

    def test_drupal_cookie_parse(self):
        res = DrupalAuthMiddleware._drupal_cookie_parse(self.drupal_cookie, self.environ['SERVER_NAME'])
        assert_equal(res, 'ae257e890935e0cc123ccc71797668e4')

    def test_drupal_cookie_parse__multiple_cookies(self):
        # pick out the correct Drupal cookie for this server (Drupal cookies are per-sub-domain)
        res = DrupalAuthMiddleware._drupal_cookie_parse(self.drupal_cookies, self.environ['SERVER_NAME'])
        assert_equal(res, 'ae257e890935e0cc123ccc71797668e4')

    def test_drupal_cookie_parse__wrong_server(self):
        server_name = 'wrong_server_for_the_SESS.org'
        res = DrupalAuthMiddleware._drupal_cookie_parse(self.drupal_cookie, server_name)
        assert_equal(res, None)

    def test_is_this_a_ckan_cookie(self):
        res = DrupalAuthMiddleware._is_this_a_ckan_cookie(self.drupal_and_ckan_cookies)
        assert_equal(res, True)

    def test_is_this_a_ckan_cookie__no(self):
        res = DrupalAuthMiddleware._is_this_a_ckan_cookie(self.drupal_cookie)
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
    cookie_name = 'auth_tkt'
    ckan_session_base = 'ab48fe'

    def __init__(self):
        self.remembered = []

    def remember(self, environ, identity):
        self.remembered.append((environ, identity))
        ckan_session_id = '%s!%s' % (self.ckan_session_base,
                                     identity.get('userdata', ''))
        set_cookie = '%s=%s; Path=/;' % (self.cookie_name, ckan_session_id)
        return [('Set-Cookie', set_cookie)]
    
class TestDrupalAuthMiddleware(MockDrupalCase):
    @classmethod
    def setup_class(cls):
        MockDrupalCase.setup_class()

        # delete user
        user = model.User.by_name(u'62')
        if user:
            user.delete()
            model.Session.commit_and_remove()
        
    def test_1_sign_in(self):
        cookie_string = 'Cookie: __utma=217959684.178461911.1286034407.1286034407.1286178542.2; __utmz=217959684.1286178542.2.2.utmcsr=google|utmccn=(organic)|utmcmd=organic|utmctr=coi%20london; DRXtrArgs=James+Gardner; DRXtrArgs2=3e174e7f1e1d3fab5ca138c0a023e13a; SESSff851ac67dd7b161b4807a4288bdeaba=4160a72a4d6831abec1ac57d7b5a59eb;"'
        assert not DrupalAuthMiddleware._is_this_a_ckan_cookie(cookie_string)
        app = MockApp()
        app_conf = None
        self.middleware = DrupalAuthMiddleware(app, app_conf)
        # (the drupal client defaults to mock drupal instance)

        # make request with the Drupal cookie
        self.mock_auth_tkt = MockAuthTkt()
        environ = {'HTTP_COOKIE': cookie_string,
                   'SERVER_NAME': 'testserver.org',
                   'repoze.who.plugins': {'dgu_auth_tkt': self.mock_auth_tkt}}
        start_response = mock_start_response
        self.res = self.middleware(environ, start_response)

        # check environ has Drupal user info
        assert isinstance(self.res, MockApp)
        assert_equal(len(self.res.calls), 1)
        environ = self.res.calls[0][0]

        # check the ckan user was created
        user = model.User.by_name(u'user_d62')
        assert user
        assert_equal(user.fullname, u'testname')
        assert_equal(user.email, u'joe@dept.gov.uk')
        assert_equal(user.created, datetime.datetime(2011, 10, 20, 15, 9, 22))

        # check environ's HTTP_COOKIE has CKAN user info for the app to use
        assert_equal(environ['REMOTE_USER'], 'user_d62')

        # check response has Set-Cookie instructions which tell the browser
        # to store for the future
        start_response = self.res.calls[0][1]
        status, headers, exc_info = (1, [], None)
        res = start_response(status, headers, exc_info)
        headers = res[1]
        assert_equal(headers, [('Set-Cookie', 'auth_tkt=ab48fe!4160a72a4d6831abec1ac57d7b5a59eb; Path=/;'),
                               ('Existing_header', 'existing_header_value;')])

        # check auth_tkt was told to remember the Drupal user info
        assert_equal(len(self.mock_auth_tkt.remembered), 1)
        assert_equal(len(self.mock_auth_tkt.remembered[0]), 2)
        remembered_environ, remembered_identity = self.mock_auth_tkt.remembered[0]
        remembered_environ_keys = set(remembered_environ.keys())
        expected_keys = set(('REMOTE_USER', 'repoze.who.plugins', 'HTTP_COOKIE'))
        missing_keys = expected_keys - remembered_environ_keys
        assert not missing_keys, 'Missing %s. %r != %r' % (remembered_environ_keys, expected_keys, remembered_environ_keys)
        assert_equal(remembered_environ['REMOTE_USER'], 'user_d62')
        assert_equal(set(remembered_identity.keys()), set(('tokens', 'userdata', 'repoze.who.userid')))
        assert_equal(remembered_identity['repoze.who.userid'], 'user_d62')
        
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
        cookie_string = 'Cookie: __utma=217959684.178461911.1286034407.1286034407.1286178542.2; __utmz=217959684.1286178542.2.2.utmcsr=google|utmccn=(organic)|utmcmd=organic|utmctr=coi%%20london; DRXtrArgs=James+Gardner; DRXtrArgs2=3e174e7f1e1d3fab5ca138c0a023e13a; SESSff851ac67dd7b161b4807a4288bdeaba=4160a72a4d6831abec1ac57d7b5a59eb; auth_tkt="ab48fe!4160a72a4d6831abec1ac57d7b5a59eb";"'
        assert DrupalAuthMiddleware._is_this_a_ckan_cookie(cookie_string)
        app = MockApp()
        app_conf = None
        self.middleware = DrupalAuthMiddleware(app, app_conf)
        # (the drupal client defaults to mock drupal instance)

        # make request with the Drupal auth_tkt cookie
        self.mock_auth_tkt = MockAuthTkt()
        environ = {'HTTP_COOKIE': cookie_string,
                   'SERVER_NAME': 'testserver.org',
                   'repoze.who.plugins': {'dgu_auth_tkt': self.mock_auth_tkt},
                   # inserted by auth_tkt on seeing the auth_tkt cookie:
                   'repoze.who.identity': {
                       'repoze.who.userid': 'user_d62',
                       'userdata': '4160a72a4d6831abec1ac57d7b5a59eb'
                       }
                   }
        start_response = mock_start_response
        self.res = self.middleware(environ, start_response)

        # environ doesn't have Drupal user info this time
        assert isinstance(self.res, MockApp)
        assert_equal(len(self.res.calls), 1)
        environ = self.res.calls[0][0]

        # check the ckan user was created
        user = model.User.by_name(u'62')
        assert user
        assert_equal(user.fullname, u'testname')

        # response has no need for Set-Cookie instructions as cookie already
        # there
        start_response = self.res.calls[0][1]
        status, headers, exc_info = (1, [], None)
        res = start_response(status, headers, exc_info)
        headers = res[1]
        assert_equal(headers, [('Existing_header', 'existing_header_value;')])

        # no need for auth_tkt to be told to remember the Drupal user info
        assert_equal(len(self.mock_auth_tkt.remembered), 0)

    #TODO: test when there is a non-Drupal auth_tkt cookie.

    #TODO: test when you were signed in as user A and then logout and sign in
    #      as user B without a clear a request to CKAN in between.
