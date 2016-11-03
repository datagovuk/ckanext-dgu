from nose.tools import assert_equal

import ckan.new_tests.factories as factories
import ckan.new_tests.helpers as helpers

from ckanext.dgu.gemini_postprocess import (
    process_package_,
    process_resource,
    _is_wms,
    wms_capabilities_url,
    _wms_base_urls,
    strip_session_id,
    )


class TestProcessPackage(object):
    # Warning - servers may go down
    def test_process_package(self):
        pkg = {
            'notes': 'Test',
            'license_id': 'uk-ogl',
            'extras': [{'key': 'UKLP', 'value': 'True'}],
            'resources': [
                {
                    'url': 'http://environment.data.gov.uk/ds/wms?SERVICE=WMS&INTERFACE=ENVIRONMENT--6f51a299-351f-4e30-a5a3-2511da9688f7',
                    'description': 'Resource locator',
                }
                ]
            }
        pkg = factories.Dataset(**pkg)

        process_package_(pkg['id'])

        pkg = helpers.call_action('package_show', id=pkg['id'])
        res = pkg['resources'][0]
        assert_equal(res['format'], 'WMS')
        assert_equal(res['wms_base_urls'], 'http://www.geostore.com/OGC/OGCInterface;jsessionid=')


class TestProcessResource(object):
    # Warning - servers may go down
    def test_process_resource(self):
        res = {
            'url': 'http://environment.data.gov.uk/ds/wms?SERVICE=WMS&INTERFACE=ENVIRONMENT--6f51a299-351f-4e30-a5a3-2511da9688f7'
            }
        process_resource(res)
        assert_equal(res['format'], 'WMS')
        assert_equal(res['wms_base_urls'], 'http://www.geostore.com/OGC/OGCInterface;jsessionid=')


class TestStripSessionId(object):
    def test_jsessionid(self):
        assert_equal(strip_session_id(
            'http://www.geostore.com/OGC/OGCInterface;jsessionid=d5A2nBGr7eFdyUDUfo5gWD8R'
            ),
            'http://www.geostore.com/OGC/OGCInterface;jsessionid='
        )


class TestWmsBaseUrls(object):
    def test_ea(self):
        # https://data.gov.uk/dataset/lidar-composite-dsm-1m1
        assert_equal(
            _wms_base_urls('http://environment.data.gov.uk/ds/wms?SERVICE=WMS&INTERFACE=ENVIRONMENT--6f51a299-351f-4e30-a5a3-2511da9688f7&request=GetCapabilities'),
            set(['http://www.geostore.com/OGC/OGCInterface;jsessionid=']))


class TestWmsCapabilitiesUrl(object):
    def test_real(self):
        assert_equal(wms_capabilities_url(
            'http://environment.data.gov.uk/ds/wms?SERVICE=WMS&INTERFACE=ENVIRONMENT--6f51a299-351f-4e30-a5a3-2511da9688f7&request=GetCapabilities'
            ),
            'http://environment.data.gov.uk/ds/wms?SERVICE=WMS&INTERFACE=ENVIRONMENT--6f51a299-351f-4e30-a5a3-2511da9688f7&request=GetCapabilities'
            )

    def test_base_url(self):
        assert_equal(wms_capabilities_url(
            'http://example/com?'
            ),
            'http://example/com?service=WMS&request=GetCapabilities'
            )

    def test_existing_params_left_unchanged(self):
        assert_equal(wms_capabilities_url(
            'http://example/com?service=WFS&request=GetThing'
            ),
            'http://example/com?service=WFS&request=GetThing'
            )

    def test_version_added(self):
        assert_equal(wms_capabilities_url(
            'http://example/com?', '1.3'
            ),
            'http://example/com?service=WMS&request=GetCapabilities&version=1.3'
            )

    def test_version_removed(self):
        assert_equal(wms_capabilities_url(
            'http://example/com?service=WMS&request=GetCapabilities&version=1.3'
            ),
            'http://example/com?service=WMS&request=GetCapabilities'
            )

    def test_version_changed(self):
        assert_equal(wms_capabilities_url(
            'http://example/com?service=WMS&request=GetCapabilities&version=1.3',
            '1.4'
            ),
            'http://example/com?service=WMS&request=GetCapabilities&version=1.4'
            )

    def test_uppercase_params_left_unchanged(self):
        assert_equal(wms_capabilities_url(
            'http://example/com?SERVICE=WFS&REQUEST=GetThing'
            ),
            'http://example/com?SERVICE=WFS&REQUEST=GetThing'
            )


class TestIsWms(object):
    # Warning - servers may go down
    def test_html(self):
        assert_equal(_is_wms(
            'http://environment.data.gov.uk/ds/survey/'
            ), False)

    def test_wms_ea(self):
        # http://data.gov.uk/dataset/lidar-composite-dsm-1m1
        assert_equal(_is_wms(
            'http://environment.data.gov.uk/ds/wms?SERVICE=WMS&INTERFACE=ENVIRONMENT--6f51a299-351f-4e30-a5a3-2511da9688f7'
            ), True)
