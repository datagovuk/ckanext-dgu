import logging
import re
import urllib2
import socket
import httplib
from lxml import etree
import traceback
import urlparse
import urllib
import json

from owslib import wms as owslib_wms

from ckan.common import OrderedDict
import ckan.plugins as p
from ckan import logic

log = logging.getLogger(__name__)


def is_id(id_string):
    '''Tells the client if the string looks like a revision id or not'''
    reg_ex = '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(reg_ex, id_string))


def hash_a_dict(dict_):
    return json.dumps(dict_, sort_keys=True)


def process_package_(package_id):
    from ckan import model

    # Using default CKAN schema instead of DGU, because we will write it back
    # in the same way in a moment. However it changes formats to lowercase.
    context_ = {'model': model, 'ignore_auth': True, 'session': model.Session,
                #'schema': logic.schema.default_show_package_schema()
                }
    package = p.toolkit.get_action('package_show')(context_, {'id': package_id})
    package_changed = None

    # process each resource
    for resource in package.get('individual_resources', []) + \
            package.get('timeseries_resources', []) + \
            package.get('additional_resources', []):
        log.info('Processing package=%s resource=%s',
                 package['name'], resource['id'][:4])
        resource_hash_before = hash_a_dict(resource)
        process_resource(resource)
        # note if it made a change
        if not package_changed:
            resource_changed = hash_a_dict(resource) != resource_hash_before
            log.info('Resource change: %s %s', resource_changed, resource['url'])
            if resource_changed:
                package_changed = True

    if package_changed:
        log.info('Writing dataset changes')
        tidy_up_package(package)
        # use default schema so that format can be missing
        user = p.toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
        context = {'model': model,
                   'session': model.Session,
                   'ignore_auth': True,
                   'user': user['name'],
                   #'schema': logic.schema.default_update_package_schema()
                   }
        p.toolkit.get_action('package_update')(context, package)
    else:
        log.info('No changes to write')


def process_resource(resource):
    '''
    Edits resource in-place.
    '''
    #log = process_resource.get_logger()
    #load_config(ckan_ini_filepath)
    #register_translator()

    url = resource['url']

    # Check if the service is a view service
    is_wms = _is_wms(url)
    if is_wms:
        #resource['verified'] = True
        #resource['verified_date'] = datetime.now().isoformat()
        base_urls = _wms_base_urls(url)
        resource['wms_base_urls'] = ' '.join(base_urls)
        resource['format'] = 'WMS'


def _is_wms(url):
    '''Given a WMS URL this method returns whether it thinks it is a WMS
    server or not. It does it by making basic WMS requests.
    '''
    # Try WMS 1.3 as that is what INSPIRE expects
    is_wms = _try_wms_url(url, version='1.3')
    # is_wms None means socket timeout, so don't bother trying again
    if is_wms is False:
        # Try using WMS 1.1.1 as that is very common
        is_wms = _try_wms_url(url, version='1.1.1')
    log.debug('WMS check result: %s', is_wms)
    return is_wms


def strip_session_id(url):
    return re.sub(';jsessionid=[^/\?]+', ';jsessionid=', url)


def get_wms_base_url(url):
    return strip_session_id(url.split('?')[0])


# Like owslib_wms.WMSCapabilitiesReader(version=version).capabilities_url only:
# * it deals with uppercase param keys too!
# * version is configurable or can be not included at all
def wms_capabilities_url(url, version=None):
    '''Given what is assumed to be a WMS base URL, adds any missing parameters
    to cajole it to work ('service' & 'request'). The 'version' parameter is
    man-handled to be what you specify or removed if necessary.
    '''
    if url.find('?') != -1:
        param_list = urlparse.parse_qsl(url.split('?')[1])
        params = OrderedDict(param_list)
    else:
        params = OrderedDict()
    params_lower = (param.lower() for param in params)

    if 'service' not in params_lower:
        params['service'] = 'WMS'
    if 'request' not in params_lower:
        params['request'] = 'GetCapabilities'

    if 'version' in params:
        del params['version']
    if 'VERSION' in params:
        del params['VERSION']
    if version:
        params['version'] = version

    urlqs = urllib.urlencode(params)
    return url.split('?')[0] + '?' + urlqs


def _try_wms_url(url, version='1.3'):
    # Here's a neat way to run this manually:
    # python -c "import logging; logging.basicConfig(level=logging.INFO); from ckanext.dgu.gemini_postprocess import _try_wms_url; print _try_wms_url('http://soilbio.nerc.ac.uk/datadiscovery/WebPage5.aspx')"
    '''Does a GetCapabilities request and returns whether it responded ok.

    Returns:
      True - got a WMS response that isn't a ServiceException
      False - got a different response, or got HTTP/WMS error
      None - socket timeout - host is simply not responding, and is so slow communicating there is no point trying it again
    '''

    try:
        capabilities_url = wms_capabilities_url(url, version)
        log.debug('WMS check url: %s', capabilities_url)
        try:
            res = urllib2.urlopen(capabilities_url, None, 10)
            xml = res.read()
        except urllib2.HTTPError, e:
            # e.g. http://aws2.caris.com/sfs/services/ows/download/feature/UKHO_TS_DS
            log.info('WMS check for %s failed due to HTTP error status "%s". Response body: %s', capabilities_url, e, e.read())
            return False
        except urllib2.URLError, e:
            log.info('WMS check for %s failed due to HTTP connection error "%s".', capabilities_url, e)
            return False
        except socket.timeout, e:
            log.info('WMS check for %s failed due to HTTP connection timeout error "%s".', capabilities_url, e)
            return None
        except socket.error, e:
            log.info('WMS check for %s failed due to HTTP socket connection error "%s".', capabilities_url, e)
            return False
        except httplib.HTTPException, e:
            log.info('WMS check for %s failed due to HTTP error "%s".', capabilities_url, e)
            return False
        if not xml.strip():
            log.info('WMS check for %s failed due to empty response')
            return False
        # owslib only supports reading WMS 1.1.1 (as of 10/2014)
        if version == '1.1.1':
            try:
                wms = owslib_wms.WebMapService(url, xml=xml)
            except AttributeError, e:
                # e.g. http://csw.data.gov.uk/geonetwork/srv/en/csw
                log.info('WMS check for %s failed due to GetCapabilities response not containing a required field', url)
                return False
            except etree.XMLSyntaxError, e:
                # e.g. http://www.ordnancesurvey.co.uk/oswebsite/xml/atom/
                log.info('WMS check for %s failed parsing the XML response: %s', url, e)
                return False
            except owslib_wms.ServiceException:
                # e.g. https://gatewaysecurity.ceh.ac.uk/wss/service/LCM2007_GB_25m_Raster/WSS
                log.info('WMS check for %s failed - OGC error message: %s', url, traceback.format_exc())
                return False
            except socket.timeout, e:
                # e.g. http://lichfielddc.maps.arcgis.com/apps/webappviewer/index.html?id=2be0619b59a5418c8c9d785c09504f57
                log.info('WMS check for %s failed due to HTTP connection timeout error "%s".', capabilities_url, e)
                return False
            except socket.error, e:
                log.info('WMS check for %s failed due to HTTP socket connection error "%s".', capabilities_url, e)
                return False
            is_wms = isinstance(wms.contents, dict) and wms.contents != {}
            return is_wms
        else:
            try:
                tree = etree.fromstring(xml)
            except etree.XMLSyntaxError, e:
                # e.g. http://www.ordnancesurvey.co.uk/oswebsite/xml/atom/
                log.info('WMS check for %s failed parsing the XML response: %s', url,  e)
                return False
            if tree.tag != '{http://www.opengis.net/wms}WMS_Capabilities':
                # e.g. https://gatewaysecurity.ceh.ac.uk/wss/service/LCM2007_GB_25m_Raster/WSS
                log.info('WMS check for %s failed as top tag is not wms:WMS_Capabilities, it was %s', url, tree.tag)
                return False
            # check based on https://github.com/geopython/OWSLib/blob/master/owslib/wms.py
            se = tree.find('ServiceException')
            if se:
                log.info('WMS check for %s failed as it contained a ServiceException: %s', url, str(se.text).strip())
                return False
            return True
    except Exception, e:
        log.exception('WMS check for %s failed with uncaught exception: %s' % (url, str(e)))
    return False


def _wms_base_urls(url):
    '''Given a WMS URL this method returns the base URLs it uses (so that they
    can be proxied when previewing it). It does it by making basic WMS
    requests.
    http://redmine.dguteam.org.uk/issues/1322
    '''
    # Here's a neat way to test this manually:
    # python -c "import logging; logging.basicConfig(level=logging.INFO); from ckanext.dgu.gemini_postprocess import _wms_base_urls; print _wms_base_urls('http://environment.data.gov.uk/ds/wms?SERVICE=WMS&INTERFACE=ENVIRONMENT--6f51a299-351f-4e30-a5a3-2511da9688f7&request=GetCapabilities')"
    try:
        capabilities_url = wms_capabilities_url(url, version=None)
        # We don't want a "version" param, because the OS WMS previewer doesn't
        # specify a version, so may receive later versions by default.  And
        # versions like 1.3 may have different base URLs. It does mean that we
        # can't use OWSLIB to parse the result though.
        try:
            log.debug('WMS base url check: %s', capabilities_url)
            res = urllib2.urlopen(capabilities_url, None, 10)
            xml_str = res.read()
        except urllib2.HTTPError, e:
            # e.g. http://aws2.caris.com/sfs/services/ows/download/feature/UKHO_TS_DS
            log.info('WMS check for %s failed due to HTTP error status "%s". Response body: %s', capabilities_url, e, e.read())
            return False, set()
        except urllib2.URLError, e:
            log.info('WMS check for %s failed due to HTTP connection error "%s".', capabilities_url, e)
            return False, set()
        except socket.timeout, e:
            log.info('WMS check for %s failed due to HTTP connection timeout error "%s".', capabilities_url, e)
            return False, set()
        except socket.error, e:
            log.info('WMS check for %s failed due to HTTP connection socket error "%s".', capabilities_url, e)
            return False, set()
        except httplib.HTTPException, e:
            log.info('WMS check for %s failed due to HTTP error "%s".', capabilities_url, e)
            return False
        parser = etree.XMLParser(remove_blank_text=True)
        try:
            xml_tree = etree.fromstring(xml_str, parser=parser)
        except etree.XMLSyntaxError, e:
            # e.g. http://www.ordnancesurvey.co.uk/oswebsite/xml/atom/
            log.info('WMS base urls for %s failed parsing the XML response: %s', url, traceback.format_exc())
            return []
        # check it is a WMS
        if not 'wms' in str(xml_tree).lower():
            log.info('WMS base urls %s failed - XML top tag was not WMS response: %s', url, str(xml_tree))
            return []
        base_urls = set()
        namespaces = {'wms': 'http://www.opengis.net/wms', 'xlink': 'http://www.w3.org/1999/xlink'}
        xpath = '//wms:HTTP//wms:OnlineResource/@xlink:href'
        urls = xml_tree.xpath(xpath, namespaces=namespaces)
        for url in urls:
            if url:
                base_url = get_wms_base_url(url)
                base_urls.add(base_url)
        log.info('Extra WMS base urls: %r', base_urls)
        return base_urls
    except Exception, e:
        log.exception('WMS base url extraction %s failed with uncaught exception: %s' % (url, str(e)))
    return False


def tidy_up_package(package):
    '''Removes bits from the package that shouldn't be written'''
    def del_archiver_and_qa(dict_):
        if 'archiver' in dict_:
            del dict_['archiver']
        if 'qa' in dict_:
            del dict_['qa']
    del_archiver_and_qa(package)
    for resource in package.get('individual_resources', []) + \
            package.get('timeseries_resources', []) + \
            package.get('additional_resources', []):
        del_archiver_and_qa(resource)
